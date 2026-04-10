"""Diagnostics support for multi_zone_heating."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.core import HomeAssistant

from . import MultiZoneHeatingConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: MultiZoneHeatingConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    del hass

    runtime_data = getattr(entry, "runtime_data", None)
    coordinator = runtime_data.coordinator if runtime_data is not None else None

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
        },
        "config": _serialize_value(runtime_data.config if runtime_data is not None else dict(entry.data)),
        "runtime": {
            "loaded": coordinator is not None,
            "global_force_off": coordinator.data.global_force_off
            if coordinator is not None and coordinator.data is not None
            else None,
            "snapshot": _serialize_value(coordinator.data) if coordinator is not None else None,
        },
    }


def _serialize_value(value: Any) -> Any:
    """Convert runtime models into JSON-serializable diagnostics data."""
    if is_dataclass(value):
        return {
            field.name: _serialize_value(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): _serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]

    return value
