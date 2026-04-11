"""Climate platform for multi_zone_heating."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MultiZoneHeatingConfigEntry
from .const import DOMAIN
from .models import ControlType


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities for a config entry."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    if coordinator is None:
        return
    async_add_entities(
        [
            MultiZoneHeatingSystemClimate(entry),
            *[
                MultiZoneHeatingZoneClimate(entry, zone.name)
                for zone in runtime_data.config.zones
            ],
        ]
    )


class MultiZoneHeatingClimateBase(CoordinatorEntity, ClimateEntity):
    """Base climate entity backed by the runtime coordinator."""

    _attr_has_entity_name = True
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the climate entity."""
        super().__init__(entry.runtime_data.coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        """Return whether coordinator data is available."""
        return self.coordinator.data is not None

    @property
    def device_info(self) -> dict[str, object]:
        """Describe the integration device that owns these entities."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.title,
        }


class MultiZoneHeatingSystemClimate(MultiZoneHeatingClimateBase):
    """Top-level climate entity for system-wide master commands."""

    def __init__(self, entry: MultiZoneHeatingConfigEntry) -> None:
        """Initialize the climate entity."""
        super().__init__(entry)
        self._attr_name = "System"
        self._attr_unique_id = f"{entry.entry_id}_system_climate"

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the effective HVAC mode."""
        if self.coordinator.data is None:
            return None
        return HVACMode.OFF if self.coordinator.data.global_force_off else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return whether the system is heating right now."""
        data = self.coordinator.data
        if data is None:
            return None
        if data.global_force_off:
            return HVACAction.OFF
        return HVACAction.HEATING if data.system_demand else HVACAction.IDLE

    @property
    def target_temperature(self) -> float | None:
        """Return the shared zone target when the system is aligned."""
        data = self.coordinator.data
        if data is None:
            return None
        targets = {
            evaluation.target_temperature
            for evaluation in data.zone_evaluations
            if evaluation.target_temperature is not None
        }
        if len(targets) != 1:
            return None
        return next(iter(targets))

    @property
    def current_temperature(self) -> float | None:
        """Return the mean visible zone temperature when available."""
        data = self.coordinator.data
        if data is None:
            return None

        temperatures: list[float] = []
        for evaluation in data.zone_evaluations:
            if evaluation.current_temperature is not None:
                temperatures.append(evaluation.current_temperature)
            for group in evaluation.local_groups:
                if group.current_temperature is not None:
                    temperatures.append(group.current_temperature)

        if not temperatures:
            return None
        return sum(temperatures) / len(temperatures)

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature the entity should expose."""
        config_minimums = [5.0]
        if self.coordinator.config.frost_protection_min_temp is not None:
            config_minimums.append(self.coordinator.config.frost_protection_min_temp)
        for zone in self.coordinator.config.zones:
            if zone.frost_protection_min_temp is not None:
                config_minimums.append(zone.frost_protection_min_temp)
        return max(config_minimums)

    @property
    def max_temp(self) -> float:
        """Return the maximum supported target temperature."""
        return 35.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return system summary attributes rooted in zone state."""
        data = self.coordinator.data
        if data is None:
            return {}

        return {
            "zones_calling_for_heat": [
                evaluation.name for evaluation in data.zone_evaluations if evaluation.demand
            ],
            "zone_target_temperatures": {
                evaluation.name: evaluation.target_temperature
                for evaluation in data.zone_evaluations
            },
            "global_force_off": data.global_force_off,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set system HVAC mode."""
        await self.coordinator.async_set_global_force_off(hvac_mode == HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Fan a master target change out to every zone climate."""
        target_temperature = kwargs.get("temperature")
        if target_temperature is None:
            return

        await self.coordinator.async_set_all_zone_target_temperatures(
            float(target_temperature)
        )


class MultiZoneHeatingZoneClimate(MultiZoneHeatingClimateBase):
    """Virtual climate entity that owns one zone target temperature."""

    def __init__(self, entry: MultiZoneHeatingConfigEntry, zone_name: str) -> None:
        """Initialize the zone climate entity."""
        super().__init__(entry)
        self._zone_name = zone_name
        self._attr_name = zone_name
        self._attr_unique_id = f"{entry.entry_id}_{zone_name}_climate"

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return whether the zone is enabled for heating."""
        zone = self.coordinator.get_zone_config(self._zone_name)
        if zone is None:
            return None
        return HVACMode.HEAT if zone.enabled else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return whether the zone is actively demanding heat."""
        evaluation = self.coordinator.get_zone_evaluation(self._zone_name)
        if evaluation is None:
            return None

        zone = self.coordinator.get_zone_config(self._zone_name)
        if zone is None or not zone.enabled:
            return HVACAction.OFF
        return HVACAction.HEATING if evaluation.demand else HVACAction.IDLE

    @property
    def target_temperature(self) -> float | None:
        """Return the owned target temperature for the zone."""
        evaluation = self.coordinator.get_zone_evaluation(self._zone_name)
        if evaluation is not None and evaluation.target_temperature is not None:
            return evaluation.target_temperature

        zone = self.coordinator.get_zone_config(self._zone_name)
        if zone is None:
            return None
        return zone.target_temperature

    @property
    def current_temperature(self) -> float | None:
        """Return the aggregated current temperature for the zone when available."""
        evaluation = self.coordinator.get_zone_evaluation(self._zone_name)
        if evaluation is None:
            return None
        return evaluation.current_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum target temperature the entity should expose."""
        zone = self.coordinator.get_zone_config(self._zone_name)
        if zone is None:
            return 5.0

        minimums = [5.0]
        if self.coordinator.config.frost_protection_min_temp is not None:
            minimums.append(self.coordinator.config.frost_protection_min_temp)
        if zone.frost_protection_min_temp is not None:
            minimums.append(zone.frost_protection_min_temp)
        return max(minimums)

    @property
    def max_temp(self) -> float:
        """Return the maximum supported target temperature."""
        return 35.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes for the virtual zone climate."""
        zone = self.coordinator.get_zone_config(self._zone_name)
        evaluation = self.coordinator.get_zone_evaluation(self._zone_name)
        if zone is None or evaluation is None:
            return {}

        attributes: dict[str, Any] = {
            "zone_name": self._zone_name,
            "control_type": zone.control_type.value,
            "aggregation_mode": zone.aggregation_mode.value,
            "enabled": zone.enabled,
            "demand": evaluation.demand,
        }
        if zone.primary_sensor_entity_id is not None:
            attributes["primary_sensor_entity_id"] = zone.primary_sensor_entity_id
        if zone.control_type is ControlType.CLIMATE:
            attributes["sensor_entity_ids"] = zone.sensor_entity_ids
        return attributes

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Enable or disable the zone from the climate surface."""
        await self.coordinator.async_set_zone_enabled(
            self._zone_name,
            hvac_mode == HVACMode.HEAT,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Persist a new owned target temperature for the zone."""
        target_temperature = kwargs.get("temperature")
        if target_temperature is None:
            return

        await self.coordinator.async_set_zone_target_temperature(
            self._zone_name,
            float(target_temperature),
        )
