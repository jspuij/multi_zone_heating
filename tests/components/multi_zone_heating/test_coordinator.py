"""Tests for the runtime coordinator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    HVACMode,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.components.number import ATTR_VALUE, SERVICE_SET_VALUE
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from homeassistant.core import ServiceCall

from custom_components.multi_zone_heating.coordinator import (
    MultiZoneHeatingCoordinator,
    integration_config_from_dict,
)
from custom_components.multi_zone_heating.models import (
    AggregationMode,
    ControlType,
    IntegrationConfig,
    LocalControlGroup,
    NumberSemanticType,
    ZoneConfig,
)


def _build_switch_config(*, relay_off_delay_seconds: int = 0) -> IntegrationConfig:
    """Create a small config with one switch-based local control group."""
    return IntegrationConfig(
        main_relay_entity_id="switch.boiler",
        default_hysteresis=0.3,
        relay_off_delay_seconds=relay_off_delay_seconds,
        zones=[
            ZoneConfig(
                name="Living Room",
                control_type=ControlType.SWITCH,
                target_temperature=20.0,
                local_groups=[
                    LocalControlGroup(
                        name="Radiator",
                        control_type=ControlType.SWITCH,
                        actuator_entity_ids=["switch.radiator"],
                        sensor_entity_ids=["sensor.living_room_temperature"],
                        aggregation_mode=AggregationMode.AVERAGE,
                    )
                ],
            )
        ],
    )


def _build_flow_warning_config(*, missing_flow_timeout_seconds: int) -> IntegrationConfig:
    """Create a config that can raise a missing-flow warning."""
    config = _build_switch_config()
    config.flow_sensor_entity_id = "sensor.system_flow"
    config.flow_detection_threshold = 1.5
    config.missing_flow_timeout_seconds = missing_flow_timeout_seconds
    return config


def _register_recording_switch_services(hass) -> list[tuple[str, dict[str, str]]]:
    """Register fake switch services and record each invocation."""
    return _register_recording_toggle_services(hass, "switch")


def _register_recording_toggle_services(
    hass, domain: str
) -> list[tuple[str, dict[str, str]]]:
    """Register fake on/off services and record each invocation."""
    calls: list[tuple[str, dict[str, str]]] = []

    async def _record_turn_on(call: ServiceCall) -> None:
        calls.append(("turn_on", dict(call.data)))

    async def _record_turn_off(call: ServiceCall) -> None:
        calls.append(("turn_off", dict(call.data)))

    hass.services.async_register(domain, "turn_on", _record_turn_on)
    hass.services.async_register(domain, "turn_off", _record_turn_off)
    return calls


def _register_recording_climate_services(hass) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Register fake climate services and record each invocation."""
    temperature_calls: list[dict[str, object]] = []
    hvac_mode_calls: list[dict[str, object]] = []

    async def _record_set_temperature(call: ServiceCall) -> None:
        temperature_calls.append(dict(call.data))

    async def _record_set_hvac_mode(call: ServiceCall) -> None:
        hvac_mode_calls.append(dict(call.data))

    hass.services.async_register("climate", SERVICE_SET_TEMPERATURE, _record_set_temperature)
    hass.services.async_register("climate", SERVICE_SET_HVAC_MODE, _record_set_hvac_mode)
    return temperature_calls, hvac_mode_calls


def _register_recording_number_services(hass) -> list[dict[str, object]]:
    """Register a fake number set-value service."""
    calls: list[dict[str, object]] = []

    async def _record_set_value(call: ServiceCall) -> None:
        calls.append(dict(call.data))

    hass.services.async_register("number", SERVICE_SET_VALUE, _record_set_value)
    return calls


