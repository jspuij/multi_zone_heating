"""Runtime coordinator for multi_zone_heating."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    DOMAIN as CLIMATE_DOMAIN,
    HVACMode,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time, async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .control_logic import (
    aggregate_system_demand,
    decide_relay_action,
    evaluate_missing_flow_warning,
    evaluate_zone,
    flow_threshold_reached,
)
from .models import (
    AggregationMode,
    ControlType,
    GlobalOverride,
    IntegrationConfig,
    LocalControlGroup,
    NumberSemanticType,
    RelayDecision,
    RelayRuntimeState,
    RuntimeSnapshot,
    ZoneConfig,
    ZoneEvaluation,
)

_LOGGER = logging.getLogger(__name__)


def integration_config_from_dict(data: Mapping[str, Any]) -> IntegrationConfig:
    """Build the typed integration config from config-entry data."""
    return IntegrationConfig(
        main_relay_entity_id=data.get("main_relay_entity_id"),
        flow_sensor_entity_id=data.get("flow_sensor_entity_id"),
        flow_detection_threshold=_as_float(data.get("flow_detection_threshold")),
        missing_flow_timeout_seconds=_as_int(data.get("missing_flow_timeout_seconds")),
        zones=[_zone_from_dict(zone_data) for zone_data in data.get("zones", [])],
        default_hysteresis=float(data.get("default_hysteresis", 0.3)),
        min_relay_on_time_seconds=_as_int(data.get("min_relay_on_time_seconds")),
        min_relay_off_time_seconds=_as_int(data.get("min_relay_off_time_seconds")),
        relay_off_delay_seconds=_as_int(data.get("relay_off_delay_seconds")),
        frost_protection_min_temp=_as_float(data.get("frost_protection_min_temp")),
        failsafe_mode=data.get("failsafe_mode"),
    )


def _zone_from_dict(data: Mapping[str, Any]) -> ZoneConfig:
    """Build a typed zone config from config-entry data."""
    return ZoneConfig(
        name=str(data["name"]),
        control_type=ControlType(data["control_type"]),
        target_temperature=_as_float(data.get("target_temperature")) or 20.0,
        sensor_entity_ids=list(data.get("sensor_entity_ids", [])),
        climate_entity_ids=list(data.get("climate_entity_ids", [])),
        climate_off_fallback_temperature=_as_float(
            data.get("climate_off_fallback_temperature")
        ),
        local_groups=[_group_from_dict(group_data) for group_data in data.get("local_groups", [])],
        aggregation_mode=AggregationMode(data.get("aggregation_mode", "average")),
        primary_sensor_entity_id=data.get("primary_sensor_entity_id"),
        enabled=bool(data.get("enabled", True)),
        frost_protection_min_temp=_as_float(data.get("frost_protection_min_temp")),
    )


def _group_from_dict(data: Mapping[str, Any]) -> LocalControlGroup:
    """Build a typed local control group from config-entry data."""
    number_semantic_type = data.get("number_semantic_type")
    return LocalControlGroup(
        name=str(data["name"]),
        control_type=ControlType(data["control_type"]),
        actuator_entity_ids=list(data.get("actuator_entity_ids", [])),
        sensor_entity_ids=list(data.get("sensor_entity_ids", [])),
        aggregation_mode=AggregationMode(data.get("aggregation_mode", "average")),
        primary_sensor_entity_id=data.get("primary_sensor_entity_id"),
        number_semantic_type=(
            NumberSemanticType(number_semantic_type) if number_semantic_type is not None else None
        ),
        active_value=_as_float(data.get("active_value")),
        inactive_value=_as_float(data.get("inactive_value")),
    )


def _as_float(value: Any) -> float | None:
    """Convert a value into a float when possible."""
    if value is None:
        return None
    return float(value)


def _as_int(value: Any) -> int | None:
    """Convert a value into an int when possible."""
    if value is None:
        return None
    return int(value)


class MultiZoneHeatingCoordinator(DataUpdateCoordinator[RuntimeSnapshot]):
    """Observe runtime state, evaluate demand, and dispatch commands."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: IntegrationConfig,
        *,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        try:
            super().__init__(
                hass,
                _LOGGER,
                name="multi_zone_heating",
                config_entry=config_entry,
            )
        except TypeError:
            super().__init__(
                hass,
                _LOGGER,
                name="multi_zone_heating",
            )
            self.config_entry = config_entry
        self.config = config
        self._unsub_state_changes: CALLBACK_TYPE | None = None
        self._unsub_recheck: CALLBACK_TYPE | None = None
        self._last_zone_demands: dict[str, bool] = {}
        self._last_group_demands: dict[str, dict[str, bool]] = {}
        self._last_commanded_switch_states: dict[str, bool] = {}
        self._last_commanded_number_values: dict[str, float] = {}
        self._last_commanded_climate_targets: dict[str, float] = {}
        self._last_commanded_climate_hvac_modes: dict[str, HVACMode] = {}
        self._relay_runtime_state = RelayRuntimeState(is_on=False)
        self._global_override: GlobalOverride | None = None
        self._global_force_off = False

    async def async_start(self) -> None:
        """Subscribe to state changes and run the initial evaluation."""
        relevant_entity_ids = list(_iter_relevant_entity_ids(self.config))
        if relevant_entity_ids:
            self._unsub_state_changes = async_track_state_change_event(
                self.hass,
                relevant_entity_ids,
                self._async_handle_relevant_state_change,
            )

        if self.config_entry is None:
            await self.async_refresh()
            return

        await self.async_config_entry_first_refresh()

    async def async_stop(self) -> None:
        """Stop subscriptions and pending rechecks."""
        if self._unsub_state_changes is not None:
            self._unsub_state_changes()
            self._unsub_state_changes = None

        self._cancel_recheck()

    @callback
    def _async_handle_relevant_state_change(self, _event: Any) -> None:
        """Reevaluate the system when a relevant entity changes."""
        self.hass.async_create_task(self.async_request_refresh())

    async def async_set_zone_enabled(self, zone_name: str, enabled: bool) -> None:
        """Enable or disable one configured zone."""
        zone = self.get_zone_config(zone_name)
        if zone is None or zone.enabled == enabled:
            return

        zone.enabled = enabled
        self._persist_zone_enabled(zone_name, enabled)
        await self.async_refresh()

    async def async_set_global_force_off(self, enabled: bool) -> None:
        """Enable or disable global force-off."""
        if self._global_force_off == enabled:
            return

        self._global_force_off = enabled
        await self.async_refresh()

    async def async_set_global_override(self, target_temperature: float) -> None:
        """Set the system-wide override temperature."""
        if self._global_override is None:
            self._global_override = GlobalOverride(target_temperature=target_temperature)
        else:
            self._global_override.target_temperature = target_temperature
            self._global_override.active = True
        await self.async_refresh()

    async def async_clear_global_override(self) -> None:
        """Remove the system-wide override temperature."""
        if self._global_override is None:
            return

        self._global_override.active = False
        await self.async_refresh()

    def get_zone_config(self, zone_name: str) -> ZoneConfig | None:
        """Return one configured zone by name."""
        for zone in self.config.zones:
            if zone.name == zone_name:
                return zone
        return None

    async def _async_update_data(self) -> RuntimeSnapshot:
        """Build a snapshot, evaluate demand, and dispatch required commands."""
        now = self._utcnow()
        snapshot = self._build_runtime_snapshot()
        snapshot.global_override = self._global_override
        snapshot.global_force_off = self._global_force_off
        flow_value = snapshot.flow_value

        previous_relay_is_on = self._relay_runtime_state.is_on
        current_relay_is_on = self._read_toggle_state(self.config.main_relay_entity_id)
        pending_relay_command = self._last_commanded_switch_states.get(
            self.config.main_relay_entity_id or ""
        )
        # Ignore stale HA state while a relay command is still in flight so we
        # do not flip runtime state back and resend the same command.
        if current_relay_is_on is not None and not (
            pending_relay_command is not None and current_relay_is_on != pending_relay_command
        ):
            self._relay_runtime_state.is_on = current_relay_is_on
            if current_relay_is_on != previous_relay_is_on:
                if current_relay_is_on:
                    self._relay_runtime_state.last_on_at = now
                    self._relay_runtime_state.off_requested_at = None
                else:
                    self._relay_runtime_state.last_off_at = now
                    self._relay_runtime_state.off_requested_at = None
            if pending_relay_command == current_relay_is_on:
                self._last_commanded_switch_states.pop(
                    self.config.main_relay_entity_id or "",
                    None,
                )

        zone_evaluations = []
        for zone in self.config.zones:
            evaluation = evaluate_zone(
                zone,
                snapshot.sensor_values,
                zone_target_temperature=snapshot.target_temperatures.get(zone.name),
                available_actuator_entity_ids=snapshot.actuator_available_entity_ids,
                previous_demand=self._last_zone_demands.get(zone.name, False),
                previous_group_demands=self._last_group_demands.get(zone.name),
                hysteresis=self.config.default_hysteresis,
                global_override=self._global_override,
                global_frost_protection_min_temp=self.config.frost_protection_min_temp,
            )
            zone_evaluations.append(evaluation)
            self._last_zone_demands[zone.name] = evaluation.demand
            if evaluation.local_groups:
                self._last_group_demands[zone.name] = {
                    group.name: group.demand for group in evaluation.local_groups
                }

        snapshot.zone_evaluations = zone_evaluations
        snapshot.system_demand = aggregate_system_demand(zone_evaluations)
        effective_system_demand = snapshot.system_demand and not self._global_force_off
        snapshot.relay_decision = decide_relay_action(
            system_demand=effective_system_demand,
            relay_state=self._relay_runtime_state,
            now=now,
            min_relay_on_time_seconds=self.config.min_relay_on_time_seconds,
            min_relay_off_time_seconds=self.config.min_relay_off_time_seconds,
            relay_off_delay_seconds=self.config.relay_off_delay_seconds,
            flow_value=flow_value,
            flow_detection_threshold=self.config.flow_detection_threshold,
        )
        projected_relay_state = _project_relay_runtime_state(
            self._relay_runtime_state,
            snapshot.relay_decision,
            now,
        )
        snapshot.relay_runtime_state = RelayRuntimeState(
            is_on=projected_relay_state.is_on,
            last_on_at=projected_relay_state.last_on_at,
            last_off_at=projected_relay_state.last_off_at,
            off_requested_at=projected_relay_state.off_requested_at,
        )
        flow_warning = evaluate_missing_flow_warning(
            system_demand=effective_system_demand,
            relay_state=projected_relay_state,
            now=now,
            flow_value=flow_value,
            flow_detection_threshold=self.config.flow_detection_threshold,
            missing_flow_timeout_seconds=self.config.missing_flow_timeout_seconds,
        )
        snapshot.missing_flow_warning = flow_warning.warning_active
        snapshot.missing_flow_warning_since = flow_warning.warning_since

        await self._async_dispatch_zone_commands(
            zone_evaluations,
            force_off=self._global_force_off,
        )
        await self._async_dispatch_relay_command(snapshot.relay_decision, now)
        self._schedule_recheck(
            _earliest_datetime(
                snapshot.relay_decision.next_recheck_at if snapshot.relay_decision else None,
                flow_warning.next_recheck_at,
            )
        )
        return snapshot

    def _build_runtime_snapshot(self) -> RuntimeSnapshot:
        """Collect all relevant Home Assistant state into one snapshot."""
        snapshot = RuntimeSnapshot()
        unavailable_entity_ids: set[str] = set()
        actuator_available_entity_ids: set[str] = set()

        for zone in self.config.zones:
            snapshot.target_temperatures[zone.name] = self._read_target_temperature(zone)

            for sensor_entity_id in zone.sensor_entity_ids:
                sensor_value = self._read_numeric_state(sensor_entity_id)
                snapshot.sensor_values[sensor_entity_id] = sensor_value
                if sensor_value is None:
                    unavailable_entity_ids.add(sensor_entity_id)

            for climate_entity_id in zone.climate_entity_ids:
                if self._entity_is_available(climate_entity_id):
                    actuator_available_entity_ids.add(climate_entity_id)
                else:
                    unavailable_entity_ids.add(climate_entity_id)

            for group in zone.local_groups:
                for sensor_entity_id in group.sensor_entity_ids:
                    sensor_value = self._read_numeric_state(sensor_entity_id)
                    snapshot.sensor_values[sensor_entity_id] = sensor_value
                    if sensor_value is None:
                        unavailable_entity_ids.add(sensor_entity_id)

                for actuator_entity_id in group.actuator_entity_ids:
                    if self._entity_is_available(actuator_entity_id):
                        actuator_available_entity_ids.add(actuator_entity_id)
                    else:
                        unavailable_entity_ids.add(actuator_entity_id)

        if self.config.main_relay_entity_id:
            if self._entity_is_available(self.config.main_relay_entity_id):
                actuator_available_entity_ids.add(self.config.main_relay_entity_id)
            else:
                unavailable_entity_ids.add(self.config.main_relay_entity_id)

        if self.config.flow_sensor_entity_id:
            flow_value = self._read_numeric_state(self.config.flow_sensor_entity_id)
            snapshot.flow_value = flow_value
            snapshot.flow_detected = flow_threshold_reached(
                flow_value,
                self.config.flow_detection_threshold,
            )
            snapshot.sensor_values[self.config.flow_sensor_entity_id] = flow_value
            if flow_value is None:
                unavailable_entity_ids.add(self.config.flow_sensor_entity_id)

        snapshot.actuator_available_entity_ids = sorted(actuator_available_entity_ids)
        snapshot.unavailable_entity_ids = sorted(unavailable_entity_ids)
        return snapshot

    def _persist_zone_enabled(self, zone_name: str, enabled: bool) -> None:
        """Persist the zone-enabled flag into the config entry data."""
        if self.config_entry is None:
            return

        zones = []
        for zone_data in self.config_entry.data.get("zones", []):
            updated_zone_data = dict(zone_data)
            if updated_zone_data.get("name") == zone_name:
                updated_zone_data["enabled"] = enabled
            zones.append(updated_zone_data)

        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                "zones": zones,
            },
        )

    async def _async_dispatch_zone_commands(
        self,
        zone_evaluations: list[ZoneEvaluation],
        *,
        force_off: bool,
    ) -> None:
        """Send zone-level actuator commands when outputs should change."""
        for zone, evaluation in zip(self.config.zones, zone_evaluations, strict=True):
            if zone.control_type is ControlType.CLIMATE:
                await self._async_dispatch_climate_zone(zone, evaluation, force_off=force_off)
                continue

            if force_off or not zone.enabled:
                for group_config in zone.local_groups:
                    if group_config.control_type is ControlType.SWITCH:
                        await self._async_dispatch_switch_group(group_config, False)
                    elif group_config.control_type is ControlType.NUMBER:
                        await self._async_dispatch_number_group(group_config, False)
                continue

            for group_config, group_evaluation in zip(
                zone.local_groups,
                evaluation.local_groups,
                strict=True,
            ):
                if group_config.control_type is ControlType.SWITCH:
                    await self._async_dispatch_switch_group(
                        group_config,
                        group_evaluation.demand,
                    )
                elif group_config.control_type is ControlType.NUMBER:
                    await self._async_dispatch_number_group(
                        group_config,
                        group_evaluation.demand,
                    )

    async def _async_dispatch_climate_zone(
        self,
        zone: ZoneConfig,
        evaluation: ZoneEvaluation,
        *,
        force_off: bool,
    ) -> None:
        """Synchronize climate actuators with the effective target temperature."""
        for entity_id in zone.climate_entity_ids:
            if not self._entity_is_available(entity_id):
                continue

            state = self.hass.states.get(entity_id)
            if state is None:
                continue

            current_hvac_mode = self._read_climate_hvac_mode(entity_id)
            if current_hvac_mode is not None:
                self._clear_climate_hvac_mode_if_synced(entity_id, current_hvac_mode)

            hvac_modes = self._read_supported_hvac_modes(entity_id)
            if evaluation.demand and not force_off:
                if HVACMode.HEAT in hvac_modes and current_hvac_mode == HVACMode.OFF:
                    await self._async_dispatch_climate_hvac_mode(entity_id, HVACMode.HEAT)

                target_temperature = evaluation.effective_target_temperature
                if target_temperature is None:
                    continue

                current_target = _as_float(state.attributes.get("temperature"))
                if current_target is not None and math.isclose(
                    current_target, target_temperature, abs_tol=0.01
                ):
                    self._last_commanded_climate_targets.pop(entity_id, None)
                    continue

                last_target = self._last_commanded_climate_targets.get(entity_id)
                if last_target is not None and math.isclose(
                    last_target, target_temperature, abs_tol=0.01
                ):
                    continue

                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {
                        ATTR_ENTITY_ID: entity_id,
                        "temperature": target_temperature,
                    },
                    blocking=True,
                )
                self._last_commanded_climate_targets[entity_id] = target_temperature
                continue

            self._last_commanded_climate_targets.pop(entity_id, None)
            if HVACMode.OFF in hvac_modes:
                await self._async_dispatch_climate_hvac_mode(entity_id, HVACMode.OFF)
                continue

            fallback_temperature = zone.climate_off_fallback_temperature
            if fallback_temperature is None:
                continue

            current_target = _as_float(state.attributes.get("temperature"))
            if current_target is not None and math.isclose(
                current_target, fallback_temperature, abs_tol=0.01
            ):
                continue

            last_target = self._last_commanded_climate_targets.get(entity_id)
            if last_target is not None and math.isclose(
                last_target, fallback_temperature, abs_tol=0.01
            ):
                continue

            await self.hass.services.async_call(
                CLIMATE_DOMAIN,
                SERVICE_SET_TEMPERATURE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    "temperature": fallback_temperature,
                },
                blocking=True,
            )
            self._last_commanded_climate_targets[entity_id] = fallback_temperature

    async def _async_dispatch_switch_group(self, group: LocalControlGroup, demand: bool) -> None:
        """Turn switch actuators on or off for one local group."""
        for entity_id in group.actuator_entity_ids:
            await self._async_dispatch_toggle_entity(entity_id, demand)

    async def _async_dispatch_number_group(self, group: LocalControlGroup, demand: bool) -> None:
        """Write active or inactive values for number-based actuators."""
        desired_value = group.active_value if demand else group.inactive_value
        if desired_value is None:
            return

        for entity_id in group.actuator_entity_ids:
            if not self._entity_is_available(entity_id):
                continue

            current_value = self._read_numeric_state(entity_id)
            if current_value is not None and math.isclose(current_value, desired_value, abs_tol=0.01):
                self._last_commanded_number_values.pop(entity_id, None)
                continue

            last_value = self._last_commanded_number_values.get(entity_id)
            if last_value is not None and math.isclose(last_value, desired_value, abs_tol=0.01):
                continue

            await self.hass.services.async_call(
                entity_id.split(".", 1)[0],
                SERVICE_SET_VALUE,
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_VALUE: desired_value,
                },
                blocking=True,
            )
            self._last_commanded_number_values[entity_id] = desired_value

    async def _async_dispatch_relay_command(
        self,
        relay_decision: RelayDecision | None,
        now: datetime,
    ) -> None:
        """Apply the main relay decision when a state transition is required."""
        if self.config.main_relay_entity_id is None or relay_decision is None:
            return

        if relay_decision.should_turn_on:
            await self._async_dispatch_toggle_entity(self.config.main_relay_entity_id, True)
            self._relay_runtime_state.is_on = True
            self._relay_runtime_state.last_on_at = now
            self._relay_runtime_state.off_requested_at = None
            return

        if relay_decision.should_turn_off:
            await self._async_dispatch_toggle_entity(self.config.main_relay_entity_id, False)
            self._relay_runtime_state.is_on = False
            self._relay_runtime_state.last_off_at = now
            self._relay_runtime_state.off_requested_at = None
            return

        self._relay_runtime_state.off_requested_at = relay_decision.off_requested_at

    async def _async_dispatch_toggle_entity(self, entity_id: str, desired_on: bool) -> None:
        """Turn an on/off entity on or off only when required."""
        if not self._entity_is_available(entity_id):
            return

        current_state = self._read_toggle_state(entity_id)
        if current_state is desired_on:
            self._last_commanded_switch_states.pop(entity_id, None)
            return

        last_commanded = self._last_commanded_switch_states.get(entity_id)
        if last_commanded is desired_on:
            return

        await self.hass.services.async_call(
            entity_id.split(".", 1)[0],
            SERVICE_TURN_ON if desired_on else SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        self._last_commanded_switch_states[entity_id] = desired_on

    async def _async_dispatch_climate_hvac_mode(
        self,
        entity_id: str,
        desired_hvac_mode: HVACMode,
    ) -> None:
        """Set a climate entity HVAC mode only when required."""
        current_hvac_mode = self._read_climate_hvac_mode(entity_id)
        if current_hvac_mode == desired_hvac_mode:
            self._last_commanded_climate_hvac_modes.pop(entity_id, None)
            return

        last_commanded = self._last_commanded_climate_hvac_modes.get(entity_id)
        if last_commanded == desired_hvac_mode:
            return

        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: entity_id,
                ATTR_HVAC_MODE: desired_hvac_mode,
            },
            blocking=True,
        )
        self._last_commanded_climate_hvac_modes[entity_id] = desired_hvac_mode

    def _clear_climate_hvac_mode_if_synced(
        self,
        entity_id: str,
        current_hvac_mode: HVACMode,
    ) -> None:
        """Clear a pending climate HVAC-mode command once HA reflects it."""
        if self._last_commanded_climate_hvac_modes.get(entity_id) == current_hvac_mode:
            self._last_commanded_climate_hvac_modes.pop(entity_id, None)

    def _read_target_temperature(self, zone: ZoneConfig) -> float | None:
        """Read the configured integration-owned zone target."""
        return zone.target_temperature

    def _read_numeric_state(self, entity_id: str | None) -> float | None:
        """Read a numeric state from Home Assistant."""
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None

        return _as_float(state.state)

    def _read_climate_hvac_mode(self, entity_id: str | None) -> HVACMode | None:
        """Read the current HVAC mode from Home Assistant."""
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None

        try:
            return HVACMode(state.state)
        except ValueError:
            return None

    def _read_supported_hvac_modes(self, entity_id: str | None) -> set[HVACMode]:
        """Read the supported HVAC modes from a climate entity state."""
        if entity_id is None:
            return set()

        state = self.hass.states.get(entity_id)
        if state is None:
            return set()

        supported_modes: set[HVACMode] = set()
        for mode in state.attributes.get(ATTR_HVAC_MODES) or []:
            try:
                supported_modes.add(HVACMode(mode))
            except ValueError:
                continue

        return supported_modes

    def _read_toggle_state(self, entity_id: str | None) -> bool | None:
        """Read an on/off state from Home Assistant."""
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            return None

        return state.state == STATE_ON

    def _entity_is_available(self, entity_id: str | None) -> bool:
        """Return whether an entity currently has a usable state."""
        if entity_id is None:
            return False

        state = self.hass.states.get(entity_id)
        return state is not None and state.state not in {STATE_UNKNOWN, STATE_UNAVAILABLE}

    def _schedule_recheck(self, when: datetime | None) -> None:
        """Schedule the next relay timing reevaluation."""
        self._cancel_recheck()
        if when is None:
            return

        @callback
        def _async_trigger_recheck(_now: datetime) -> None:
            self._unsub_recheck = None
            self.hass.async_create_task(self.async_request_refresh())

        self._unsub_recheck = async_track_point_in_utc_time(self.hass, _async_trigger_recheck, when)

    def _cancel_recheck(self) -> None:
        """Cancel a pending reevaluation timer."""
        if self._unsub_recheck is not None:
            self._unsub_recheck()
            self._unsub_recheck = None

    def _utcnow(self) -> datetime:
        """Return the current UTC time."""
        now = dt_util.utcnow()
        if now.tzinfo is None:
            return now.replace(tzinfo=UTC)
        return now.astimezone(UTC)


