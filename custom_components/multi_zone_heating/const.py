"""Constants for the multi_zone_heating integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "multi_zone_heating"
NAME = "Multi-Zone Heating"
DEFAULT_TITLE = NAME
CONFIG_ENTRY_VERSION = 2
DEFAULT_ZONE_TARGET_TEMPERATURE = 20.0

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
)
