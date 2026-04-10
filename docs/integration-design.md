# Multi-Zone Heating Integration Design

## Purpose

Design a custom Home Assistant integration that coordinates a multi-zone wet heating system with:

- One or more controllable valves per zone
- One or more room temperature sensors per zone
- One target temperature source per zone
- One shared relay that enables water flow for the full system

The key control rule is straightforward:

- If one or more zones require heat, open the main relay.
- If no zones require heat, close the main relay.

Zone valves are controlled independently according to each zone's temperature, target, and configuration.

## Design Goals

- Be configurable from the Home Assistant UI
- Model heating demand explicitly, not only final outputs
- Keep control logic centralized and testable
- Support a range of zone hardware capabilities
- Prevent short-cycling and relay chatter
- Provide diagnostics and override mechanisms
- Make it easy to add or remove zones later

## Non-Goals

- Replacing a full scheduling UI
- Implementing boiler modulation logic
- Vendor-specific thermostat integrations
- Predictive heating in the first version

## Core Concepts

### Zone

A zone is an independently controlled heated space. A zone has:

- A name
- One or more temperature sensors
- A target temperature source
- One or more control targets
- Optional enable/disable state
- Optional per-zone tuning values

Each zone behaves as a logical grouping. For example, a large living area may have:

- Multiple temperature sensors across the space
- Multiple thermostatic valves on separate radiators or local spots

Zone-level sensors are primarily relevant for `climate` controlled zones.

For `switch` and `number` controlled zones, sensing and actuation should usually be modeled through local control groups, where each group measures and controls its own local spot.

The integration should compute one demand state for the zone.

For `climate` control, all climate entities in the zone move together.

For `switch` and `number` control, a zone may contain one or more local control groups. These groups represent local spots inside the room and pair local temperature measurement with local actuation, while still sharing the same zone target temperature.

If a local spot needs its own target temperature, it should be modeled as a separate zone instead.

### Local Control Group

A local control group is a sub-part of a zone used for `switch` and `number` based control.

Each local control group must have:

- One or more temperature sensors
- One or more actuator entities
- One control type: `switch` or `number`

The intent is that the actuators in the group primarily affect the measured temperature of that same local spot. In other words, a group is a paired sensor-and-actuator combination inside a shared zone.

All groups in a zone share the same target temperature, but each group computes its own local demand from its own sensor set.

### Zone Temperature

Because a zone may contain multiple sensors, the integration needs a configurable aggregation strategy.

Supported aggregation modes:

1. Average
   Good general default when sensors represent the same space fairly well.
2. Minimum
   Useful when the coldest point in the zone should drive heating.
3. Specific primary sensor
   Useful when one sensor should be authoritative and others are diagnostic only.

Version 1 should support `average`, `minimum`, and `primary`.

### Zone Demand

Zone demand is a computed boolean state indicating whether a zone currently requires heat.

Suggested initial rule:

- Demand is `on` when `current_temperature < target_temperature - hysteresis_on`
- Demand is `off` when `current_temperature > target_temperature + hysteresis_off`

For the first version, symmetric hysteresis is likely enough:

- `demand on` below `target - hysteresis`
- `demand off` above or equal to `target`

This can be represented internally with stateful logic to avoid rapid toggling.

### System Demand

System demand is the aggregate of all enabled zone demands.

- If any enabled zone demands heat, system demand is `on`
- Otherwise, system demand is `off`

### Main Relay

The main relay controls water flow to the heating system. It should be on only when the system requires heat, subject to configured timing protections.

### Valve Strategy

Different hardware may expose different control models. The integration should be designed to support at least these modes:

1. Binary valve control
   A valve can be turned on or off directly.
2. Target-based climate control
   A climate entity can be driven by setting its HVAC mode or target temperature.
3. Number-based valve target
   A numeric entity can be set to a temperature or opening percentage.

Version 1 must support all three modes.

Actuation behavior by control type:

- `climate`
  All climate entities in the zone should receive the same target temperature and move together.
- `switch`
  Local control groups may turn subsets of actuators on or off together.
- `number`
  Local control groups may write configured active or inactive values to subsets of actuators.

For `number` entities, the configured meaning should be explicit:

- Valve opening percentage
- Temperature-like setpoint

## Recommended Architecture

## Integration Domain

- Domain: `multi_zone_heating`

## Main Components

### Config Entry

Stores:

- Main relay entity ID
- Optional flow meter entity ID
- Global defaults
- Zone definitions
- Optional operating mode settings

### Options Flow

Allows changing:

- Global timing settings
- Hysteresis defaults
- Zone membership
- Per-zone overrides
- Override behavior

### Runtime Coordinator

A central coordinator evaluates zone state and applies outputs.

Responsibilities:

