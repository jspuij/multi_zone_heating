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
- Per-zone open door/window detection from configured binary sensors
- Global force-off
- Global and per-zone frost protection minimums
- Zone and system demand entities
- Top-level climate entity with master control semantics
- Slave climate HVAC mode following the virtual zone master instead of demand edges
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
8. Add per-zone open door/window sensor configuration and runtime inhibition
9. Finish options flow, diagnostics polish, and tests

Step 8 is not a standalone milestone. It maps across schema work, pure decision logic, coordinator subscriptions, actuator dispatch, diagnostics, and tests in Milestones 1, 2, 4, 6, and 7.

## Runtime Persistence Fix Plan

The current runtime bug shows that zone climate target and enable changes are being persisted through config-entry updates, which causes the integration to reload and briefly drop its entities. The fix should separate structural configuration from runtime-owned thermostat state.

Recommended sequence:

1. Define reload boundaries explicitly.
   Structural edits made through the options flow should continue to reload the integration. Runtime climate actions such as zone target changes, zone enable or disable, and system target fan-out must not trigger config-entry reloads.
2. Introduce a runtime-owned persistence layer.
   Move per-zone target temperature and zone enabled state out of config-entry update paths. Persist them in integration-managed runtime storage that survives restart without requiring entry reload.
3. Restore runtime-owned state during startup.
   On setup, load persisted zone targets and enabled flags before entities are added so the virtual climates come up with stable state immediately.
4. Keep config-entry payloads structural only.
   The config entry should continue to describe zone topology, entity bindings, timing rules, frost settings, and other wiring data, but not mutable thermostat operating state.
5. Narrow reload behavior to structural edits.
   Update the config-entry listener and related flows so that reloads still happen after zone topology or global setting edits, but not after runtime thermostat commands.
6. Add regression coverage around entity availability.
   Tests should verify that changing a zone target, zone HVAC mode, or system target does not unload climate entities or surface `Unavailable`, while structural options edits still reload as expected.

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
- US-027
- US-024

### Milestone 2: Core Decision Engine

Goal:
Implement pure logic for temperature aggregation, demand state transitions, open door/window inhibition, frost protection, and relay timing using integration-owned zone targets.

Deliverables:

- Updated `models.py`
- Updated `control_logic.py`
- Unit tests for aggregation and hysteresis
- Unit tests for open door/window inhibition
- Unit tests that validate zone climate `current_temperature` behavior
- Unit tests for relay timing rules

Related stories:

- US-005
- US-006
- US-007
- US-008
- US-009
- US-027
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
- Door/window sensor state collection and validation
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
- US-027

### Milestone 5: Zone Control Types

Goal:
Support all three zone and actuator control styles with zone climates as masters and actuators as slaves.

Deliverables:

- Slave climate zone handling
- Slave climate target sync while zone-enabled master state owns `heat` or `off`
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
Make whole-system operation reliable and understandable with the new target ownership model, including automatic per-zone inhibition when configured openings are open.

Deliverables:

- Main relay state machine
- Numeric flow threshold support
- Demand-without-flow warning handling
- Per-zone enable or disable
- Per-zone door/window sensor selection and automatic zone inhibition
- Zone climate HVAC mode aligned with zone enable or disable state
- Global force-off behavior
- Top-level climate semantics aligned with zone-owned targets

Related stories:

- US-016
- US-017
- US-018
- US-019
- US-021
- US-027

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
- US-027

## Technical Design Decisions

### Configuration Approach

- Use Home Assistant config flow and options flow only
- Do not write YAML configuration files
- Persist user configuration in config entries
- Persist zone-owned target temperatures and zone enabled state in integration-managed runtime storage
- Keep config entries limited to structural configuration that defines setup, subscriptions, and entity topology

### Reload Boundaries

- Reload the entry when structural configuration changes
- Structural changes include zone additions or removals, zone renames, control-type changes, sensor or actuator membership changes, local-group edits, relay or flow entity changes, and global timing or safety settings changed through the options flow
- Door/window sensor membership is structural per-zone configuration and changes through config or options flow may reload the entry
- Do not reload the entry for runtime thermostat actions
- Runtime actions include zone target changes, zone HVAC mode changes that map to enable or disable, system climate target fan-out, and global force-off toggles
- Runtime door/window sensor state changes must reevaluate zones in place without updating config entries or unloading platforms
- Runtime actions must update entity state in place and persist without unloading platforms

### Zone Climate Ownership

- Each zone has one virtual climate entity owned by this integration
- The zone climate is the only source of truth for that zone target
- External climate entities, if configured, are slave actuators only
- The coordinator must not read target temperature from slave entities
- The zone climate `hvac_mode` is the canonical enabled or disabled state for the zone
- Zone target and enabled-state writes must not go through config-entry reload paths

### Door/Window Detection

- Each zone may configure zero or more open-state detector entities
- Detector entities are selected from Home Assistant `binary_sensor` entities, including sensors with door, window, or opening device classes
- A configured detector is considered open when its state is `on`
- A zone is effectively disabled while one or more configured detector entities in that zone are open
- Open-detector inhibition is runtime state and must not overwrite the persisted manual zone enabled state
- Closing the last open detector automatically removes the inhibition
- After inhibition clears, the zone resumes normal control only if it is manually enabled and global force-off is inactive
- While inhibited, the zone must not generate heat demand and downstream actuators follow the same safe inactive behavior used for an effective zone disable
- System demand and relay decisions must ignore inhibited zone demand
- Diagnostics should expose configured detector entities, currently open detector entities, unavailable detector entities, and whether the zone is inhibited by openings
- Unavailable detector entities do not count as open in version 1, but they must be visible in diagnostics; persistent notifications or repair flows are future work
- Open-detector inhibition is immediate in version 1; debounce, grace periods, and configurable open-delay behavior are future work

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

### Slave Climate Behavior

- Slave climate targets follow the zone-owned target while the zone is enabled
- Slave climate HVAC mode follows the virtual zone or global master state, not momentary demand transitions
- Clearing zone demand must not turn slave climates `off` by itself
- Zone disable and global force-off may turn slave climates `off` or apply a configured fallback target where `off` is unsupported

### Frost Protection

- Included in version 1
- Support global minimum temperature
- Support per-zone minimum temperature overrides
- Effective target temperature is never allowed below the applicable frost minimum
