"""Tests for multi_zone_heating entry setup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME

from custom_components.multi_zone_heating.const import DOMAIN
from custom_components.multi_zone_heating.config_flow import (
    CONF_AGGREGATION_MODE,
    CONF_CLIMATE_ENTITY_IDS,
    CONF_CONTROL_TYPE,
    CONF_DEFAULT_HYSTERESIS,
    CONF_ENABLED,
    CONF_LOCAL_GROUPS,
    CONF_PRIMARY_SENSOR_ENTITY_ID,
    CONF_SENSOR_ENTITY_IDS,
    CONF_TARGET_TEMPERATURE,
    CONF_ZONES,
)
from custom_components.multi_zone_heating.coordinator import MultiZoneHeatingCoordinator
from custom_components.multi_zone_heating.models import (
    AggregationMode,
    ControlType,
    RuntimeData,
)
from custom_components.multi_zone_heating.runtime_state import RuntimeStateStore
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_and_unload_entry(hass, config_entry) -> None:
    """A config entry should set up and unload cleanly."""
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert isinstance(config_entry.runtime_data, RuntimeData)
    assert config_entry.runtime_data.config_entry_id == config_entry.entry_id
    assert isinstance(config_entry.runtime_data.coordinator, MultiZoneHeatingCoordinator)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert DOMAIN in hass.config.components


async def test_setup_entry_prefers_options_over_data(hass) -> None:
    """Runtime config should honor full replacement config stored in entry options."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_ZONES: [],
        },
        options={
            CONF_DEFAULT_HYSTERESIS: 0.6,
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    CONF_TARGET_TEMPERATURE: 20.0,
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=1,
        state=ConfigEntryState.NOT_LOADED,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data.config.default_hysteresis == 0.6
    assert [zone.name for zone in config_entry.runtime_data.config.zones] == ["Living Room"]


async def test_options_update_triggers_entry_reload(hass, config_entry) -> None:
    """Updating entry options should reload the integration immediately."""
    config_entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_reload",
        AsyncMock(return_value=True),
    ) as mock_reload:
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        hass.config_entries.async_update_entry(
            config_entry,
            options={CONF_DEFAULT_HYSTERESIS: 0.5},
        )
        await hass.async_block_till_done()

    mock_reload.assert_awaited_once_with(config_entry.entry_id)


async def test_setup_migrates_legacy_zone_target_entities(hass) -> None:
    """Legacy target entity config should migrate to owned target temperatures."""
    hass.states.async_set("input_number.living_room_target", "20.5")

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    "target_source": "input_number",
                    "target_entity_id": "input_number.living_room_target",
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=1,
        state=ConfigEntryState.NOT_LOADED,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.version == 2
    assert config_entry.data[CONF_ZONES][0][CONF_TARGET_TEMPERATURE] == 20.5
    assert "target_source" not in config_entry.data[CONF_ZONES][0]
    assert "target_entity_id" not in config_entry.data[CONF_ZONES][0]
    assert config_entry.runtime_data.config.zones[0].target_temperature == 20.5


async def test_setup_rejects_legacy_zone_migration_without_usable_target(hass) -> None:
    """Migration should fall back to an owned default when the old target is unreadable."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    "target_source": "input_number",
                    "target_entity_id": "input_number.living_room_target",
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=1,
        state=ConfigEntryState.NOT_LOADED,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.version == 2
    assert config_entry.data[CONF_ZONES][0][CONF_TARGET_TEMPERATURE] == 20.0


async def test_zone_target_updates_persist_in_runtime_store_when_options_own_zones(hass) -> None:
    """Runtime target changes should persist outside options-owned zone config."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            CONF_DEFAULT_HYSTERESIS: 0.3,
            CONF_ZONES: [],
        },
        options={
            CONF_DEFAULT_HYSTERESIS: 0.6,
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    CONF_TARGET_TEMPERATURE: 20.0,
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: [],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=2,
        state=ConfigEntryState.NOT_LOADED,
    )
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("switch.boiler", "off")
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": "climate.multi_zone_heating_living_room",
            "temperature": 21.5,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    assert config_entry.options[CONF_ZONES][0][CONF_TARGET_TEMPERATURE] == 20.0
    assert config_entry.runtime_data.config.zones[0].target_temperature == 21.5
    assert await RuntimeStateStore(hass, config_entry.entry_id).async_load() == {
        "Living Room": {
            CONF_TARGET_TEMPERATURE: 21.5,
            CONF_ENABLED: True,
        }
    }


async def test_setup_restores_runtime_zone_state_before_entities_load(hass) -> None:
    """Setup should overlay persisted runtime-owned zone state onto runtime config."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    CONF_TARGET_TEMPERATURE: 20.0,
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: [],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=2,
        state=ConfigEntryState.NOT_LOADED,
    )
    hass.states.async_set("sensor.living_room_temperature", "19.0")
    hass.states.async_set("switch.boiler", "off")
    config_entry.add_to_hass(hass)

    await RuntimeStateStore(hass, config_entry.entry_id).async_save_zone_state_map(
        {
            "Living Room": {
                CONF_TARGET_TEMPERATURE: 21.5,
                CONF_ENABLED: False,
            }
        }
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.runtime_data.config.zones[0].target_temperature == 21.5
    assert config_entry.runtime_data.config.zones[0].enabled is False
    climate_state = hass.states.get("climate.multi_zone_heating_living_room")
    assert climate_state is not None
    assert climate_state.attributes["temperature"] == 21.5
    assert climate_state.state == "off"


async def test_setup_migrates_legacy_climate_target_entities(hass) -> None:
    """Legacy climate target entities should migrate from their temperature attribute."""
    hass.states.async_set(
        "climate.living_room_target",
        "heat",
        {"temperature": 21.5},
    )

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    "target_source": "climate",
                    "target_entity_id": "climate.living_room_target",
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=1,
        state=ConfigEntryState.NOT_LOADED,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.data[CONF_ZONES][0][CONF_TARGET_TEMPERATURE] == 21.5


async def test_setup_migration_applies_frost_floor_to_legacy_targets(hass) -> None:
    """Legacy targets should migrate upward to the effective frost floor when needed."""
    hass.states.async_set("input_number.living_room_target", "18.0")

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Zone Heating",
        data={
            "frost_protection_min_temp": 19.0,
            CONF_ZONES: [
                {
                    CONF_NAME: "Living Room",
                    CONF_ENABLED: True,
                    CONF_CONTROL_TYPE: ControlType.CLIMATE,
                    "target_source": "input_number",
                    "target_entity_id": "input_number.living_room_target",
                    "frost_protection_min_temp": 21.0,
                    CONF_SENSOR_ENTITY_IDS: ["sensor.living_room_temperature"],
                    CONF_CLIMATE_ENTITY_IDS: ["climate.living_room_radiator"],
                    CONF_LOCAL_GROUPS: [],
                    CONF_AGGREGATION_MODE: AggregationMode.AVERAGE,
                    CONF_PRIMARY_SENSOR_ENTITY_ID: None,
                }
            ],
        },
        version=1,
        state=ConfigEntryState.NOT_LOADED,
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.data[CONF_ZONES][0][CONF_TARGET_TEMPERATURE] == 21.0
