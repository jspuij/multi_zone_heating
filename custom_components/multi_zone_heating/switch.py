"""Switch platform for multi_zone_heating."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant

from . import MultiZoneHeatingConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
    async_add_entities: Callable[[list[Any]], None],
) -> None:
    """Set up switches for a config entry."""
