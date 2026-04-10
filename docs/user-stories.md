# Multi-Zone Heating User Stories

## Purpose

This document translates the current integration design into a user-story oriented backlog for version 1 of the custom Home Assistant integration.

The stories are split into:

- Must-have stories for the first usable release
- Should-have stories for a strong version 1
- Later stories that are intentionally deferred

## Actors

- Home owner
- Installer or advanced Home Assistant user
- Home Assistant automation author

## Must-Have Stories

### Setup and Configuration

#### US-001 Create a heating system configuration

As a home owner,
I want to configure a multi-zone heating system from the Home Assistant UI,
so that I can use the integration without editing YAML.

Acceptance criteria:

- A config flow exists for initial setup
- The user can select a main relay entity
- The user can optionally select a numeric flow meter entity
- The user can configure a flow detection threshold
- The integration stores configuration as a config entry

#### US-002 Add and edit zones

As a home owner,
I want to define one or more heating zones,
so that each room or area can be controlled independently.

Acceptance criteria:

- A zone has a name
- A zone can be enabled or disabled
- A zone has one integration-owned virtual climate entity
- A zone has one control type: `climate`, `switch`, or `number`
- Zones can be added and edited through the UI
- Core zone config does not require `target_source` or `target_entity_id`

#### US-003 Configure a climate-controlled zone

As a home owner,
I want to configure a zone that is controlled through one or more slave climate entities,
so that all climate devices in that zone act together.

Acceptance criteria:

- A climate zone can have one or more temperature sensors
- A climate zone supports temperature aggregation modes `average`, `minimum`, and `primary`
- A climate zone can define a primary sensor when using `primary`
- A climate zone can contain one or more slave climate entities
- The zone virtual climate is the only source of truth for the zone target temperature

#### US-004 Configure local control groups for switch and number zones

As a home owner,
I want to define local control groups inside a zone,
so that local temperature measurements can drive local valves while still sharing one zone target.

Acceptance criteria:

- A `switch` or `number` zone can contain one or more local control groups
- Each local control group must contain one or more temperature sensors
- Each local control group must contain one or more actuators
- Each local control group has one control type: `switch` or `number`
- Each local control group can be named
- All local control groups in the same zone share the zone climate target temperature

#### US-005 Persist zone target temperatures in integration-owned state

As a home owner,
I want each zone target temperature to be stored by the integration itself,
so that target state is stable and survives restart without depending on external entities.

Acceptance criteria:

- Each zone target temperature is stored in integration-owned state or config
- A restart restores the last persisted zone target temperature
- Zone control decisions use the restored value without waiting on an external target entity
- External Home Assistant automations can change a zone by calling the zone climate entity

### Temperature and Demand Logic

#### US-006 Compute climate zone demand from multiple sensors

As a home owner,
I want a climate-controlled zone to compute demand from multiple sensors,
so that the room heats according to the configured temperature strategy.

Acceptance criteria:

- The integration computes an effective zone temperature from the zone's sensors
- Aggregation modes `average`, `minimum`, and `primary` are supported
- Global hysteresis is applied to demand decisions
- Demand retains its prior state between on and off thresholds

#### US-007 Compute local demand for switch and number groups

As a home owner,
I want each local control group to compute its own demand from its own sensors,
so that each local spot can be heated according to its measured temperature.

Acceptance criteria:

- Each local control group computes its own effective temperature
- Each local control group uses the shared zone target temperature from the zone climate
- Each local control group applies the global hysteresis
- A zone is considered to have demand if one or more local groups have demand

#### US-008 Expose zone climate current temperature from aggregation logic

As a home owner,
I want the zone virtual climate to show the actual zone temperature,
so that the UI reflects the same temperature the integration uses for control.

Acceptance criteria:

- The zone climate exposes `current_temperature`
- For `average`, `current_temperature` is the mean of available configured zone sensors
- For `minimum`, `current_temperature` is the minimum of available configured zone sensors
- For `primary`, `current_temperature` is the configured primary sensor value
- If no valid sensor remains, `current_temperature` is unavailable or `None`

#### US-009 Handle unavailable sensors safely

