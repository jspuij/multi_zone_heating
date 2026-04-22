"""Tests for the pure control logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from custom_components.multi_zone_heating.control_logic import (
    aggregate_system_demand,
    aggregate_temperature,
    decide_relay_action,
    evaluate_hysteresis_demand,
    evaluate_local_control_group,
    evaluate_missing_flow_warning,
    evaluate_zone,
    flow_threshold_reached,
    resolve_effective_target_temperature,
)
from custom_components.multi_zone_heating.models import (
    AggregationMode,
    ControlType,
    LocalControlGroup,
    RelayRuntimeState,
    ZoneConfig,
)


def test_aggregate_temperature_supports_average_minimum_and_primary() -> None:
    """Configured aggregation modes should produce the expected value."""
    sensor_values = {
        "sensor.a": 20.0,
        "sensor.b": 22.0,
        "sensor.c": None,
    }

    assert aggregate_temperature(
        sensor_values,
        ["sensor.a", "sensor.b", "sensor.c"],
        AggregationMode.AVERAGE,
    ) == 21.0
    assert aggregate_temperature(
        sensor_values,
        ["sensor.a", "sensor.b", "sensor.c"],
        AggregationMode.MINIMUM,
    ) == 20.0
    assert aggregate_temperature(
        sensor_values,
        ["sensor.a", "sensor.b", "sensor.c"],
        AggregationMode.PRIMARY,
        primary_sensor_entity_id="sensor.b",
    ) == 22.0


def test_aggregate_temperature_returns_none_when_primary_sensor_is_unavailable() -> None:
    """Primary aggregation should depend on the primary sensor only."""
    sensor_values = {
        "sensor.a": 20.0,
        "sensor.b": None,
    }

    assert (
        aggregate_temperature(
            sensor_values,
            ["sensor.a", "sensor.b"],
            AggregationMode.PRIMARY,
            primary_sensor_entity_id="sensor.b",
        )
        is None
    )


def test_hysteresis_retains_previous_state_inside_band() -> None:
    """Demand should retain state between the on and off thresholds."""
    assert evaluate_hysteresis_demand(19.0, 20.0, previous_demand=False, hysteresis=0.3) is True
    assert evaluate_hysteresis_demand(19.8, 20.0, previous_demand=True, hysteresis=0.3) is True
    assert evaluate_hysteresis_demand(19.8, 20.0, previous_demand=False, hysteresis=0.3) is False
    assert evaluate_hysteresis_demand(20.0, 20.0, previous_demand=True, hysteresis=0.3) is False


def test_effective_target_uses_frost_clamp() -> None:
    """Frost protection should clamp the owned target upward."""
    assert resolve_effective_target_temperature(
        19.0,
        zone_frost_protection_min_temp=18.0,
        global_frost_protection_min_temp=7.0,
    ) == 19.0

    assert resolve_effective_target_temperature(
        19.0,
        zone_frost_protection_min_temp=None,
        global_frost_protection_min_temp=20.0,
    ) == 20.0


def test_switch_zone_demand_is_aggregated_from_local_groups() -> None:
    """A switch or number zone should demand heat when any local group does."""
    zone = ZoneConfig(
        name="Bedroom",
        control_type=ControlType.SWITCH,
        target_temperature=20.0,
        local_groups=[
            LocalControlGroup(
                name="Radiator",
                control_type=ControlType.SWITCH,
                sensor_entity_ids=["sensor.radiator"],
                actuator_entity_ids=["switch.radiator"],
                aggregation_mode=AggregationMode.AVERAGE,
            ),
            LocalControlGroup(
                name="Floor",
                control_type=ControlType.SWITCH,
                sensor_entity_ids=["sensor.floor"],
                actuator_entity_ids=["switch.floor"],
                aggregation_mode=AggregationMode.AVERAGE,
            ),
        ],
    )

    evaluation = evaluate_zone(
        zone,
        {
            "sensor.radiator": 19.0,
            "sensor.floor": 20.5,
        },
        zone_target_temperature=20.0,
        previous_demand=False,
        previous_group_demands={"Radiator": False, "Floor": False},
        hysteresis=0.3,
    )

    assert evaluation.demand is True
    assert [group.demand for group in evaluation.local_groups] == [True, False]
    assert aggregate_system_demand([evaluation]) is True


def test_local_control_group_evaluation_is_independently_testable() -> None:
    """A local group should apply frost and hysteresis on its own."""
    group = LocalControlGroup(
        name="Radiator",
        control_type=ControlType.SWITCH,
        sensor_entity_ids=["sensor.radiator"],
        actuator_entity_ids=["switch.radiator"],
        aggregation_mode=AggregationMode.AVERAGE,
    )

    evaluation = evaluate_local_control_group(
        group,
        {"sensor.radiator": 17.6},
        zone_target_temperature=19.0,
        available_actuator_entity_ids=["switch.radiator"],
        previous_demand=False,
        hysteresis=0.3,
        zone_frost_protection_min_temp=18.0,
        global_frost_protection_min_temp=7.0,
    )

    assert evaluation.current_temperature == 17.6
    assert evaluation.target_temperature == 19.0
    assert evaluation.effective_target_temperature == 19.0
    assert evaluation.demand is True
    assert evaluation.available_actuator_entity_ids == ["switch.radiator"]


def test_climate_zone_without_any_valid_sensors_turns_demand_off() -> None:
    """Unavailable sensors should result in no climate-zone demand."""
    zone = ZoneConfig(
        name="Living Room",
        control_type=ControlType.CLIMATE,
        target_temperature=20.0,
        sensor_entity_ids=["sensor.a", "sensor.b"],
        aggregation_mode=AggregationMode.AVERAGE,
    )

    evaluation = evaluate_zone(
        zone,
        {
            "sensor.a": None,
            "sensor.b": None,
        },
        zone_target_temperature=20.0,
        available_actuator_entity_ids=["climate.living_room"],
        previous_demand=True,
        hysteresis=0.3,
    )

    assert evaluation.current_temperature is None
    assert evaluation.demand is False


def test_zone_demand_turns_off_when_no_actuators_are_available() -> None:
    """A zone should not call for heat when it cannot actuate anything."""
    zone = ZoneConfig(
        name="Bedroom",
        control_type=ControlType.SWITCH,
        target_temperature=20.0,
        local_groups=[
            LocalControlGroup(
                name="Radiator",
                control_type=ControlType.SWITCH,
                sensor_entity_ids=["sensor.radiator"],
                actuator_entity_ids=["switch.radiator"],
                aggregation_mode=AggregationMode.AVERAGE,
            )
        ],
    )

    evaluation = evaluate_zone(
        zone,
        {"sensor.radiator": 19.0},
        zone_target_temperature=20.0,
        available_actuator_entity_ids=[],
        previous_demand=True,
        previous_group_demands={"Radiator": True},
        hysteresis=0.3,
    )

    assert evaluation.demand is False
    assert evaluation.local_groups[0].demand is False
    assert evaluation.local_groups[0].available_actuator_entity_ids == []


def test_disabled_zone_stays_off() -> None:
    """Disabled zones should never call for heat."""
    zone = ZoneConfig(
        name="Study",
        control_type=ControlType.CLIMATE,
        target_temperature=20.0,
        sensor_entity_ids=["sensor.study"],
        aggregation_mode=AggregationMode.AVERAGE,
        enabled=False,
    )

    evaluation = evaluate_zone(
        zone,
        {"sensor.study": 16.0},
        zone_target_temperature=21.0,
        previous_demand=True,
        hysteresis=0.3,
    )

    assert evaluation.current_temperature is None
    assert evaluation.demand is False


def test_open_detector_inhibited_zone_stays_off_without_disabling_zone() -> None:
    """Open detectors should suppress demand without changing manual enabled state."""
    zone = ZoneConfig(
        name="Study",
        control_type=ControlType.CLIMATE,
        target_temperature=20.0,
        sensor_entity_ids=["sensor.study"],
        climate_entity_ids=["climate.study"],
        open_detector_entity_ids=["binary_sensor.study_window"],
        aggregation_mode=AggregationMode.AVERAGE,
        enabled=True,
    )

    evaluation = evaluate_zone(
        zone,
        {"sensor.study": 16.0},
        zone_target_temperature=21.0,
        opening_inhibited=True,
        open_detector_open_entity_ids=["binary_sensor.study_window"],
        available_actuator_entity_ids=["climate.study"],
        previous_demand=True,
        hysteresis=0.3,
    )

    assert zone.enabled is True
    assert evaluation.opening_inhibited is True
    assert evaluation.open_detector_open_entity_ids == ["binary_sensor.study_window"]
    assert evaluation.current_temperature is None
    assert evaluation.demand is False


def test_flow_threshold_reached_requires_value_and_threshold() -> None:
    """Flow detection should only become true with both configured inputs."""
    assert flow_threshold_reached(1.6, 1.5) is True
    assert flow_threshold_reached(1.4, 1.5) is False
    assert flow_threshold_reached(None, 1.5) is False
    assert flow_threshold_reached(1.6, None) is False


def test_missing_flow_warning_waits_for_timeout_then_turns_on() -> None:
    """Missing-flow warnings should become active only after the timeout elapses."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    relay_state = RelayRuntimeState(
        is_on=True,
        last_on_at=now,
    )

    pending = evaluate_missing_flow_warning(
        system_demand=True,
        relay_state=relay_state,
        now=now,
        flow_value=0.0,
        flow_detection_threshold=1.5,
        missing_flow_timeout_seconds=30,
    )

    assert pending.warning_active is False
    assert pending.warning_since is None
    assert pending.next_recheck_at == now + timedelta(seconds=30)

    active = evaluate_missing_flow_warning(
        system_demand=True,
        relay_state=relay_state,
        now=now + timedelta(seconds=30),
        flow_value=0.0,
        flow_detection_threshold=1.5,
        missing_flow_timeout_seconds=30,
    )

    assert active.warning_active is True
    assert active.warning_since == now + timedelta(seconds=30)
    assert active.next_recheck_at is None


