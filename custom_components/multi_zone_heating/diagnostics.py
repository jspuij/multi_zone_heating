"""Diagnostics support for multi_zone_heating."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from homeassistant.core import HomeAssistant

from . import MultiZoneHeatingConfigEntry
from .const import (
    RELOAD_BOUNDARY_TERMINOLOGY,
    RUNTIME_NO_RELOAD_EXAMPLES,
    STRUCTURAL_RELOAD_EXAMPLES,
)
from .models import ZoneConfig, ZoneEvaluation


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
        "reload_boundaries": {
            "terminology": RELOAD_BOUNDARY_TERMINOLOGY,
            "structural_changes_reload": list(STRUCTURAL_RELOAD_EXAMPLES),
            "runtime_actions_do_not_reload": list(RUNTIME_NO_RELOAD_EXAMPLES),
        },
        "runtime": {
            "loaded": coordinator is not None,
            "global_force_off": coordinator.data.global_force_off
            if coordinator is not None and coordinator.data is not None
            else None,
            "system_climate": _system_climate_diagnostics(coordinator),
            "zone_climates": _zone_climate_diagnostics(coordinator),
            "snapshot": _serialize_value(coordinator.data) if coordinator is not None else None,
        },
    }


def _system_climate_diagnostics(coordinator: Any) -> dict[str, Any] | None:
    """Return a diagnostics-friendly view of the system climate surface."""
    if coordinator is None or coordinator.data is None:
        return None

    visible_temperatures: list[float] = []
    for evaluation in coordinator.data.zone_evaluations:
        if evaluation.current_temperature is not None:
            visible_temperatures.append(evaluation.current_temperature)
        for group in evaluation.local_groups:
            if group.current_temperature is not None:
                visible_temperatures.append(group.current_temperature)

    targets = {
        evaluation.target_temperature
        for evaluation in coordinator.data.zone_evaluations
        if evaluation.target_temperature is not None
    }
    target_temperature = next(iter(targets)) if len(targets) == 1 else None

    return {
        "hvac_mode": "off" if coordinator.data.global_force_off else "heat",
        "hvac_action": (
            "off"
            if coordinator.data.global_force_off
            else "heating" if coordinator.data.system_demand else "idle"
        ),
        "target_temperature": target_temperature,
        "current_temperature": (
            sum(visible_temperatures) / len(visible_temperatures)
            if visible_temperatures
            else None
        ),
        "zones_calling_for_heat": [
            evaluation.name
            for evaluation in coordinator.data.zone_evaluations
            if evaluation.demand
        ],
        "zone_target_temperatures": {
            evaluation.name: evaluation.target_temperature
            for evaluation in coordinator.data.zone_evaluations
        },
        "global_force_off": coordinator.data.global_force_off,
    }


def _zone_climate_diagnostics(coordinator: Any) -> list[dict[str, Any]] | None:
    """Return zone climate details that reflect the owned target model."""
    if coordinator is None or coordinator.data is None:
        return None

    diagnostics: list[dict[str, Any]] = []
    evaluations_by_name = {
        evaluation.name: evaluation for evaluation in coordinator.data.zone_evaluations
    }
    for zone in coordinator.config.zones:
        evaluation = evaluations_by_name.get(zone.name)
        if evaluation is None:
            continue
        diagnostics.append(
            _zone_diagnostics(
                zone,
                evaluation,
                global_force_off=coordinator.data.global_force_off,
            )
        )
    return diagnostics


def _zone_diagnostics(
    zone: ZoneConfig,
    evaluation: ZoneEvaluation,
    *,
    global_force_off: bool,
) -> dict[str, Any]:
    """Assemble one zone climate diagnostics record."""
    return {
        "name": zone.name,
        "hvac_mode": "heat" if zone.enabled else "off",
        "hvac_action": (
            "off"
            if not zone.enabled or global_force_off or evaluation.opening_inhibited
            else "heating" if evaluation.demand else "idle"
        ),
        "control_type": zone.control_type.value,
        "aggregation_mode": zone.aggregation_mode.value,
        "enabled": zone.enabled,
        "demand": evaluation.demand,
        "global_force_off": global_force_off,
        "opening_inhibited": evaluation.opening_inhibited,
        "open_detector_entity_ids": evaluation.open_detector_entity_ids,
        "open_detector_open_entity_ids": evaluation.open_detector_open_entity_ids,
        "open_detector_unavailable_entity_ids": (
            evaluation.open_detector_unavailable_entity_ids
        ),
        "target_temperature": evaluation.target_temperature,
        "effective_target_temperature": evaluation.effective_target_temperature,
        "current_temperature": evaluation.current_temperature,
        "available_sensor_entity_ids": evaluation.available_sensor_entity_ids,
        "available_actuator_entity_ids": evaluation.available_actuator_entity_ids,
        "local_groups": _serialize_value(evaluation.local_groups),
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