- Track subscribed entity state changes
- Compute zone demand
- Compute aggregate demand
- Apply valve commands
- Apply main relay commands
- Enforce minimum on/off timings
- Publish diagnostics state

### Entity Layer

The integration should expose Home Assistant entities for visibility and control.

Recommended entities:

- One binary sensor per zone for heat demand
- One binary sensor for system heat demand
- One top-level climate entity for the whole system
- One sensor or enum for system control state
- One switch for global relay force-off
- One switch per zone for zone enable/disable
- Optional sensors for last action reason or last transition time

## Configuration Model

## Global Configuration

Suggested initial global options:

- Main relay entity
- Optional numeric flow meter entity
- Flow detection threshold
- Poll/event debounce interval
- Default hysteresis
- Minimum relay on time
- Minimum relay off time
- Relay off delay after last demand clears
- Flow-detection timeout after relay-on
- Global frost protection minimum
- Failsafe mode

## Per-Zone Configuration

Each zone should support:

- Zone name
- Enabled
- Target source type
- Target entity
- Control type
- Climate entities or local control groups
- For `climate` zones: temperature sensor entities
- For `climate` zones: temperature aggregation mode
- For `climate` zones: optional primary sensor
- Optional per-zone frost protection minimum temperature
- Optional low target temperature fallback for climate off behavior
- Optional number inactive value configuration

Each local control group should support:

- Group name
- One or more actuator entities
- One or more temperature sensors
- Temperature aggregation mode
- Optional primary sensor
- Control type: `switch` or `number`
- For `number`, semantic type: percentage or temperature-like value
- For `number`, active value
- For `number`, inactive value

## Target Temperature Sources

The design should support these possible target sources:

1. Home Assistant `input_number`
2. Home Assistant `climate` entity target temperature

Version 1 should support both source types.

## Control Algorithm

## High-Level Loop

Whenever a relevant entity changes:

1. Read current temperature and target for each enabled zone
2. Compute each zone demand with hysteresis
3. Determine desired zone or local-group actuator state
4. Determine desired system relay state
5. Apply timing guards
6. Write state changes only when needed
7. Update diagnostic entities

## Suggested Zone Demand Logic

Per zone:

- If the zone is disabled, demand is off
- If sensor or target data is unavailable, use configured failsafe behavior
- Compute an effective zone temperature from the configured sensor set
- If effective zone temperature is below `target - hysteresis`, demand becomes on
- If effective zone temperature is at or above `target`, demand becomes off
- Otherwise retain prior demand state

This state retention is important for stable behavior.

Sensor availability handling:

- Ignore unavailable sensors if one or more valid sensors remain
- If no valid sensors remain in the zone, demand becomes off

For `climate` controlled zones, this logic applies directly at the zone level.

For `switch` and `number` controlled zones, each local control group computes its own effective temperature and local demand from its own sensor set. The zone is considered to have demand if one or more local groups have demand.

## Suggested Relay Logic

- Relay desired state is on if any enabled zone demand is on
- When changing to on, respect minimum off time
- When changing to off, respect minimum on time and optional off delay
- If a flow meter is configured, keep relay-off pending until flow drops

Flow meter behavior in version 1:

- Use it to delay relay-off until measured flow drops below the configured threshold
- Raise a warning if there is demand but measured flow does not rise above the configured threshold after relay-on
- Do not infer fault from unexpected flow with zero demand because domestic water heating shares the meter

## Suggested Actuator Logic

- `climate`
  - When zone demand is on, set all climate entities in the zone to the zone target
  - When zone demand is off, set HVAC mode to `off` where supported
  - If `off` is unavailable, set a configured low target temperature instead
- `switch`
  - Each local control group turns all of its actuators on or off together
- `number`
  - Each local control group writes its configured active value when heating and inactive value when not heating

Switch and number local control groups should decide whether that local spot should be active from the group's own sensor set, while still sharing the zone target temperature.

## Failure Handling

Important decisions:

- What happens if a sensor is unavailable?
- What happens if a target source is unavailable?
- What happens if the relay command fails?
- What happens if a valve entity becomes unavailable?

Recommended default approach:

- Unavailable zone inputs disable demand for that zone and mark the zone as degraded
- System relay stays off unless another healthy zone still calls for heat
- Diagnostics should expose the degraded condition clearly
- If one or more actuators in a zone are unavailable, continue heating while at least one actuator remains available
- If no actuators remain available in a zone, that zone is failed for actuation

An alternative optional mode could be:

- Fail-safe heat retention for previously heating zones for a short grace period

## Manual Overrides

The design should leave room for manual interventions.

Possible override types:

- Per-zone on or off
- Force system relay off

For version 1, global relay force-off should also disable downstream heat calls by:

- Turning off switch actuators
- Writing inactive values to number actuators
- Setting climate HVAC mode to `off`, or a configured low target if `off` is unavailable

