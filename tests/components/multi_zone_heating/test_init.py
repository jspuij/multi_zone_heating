"""Tests for multi_zone_heating entry setup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState

from custom_components.multi_zone_heating.const import DOMAIN
from custom_components.multi_zone_heating.coordinator import MultiZoneHeatingCoordinator
from custom_components.multi_zone_heating.models import RuntimeData


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
