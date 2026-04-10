"""The multi_zone_heating integration."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS
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
    domain_data: dict[str, RuntimeData] = hass.data.setdefault(DOMAIN, {})
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    merged_config = deepcopy(dict(entry.data))
    merged_config.update(deepcopy(dict(entry.options)))
    config = integration_config_from_dict(merged_config)
    coordinator = MultiZoneHeatingCoordinator(hass, config, config_entry=entry)
    entry.runtime_data = RuntimeData(
        config_entry_id=entry.entry_id,
        title=entry.title,
        config=config,
        coordinator=coordinator,
    )
    domain_data[entry.entry_id] = entry.runtime_data

    if not hass.services.has_service(DOMAIN, "clear_override"):

        async def _async_handle_clear_override(_call: ServiceCall) -> None:
            """Clear overrides across loaded integration entries."""
            await _async_clear_overrides(hass)

        hass.services.async_register(
            DOMAIN,
            "clear_override",
            _async_handle_clear_override,
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
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, "clear_override")
    return unloaded


async def _async_clear_overrides(hass: HomeAssistant) -> None:
    """Clear runtime overrides for all loaded entries."""
    for runtime_data in hass.data.get(DOMAIN, {}).values():
        if runtime_data.coordinator is not None:
            await runtime_data.coordinator.async_clear_global_override()


async def _async_update_listener(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> None:
    """Reload the entry when options change so runtime state stays in sync."""
    await hass.config_entries.async_reload(entry.entry_id)