async def test_coordinator_dispatches_switch_group_and_relay_once_until_state_changes(
    hass,
) -> None:
    """Repeated reevaluations should not spam duplicate commands."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("switch.radiator", "off")
    hass.states.async_set("switch.boiler", "off")

    calls = _register_recording_switch_services(hass)

    coordinator = MultiZoneHeatingCoordinator(hass, _build_switch_config())
    await coordinator.async_start()
    await hass.async_block_till_done()

    assert calls == [
        ("turn_on", {"entity_id": "switch.radiator"}),
        ("turn_on", {"entity_id": "switch.boiler"}),
    ]

    calls.clear()
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert calls == []
    await coordinator.async_stop()


async def test_coordinator_tracks_unavailable_entities_in_snapshot(hass) -> None:
    """Missing sensors and actuators should be exposed in the runtime snapshot."""
    hass.states.async_set("switch.boiler", "off")

    coordinator = MultiZoneHeatingCoordinator(hass, _build_switch_config())
    await coordinator.async_start()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert "sensor.living_room_temperature" in coordinator.data.unavailable_entity_ids
    assert "switch.radiator" in coordinator.data.unavailable_entity_ids
    assert coordinator.data.system_demand is False
    await coordinator.async_stop()


async def test_coordinator_rechecks_relay_after_off_delay(hass, monkeypatch) -> None:
    """A deferred relay-off should complete via the scheduled reevaluation."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    hass.states.async_set("sensor.living_room_temperature", "20.5")
    hass.states.async_set("switch.radiator", "off")
    hass.states.async_set("switch.boiler", "on")

    calls = _register_recording_switch_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        _build_switch_config(relay_off_delay_seconds=30),
    )
    monkeypatch.setattr(coordinator, "_utcnow", lambda: now)

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert coordinator.data.relay_decision is not None
    assert coordinator.data.relay_decision.hold_reason == "off_delay"
    assert coordinator.data.relay_decision.next_recheck_at == now + timedelta(seconds=30)
    assert calls == []

    monkeypatch.setattr(
        coordinator,
        "_utcnow",
        lambda: now + timedelta(seconds=30),
    )
    async_fire_time_changed(hass, now + timedelta(seconds=30))
    await hass.async_block_till_done()

    assert calls == [("turn_off", {"entity_id": "switch.boiler"})]
    await coordinator.async_stop()


async def test_coordinator_dispatches_input_boolean_global_relay(hass) -> None:
    """The main relay may be backed by an input_boolean helper."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("switch.radiator", "off")
    hass.states.async_set("input_boolean.boiler_enable", "off")

    switch_calls = _register_recording_switch_services(hass)
    relay_calls = _register_recording_toggle_services(hass, "input_boolean")

    config = _build_switch_config()
    config.main_relay_entity_id = "input_boolean.boiler_enable"

    coordinator = MultiZoneHeatingCoordinator(hass, config)
    await coordinator.async_start()
    await hass.async_block_till_done()

    assert switch_calls == [("turn_on", {"entity_id": "switch.radiator"})]
    assert relay_calls == [("turn_on", {"entity_id": "input_boolean.boiler_enable"})]

    hass.states.async_set("sensor.living_room_temperature", "20.5")
    hass.states.async_set("switch.radiator", "on")
    hass.states.async_set("input_boolean.boiler_enable", "on")
    switch_calls.clear()
    relay_calls.clear()

    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert switch_calls == [("turn_off", {"entity_id": "switch.radiator"})]
    assert relay_calls == [("turn_off", {"entity_id": "input_boolean.boiler_enable"})]
    await coordinator.async_stop()


async def test_coordinator_raises_missing_flow_warning_after_timeout(hass, monkeypatch) -> None:
    """Missing-flow warnings should trip on the scheduled timeout boundary."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.system_flow", "0.0")
    hass.states.async_set("switch.radiator", "off")
    hass.states.async_set("switch.boiler", "on")

    calls = _register_recording_switch_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        _build_flow_warning_config(missing_flow_timeout_seconds=30),
    )
    monkeypatch.setattr(coordinator, "_utcnow", lambda: now)

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert coordinator.data.flow_value == 0.0
    assert coordinator.data.flow_detected is False
    assert coordinator.data.missing_flow_warning is False
    assert coordinator.data.missing_flow_warning_since is None
    assert calls == [("turn_on", {"entity_id": "switch.radiator"})]

    monkeypatch.setattr(
        coordinator,
        "_utcnow",
        lambda: now + timedelta(seconds=30),
    )
    async_fire_time_changed(hass, now + timedelta(seconds=30))
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert coordinator.data.missing_flow_warning is True
    assert coordinator.data.missing_flow_warning_since == now + timedelta(seconds=30)
    assert calls == [("turn_on", {"entity_id": "switch.radiator"})]
    await coordinator.async_stop()


