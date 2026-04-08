# Multi-Zone Heating Implementation Plan

## Purpose

This document turns the current design and user stories into an implementation sequence for version 1 of the `multi_zone_heating` Home Assistant custom integration.

The plan is optimized for:

- Early end-to-end validation
- Low rework between milestones
- Clear separation between data modeling, control logic, and Home Assistant entity surfaces

## Version 1 Scope

Version 1 includes:

- Config flow and options flow
- Multiple zones
- Zone control types: `climate`, `switch`, `number`
- Local control groups for `switch` and `number`
- Multi-sensor aggregation with `average`, `minimum`, and `primary`
- Global hysteresis
- Main relay control
- Numeric flow meter thresholding
- Relay minimum on and off times
- Relay off-delay and flow-aware shutdown
- Per-zone enable or disable
- Global force-off
- Global and per-zone frost protection minimums
- Zone and system demand entities
- Top-level climate entity with global override target
- Diagnostics and warnings

## Architecture Summary

The integration should be built around four layers:

1. Configuration layer
   Config flow, options flow, config-entry persistence, migration support
2. Domain model and control logic layer
   Pure Python models and decision logic for temperatures, demand, overrides, relay state, and fault handling
3. Runtime coordinator layer
   Home Assistant state subscriptions, scheduling, command dispatch, and transition handling
4. Entity layer
   Binary sensors, sensors, switches, and the top-level climate entity

## Delivery Strategy

Build the integration in vertical slices with an emphasis on getting a basic end-to-end system running early.

Recommended order:

1. Scaffold the integration and basic config entry setup
2. Implement models and pure control logic
3. Implement runtime coordinator and relay control
4. Add climate-controlled zones
5. Add switch and number local control groups
6. Add flow meter handling and warnings
7. Add entities, overrides, and top-level climate behavior
8. Add editing flows, diagnostics polish, and tests

## Milestones

### Milestone 1: Foundation

Goal:
Create a loadable custom integration with config entry plumbing, constants, models, and a testable project structure.

Deliverables:

- `custom_components/multi_zone_heating/` scaffold
- `manifest.json`
- `__init__.py`
- `const.py`
- `models.py`
- Base config entry setup and unload support
- Initial test scaffolding

Related stories:

- US-001
- US-002

### Milestone 2: Core Decision Engine

Goal:
Implement pure logic for temperature aggregation, demand state transitions, frost protection, override evaluation, and relay timing.

Deliverables:

- `control_logic.py`
- Dataclasses for zones, local groups, actuator targets, and runtime state
- Unit tests for aggregation and hysteresis
- Unit tests for relay timing rules

Related stories:

- US-006
- US-007
- US-008
- US-013
- US-014
- US-020
- US-021

### Milestone 3: Runtime Coordinator

Goal:
Subscribe to entity changes, evaluate system state, and dispatch commands safely.

Deliverables:

- `coordinator.py`
- Entity state collection and validation
- Scheduled reevaluation support for relay timing
- Command dispatch helpers
- Availability tracking for sensors and actuators

Related stories:

- US-008
- US-012
- US-013
- US-014
- US-015

### Milestone 4: Zone Control Types

Goal:
Support all three zone control styles required for version 1.

Deliverables:

- Climate zone handling
- Switch local control groups
- Number local control groups
- Shared zone target behavior across groups
- Actuator write helpers per control type

Related stories:

- US-003
- US-004
- US-005
- US-009
- US-010
- US-011

### Milestone 5: Relay, Flow, and Overrides

Goal:
Make whole-system operation reliable and understandable.

Deliverables:

- Main relay state machine
- Numeric flow threshold support
- Demand-without-flow warning handling
- Per-zone enable or disable
- Global force-off behavior
- Frost protection integration into target resolution

Related stories:

- US-013
- US-014
- US-015
- US-016
- US-017
- US-020
- US-021

### Milestone 6: Entity Surface and UX

Goal:
Expose the system in Home Assistant with useful entities and a coherent top-level control model.

Deliverables:

- Zone demand binary sensors
- System demand binary sensor
- Diagnostic sensors
- Zone enable switches
- Global force-off switch
- Top-level system climate entity
- `clear_override` service or equivalent action

Related stories:

- US-016
- US-017
- US-018
- US-019
- US-022

### Milestone 7: Configuration Editing and Quality

Goal:
Make the integration maintainable and ready for real use.

Deliverables:

- Options flow for editing zones and local groups
- Diagnostics output
- Integration tests
- Migration support for evolving config schema
- User-facing documentation inside the repo

Related stories:

- US-023

## Technical Design Decisions

### Configuration Approach

- Use Home Assistant config flow and options flow only
- Do not write YAML configuration files
- Persist user configuration in config entries

### Flow Meter Handling

- Flow source is a numeric sensor
- A configurable threshold determines whether flow is considered present
- Flow is used to:
  - delay relay-off until flow falls below threshold
  - raise warnings when demand exists but flow does not exceed threshold after relay-on
- Flow is not used to infer zero-demand faults because domestic water heating shares the same meter

### Top-Level Climate Behavior

- Supports `heat` and `off`
- `off` maps to global force-off
- `heat` clears global force-off
- Setting target temperature creates a global override target
- Override ends when a zone target changes or when explicitly cleared
- Override persists while HVAC mode is `off`
- Setting target temperature while `off` stores the override without resuming heating

### Frost Protection

- Included in version 1
- Support global minimum temperature
- Support per-zone minimum temperature overrides
- Effective target temperature is never allowed below the applicable frost minimum

## Suggested File Layout

```text
custom_components/
  multi_zone_heating/
    __init__.py
    manifest.json
    const.py
    config_flow.py
    coordinator.py
    models.py
    control_logic.py
    binary_sensor.py
    climate.py
    number.py
    sensor.py
    switch.py
    switch.py
    climate.py
    diagnostics.py
    services.yaml
    strings.json
    translations/
      en.json
tests/
  components/
    multi_zone_heating/
```

## Risks and Mitigations

### Risk: Complex configuration for local control groups

Mitigation:

- Keep version 1 options flow structured and explicit
- Favor a small number of required fields
- Add validation that each local group has both sensors and actuators

### Risk: Climate entity semantics are awkward for "no meaningful target"

Mitigation:

- Expose explicit attributes for override state
- Retain last override target for compatibility while using `override_active` to express truth

### Risk: Relay timing and flow handling create edge cases

Mitigation:

- Keep timing decisions in pure logic with tests
- Separate desired relay state from actual relay command timing

### Risk: Availability handling becomes inconsistent between zone types

Mitigation:

- Centralize availability evaluation in shared helpers
- Test climate zones and local-group zones separately

## Completion Criteria

Version 1 is complete when:

- A user can configure a system fully from the UI
- All required zone types work
- Relay behavior is stable
- Flow warnings and relay-off delay work
- Override behavior is consistent
- The top-level climate entity behaves as designed
- Core logic is covered by tests
- The integration exposes enough diagnostics for troubleshooting

## Issue Breakdown

Implementation work is split into issue-sized documents under [docs/issues](/Users/jws/Projects/thermostat/docs/issues).