As a home owner,
I want the system to behave safely when sensors become unavailable,
so that heating does not run uncontrolled.

Acceptance criteria:

- Unavailable sensors are ignored if one or more valid sensors remain
- If no valid sensors remain for a climate-controlled zone, that zone demand becomes off
- If no valid sensors remain across all local groups in a `switch` or `number` zone, that zone demand becomes off
- Sensor availability problems are exposed in diagnostics

### Actuator Control

#### US-010 Control slave climate entities together within a zone

As a home owner,
I want all slave climate entities in a climate-controlled zone to move together,
so that the zone behaves as one heating area.

Acceptance criteria:

- When a climate zone demands heat, all slave climate entities in the zone are driven to the zone target
- When a climate zone no longer demands heat, slave climate entities are set to HVAC mode `off` where supported
- If a climate entity does not support `off`, a configured low target temperature is used instead
- Slave climate entities do not provide the source of truth for the zone target

#### US-011 Control switch local groups independently

As a home owner,
I want each switch-based local control group to turn its own valves on or off,
so that local heating can respond to local temperature.

Acceptance criteria:

- When a switch group demands heat, all switch actuators in that group are turned on
- When a switch group no longer demands heat, all switch actuators in that group are turned off
- Different groups in the same zone can be on or off independently

#### US-012 Control number local groups independently

As a home owner,
I want each number-based local control group to write active and inactive values,
so that valves or setpoints can be controlled numerically.

Acceptance criteria:

- A number group supports a configured semantic type
- Supported semantic types are opening percentage and temperature-like value
- When a number group demands heat, the active value is written
- When a number group no longer demands heat, the inactive value is written
- Different groups in the same zone can be active or inactive independently

#### US-013 Continue operating while at least one actuator remains available

As a home owner,
I want heating to continue if some actuators fail but others remain available,
so that a partial hardware issue does not fully disable a zone.

Acceptance criteria:

- If one or more actuators in a zone are unavailable, the integration continues using the remaining available actuators
- If no actuators remain available in a zone, the zone is marked failed for actuation
- Actuator availability problems are exposed in diagnostics

### Main Relay and Flow Control

#### US-014 Turn on the main relay when any zone needs heat

As a home owner,
I want the main relay to turn on whenever the system requires heat,
so that water can flow when one or more zones are heating.

Acceptance criteria:

- If any enabled zone has demand, the relay desired state becomes on
- The relay on command respects the configured minimum off time
- Relay state is exposed in diagnostics

#### US-015 Turn off the main relay only after heating demand ends and flow drops

As a home owner,
I want the relay to stay on briefly and wait for flow to drop,
so that the system shuts down cleanly.

Acceptance criteria:

- When no zones have demand, relay off is delayed by the configured off delay
- Minimum relay on time is respected
- If a flow meter is configured, relay off remains pending until flow is no longer detected
- If no flow meter is configured, relay off uses timing rules only

#### US-016 Warn when there is heating demand but no detected flow

As a home owner,
I want the integration to raise a warning if the system calls for heat but no flow is detected,
so that I can notify myself about possible faults.

Acceptance criteria:

- A configurable timeout exists for missing flow after relay-on
- If demand exists and the relay is on but measured flow does not exceed the configured threshold within the timeout, a warning state is raised
- The warning can be consumed by Home Assistant automations
- The warning is visible through integration entities or diagnostics

### Overrides and User-Facing Entities

#### US-017 Disable a zone manually

As a home owner,
I want to turn a zone on or off manually,
so that I can temporarily disable heating in that zone.

Acceptance criteria:

- Each zone exposes an enable or disable control
- A disabled zone does not generate demand
- Disabling a zone updates downstream actuation accordingly

#### US-018 Force all heating off globally

As a home owner,
I want to force the whole heating system off,
so that I can disable heating when leaving home.

Acceptance criteria:

- A global force-off control exists
- While global force-off is active, the main relay is kept off
- While global force-off is active, switch actuators are turned off
- While global force-off is active, number actuators are set to inactive values
- While global force-off is active, climate actuators are set to `off` or low-target fallback

#### US-019 Expose zone and system demand entities

