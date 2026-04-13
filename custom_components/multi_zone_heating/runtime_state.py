"""Runtime-owned state persistence for multi_zone_heating."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .models import IntegrationConfig, ZoneConfig

_STORAGE_VERSION = 1


class RuntimeStateStore:
    """Persist runtime-owned zone state outside config-entry reload paths."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the runtime state store for one config entry."""
        self._store = Store[dict[str, Any]](
            hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.runtime_state.{entry_id}",
        )

    async def async_apply_to_config(self, config: IntegrationConfig) -> None:
        """Overlay persisted runtime-owned state onto the in-memory config."""
        zones = await self.async_load()
        if not zones:
            return

        for zone in config.zones:
            self._apply_zone_state(zone, zones.get(zone.name))

    async def async_load(self) -> dict[str, dict[str, Any]]:
        """Load the persisted zone state payload."""
        payload = await self._store.async_load()
        if not isinstance(payload, dict):
            return {}

        zones = payload.get("zones")
        if not isinstance(zones, dict):
            return {}

        return {
            str(zone_name): dict(zone_state)
            for zone_name, zone_state in zones.items()
            if isinstance(zone_state, Mapping)
        }

    async def async_save_zones(self, zones: list[ZoneConfig]) -> None:
        """Persist the current runtime-owned state for all configured zones."""
        await self.async_save_zone_state_map(
            {
                zone.name: {
                    "target_temperature": zone.target_temperature,
                    "enabled": zone.enabled,
                }
                for zone in zones
            }
        )

    async def async_save_zone_state_map(
        self,
        zones: Mapping[str, Mapping[str, Any]],
    ) -> None:
        """Persist a prebuilt zone state payload."""
        await self._store.async_save(
            {
                "zones": {str(zone_name): dict(zone_state) for zone_name, zone_state in zones.items()}
            }
        )

    def _apply_zone_state(
        self,
        zone: ZoneConfig,
        zone_state: Mapping[str, Any] | None,
    ) -> None:
        """Apply one stored zone state record to a runtime config zone."""
        if zone_state is None:
            return

        target_temperature = _coerce_float(zone_state.get("target_temperature"))
        if target_temperature is not None:
            zone.target_temperature = target_temperature

        enabled = zone_state.get("enabled")
        if isinstance(enabled, bool):
            zone.enabled = enabled


def _coerce_float(value: object) -> float | None:
    """Convert a persisted numeric value into a float when possible."""
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
