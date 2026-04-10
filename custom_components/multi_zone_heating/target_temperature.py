"""Helpers for integration-owned zone target temperatures."""

from __future__ import annotations

from .const import DEFAULT_ZONE_TARGET_TEMPERATURE


def initial_zone_target_temperature(
    global_frost_protection_min_temp: object | None,
    zone_frost_protection_min_temp: object | None,
) -> float:
    """Compute the initial owned zone target with frost floors applied."""
    target_temperature = DEFAULT_ZONE_TARGET_TEMPERATURE
    for floor in (global_frost_protection_min_temp, zone_frost_protection_min_temp):
        if floor is None:
            continue
        target_temperature = max(target_temperature, float(floor))
    return target_temperature
