"""The multi_zone_heating integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .models import RuntimeData

if TYPE_CHECKING:
    MultiZoneHeatingConfigEntry: TypeAlias = ConfigEntry[RuntimeData]
else:
    # Older Home Assistant test targets expose ConfigEntry as a non-generic type.
    MultiZoneHeatingConfigEntry: TypeAlias = ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> bool:
    """Set up multi_zone_heating from a config entry."""
    entry.runtime_data = RuntimeData(config_entry_id=entry.entry_id)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
