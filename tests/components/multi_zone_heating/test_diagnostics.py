"""Tests for multi_zone_heating diagnostics export."""

from __future__ import annotations

from homeassistant.const import STATE_OFF
from homeassistant.core import ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.multi_zone_heating.const import DOMAIN
from custom_components.multi_zone_heating.diagnostics import (
    async_get_config_entry_diagnostics,
)


def _build_config_entry() -> MockConfigEntry:
    """Create a representative config entry for diagnostics tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "main_relay_entity_id": "switch.boiler",
            "flow_sensor_entity_id": "sensor.system_flow",
            "flow_detection_threshold": 1.5,
            "missing_flow_timeout_seconds": 60,
            "default_hysteresis": 0.3,
            "relay_off_delay_seconds": 0,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": "switch",
                    "target_temperature": 20.0,
                    "local_groups": [
                        {
                            "name": "Radiator",
                            "control_type": "switch",
                            "actuator_entity_ids": ["switch.radiator"],
                            "sensor_entity_ids": ["sensor.living_room_temperature"],
                            "aggregation_mode": "average",
                        }
                    ],
                }
            ],
        },
        version=1,
    )


def _register_recording_switch_services(hass) -> None:
    """Register fake switch services needed during coordinator refresh."""

    async def _record_turn_on(call: ServiceCall) -> None:
        hass.states.async_set(call.data["entity_id"], "on")

    async def _record_turn_off(call: ServiceCall) -> None:
        hass.states.async_set(call.data["entity_id"], STATE_OFF)

    hass.services.async_register("switch", "turn_on", _record_turn_on)
    hass.services.async_register("switch", "turn_off", _record_turn_off)


async def test_config_entry_diagnostics_include_config_and_runtime_state(hass) -> None:
    """Diagnostics should expose both typed config and live runtime state."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.system_flow", "0.0")
    hass.states.async_set("switch.radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)
    _register_recording_switch_services(hass)

    entry = _build_config_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["config_entry"]["version"] == 2
    assert diagnostics["config"]["main_relay_entity_id"] == "switch.boiler"
    assert diagnostics["config"]["zones"][0]["control_type"] == "switch"
    assert diagnostics["reload_boundaries"]["terminology"] == "runtime-versus-structural"
    assert (
        "changing global timing, flow, frost, or failsafe settings through the options flow"
        in diagnostics["reload_boundaries"]["structural_changes_reload"]
    )
    assert (
        "setting the system climate target and fanning it out to zones"
        in diagnostics["reload_boundaries"]["runtime_actions_do_not_reload"]
    )
    assert diagnostics["runtime"]["loaded"] is True
    assert diagnostics["runtime"]["global_force_off"] is False
    assert diagnostics["runtime"]["system_climate"]["hvac_mode"] == "heat"
    assert diagnostics["runtime"]["system_climate"]["target_temperature"] == 20.0
    assert diagnostics["runtime"]["system_climate"]["zone_target_temperatures"] == {
        "Living Room": 20.0,
    }
    assert diagnostics["runtime"]["zone_climates"][0]["name"] == "Living Room"
    assert diagnostics["runtime"]["zone_climates"][0]["hvac_mode"] == "heat"
    assert diagnostics["runtime"]["zone_climates"][0]["hvac_action"] == "heating"
    assert diagnostics["runtime"]["zone_climates"][0]["demand"] is True
    assert diagnostics["runtime"]["zone_climates"][0]["global_force_off"] is False
    assert diagnostics["runtime"]["zone_climates"][0]["target_temperature"] == 20.0
    assert diagnostics["runtime"]["zone_climates"][0]["effective_target_temperature"] == 20.0
    assert diagnostics["runtime"]["zone_climates"][0]["local_groups"][0]["target_temperature"] == 20.0
    assert diagnostics["runtime"]["snapshot"]["flow_detected"] is False
    assert diagnostics["runtime"]["snapshot"]["relay_runtime_state"]["is_on"] is True
    assert diagnostics["runtime"]["snapshot"]["zone_evaluations"][0]["name"] == "Living Room"
    assert diagnostics["runtime"]["snapshot"]["zone_evaluations"][0]["local_groups"][0]["name"] == "Radiator"
    assert diagnostics["runtime"]["snapshot"]["target_temperatures"] == {
        "Living Room": 20.0,
    }


async def test_zone_climate_diagnostics_distinguish_idle_disabled_and_forced_off(hass) -> None:
    """Zone diagnostics should separate demand, zone enable, and global force-off."""
    hass.states.async_set("sensor.living_room_temperature", "20.5")
    hass.states.async_set("sensor.system_flow", "0.0")
    hass.states.async_set("switch.radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)
    _register_recording_switch_services(hass)

    entry = _build_config_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    zone = diagnostics["runtime"]["zone_climates"][0]
    assert zone["hvac_mode"] == "heat"
    assert zone["hvac_action"] == "idle"
    assert zone["demand"] is False

    await entry.runtime_data.coordinator.async_set_zone_enabled("Living Room", False)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    zone = diagnostics["runtime"]["zone_climates"][0]
    assert zone["hvac_mode"] == "off"
    assert zone["hvac_action"] == "off"
    assert zone["demand"] is False

    await entry.runtime_data.coordinator.async_set_zone_enabled("Living Room", True)
    await entry.runtime_data.coordinator.async_set_global_force_off(True)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    zone = diagnostics["runtime"]["zone_climates"][0]
    assert zone["hvac_mode"] == "heat"
    assert zone["hvac_action"] == "off"
    assert zone["demand"] is False
    assert zone["global_force_off"] is True


async def test_diagnostics_include_open_detector_state_by_zone(hass) -> None:
    """Diagnostics should identify configured, open, and unavailable detectors."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.system_flow", "0.0")
    hass.states.async_set("switch.radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)
    hass.states.async_set("binary_sensor.living_room_window", "on")
    _register_recording_switch_services(hass)

    entry = _build_config_entry()
    entry.data["zones"][0]["open_detector_entity_ids"] = [
        "binary_sensor.living_room_window",
        "binary_sensor.living_room_door",
    ]
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    zone = diagnostics["runtime"]["zone_climates"][0]

    assert zone["open_detector_entity_ids"] == [
        "binary_sensor.living_room_window",
        "binary_sensor.living_room_door",
    ]
    assert zone["open_detector_open_entity_ids"] == [
        "binary_sensor.living_room_window"
    ]
    assert zone["open_detector_unavailable_entity_ids"] == [
        "binary_sensor.living_room_door"
    ]
    assert zone["opening_inhibited"] is True
    assert zone["hvac_action"] == "off"
    assert zone["demand"] is False
    assert diagnostics["runtime"]["snapshot"]["open_detector_states"] == {
        "binary_sensor.living_room_window": True,
        "binary_sensor.living_room_door": None,
    }
