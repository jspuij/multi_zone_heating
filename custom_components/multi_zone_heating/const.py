"""Constants for the multi_zone_heating integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "multi_zone_heating"
NAME = "Multi-Zone Heating"
DEFAULT_TITLE = NAME
CONFIG_ENTRY_VERSION = 2
DEFAULT_ZONE_TARGET_TEMPERATURE = 20.0
RELOAD_BOUNDARY_TERMINOLOGY = "runtime-versus-structural"

STRUCTURAL_RELOAD_EXAMPLES: tuple[str, ...] = (
    "adding, removing, or renaming zones",
    "changing zone control type",
    "changing configured sensors, actuators, local groups, relay, or flow sensor bindings",
    "changing global timing, flow, frost, or failsafe settings through the options flow",
)

RUNTIME_NO_RELOAD_EXAMPLES: tuple[str, ...] = (
    "setting a zone climate target temperature",
    "setting a zone climate hvac_mode to enable or disable a zone",
    "setting the system climate target and fanning it out to zones",
    "toggling global force-off",
)

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
)
