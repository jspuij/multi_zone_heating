# Multi-Zone Heating Implementation Plan

## Purpose

This document turns the current design and user stories into an implementation sequence for version 1 of the `multi_zone_heating` Home Assistant custom integration.

The plan is optimized for:

- Early end-to-end validation
- Low rework between milestones
- Clear separation between data modeling, control logic, runtime ownership, and Home Assistant entity surfaces

## Version 1 Scope

Version 1 includes:

- Config flow and options flow
- Multiple zones
- One virtual climate entity per zone
- Integration-owned persistence of zone target temperatures
- Zone control types: `climate`, `switch`, `number`
- Local control groups for `switch` and `number`
- Multi-sensor aggregation with `average`, `minimum`, and `primary`
- Zone climate `current_temperature` derived from the configured aggregation algorithm
- Global hysteresis
- Main relay control
- Numeric flow meter thresholding
- Relay minimum on and off times
- Relay off-delay and flow-aware shutdown
- Per-zone enable or disable
- Global force-off
- Global and per-zone frost protection minimums
- Zone and system demand entities
- Top-level climate entity with master control semantics
- Diagnostics and warnings
- Config migration away from `target_source` and `target_entity_id`

## Architecture Summary

The integration should be built around four layers:

1. Configuration layer
   Config flow, options flow, config-entry persistence, migration support
2. Domain model and control logic layer
   Pure Python models and decision logic for temperatures, demand, frost protection, relay state, and fault handling
3. Runtime coordinator layer
   Home Assistant state subscriptions, zone-target persistence ownership, scheduling, and slave command dispatch
4. Entity layer
   Zone climates, system climate, binary sensors, sensors, and switches

## Delivery Strategy

Build the integration in vertical slices with an emphasis on getting a stable master / slave model working early.

Recommended order:

1. Replace the zone target config model and add migration support
2. Implement integration-owned zone target persistence
3. Add zone virtual climate entities
4. Update runtime coordinator to read zone targets from owned zone climate state only
5. Update slave actuator dispatch for `climate`, `switch`, and `number`
6. Add relay, flow, and diagnostics behavior
7. Add top-level climate behavior aligned with the new model
8. Finish options flow, diagnostics polish, and tests

## Milestones

### Milestone 1: Schema And Migration

Goal:
Replace external target-entity configuration with zone-owned target state and migration support.

Deliverables:

- Updated config schema without `target_source` or `target_entity_id`
- Config-entry migration logic
- Updated config flow and options flow forms
- Tests for new and migrated config entries

Related stories:

- US-001
- US-002
- US-024

### Milestone 2: Core Decision Engine

Goal:
Implement pure logic for temperature aggregation, demand state transitions, frost protection, and relay timing using integration-owned zone targets.

Deliverables:

- Updated `models.py`
- Updated `control_logic.py`
- Unit tests for aggregation and hysteresis
- Unit tests that validate zone climate `current_temperature` behavior
- Unit tests for relay timing rules

Related stories:

- US-005
- US-006
- US-007
- US-008
- US-009
- US-014
- US-015
- US-022
- US-023

### Milestone 3: Zone Climate Ownership

Goal:
Create the per-zone virtual climate entities and persist zone target temperatures in integration-owned state.

Deliverables:

- Zone virtual climate entities in `climate.py`
- Restore-state behavior for zone targets
- Zone climate current temperature projection from aggregation logic
- Coordinator APIs for reading and updating owned zone targets

Related stories:

- US-005
- US-008
- US-020

### Milestone 4: Runtime Coordinator

Goal:
Subscribe to relevant entity changes, evaluate system state, and dispatch commands safely in a strict master / slave model.

Deliverables:

- Updated `coordinator.py`
- Entity state collection and validation
- Owned target reads from zone climate state only
- Scheduled reevaluation support for relay timing
- Command dispatch helpers
- Availability tracking for sensors and actuators

Related stories:

- US-009
- US-013
- US-014
- US-015
- US-016

### Milestone 5: Zone Control Types

Goal:
Support all three zone and actuator control styles with zone climates as masters and actuators as slaves.

Deliverables:

- Slave climate zone handling
- Switch local control group handling
- Number local control group handling
- Shared zone target behavior across groups
- Actuator write helpers per control type

Related stories:

- US-003
- US-004
- US-010
- US-011
- US-012
- US-013

### Milestone 6: Relay, Overrides, And UX

Goal:
Make whole-system operation reliable and understandable with the new target ownership model.

Deliverables:

- Main relay state machine
- Numeric flow threshold support
- Demand-without-flow warning handling
- Per-zone enable or disable
- Global force-off behavior
- Top-level climate semantics aligned with zone-owned targets

Related stories:

- US-016
- US-017
- US-018
- US-019
- US-021

### Milestone 7: Diagnostics And Quality

Goal:
Make the integration maintainable and ready for real use.

Deliverables:

- Diagnostics output
- Integration tests
- Translation updates
- Documentation updates inside the repo

Related stories:

- US-019
- US-025
- US-026

## Technical Design Decisions

### Configuration Approach

- Use Home Assistant config flow and options flow only
- Do not write YAML configuration files
- Persist user configuration in config entries
- Persist zone-owned target temperatures in integration-managed state or config

### Zone Climate Ownership

- Each zone has one virtual climate entity owned by this integration
- The zone climate is the only source of truth for that zone target
- External climate entities, if configured, are slave actuators only
- The coordinator must not read target temperature from slave entities

### Zone Climate Temperature Presentation

- `current_temperature` is computed from the configured zone aggregation logic
- `average` uses the mean of available zone sensors
- `minimum` uses the lowest available zone sensor
- `primary` uses the configured primary sensor directly

### Top-Level Climate Behavior

- Supports `heat` and `off`
- `off` maps to global force-off
- `heat` clears global force-off
- If it supports target writes, they must update zone-owned targets through integration logic
- It must not reintroduce external target-source ownership indirectly

### Frost Protection

- Included in version 1
- Support global minimum temperature
- Support per-zone minimum temperature overrides
- Effective target temperature is never allowed below the applicable frost minimum