def _iter_relevant_entity_ids(config: IntegrationConfig) -> Iterable[str]:
    """Yield all entities that should trigger a runtime reevaluation."""
    if config.main_relay_entity_id:
        yield config.main_relay_entity_id
    if config.flow_sensor_entity_id:
        yield config.flow_sensor_entity_id

    for zone in config.zones:
        yield from zone.sensor_entity_ids
        yield from zone.climate_entity_ids
        for group in zone.local_groups:
            yield from group.sensor_entity_ids
            yield from group.actuator_entity_ids


def _project_relay_runtime_state(
    relay_state: RelayRuntimeState,
    relay_decision: RelayDecision | None,
    now: datetime,
) -> RelayRuntimeState:
    """Project the relay runtime state after the current decision is applied."""
    projected_state = RelayRuntimeState(
        is_on=relay_state.is_on,
        last_on_at=relay_state.last_on_at,
        last_off_at=relay_state.last_off_at,
        off_requested_at=relay_state.off_requested_at,
    )
    if relay_decision is None:
        return projected_state

    if relay_decision.should_turn_on:
        projected_state.is_on = True
        projected_state.last_on_at = now
        projected_state.off_requested_at = None
        return projected_state

    if relay_decision.should_turn_off:
        projected_state.is_on = False
        projected_state.last_off_at = now
        projected_state.off_requested_at = None
        return projected_state

    projected_state.is_on = relay_decision.resulting_state
    projected_state.off_requested_at = relay_decision.off_requested_at
    return projected_state


def _earliest_datetime(*values: datetime | None) -> datetime | None:
    """Return the earliest non-null recheck time."""
    concrete_values = [value for value in values if value is not None]
    if not concrete_values:
        return None
    return min(concrete_values)