async def test_coordinator_dispatches_climate_targets(hass) -> None:
    """Climate zones should set shared target temperatures once."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("climate.radiator_a", "heat", {"temperature": 18.0})
    hass.states.async_set("climate.radiator_b", "heat", {"temperature": 21.0})
    hass.states.async_set("switch.boiler", "off")
    _register_recording_switch_services(hass)
    climate_calls, hvac_mode_calls = _register_recording_climate_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        IntegrationConfig(
            main_relay_entity_id="switch.boiler",
            zones=[
                ZoneConfig(
                    name="Living Room",
                    control_type=ControlType.CLIMATE,
                    target_temperature=21.0,
                    sensor_entity_ids=["sensor.living_room_temperature"],
                    climate_entity_ids=["climate.radiator_a", "climate.radiator_b"],
                    aggregation_mode=AggregationMode.AVERAGE,
                )
            ],
        ),
    )

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert climate_calls == [{"entity_id": "climate.radiator_a", "temperature": 21.0}]
    assert hvac_mode_calls == []
    await coordinator.async_stop()


async def test_coordinator_restores_heat_mode_before_setting_target(hass) -> None:
    """Climate zones should resume heat mode before pushing the target again."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set(
        "climate.radiator_a",
        "off",
        {"temperature": 18.0, "hvac_modes": [HVACMode.HEAT, HVACMode.OFF]},
    )
    hass.states.async_set("switch.boiler", "off")
    _register_recording_switch_services(hass)
    climate_calls, hvac_mode_calls = _register_recording_climate_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        IntegrationConfig(
            main_relay_entity_id="switch.boiler",
            zones=[
                ZoneConfig(
                    name="Living Room",
                    control_type=ControlType.CLIMATE,
                    target_temperature=21.0,
                    sensor_entity_ids=["sensor.living_room_temperature"],
                    climate_entity_ids=["climate.radiator_a"],
                    aggregation_mode=AggregationMode.AVERAGE,
                )
            ],
        ),
    )

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert hvac_mode_calls == [{"entity_id": "climate.radiator_a", ATTR_HVAC_MODE: HVACMode.HEAT}]
    assert climate_calls == [{"entity_id": "climate.radiator_a", "temperature": 21.0}]
    await coordinator.async_stop()


async def test_coordinator_turns_climate_zone_off_when_demand_clears(hass) -> None:
    """Climate zones should turn supported actuators off when they stop demanding heat."""
    hass.states.async_set("sensor.living_room_temperature", "20.5")
    hass.states.async_set(
        "climate.radiator_a",
        "heat",
        {"temperature": 20.0, "hvac_modes": [HVACMode.HEAT, HVACMode.OFF]},
    )
    hass.states.async_set("switch.boiler", "on")
    _register_recording_switch_services(hass)
    climate_calls, hvac_mode_calls = _register_recording_climate_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        IntegrationConfig(
            main_relay_entity_id="switch.boiler",
            zones=[
                ZoneConfig(
                    name="Living Room",
                    control_type=ControlType.CLIMATE,
                    target_temperature=20.0,
                    sensor_entity_ids=["sensor.living_room_temperature"],
                    climate_entity_ids=["climate.radiator_a"],
                    aggregation_mode=AggregationMode.AVERAGE,
                )
            ],
        ),
    )

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert climate_calls == []
    assert hvac_mode_calls == [{"entity_id": "climate.radiator_a", ATTR_HVAC_MODE: HVACMode.OFF}]
    await coordinator.async_stop()


async def test_coordinator_uses_climate_fallback_target_when_off_is_unsupported(hass) -> None:
    """Climate zones should write the fallback target when off cannot be selected."""
    hass.states.async_set("sensor.living_room_temperature", "20.5")
    hass.states.async_set(
        "climate.radiator_a",
        "heat",
        {"temperature": 20.0, "hvac_modes": [HVACMode.HEAT]},
    )
    hass.states.async_set("switch.boiler", "on")
    _register_recording_switch_services(hass)
    climate_calls, hvac_mode_calls = _register_recording_climate_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        IntegrationConfig(
            main_relay_entity_id="switch.boiler",
            zones=[
                ZoneConfig(
                    name="Living Room",
                    control_type=ControlType.CLIMATE,
                    target_temperature=20.0,
                    sensor_entity_ids=["sensor.living_room_temperature"],
                    climate_entity_ids=["climate.radiator_a"],
                    climate_off_fallback_temperature=7.5,
                    aggregation_mode=AggregationMode.AVERAGE,
                )
            ],
        ),
    )

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert climate_calls == [{"entity_id": "climate.radiator_a", "temperature": 7.5}]
    assert hvac_mode_calls == []
    await coordinator.async_stop()


