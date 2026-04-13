"""The multi_zone_heating integration."""

from __future__ import annotations

from copy import deepcopy
import logging
from typing import TYPE_CHECKING, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .const import (
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    PLATFORMS,
    RELOAD_BOUNDARY_TERMINOLOGY,
)
from .coordinator import MultiZoneHeatingCoordinator, integration_config_from_dict
from .models import RuntimeData
from .runtime_state import RuntimeStateStore
from .target_temperature import initial_zone_target_temperature

if TYPE_CHECKING:
    MultiZoneHeatingConfigEntry: TypeAlias = ConfigEntry[RuntimeData]
else:
    # Older Home Assistant test targets expose ConfigEntry as a non-generic type.
    MultiZoneHeatingConfigEntry: TypeAlias = ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> bool:
    """Migrate older config entries to the current schema."""
    if entry.version >= CONFIG_ENTRY_VERSION:
        return True

    if entry.version != 1:
        _LOGGER.error("Unsupported config entry version %s", entry.version)
        return False

    migrated_data = _migrate_payload(hass, dict(entry.data), fallback_payload=dict(entry.data))
    if migrated_data is None:
        return False

    migrated_options = _migrate_payload(
        hass,
        dict(entry.options),
        fallback_payload=dict(entry.data),
    )
    if migrated_options is None:
        return False

    hass.config_entries.async_update_entry(
        entry,
        data=migrated_data,
        options=migrated_options,
        version=CONFIG_ENTRY_VERSION,
    )
    _LOGGER.info("Migrated config entry %s to version %s", entry.entry_id, CONFIG_ENTRY_VERSION)
    return True


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
    runtime_state_store = RuntimeStateStore(hass, entry.entry_id)
    await runtime_state_store.async_apply_to_config(config)
    coordinator = MultiZoneHeatingCoordinator(
        hass,
        config,
        config_entry=entry,
        runtime_state_store=runtime_state_store,
    )
    entry.runtime_data = RuntimeData(
        config_entry_id=entry.entry_id,
        title=entry.title,
        config=config,
        coordinator=coordinator,
    )
    domain_data[entry.entry_id] = entry.runtime_data

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
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> None:
    """Reload the entry when structural options change."""
    _LOGGER.debug(
        "Reloading config entry %s after a structural options update (%s)",
        entry.entry_id,
        RELOAD_BOUNDARY_TERMINOLOGY,
    )
    await hass.config_entries.async_reload(entry.entry_id)


def _migrate_payload(
    hass: HomeAssistant,
    payload: dict[str, object],
    *,
    fallback_payload: dict[str, object],
) -> dict[str, object] | None:
    """Migrate one config payload that may contain zone definitions."""
    zones = payload.get("zones")
    if not isinstance(zones, list):
        return payload

    migrated_payload = deepcopy(payload)
    # Options may override only zone definitions and omit the global frost minimum,
    # so keep the data payload as the fallback source for that shared setting.
    global_frost = migrated_payload.get(
        "frost_protection_min_temp",
        fallback_payload.get("frost_protection_min_temp"),
    )
    migrated_zones = []
    for zone_data in zones:
        migrated_zone = _migrate_zone_data(
            hass,
            zone_data,
            global_frost_protection_min_temp=global_frost,
        )
        if migrated_zone is None:
            return None
        migrated_zones.append(migrated_zone)

    migrated_payload["zones"] = migrated_zones
    return migrated_payload


def _migrate_zone_data(
    hass: HomeAssistant,
    zone_data: object,
    *,
    global_frost_protection_min_temp: object | None,
) -> dict[str, object] | None:
    """Migrate one zone from external targets to an owned target value."""
    if not isinstance(zone_data, dict):
        return None

    migrated_zone = deepcopy(zone_data)
    if "target_temperature" in migrated_zone:
        migrated_zone.pop("target_source", None)
        migrated_zone.pop("target_entity_id", None)
        return migrated_zone

    target_entity_id = migrated_zone.get("target_entity_id")
    zone_name = migrated_zone.get("name", "<unknown>")
    target_temperature = _read_legacy_target_temperature(hass, target_entity_id)
    fallback_target_temperature = initial_zone_target_temperature(
        global_frost_protection_min_temp,
        migrated_zone.get("frost_protection_min_temp"),
    )
    if target_temperature is None:
        _LOGGER.warning(
            "Migrating zone %s without a readable target from %s; using fallback target %s",
            zone_name,
            target_entity_id,
            fallback_target_temperature,
        )
        target_temperature = fallback_target_temperature

    migrated_zone["target_temperature"] = max(
        target_temperature,
        fallback_target_temperature,
    )
    migrated_zone.pop("target_source", None)
    migrated_zone.pop("target_entity_id", None)
    return migrated_zone


def _read_legacy_target_temperature(
    hass: HomeAssistant,
    target_entity_id: object | None,
) -> float | None:
    """Read the current target from an old external target entity."""
    if not isinstance(target_entity_id, str):
        return None

    state = hass.states.get(target_entity_id)
    if state is None or state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
        return None

    if target_entity_id.startswith("climate."):
        value = state.attributes.get("temperature")
    else:
        value = state.state

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
