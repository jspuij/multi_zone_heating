# Multi-Zone Heating Integration Design

## Purpose

Design a custom Home Assistant integration that coordinates a multi-zone wet heating system with:

- One or more controllable valves per zone
- One or more room temperature sensors per zone
- One integration-managed virtual climate entity per zone
- One shared relay that enables water flow for the full system

The key control rule remains:

- If one or more zones require heat, open the main relay
- If no zones require heat, close the main relay

Zone actuators are controlled independently according to each zone's temperature, target, and configuration, but all zone targets are owned by this integration.

## Design Goals

- Be configurable from the Home Assistant UI
- Model heating demand explicitly, not only final outputs
- Keep control logic centralized and testable
- Support a range of zone hardware capabilities
- Prevent short-cycling and relay chatter
- Remove subtle state drift between target sources and actuators
- Fully adopt a master / slave control model
- Provide diagnostics and override mechanisms

## Non-Goals

- Replacing a full scheduling UI
- Implementing boiler modulation logic
- Vendor-specific thermostat integrations
- Predictive heating in the first version

## Core Concepts

### Zone

A zone is an independently controlled heated space. A zone has:

- A name
- One integration-owned virtual climate entity
- One or more temperature sensors
- One or more control targets
- Optional enable or disable state
- Optional per-zone tuning values

The integration computes one demand state per zone.

The zone climate entity is the master target interface for the zone. Every actuator in the zone is a slave:

- Slave `climate` actuators receive target commands from the coordinator and follow the virtual zone or system master for HVAC mode
- Slave `switch` actuators are turned on or off by the coordinator
- Slave `number` actuators receive active and inactive values from the coordinator

Downstream actuator state never acts as the source of truth for zone targets.
For climate zones, demand affects relay and idle or heating state, but not whether the slave thermostat stays in `heat` or `off`.

### Local Control Group

A local control group is a sub-part of a zone used for `switch` and `number` based control.

Each local control group must have:

- One or more temperature sensors
- One or more actuator entities
- One control type: `switch` or `number`

All groups in a zone share the same zone climate target temperature, but each group computes its own local demand from its own sensor set.

If a local spot needs its own target temperature, it should be modeled as a separate zone.

### Zone Temperature

Because a zone may contain multiple sensors, the integration needs a configurable aggregation strategy.

Supported aggregation modes:

1. `average`
   Good general default when sensors represent the same space fairly well.
2. `minimum`
   Useful when the coldest point in the zone should drive heating.
3. `primary`
   Useful when one sensor should be authoritative and others are diagnostic only.

The zone virtual climate entity must expose `current_temperature` from this same aggregation logic:

- `average` reports the mean of available configured zone sensors
- `minimum` reports the lowest available configured zone sensor
- `primary` reports the configured primary sensor directly

If no valid sensor remains, the zone climate reports no `current_temperature` and the zone does not demand heat.

### Zone Target Ownership

Each zone target temperature is persisted in integration-owned state or config.

Implications:

- `target_source` and `target_entity_id` are removed from core zone configuration
- A zone target is read from the zone virtual climate state only
- Target changes made through the zone climate must survive restart
- External Home Assistant entities may still automate the zone climate, but are not part of core zone config

### Zone Demand

Zone demand is a computed boolean state indicating whether a zone currently requires heat.

Suggested rule:

- Demand is `on` when `current_temperature < target_temperature - hysteresis`
- Demand is `off` when `current_temperature >= target_temperature`
- Otherwise retain prior demand state

For `climate` controlled zones, this logic applies at zone level.

For `switch` and `number` controlled zones, each local control group computes local demand from its own sensor set while sharing the zone target.

### System Demand

System demand is the aggregate of all enabled zone demands.

- If any enabled zone demands heat, system demand is `on`
- Otherwise, system demand is `off`

### Main Relay

The main relay controls water flow to the heating system. It should be on only when the system requires heat, subject to configured timing protections.

### Valve Strategy

Different hardware may expose different control models. The integration must support:

1. Binary valve control
   A valve can be turned on or off directly.
2. Slave climate control
   A climate entity can be driven by setting HVAC mode or target temperature.
3. Number-based control
   A numeric entity can be set to a configured active or inactive value.

Version 1 must support all three modes.

## Recommended Architecture

### Config Entry

Stores:

- Main relay entity ID
- Optional flow meter entity ID
- Global defaults
- Zone definitions
- Persisted zone target temperatures or references to owned stored state
- Optional operating mode settings

### Options Flow

Allows changing:

- Global timing settings
- Hysteresis defaults
- Zone membership
- Per-zone overrides
- Per-zone target defaults when needed

### Runtime Coordinator

A central coordinator evaluates zone state and applies outputs.

Responsibilities:

- Track subscribed entity state changes
- Compute aggregated zone temperatures
- Compute zone demand
- Compute aggregate demand
- Read zone targets from integration-owned zone climate state only
- Dispatch actuator and relay commands only when needed
- Enforce minimum on and off timings
- Publish diagnostics state

### Entity Layer

The integration should expose Home Assistant entities for visibility and control.

Recommended entities:

- One virtual climate entity per zone
- One binary sensor per zone for heat demand
- One binary sensor for system heat demand
- One top-level climate entity for the whole system
- One sensor or enum for system control state
- One switch for global relay force-off
- One switch per zone for zone enable or disable
- Optional sensors for last action reason or last transition time

## Configuration Model

### Global Configuration

Suggested initial global options:

- Main relay entity
- Optional numeric flow meter entity
- Flow detection threshold
- Poll or event debounce interval
- Default hysteresis
- Minimum relay on time
- Minimum relay off time
- Relay off delay after last demand clears
- Flow-detection timeout after relay-on
- Global frost protection minimum
- Failsafe mode

### Per-Zone Configuration

Each zone should support:

- Zone name
- Enabled
- Control type
- For `climate` zones: zone-level sensors
- For `climate` zones: slave climate entities
- For `climate` zones: temperature aggregation mode
- For `climate` zones: optional primary sensor
- Optional per-zone frost protection minimum temperature
- Optional low target temperature fallback for slave climate off behavior
- For `switch` and `number` zones: one or more local control groups

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

Core zone config must not include `target_source` or `target_entity_id`.

## Control Algorithm

### High-Level Loop

Whenever a relevant entity changes:

1. Read current sensor inputs and persisted zone targets
2. Compute each zone's aggregated current temperature
3. Compute each zone or local-group demand with hysteresis
4. Determine desired slave actuator state
5. Determine desired system relay state
6. Apply timing guards
7. Write state changes only when needed
8. Update diagnostic entities

### Suggested Zone Demand Logic

Per zone:

- If the zone is disabled, demand is off
- If no valid sensor remains, demand is off
- If no valid target remains, demand is off
- Compute an effective zone temperature from the configured sensor set
- Compare against the integration-owned zone target
- Retain prior demand state between on and off thresholds

### Suggested Relay Logic

- Relay desired state is on if any enabled zone demand is on
- When changing to on, respect minimum off time
- When changing to off, respect minimum on time and optional off delay
- If a flow meter is configured, keep relay-off pending until flow drops

### Suggested Actuator Logic

- `climate`
  - When a zone is enabled and not globally forced off, keep supported slave climate entities in `heat`
  - While a zone is enabled, set all slave climate entities in the zone to the zone target
  - When zone demand is off, the zone may be idle but slave climates do not switch `off` only because demand cleared
  - When a zone is disabled or global force-off is active, set HVAC mode to `off` where supported
  - If `off` is unavailable, set a configured low target temperature instead when the zone is disabled or globally forced off
- `switch`
  - Each local control group turns all of its actuators on or off together
- `number`
  - Each local control group writes its configured active value when heating and inactive value when not heating

The coordinator reads zone targets from owned zone climate state, then dispatches to actuators only.

## Manual Overrides

The design should leave room for manual interventions.

Possible override types:

- Per-zone enable or disable
- Force system relay off
- System-level master commands that fan out into zone-owned targets

Version 1 should avoid direct writes to external target sources and avoid mixed ownership.

## Diagnostics and Observability

Useful exposed states:

- Zone effective temperature
- Zone individual sensor temperatures
- Zone target temperature
- Zone climate current temperature
- Zone demand
- Zone reason for no demand
- Local group effective temperature
- Local group demand
- Zone actuator availability status
- System demand
- Main relay desired state
- Main relay actual state
- Main flow value
- Main flow detected state
- Warning state for demand-without-flow

Useful log events:

- Zone demand changes
- Zone target changes
- Relay transitions
- Suppressed relay transitions because of timing rules
- Entity unavailability affecting control

## Testing Strategy

Recommended initial tests:

- Zone temperature aggregation behavior
- Zone climate `current_temperature` for `average`, `minimum`, and `primary`
- Zone demand hysteresis behavior
- Local group demand behavior from local sensor sets
- Group-level actuation for `switch` and `number`
- Zone-wide synchronized actuation for slave `climate` entities
- Slave climate HVAC mode following virtual zone `heat` or `off` instead of demand transitions
- Aggregate demand logic
- Multi-actuator availability behavior
- Minimum relay on or off time enforcement
- Relay off delayed by flow meter
- Warning generation when demand exists without measured flow
- Zone disable behavior
- Persisted zone target restore across restart
- Config migration away from `target_source` and `target_entity_id`

## Recommended Version 1 Scope

- Support one main relay `switch` or `input_boolean`
- Support one optional numeric flow meter and configurable detection threshold
- Support multiple zones
- Support one virtual climate entity per zone
- Support integration-owned persistence of zone targets
- Support configurable zone temperature aggregation: `average`, `minimum`, `primary`
- Support `switch`, `climate`, and `number` control types
- Support zone-wide slave climate actuation
- Support local control groups for `switch` and `number`
- Support symmetric hysteresis
- Support minimum relay on or off times and off delay
- Support relay-off delay until flow drops
- Support warning state when there is demand without measured flow
- Support a top-level climate entity
- Expose zone demand and system demand binary sensors
- Expose per-zone enable or disable
- Expose global relay force-off
- Use config flow and options flow

## Top-Level Climate Entity

The integration should expose one system-level climate entity.

Version 1 behavior:

- `target_temperature`
  Acts as a master command surface for the system.
- `hvac_mode`
  Supports `heat` and `off`.
- `off`
  Maps to global force-off behavior.
- `heat`
  Clears global force-off and resumes normal zone control.

Master / slave behavior:

- Setting a zone climate target updates that zone's persisted target
- Setting a zone climate HVAC mode to `off` disables that zone and `heat` enables it
- The coordinator reads zone targets from zone climate state only
- Downstream actuators never provide target input
- Setting the system climate target may fan out to zone climates, but zone climates remain the only per-zone source of truth

Recommended attributes:

- `zones_calling_for_heat`
- `global_force_off`

## Next Step

Refine the version 1 scope into a concrete schema:

- Supported entity domains
- Config entry structure
- Zone target persistence model
- Zone climate restore-state behavior
- Detailed state machine for demand and relay control