As a Home Assistant automation author,
I want demand and status entities exposed by the integration,
so that I can build dashboards and automations on top of them.

Acceptance criteria:

- Each zone exposes a heat demand binary sensor
- The system exposes a heat demand binary sensor
- The system exposes relay desired and actual state information
- Diagnostics expose sensor and actuator availability information

#### US-020 Expose a zone climate entity per zone

As a home owner,
I want each zone to have its own climate entity,
so that I can control zone targets through a native Home Assistant climate surface.

Acceptance criteria:

- The integration exposes one climate entity per zone
- Setting zone target temperature updates the integration-owned persisted target
- The zone climate shows `current_temperature` from the configured zone aggregation logic
- The zone climate does not proxy another entity as its target source

#### US-021 Expose a top-level climate entity

As a home owner,
I want a top-level climate entity for the heating system,
so that I can interact with the integration through a familiar Home Assistant control.

Acceptance criteria:

- The integration exposes one system-level climate entity
- The entity reflects overall heating availability and state
- The entity supports turning the heating system off
- Setting HVAC mode to `off` activates global force-off
- Setting HVAC mode to `heat` clears global force-off
- If the entity exposes target temperature, writing it fans out through integration-owned zone targets rather than external target entities
- The climate entity exposes attributes for `zones_calling_for_heat` and `global_force_off`

#### US-022 Support a global frost protection minimum

As a home owner,
I want a minimum heating safeguard,
so that the home does not fall below a safe temperature.

Acceptance criteria:

- A global minimum temperature can be configured
- The integration prevents effective target temperature from falling below that minimum

#### US-023 Support per-zone frost protection minimums

As a home owner,
I want some zones to have their own minimum temperatures,
so that sensitive rooms can be protected differently.

Acceptance criteria:

- A zone can override the global minimum temperature
- Zone-specific minimums are used in demand calculations for that zone

#### US-024 Migrate existing configurations away from target entities

As an existing user,
I want the integration to migrate old zone target configuration safely,
so that the redesign does not break my installation unexpectedly.

Acceptance criteria:

- Existing configs using `target_source` or `target_entity_id` are migrated or rejected clearly
- Migration behavior is documented
- Tests cover migrated config entries

## Should-Have Stories

#### US-025 Expose detailed diagnostics for each local group

As a home owner,
I want to inspect local group temperatures and demand,
so that I can understand how different parts of a room are behaving.

Acceptance criteria:

- Local group effective temperature is exposed
- Local group demand is exposed
- Local group sensor availability is exposed
- Local group actuator availability is exposed

#### US-026 Keep configuration editable through an options flow

As a home owner,
I want to adjust system settings after setup,
so that I can refine behavior without reinstalling the integration.

Acceptance criteria:

- Zones can be edited after creation
- Local groups can be edited after creation
- Relay timing settings can be edited
- Flow warning timeout can be edited
- Entity selections can be changed through the UI

## Later Stories

#### US-027 Detect open windows from zone disable patterns

As a home owner,
I want the integration to support smarter zone disable behavior,
so that open-window logic can be added later.

#### US-028 Provide richer fault entities and repair flows

As a home owner,
I want clearer fault reporting and recovery guidance,
so that I can diagnose failed sensors, failed actuators, and flow issues more easily.

#### US-029 Auto-suggest entities during setup

As an installer,
I want the integration to suggest likely matching sensors and actuators,
so that large systems are faster to configure.

#### US-030 Add richer top-level climate behavior

As a home owner,
I want the top-level climate entity to support a well-defined target and mode model,
so that whole-home control feels natural in Home Assistant.

## Suggested Version 1 Delivery Slice

The smallest coherent version 1 should include:

- UI-based setup
- Main relay control
- Optional numeric flow meter support with thresholding
- Zone definitions
- One virtual climate entity per zone
- Integration-owned persistence of zone targets
- Climate-controlled zones
- Switch and number local control groups
- Demand calculation with global hysteresis
- Global and per-zone frost protection minimums
- Per-zone enable or disable
- Global force-off
- Zone and system demand entities
- Top-level climate entity
- Warning state for demand without flow
