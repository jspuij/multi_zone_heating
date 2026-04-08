"""Constants for the multi_zone_heating integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "multi_zone_heating"
NAME = "Multi-Zone Heating"
DEFAULT_TITLE = NAME

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
)
