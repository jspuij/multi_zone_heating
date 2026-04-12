"""Pure control logic for multi-zone heating decisions."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import datetime, timedelta

from .models import (
    AggregationMode,
    FlowWarningDecision,
    LocalControlGroup,
    LocalControlGroupEvaluation,
    RelayDecision,
    RelayRuntimeState,
    ZoneConfig,
    ZoneEvaluation,
)


def _available_temperatures(
    sensor_values: Mapping[str, float | None],
    sensor_entity_ids: Sequence[str],
) -> list[tuple[str, float]]:
    """Return usable temperature readings for the configured sensors."""
    available: list[tuple[str, float]] = []
    for entity_id in sensor_entity_ids:
        temperature = sensor_values.get(entity_id)
        if temperature is not None:
            available.append((entity_id, temperature))
    return available


def aggregate_temperature(
    sensor_values: Mapping[str, float | None],
    sensor_entity_ids: Sequence[str],
    aggregation_mode: AggregationMode,
    primary_sensor_entity_id: str | None = None,
) -> float | None:
    """Aggregate configured sensor values into one effective temperature."""
    if aggregation_mode is AggregationMode.PRIMARY:
        if primary_sensor_entity_id is None:
            return None
        return sensor_values.get(primary_sensor_entity_id)

    available = _available_temperatures(sensor_values, sensor_entity_ids)
    if not available:
        return None

    values = [temperature for _, temperature in available]
    if aggregation_mode is AggregationMode.MINIMUM:
        return min(values)

    return sum(values) / len(values)


def resolve_frost_protection_minimum(
    zone_frost_protection_min_temp: float | None,
    global_frost_protection_min_temp: float | None,
) -> float | None:
    """Return the applicable frost protection minimum for a zone."""
    if zone_frost_protection_min_temp is not None:
        return zone_frost_protection_min_temp
    return global_frost_protection_min_temp


def resolve_effective_target_temperature(
    zone_target_temperature: float | None,
    *,
    zone_frost_protection_min_temp: float | None = None,
    global_frost_protection_min_temp: float | None = None,
) -> float | None:
    """Resolve frost rules into one effective target."""
    if zone_target_temperature is None:
        return None

    frost_minimum = resolve_frost_protection_minimum(
        zone_frost_protection_min_temp,
        global_frost_protection_min_temp,
    )
    if frost_minimum is None:
        return zone_target_temperature

    return max(zone_target_temperature, frost_minimum)


def evaluate_hysteresis_demand(
    current_temperature: float | None,
    target_temperature: float | None,
    *,
    previous_demand: bool,
    hysteresis: float,
) -> bool:
    """Evaluate demand with symmetric hysteresis and state retention."""
    if current_temperature is None or target_temperature is None:
        return False

    if current_temperature < target_temperature - hysteresis:
        return True

    if current_temperature >= target_temperature:
        return False

    return previous_demand


def evaluate_local_control_group(
    group: LocalControlGroup,
    sensor_values: Mapping[str, float | None],
    *,
    zone_target_temperature: float | None,
    available_actuator_entity_ids: Collection[str] | None = None,
    previous_demand: bool,
    hysteresis: float,
    zone_frost_protection_min_temp: float | None = None,
    global_frost_protection_min_temp: float | None = None,
) -> LocalControlGroupEvaluation:
    """Evaluate the demand state for one local control group."""
    available_actuators = [
        entity_id
        for entity_id in group.actuator_entity_ids
        if available_actuator_entity_ids is None or entity_id in available_actuator_entity_ids
    ]
    current_temperature = aggregate_temperature(
        sensor_values,
        group.sensor_entity_ids,
        group.aggregation_mode,
        group.primary_sensor_entity_id,
    )
    effective_target_temperature = resolve_effective_target_temperature(
        zone_target_temperature,
        zone_frost_protection_min_temp=zone_frost_protection_min_temp,
        global_frost_protection_min_temp=global_frost_protection_min_temp,
    )
    demand = evaluate_hysteresis_demand(
        current_temperature,
        effective_target_temperature,
        previous_demand=previous_demand,
        hysteresis=hysteresis,
    ) and bool(available_actuators)
    return LocalControlGroupEvaluation(
        name=group.name,
        control_type=group.control_type,
        current_temperature=current_temperature,
        target_temperature=zone_target_temperature,
        effective_target_temperature=effective_target_temperature,
        demand=demand,
        available_sensor_entity_ids=[
            entity_id
            for entity_id, _ in _available_temperatures(sensor_values, group.sensor_entity_ids)
        ],
        available_actuator_entity_ids=available_actuators,
    )


def evaluate_zone(
    zone: ZoneConfig,
    sensor_values: Mapping[str, float | None],
    *,
    zone_target_temperature: float | None,
    available_actuator_entity_ids: Collection[str] | None = None,
    previous_demand: bool,
    previous_group_demands: Mapping[str, bool] | None = None,
    hysteresis: float,
    global_frost_protection_min_temp: float | None = None,
) -> ZoneEvaluation:
    """Evaluate the demand state for a zone."""
    effective_target_temperature = resolve_effective_target_temperature(
        zone_target_temperature,
        zone_frost_protection_min_temp=zone.frost_protection_min_temp,
        global_frost_protection_min_temp=global_frost_protection_min_temp,
    )

    if not zone.enabled:
        return ZoneEvaluation(
            name=zone.name,
            control_type=zone.control_type,
            current_temperature=None,
            target_temperature=zone_target_temperature,
            effective_target_temperature=effective_target_temperature,
            demand=False,
        )

    if zone.local_groups:
        group_demands = previous_group_demands or {}
        local_groups = [
            evaluate_local_control_group(
                group,
                sensor_values,
                zone_target_temperature=zone_target_temperature,
                available_actuator_entity_ids=available_actuator_entity_ids,
                previous_demand=group_demands.get(group.name, False),
                hysteresis=hysteresis,
                zone_frost_protection_min_temp=zone.frost_protection_min_temp,
                global_frost_protection_min_temp=global_frost_protection_min_temp,
            )
            for group in zone.local_groups
        ]
        return ZoneEvaluation(
            name=zone.name,
            control_type=zone.control_type,
            current_temperature=None,
            target_temperature=zone_target_temperature,
            effective_target_temperature=effective_target_temperature,
            demand=any(group.demand for group in local_groups),
            local_groups=local_groups,
        )

    current_temperature = aggregate_temperature(
        sensor_values,
        zone.sensor_entity_ids,
        zone.aggregation_mode,
        zone.primary_sensor_entity_id,
    )
    demand = evaluate_hysteresis_demand(
        current_temperature,
        effective_target_temperature,
        previous_demand=previous_demand,
        hysteresis=hysteresis,
    ) and any(
        available_actuator_entity_ids is None or entity_id in available_actuator_entity_ids
        for entity_id in zone.climate_entity_ids
    )
    return ZoneEvaluation(
        name=zone.name,
        control_type=zone.control_type,
        current_temperature=current_temperature,
        target_temperature=zone_target_temperature,
        effective_target_temperature=effective_target_temperature,
        demand=demand,
        available_sensor_entity_ids=[
            entity_id
            for entity_id, _ in _available_temperatures(sensor_values, zone.sensor_entity_ids)
        ],
        available_actuator_entity_ids=[
            entity_id
            for entity_id in zone.climate_entity_ids
            if available_actuator_entity_ids is None or entity_id in available_actuator_entity_ids
        ],
    )


def aggregate_system_demand(zone_evaluations: Sequence[ZoneEvaluation]) -> bool:
    """Return whether any zone currently requires heat."""
    return any(zone.demand for zone in zone_evaluations)


def flow_threshold_reached(flow_value: float | None, flow_detection_threshold: float | None) -> bool:
    """Return whether measured flow exceeds the configured threshold."""
    if flow_value is None or flow_detection_threshold is None:
        return False
    return flow_value >= flow_detection_threshold


def evaluate_missing_flow_warning(
    *,
    system_demand: bool,
    relay_state: RelayRuntimeState,
    now: datetime,
    flow_value: float | None = None,
    flow_detection_threshold: float | None = None,
    missing_flow_timeout_seconds: int | None = None,
) -> FlowWarningDecision:
    """Raise a warning only when heat demand persists without detected flow."""
    if (
        not system_demand
        or not relay_state.is_on
        or flow_detection_threshold is None
        or missing_flow_timeout_seconds is None
    ):
        return FlowWarningDecision(warning_active=False)

    if flow_threshold_reached(flow_value, flow_detection_threshold):
        return FlowWarningDecision(warning_active=False)

    warning_at = (relay_state.last_on_at or now) + timedelta(seconds=missing_flow_timeout_seconds)
    if now < warning_at:
        return FlowWarningDecision(
            warning_active=False,
            next_recheck_at=warning_at,
        )

    return FlowWarningDecision(
        warning_active=True,
        warning_since=warning_at,
    )


def decide_relay_action(
    *,
    system_demand: bool,
    relay_state: RelayRuntimeState,
    now: datetime,
    min_relay_on_time_seconds: int | None = None,
    min_relay_off_time_seconds: int | None = None,
    relay_off_delay_seconds: int | None = None,
    flow_value: float | None = None,
    flow_detection_threshold: float | None = None,
) -> RelayDecision:
    """Apply timing and flow guards to the main relay decision."""
    min_on = timedelta(seconds=min_relay_on_time_seconds or 0)
    min_off = timedelta(seconds=min_relay_off_time_seconds or 0)
    off_delay = timedelta(seconds=relay_off_delay_seconds or 0)

    if system_demand:
        if relay_state.is_on:
            return RelayDecision(
                desired_on=True,
                resulting_state=True,
                off_requested_at=None,
            )

        if relay_state.last_off_at is not None:
            ready_at = relay_state.last_off_at + min_off
            if now < ready_at:
                return RelayDecision(
                    desired_on=True,
                    resulting_state=False,
                    next_recheck_at=ready_at,
                    hold_reason="minimum_off_time",
                )

        return RelayDecision(
            desired_on=True,
            resulting_state=True,
            should_turn_on=True,
        )

    if not relay_state.is_on:
        return RelayDecision(
            desired_on=False,
            resulting_state=False,
        )

    off_requested_at = relay_state.off_requested_at or now
    gating_reasons: list[tuple[datetime, str]] = []
    if relay_state.last_on_at is not None and min_on > timedelta():
        gating_reasons.append((relay_state.last_on_at + min_on, "minimum_on_time"))
    if off_delay > timedelta():
        gating_reasons.append((off_requested_at + off_delay, "off_delay"))

    if gating_reasons:
        ready_at, hold_reason = max(gating_reasons, key=lambda item: item[0])
        if now < ready_at:
            return RelayDecision(
                desired_on=False,
                resulting_state=True,
                off_requested_at=off_requested_at,
                next_recheck_at=ready_at,
                hold_reason=hold_reason,
            )

    if flow_threshold_reached(flow_value, flow_detection_threshold):
        return RelayDecision(
            desired_on=False,
            resulting_state=True,
            off_requested_at=off_requested_at,
            hold_reason="flow_still_detected",
        )

    return RelayDecision(
        desired_on=False,
        resulting_state=False,
        should_turn_off=True,
        off_requested_at=off_requested_at,
    )
