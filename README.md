# Thermostat

This repository contains the design and, later, the implementation of a custom Home Assistant integration for controlling a multi-zone heating system.

The target system has:

- Multiple heating zones
- One or more room temperature sensors per zone
- A thermostat target temperature per zone
- One or more controllable thermostatic valves per zone
- A shared relay that enables or disables water flow for the entire system
- An optional flow meter for relay shutoff validation and flow diagnostics

The integration will coordinate zone-level heat demand and whole-home water flow in a configurable, Home Assistant-native way.

## Goals

- Support multiple independent zones
- Control a shared main relay based on aggregate heating demand
- Keep configuration in the Home Assistant UI where possible
- Expose clear entities for diagnostics, status, and overrides
- Avoid relay chatter with hysteresis and minimum run/off times
- Be flexible enough for different valve types and target sources

## Documentation

- [Integration design](/Users/jws/Projects/thermostat/docs/integration-design.md)

## Developer Notes

- Home Assistant expects `custom_components/multi_zone_heating/strings.json` and `custom_components/multi_zone_heating/translations/en.json` to stay in sync. When config-flow copy changes, update both files together.

## Planned Capabilities

- Per-zone configuration for one or more sensor entities, one target, and one or more valve entities
- Optional local control groups within a zone for `switch` and `number` actuators
- Main relay control based on any active zone demand
- Configurable hysteresis and timing safeguards
- Optional flow-aware relay shutdown and warning state when demand has no flow
- Manual override support
- Optional maintenance and frost protection modes
- Diagnostics for why heat is or is not active

## Implementation Direction

The preferred implementation is a custom Home Assistant integration under `custom_components/multi_zone_heating/`.

The integration is expected to use:

- A config flow for initial setup
- An options flow for editing zones and control parameters
- Coordinator-driven control logic
- Entities for zone demand, system demand, and system state

## Status

This repository currently starts with the design phase. The next step is to refine the architecture and then scaffold the custom integration.