## Diagnostics and Observability

Useful exposed states:

- Zone effective temperature
- Zone individual sensor temperatures
- Zone target temperature
- Zone demand
- Zone reason for no demand
- Local group effective temperature
- Local group individual sensor temperatures
- Local group demand
- Zone actuator availability status
- System demand
- Main relay desired state
- Main relay actual state
- Main flow value
- Main flow detected state
- Warning state for demand-without-flow
- Last control action timestamp
- Last control action reason

Useful log events:

- Zone demand changes
- Relay transitions
- Suppressed relay transitions because of timing rules
- Entity unavailability affecting control
- Warning conditions such as demand present without detected flow

## Proposed File Layout

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
    sensor.py
    switch.py
    climate.py
    diagnostics.py
    strings.json
    translations/
      en.json
```

## Internal Module Responsibilities

- `const.py`
  Domain constants, defaults, option keys
- `models.py`
  Dataclasses for config and runtime zone state
- `control_logic.py`
  Pure functions for demand and relay decisions
- `coordinator.py`
  Event subscriptions, state refresh, command dispatch
- `config_flow.py`
  Setup and options UI
- `binary_sensor.py`
  Zone demand and system demand entities
- `sensor.py`
  Diagnostic entities
- `switch.py`
  Enable and override switches
- `climate.py`
  Top-level system climate entity with global override target and HVAC mode
- `diagnostics.py`
  Structured diagnostic export

## Testing Strategy

The design should support both pure logic testing and Home Assistant integration testing.

Recommended initial tests:

- Zone temperature aggregation behavior
- Zone demand hysteresis behavior
- Primary sensor selection behavior
- Local group temperature aggregation behavior
- Local group demand behavior from local sensor sets
- Group-level actuation for `switch` and `number`
- Zone-wide synchronized actuation for `climate`
- Aggregate demand logic
- Multi-actuator availability behavior
- Minimum relay on/off time enforcement
- Relay off delayed by flow meter
- Warning generation when demand exists without measured flow
- Zone disable behavior
- Unavailable sensor or target handling
- Sensor loss leading to zone-off when no valid sensors remain
- Correct entity state exposure
- Config flow validation
- Options flow updates

## Open Design Decisions

These are the main choices we should resolve before implementation:

1. How should local control groups be represented in the config and options flow without making setup too heavy?
2. Should frost protection support both global and per-zone minimums from the start?
3. What secondary HVAC modes, if any, should the top-level climate entity expose beyond `heat` and `off`?

## Recommended Version 1 Scope

To keep the first implementation manageable:

- Support one main relay `switch` or `input_boolean`
- Support one optional numeric flow meter and configurable detection threshold
- Support multiple zones
- Support one or more temperature sensors per zone
- Support configurable zone temperature aggregation: `average`, `minimum`, `primary`
- Support one target temperature source per zone from `input_number` or `climate`
- Support `switch`, `climate`, and `number` control types
- Support zone-wide climate actuation
- Support local control groups for `switch` and `number`
- Require local control groups to include both sensors and actuators
- Support configurable number semantics and inactive values
- Support symmetric hysteresis
- Support minimum relay on/off times and off delay
- Support relay-off delay until flow drops
- Support warning state when there is demand without measured flow
- Support a top-level climate entity
- Support frost protection in version 1
- Expose zone demand and system demand binary sensors
- Expose per-zone enable/disable
- Expose global relay force-off
- Use config flow and options flow

## Top-Level Climate Entity

The integration should expose one system-level climate entity.

Version 1 behavior:

- `target_temperature`
  Acts as a global override target temperature and overrides all zone targets while active.
- `hvac_mode`
  Supports `heat` and `off`.
- `off`
  Maps to global force-off behavior.
- `heat`
  Clears global force-off and resumes normal zone control.

Global override behavior:

- Setting `target_temperature` creates or updates a global override target
- The global override applies to all zones and local groups
- The global override remains active until:
  - A zone target changes, or
  - A dedicated `clear_override` action is invoked
- Original per-zone targets are preserved and automatically reused once the override ends
- If `hvac_mode` is `off`, the override target and override state are preserved
- If `target_temperature` is changed while `hvac_mode` is `off`, the override is stored but heating remains off until `hvac_mode` returns to `heat`

Entity presentation:

- When override is active, the climate entity target temperature reflects the active global override
- When override is not active, there is no meaningful system target temperature
- For Home Assistant compatibility, the entity may retain the last override target as its displayed target value while exposing whether it is active through attributes

Recommended attributes:

- `override_active`
- `override_target_temperature`
- `zones_calling_for_heat`
- `global_force_off`

## Next Step

Refine the version 1 scope into a concrete schema:

- Supported entity domains
- Config entry structure
- Zone options schema
- Exact entity set to expose
- Detailed state machine for demand and relay control
