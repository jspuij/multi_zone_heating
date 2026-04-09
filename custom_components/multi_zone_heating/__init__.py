"""The multi_zone_heating integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .models import RuntimeData
from .coordinator import MultiZoneHeatingCoordinator, integration_config_from_dict

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
    config = integration_config_from_dict(entry.data)
    coordinator = MultiZoneHeatingCoordinator(hass, config, config_entry=entry)
    entry.runtime_data = RuntimeData(
        config_entry_id=entry.entry_id,
        config=config,
        coordinator=coordinator,
    )
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator = entry.runtime_data.coordinator
        if coordinator is not None:
            await coordinator.async_stop()
    return unloaded
