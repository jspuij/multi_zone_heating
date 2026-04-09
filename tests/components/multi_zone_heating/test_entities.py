"""Tests for multi_zone_heating entities and override behavior."""

from __future__ import annotations

from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.multi_zone_heating.const import DOMAIN


def _build_config_entry() -> MockConfigEntry:
    """Create a config entry with one switch-controlled zone."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "main_relay_entity_id": "switch.boiler",
            "default_hysteresis": 0.3,
            "relay_off_delay_seconds": 0,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": "switch",
                    "target_source": "input_number",
                    "target_entity_id": "input_number.living_room_target",
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


def _register_recording_switch_services(hass) -> list[tuple[str, dict[str, str]]]:
    """Register fake switch services and record each invocation."""
    calls: list[tuple[str, dict[str, str]]] = []

    async def _record_turn_on(call: ServiceCall) -> None:
        calls.append(("turn_on", dict(call.data)))
        hass.states.async_set(call.data[ATTR_ENTITY_ID], STATE_ON)

    async def _record_turn_off(call: ServiceCall) -> None:
        calls.append(("turn_off", dict(call.data)))
        hass.states.async_set(call.data[ATTR_ENTITY_ID], STATE_OFF)

    hass.services.async_register("switch", "turn_on", _record_turn_on)
    hass.services.async_register("switch", "turn_off", _record_turn_off)
    return calls


async def _setup_loaded_entry(hass) -> tuple[MockConfigEntry, list[tuple[str, dict[str, str]]]]:
    """Set up a config entry with states and switch service mocks."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("input_number.living_room_target", "20.0")
    hass.states.async_set("switch.radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)

    calls = _register_recording_switch_services(hass)
    entry = _build_config_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, calls


async def test_system_climate_sets_and_clears_override(hass) -> None:
    """The top-level climate entity should manage the global override."""
    await _setup_loaded_entry(hass)

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    assert climate_state is not None
    assert climate_state.state == "heat"
    assert climate_state.attributes["override_active"] is False

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_system",
            "temperature": 21.5,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    assert climate_state is not None
    assert climate_state.attributes["override_active"] is True
    assert climate_state.attributes["override_target_temperature"] == 21.5

    await hass.services.async_call(DOMAIN, "clear_override", {}, blocking=True)
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    assert climate_state is not None
    assert climate_state.attributes["override_active"] is False
    assert climate_state.attributes["override_target_temperature"] == 21.5


async def test_zone_target_change_clears_override(hass) -> None:
    """Changing a zone target should end the global override."""
    await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_system",
            "temperature": 21.5,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    hass.states.async_set("input_number.living_room_target", "19.0")
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    assert climate_state is not None
    assert climate_state.attributes["override_active"] is False
    assert climate_state.attributes["override_target_temperature"] == 21.5


async def test_zone_enable_and_global_force_off_switches_control_runtime(hass) -> None:
    """Entity switches should disable zones and force outputs off."""
    entry, _ = await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.multi_zone_heating_living_room_enabled"},
        blocking=True,
    )
    await hass.async_block_till_done()

    zone_state = hass.states.get("binary_sensor.multi_zone_heating_living_room_demand")
    system_state = hass.states.get("binary_sensor.multi_zone_heating_system_demand")
    assert zone_state is not None
    assert zone_state.state == STATE_OFF
    assert system_state is not None
    assert system_state.state == STATE_OFF
    assert entry.data["zones"][0]["enabled"] is False

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.multi_zone_heating_global_force_off"},
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    relay_state = hass.states.get("sensor.multi_zone_heating_relay_state")
    assert climate_state is not None
    assert climate_state.state == "off"
    assert climate_state.attributes["global_force_off"] is True
    assert relay_state is not None
    assert relay_state.state == "forced_off"


async def test_zone_enable_toggle_persists_in_config_entry(hass) -> None:
    """Zone enable changes should update the config entry data."""
    entry, _ = await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.multi_zone_heating_living_room_enabled"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert entry.data["zones"][0]["enabled"] is False

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.multi_zone_heating_living_room_enabled"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert entry.data["zones"][0]["enabled"] is True