async def test_coordinator_dispatches_number_group_values(hass) -> None:
    """Number groups should write the configured active value."""
    hass.states.async_set("sensor.floor_temperature", "19.0")
    hass.states.async_set("number.floor_valve", "0")
    hass.states.async_set("switch.boiler", "off")
    _register_recording_switch_services(hass)
    number_calls = _register_recording_number_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        IntegrationConfig(
            main_relay_entity_id="switch.boiler",
            zones=[
                ZoneConfig(
                    name="Floor",
                    control_type=ControlType.NUMBER,
                    target_temperature=20.0,
                    local_groups=[
                        LocalControlGroup(
                            name="Valve",
                            control_type=ControlType.NUMBER,
                            actuator_entity_ids=["number.floor_valve"],
                            sensor_entity_ids=["sensor.floor_temperature"],
                            aggregation_mode=AggregationMode.AVERAGE,
                            number_semantic_type=NumberSemanticType.PERCENTAGE,
                            active_value=100.0,
                            inactive_value=0.0,
                        )
                    ],
                )
            ],
        ),
    )

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert number_calls == [{"entity_id": "number.floor_valve", ATTR_VALUE: 100.0}]
    await coordinator.async_stop()


async def test_coordinator_ignores_groups_with_no_available_actuators(hass) -> None:
    """The relay should stay off when a demanding group has no available actuators left."""
    hass.states.async_set("sensor.floor_temperature", "19.0")
    hass.states.async_set("switch.boiler", "off")
    calls = _register_recording_switch_services(hass)

    coordinator = MultiZoneHeatingCoordinator(
        hass,
        IntegrationConfig(
            main_relay_entity_id="switch.boiler",
            zones=[
                ZoneConfig(
                    name="Floor",
                    control_type=ControlType.SWITCH,
                    target_temperature=20.0,
                    local_groups=[
                        LocalControlGroup(
                            name="Valve",
                            control_type=ControlType.SWITCH,
                            actuator_entity_ids=["switch.floor_valve"],
                            sensor_entity_ids=["sensor.floor_temperature"],
                            aggregation_mode=AggregationMode.AVERAGE,
                        )
                    ],
                )
            ],
        ),
    )

    await coordinator.async_start()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert coordinator.data.system_demand is False
    assert calls == []
    await coordinator.async_stop()


def test_integration_config_from_dict_builds_typed_models() -> None:
    """Entry data should round-trip into typed runtime config."""
    config = integration_config_from_dict(
        {
            "main_relay_entity_id": "switch.boiler",
            "flow_sensor_entity_id": "sensor.flow",
            "flow_detection_threshold": 1.5,
            "missing_flow_timeout_seconds": 90,
            "default_hysteresis": 0.4,
            "min_relay_on_time_seconds": 60,
            "min_relay_off_time_seconds": 30,
            "relay_off_delay_seconds": 15,
            "frost_protection_min_temp": 7.0,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": ControlType.NUMBER,
                    "target_temperature": 20.0,
                    "sensor_entity_ids": [],
                    "climate_entity_ids": [],
                    "climate_off_fallback_temperature": None,
                    "aggregation_mode": AggregationMode.AVERAGE,
                    "primary_sensor_entity_id": None,
                    "frost_protection_min_temp": 8.0,
                    "local_groups": [
                        {
                            "name": "Valve",
                            "control_type": ControlType.NUMBER,
                            "sensor_entity_ids": ["sensor.floor"],
                            "actuator_entity_ids": ["number.valve"],
                            "aggregation_mode": AggregationMode.MINIMUM,
                            "primary_sensor_entity_id": None,
                            "number_semantic_type": NumberSemanticType.PERCENTAGE,
                            "active_value": 90.0,
                            "inactive_value": 10.0,
                        }
                    ],
                }
            ],
        }
    )

    assert config.main_relay_entity_id == "switch.boiler"
    assert config.flow_sensor_entity_id == "sensor.flow"
    assert config.missing_flow_timeout_seconds == 90
    assert config.default_hysteresis == 0.4
    assert config.zones[0].control_type is ControlType.NUMBER
    assert config.zones[0].target_temperature == 20.0
    assert config.zones[0].climate_off_fallback_temperature is None
    assert config.zones[0].local_groups[0].aggregation_mode is AggregationMode.MINIMUM
    assert config.zones[0].local_groups[0].number_semantic_type is NumberSemanticType.PERCENTAGE
