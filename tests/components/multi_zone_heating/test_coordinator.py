"""Tests for the runtime coordinator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pytest_homeassistant_custom_component.common import async_fire_time_changed
from homeassistant.core import ServiceCall

from custom_components.multi_zone_heating.coordinator import MultiZoneHeatingCoordinator
from custom_components.multi_zone_heating.models import (
    AggregationMode,
    ControlType,
    IntegrationConfig,
    LocalControlGroup,
    TargetSourceType,
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
                target_source=TargetSourceType.INPUT_NUMBER,
                target_entity_id="input_number.living_room_target",
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


def _register_recording_switch_services(hass) -> list[tuple[str, dict[str, str]]]:
    """Register fake switch services and record each invocation."""
    calls: list[tuple[str, dict[str, str]]] = []

    async def _record_turn_on(call: ServiceCall) -> None:
        calls.append(("turn_on", dict(call.data)))

    async def _record_turn_off(call: ServiceCall) -> None:
        calls.append(("turn_off", dict(call.data)))

    hass.services.async_register("switch", "turn_on", _record_turn_on)
    hass.services.async_register("switch", "turn_off", _record_turn_off)
    return calls


async def test_coordinator_dispatches_switch_group_and_relay_once_until_state_changes(
    hass,
) -> None:
    """Repeated reevaluations should not spam duplicate commands."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("input_number.living_room_target", "20.0")
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
    hass.states.async_set("input_number.living_room_target", "20.0")
    hass.states.async_set("switch.boiler", "off")

    coordinator = MultiZoneHeatingCoordinator(hass, _build_switch_config())
    await coordinator.async_start()
    await hass.async_block_till_done()

    assert coordinator.data is not None
    assert "sensor.living_room_temperature" in coordinator.data.unavailable_entity_ids
    assert "switch.radiator" in coordinator.data.unavailable_entity_ids
    assert "input_number.living_room_target" not in coordinator.data.unavailable_entity_ids
    assert coordinator.data.system_demand is False
    await coordinator.async_stop()


async def test_coordinator_rechecks_relay_after_off_delay(hass, monkeypatch) -> None:
    """A deferred relay-off should complete via the scheduled reevaluation."""
    now = datetime(2026, 4, 8, 10, 0, tzinfo=UTC)
    hass.states.async_set("sensor.living_room_temperature", "20.5")
    hass.states.async_set("input_number.living_room_target", "20.0")
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
