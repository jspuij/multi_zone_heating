"""Tests for multi_zone_heating entities and climate behavior."""

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
    hass.states.async_set("switch.radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)

    calls = _register_recording_switch_services(hass)
    entry = _build_config_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, calls


async def test_system_climate_fans_target_out_to_owned_zone_targets(hass) -> None:
    """The system climate should write through to the zone-owned targets."""
    await _setup_loaded_entry(hass)

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    assert climate_state is not None
    assert climate_state.state == "heat"
    assert climate_state.attributes["temperature"] == 20.0
    assert climate_state.attributes["zone_target_temperatures"] == {"Living Room": 20.0}

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
    assert climate_state.attributes["temperature"] == 21.5
    assert climate_state.attributes["zone_target_temperatures"] == {"Living Room": 21.5}

    zone_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert zone_state is not None
    assert zone_state.attributes["temperature"] == 21.5


async def test_system_climate_reports_no_shared_target_when_zones_differ(hass) -> None:
    """The system climate should not invent a separate target source."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.bedroom_temperature", "18.0")
    hass.states.async_set("switch.living_room_radiator", STATE_OFF)
    hass.states.async_set("switch.bedroom_radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)
    _register_recording_switch_services(hass)

    entry = MockConfigEntry(
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
                    "target_temperature": 20.0,
                    "local_groups": [
                        {
                            "name": "Radiator",
                            "control_type": "switch",
                            "actuator_entity_ids": ["switch.living_room_radiator"],
                            "sensor_entity_ids": ["sensor.living_room_temperature"],
                            "aggregation_mode": "average",
                        }
                    ],
                },
                {
                    "name": "Bedroom",
                    "enabled": True,
                    "control_type": "switch",
                    "target_temperature": 18.5,
                    "local_groups": [
                        {
                            "name": "Radiator",
                            "control_type": "switch",
                            "actuator_entity_ids": ["switch.bedroom_radiator"],
                            "sensor_entity_ids": ["sensor.bedroom_temperature"],
                            "aggregation_mode": "average",
                        }
                    ],
                },
            ],
        },
        version=1,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_system")
    assert climate_state is not None
    assert climate_state.attributes["temperature"] is None
    assert climate_state.attributes["zone_target_temperatures"] == {
        "Living Room": 20.0,
        "Bedroom": 18.5,
    }


async def test_zone_climate_exposes_and_persists_owned_target(hass) -> None:
    """Each zone should expose a climate entity with an owned target."""
    entry, _ = await _setup_loaded_entry(hass)

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.state == "heat"
    assert climate_state.attributes["temperature"] == 20.0
    assert climate_state.attributes["current_temperature"] is None

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_living_room",
            "temperature": 21.5,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.attributes["temperature"] == 21.5
    assert entry.data["zones"][0]["target_temperature"] == 21.5


async def test_zone_climate_hvac_mode_toggles_zone_enabled(hass) -> None:
    """Setting zone HVAC mode should enable and disable the owned zone."""
    entry, _ = await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_living_room",
            "hvac_mode": "off",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.state == "off"
    assert entry.data["zones"][0]["enabled"] is False

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_living_room",
            "hvac_mode": "heat",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.state == "heat"
    assert entry.data["zones"][0]["enabled"] is True


async def test_zone_enabled_switch_and_zone_climate_stay_synchronized(hass) -> None:
    """Zone enable switch and climate HVAC mode should project the same state."""
    await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.multi_zone_heating_living_room_enabled"},
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    switch_state = hass.states.get("switch.multi_zone_heating_living_room_enabled")
    assert climate_state is not None
    assert switch_state is not None
    assert climate_state.state == "off"
    assert switch_state.state == STATE_OFF

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_living_room",
            "hvac_mode": "heat",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    switch_state = hass.states.get("switch.multi_zone_heating_living_room_enabled")
    assert climate_state is not None
    assert switch_state is not None
    assert climate_state.state == "heat"
    assert switch_state.state == STATE_ON


async def test_zone_climate_target_restores_after_entry_reload(hass) -> None:
    """Reloading the entry should restore the persisted owned zone target."""
    entry, _ = await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            ATTR_ENTITY_ID: "climate.multi_zone_heating_living_room",
            "temperature": 21.5,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.data["zones"][0]["target_temperature"] == 21.5

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.attributes["temperature"] == 21.5


async def test_system_climate_clamps_fanned_target_to_zone_frost_floor(hass) -> None:
    """System fan-out should respect the strictest effective zone minimum."""
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.bedroom_temperature", "18.0")
    hass.states.async_set("switch.living_room_radiator", STATE_OFF)
    hass.states.async_set("switch.bedroom_radiator", STATE_OFF)
    hass.states.async_set("switch.boiler", STATE_OFF)
    _register_recording_switch_services(hass)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "main_relay_entity_id": "switch.boiler",
            "default_hysteresis": 0.3,
            "frost_protection_min_temp": 5.0,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": "switch",
                    "target_temperature": 20.0,
                    "frost_protection_min_temp": 10.0,
                    "local_groups": [
                        {
                            "name": "Radiator",
                            "control_type": "switch",
                            "actuator_entity_ids": ["switch.living_room_radiator"],
                            "sensor_entity_ids": ["sensor.living_room_temperature"],
                            "aggregation_mode": "average",
                        }
                    ],
                },
                {
                    "name": "Bedroom",
                    "enabled": True,
                    "control_type": "switch",
                    "target_temperature": 19.0,
                    "local_groups": [
                        {
                            "name": "Radiator",
                            "control_type": "switch",
                            "actuator_entity_ids": ["switch.bedroom_radiator"],
                            "sensor_entity_ids": ["sensor.bedroom_temperature"],
                            "aggregation_mode": "average",
                        }
                    ],
                },
            ],
        },
        version=2,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    system_state = hass.states.get("climate.multi_zone_heating_system")
    assert system_state is not None
    assert system_state.attributes["min_temp"] == 10.0

    assert entry.runtime_data.coordinator is not None
    await entry.runtime_data.coordinator.async_set_all_zone_target_temperatures(6.0)

    assert entry.data["zones"][0]["target_temperature"] == 10.0
    assert entry.data["zones"][1]["target_temperature"] == 6.0


async def test_zone_climate_current_temperature_uses_average_aggregation(hass) -> None:
    """Zone climates should project the configured aggregated temperature."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "main_relay_entity_id": "switch.boiler",
            "default_hysteresis": 0.3,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": "climate",
                    "target_temperature": 20.0,
                    "sensor_entity_ids": [
                        "sensor.living_room_temperature",
                        "sensor.living_room_corner_temperature",
                    ],
                    "aggregation_mode": "average",
                    "climate_entity_ids": [],
                }
            ],
        },
        version=2,
    )
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.living_room_corner_temperature", "21.0")
    hass.states.async_set("switch.boiler", STATE_OFF)

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.attributes["current_temperature"] == 20.0
    assert climate_state.attributes["aggregation_mode"] == "average"