def test_missing_flow_warning_is_suppressed_without_active_heat_demand() -> None:
    """Unexpected domestic-water conditions should not create a heating warning."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)

    decision = evaluate_missing_flow_warning(
        system_demand=False,
        relay_state=RelayRuntimeState(
            is_on=False,
            last_on_at=now - timedelta(minutes=5),
        ),
        now=now,
        flow_value=0.0,
        flow_detection_threshold=1.5,
        missing_flow_timeout_seconds=30,
    )

    assert decision.warning_active is False
    assert decision.warning_since is None
    assert decision.next_recheck_at is None


def test_missing_flow_warning_clears_when_flow_recovers() -> None:
    """An active missing-flow warning should clear once flow is detected."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)

    decision = evaluate_missing_flow_warning(
        system_demand=True,
        relay_state=RelayRuntimeState(
            is_on=True,
            last_on_at=now - timedelta(minutes=2),
        ),
        now=now,
        flow_value=1.6,
        flow_detection_threshold=1.5,
        missing_flow_timeout_seconds=30,
    )

    assert decision.warning_active is False
    assert decision.warning_since is None
    assert decision.next_recheck_at is None


def test_relay_on_respects_minimum_off_time() -> None:
    """Relay turn-on should wait until the minimum off time has elapsed."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    decision = decide_relay_action(
        system_demand=True,
        relay_state=RelayRuntimeState(
            is_on=False,
            last_off_at=now - timedelta(seconds=10),
        ),
        now=now,
        min_relay_off_time_seconds=30,
    )

    assert decision.resulting_state is False
    assert decision.should_turn_on is False
    assert decision.hold_reason == "minimum_off_time"
    assert decision.next_recheck_at == now + timedelta(seconds=20)


def test_relay_off_waits_for_delay_and_flow_to_clear() -> None:
    """Relay turn-off should honor delay first and then hold for active flow."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    relay_state = RelayRuntimeState(
        is_on=True,
        last_on_at=now - timedelta(minutes=10),
    )

    delayed = decide_relay_action(
        system_demand=False,
        relay_state=relay_state,
        now=now,
        relay_off_delay_seconds=30,
        flow_value=2.0,
        flow_detection_threshold=1.5,
    )

    assert delayed.resulting_state is True
    assert delayed.should_turn_off is False
    assert delayed.hold_reason == "off_delay"
    assert delayed.off_requested_at == now
    assert delayed.next_recheck_at == now + timedelta(seconds=30)

    held_for_flow = decide_relay_action(
        system_demand=False,
        relay_state=RelayRuntimeState(
            is_on=True,
            last_on_at=relay_state.last_on_at,
            off_requested_at=now,
        ),
        now=now + timedelta(seconds=30),
        relay_off_delay_seconds=30,
        flow_value=2.0,
        flow_detection_threshold=1.5,
    )

    assert held_for_flow.resulting_state is True
    assert held_for_flow.hold_reason == "flow_still_detected"

    turns_off = decide_relay_action(
        system_demand=False,
        relay_state=RelayRuntimeState(
            is_on=True,
            last_on_at=relay_state.last_on_at,
            off_requested_at=now,
        ),
        now=now + timedelta(seconds=31),
        relay_off_delay_seconds=30,
        flow_value=1.0,
        flow_detection_threshold=1.5,
    )

    assert turns_off.resulting_state is False
    assert turns_off.should_turn_off is True
