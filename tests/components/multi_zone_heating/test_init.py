"""Tests for multi_zone_heating entry setup."""

from __future__ import annotations

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
    CONF_TARGET_ENTITY_ID,
    CONF_TARGET_SOURCE,
    CONF_ZONES,
)
from custom_components.multi_zone_heating.coordinator import MultiZoneHeatingCoordinator
from custom_components.multi_zone_heating.models import (
    AggregationMode,
    ControlType,
    RuntimeData,
    TargetSourceType,
)
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
                    CONF_TARGET_SOURCE: TargetSourceType.CLIMATE,
                    CONF_TARGET_ENTITY_ID: "climate.living_room_target",
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