async def test_zone_climate_current_temperature_uses_primary_sensor(hass) -> None:
    """Primary aggregation should expose the configured primary sensor directly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "main_relay_entity_id": "switch.boiler",
            "default_hysteresis": 0.3,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": "climate",
                    "target_temperature": 20.0,
                    "sensor_entity_ids": [
                        "sensor.living_room_temperature",
                        "sensor.living_room_corner_temperature",
                    ],
                    "aggregation_mode": "primary",
                    "primary_sensor_entity_id": "sensor.living_room_corner_temperature",
                    "climate_entity_ids": [],
                }
            ],
        },
        version=2,
    )
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.living_room_corner_temperature", "21.0")
    hass.states.async_set("switch.boiler", STATE_OFF)

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.attributes["current_temperature"] == 21.0
    assert (
        climate_state.attributes["primary_sensor_entity_id"]
        == "sensor.living_room_corner_temperature"
    )


async def test_zone_climate_current_temperature_uses_minimum_aggregation(hass) -> None:
    """Minimum aggregation should expose the coldest available sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "main_relay_entity_id": "switch.boiler",
            "default_hysteresis": 0.3,
            "zones": [
                {
                    "name": "Living Room",
                    "enabled": True,
                    "control_type": "climate",
                    "target_temperature": 20.0,
                    "sensor_entity_ids": [
                        "sensor.living_room_temperature",
                        "sensor.living_room_corner_temperature",
                    ],
                    "aggregation_mode": "minimum",
                    "climate_entity_ids": [],
                }
            ],
        },
        version=2,
    )
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("sensor.living_room_corner_temperature", "21.0")
    hass.states.async_set("switch.boiler", STATE_OFF)

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.attributes["current_temperature"] == 19.0
    assert climate_state.attributes["aggregation_mode"] == "minimum"


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

    zone_climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert zone_climate_state is not None
    assert zone_climate_state.state == "off"
    assert zone_climate_state.attributes["hvac_action"] == "off"


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


async def test_zone_climate_keeps_heat_mode_but_reports_off_action_during_global_force_off(
    hass,
) -> None:
    """Global force-off should not disable the zone, only suppress active heating."""
    await _setup_loaded_entry(hass)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.multi_zone_heating_global_force_off"},
        blocking=True,
    )
    await hass.async_block_till_done()

    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    switch_state = hass.states.get("switch.multi_zone_heating_living_room_enabled")
    assert climate_state is not None
    assert switch_state is not None
    assert climate_state.state == "heat"
    assert climate_state.attributes["hvac_action"] == "off"
    assert switch_state.state == STATE_ON
