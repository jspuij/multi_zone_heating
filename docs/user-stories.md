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
- A zone has one target temperature source
- A zone has one control type: `climate`, `switch`, or `number`
- Zones can be added and edited through the UI

#### US-003 Configure a climate-controlled zone

As a home owner,
I want to configure a zone that is controlled through one or more climate entities,
so that all climate devices in that zone act together.

Acceptance criteria:

- A climate zone can have one or more temperature sensors
- A climate zone supports temperature aggregation modes `average`, `minimum`, and `primary`
- A climate zone can define a primary sensor when using `primary`
- A climate zone can contain one or more climate entities
- All climate entities in the zone share the same zone target temperature

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
- All local control groups in the same zone share the same target temperature source

#### US-005 Use Home Assistant entities as target temperature sources

As a home owner,
I want zone targets to come from Home Assistant entities I already use,
so that the heating integration fits into my existing setup.

Acceptance criteria:

- A zone target can come from an `input_number`
- A zone target can come from a `climate` entity target temperature
- Target temperature changes are reflected in control decisions without restart

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
- Each local control group uses the shared zone target temperature
- Each local control group applies the global hysteresis
- A zone is considered to have demand if one or more local groups have demand

#### US-008 Handle unavailable sensors safely

As a home owner,
I want the system to behave safely when sensors become unavailable,
so that heating does not run uncontrolled.

Acceptance criteria:

- Unavailable sensors are ignored if one or more valid sensors remain
- If no valid sensors remain for a climate-controlled zone, that zone demand becomes off
- If no valid sensors remain across all local groups in a `switch` or `number` zone, that zone demand becomes off
- Sensor availability problems are exposed in diagnostics

### Actuator Control

#### US-009 Control climate entities together within a zone

As a home owner,
I want all climate entities in a climate-controlled zone to move together,
so that the zone behaves as one heating area.

Acceptance criteria:

- When a climate zone demands heat, all climate entities in the zone are driven to the zone target
- When a climate zone no longer demands heat, climate entities are set to HVAC mode `off` where supported
- If a climate entity does not support `off`, a configured low target temperature is used instead

#### US-010 Control switch local groups independently

As a home owner,
I want each switch-based local control group to turn its own valves on or off,
so that local heating can respond to local temperature.

Acceptance criteria:

- When a switch group demands heat, all switch actuators in that group are turned on
- When a switch group no longer demands heat, all switch actuators in that group are turned off
- Different groups in the same zone can be on or off independently

#### US-011 Control number local groups independently

As a home owner,
I want each number-based local control group to write active and inactive values,
so that valves or setpoints can be controlled numerically.

Acceptance criteria:

- A number group supports a configured semantic type
- Supported semantic types are opening percentage and temperature-like value
- When a number group demands heat, the active value is written
- When a number group no longer demands heat, the inactive value is written
- Different groups in the same zone can be active or inactive independently

#### US-012 Continue operating while at least one actuator remains available

As a home owner,
I want heating to continue if some actuators fail but others remain available,
so that a partial hardware issue does not fully disable a zone.

Acceptance criteria:

- If one or more actuators in a zone are unavailable, the integration continues using the remaining available actuators
- If no actuators remain available in a zone, the zone is marked failed for actuation
- Actuator availability problems are exposed in diagnostics

### Main Relay and Flow Control

#### US-013 Turn on the main relay when any zone needs heat

As a home owner,
I want the main relay to turn on whenever the system requires heat,
so that water can flow when one or more zones are heating.

Acceptance criteria:

- If any enabled zone has demand, the relay desired state becomes on
- The relay on command respects the configured minimum off time
- Relay state is exposed in diagnostics

#### US-014 Turn off the main relay only after heating demand ends and flow drops

As a home owner,
I want the relay to stay on briefly and wait for flow to drop,
so that the system shuts down cleanly.

Acceptance criteria:

- When no zones have demand, relay off is delayed by the configured off delay
- Minimum relay on time is respected
- If a flow meter is configured, relay off remains pending until flow is no longer detected
- If no flow meter is configured, relay off uses timing rules only

#### US-015 Warn when there is heating demand but no detected flow

As a home owner,
I want the integration to raise a warning if the system calls for heat but no flow is detected,
so that I can notify myself about possible faults.

Acceptance criteria:

- A configurable timeout exists for missing flow after relay-on
- If demand exists and the relay is on but measured flow does not exceed the configured threshold within the timeout, a warning state is raised
- The warning can be consumed by Home Assistant automations
- The warning is visible through integration entities or diagnostics

### Overrides and User-Facing Entities

#### US-016 Disable a zone manually

As a home owner,
I want to turn a zone on or off manually,
so that I can temporarily disable heating in that zone.

Acceptance criteria:

- Each zone exposes an enable or disable control
- A disabled zone does not generate demand
- Disabling a zone updates group or climate actuation accordingly

#### US-017 Force all heating off globally

As a home owner,
I want to force the whole heating system off,
so that I can disable heating when leaving home.

Acceptance criteria:

- A global force-off control exists
- While global force-off is active, the main relay is kept off
- While global force-off is active, switch actuators are turned off
- While global force-off is active, number actuators are set to inactive values
- While global force-off is active, climate entities are set to `off` or low-target fallback

#### US-018 Expose zone and system demand entities

As a Home Assistant automation author,
I want demand and status entities exposed by the integration,
so that I can build dashboards and automations on top of them.

Acceptance criteria:

- Each zone exposes a heat demand binary sensor
- The system exposes a heat demand binary sensor
- The system exposes relay desired and actual state information
- Diagnostics expose sensor and actuator availability information

#### US-019 Expose a top-level climate entity

As a home owner,
I want a top-level climate entity for the heating system,
so that I can interact with the integration through a familiar Home Assistant control.

Acceptance criteria:

- The integration exposes one system-level climate entity
- The entity reflects overall heating availability and state
- The entity supports turning the heating system off
- The entity exposes a global override target temperature
- Setting HVAC mode to `off` activates global force-off
- Setting HVAC mode to `heat` clears global force-off
- Setting target temperature creates or updates a global override
- The override remains active until a zone target changes or a `clear_override` action is used
- The original per-zone targets are preserved and restored when the override ends
- If HVAC mode is `off`, override state and override target are preserved
- If target temperature is changed while HVAC mode is `off`, the override is stored without resuming heating
- The climate entity exposes attributes for `override_active`, `override_target_temperature`, `zones_calling_for_heat`, and `global_force_off`

#### US-020 Support a global frost protection minimum

As a home owner,
I want a minimum heating safeguard,
so that the home does not fall below a safe temperature.

Acceptance criteria:

- A global minimum temperature can be configured
- The integration prevents effective target temperature from falling below that minimum

#### US-021 Support per-zone frost protection minimums

As a home owner,
I want some zones to have their own minimum temperatures,
so that sensitive rooms can be protected differently.

Acceptance criteria:

- A zone can override the global minimum temperature
- Zone-specific minimums are used in demand calculations for that zone

## Should-Have Stories

#### US-022 Expose detailed diagnostics for each local group

As a home owner,
I want to inspect local group temperatures and demand,
so that I can understand how different parts of a room are behaving.

Acceptance criteria:

- Local group effective temperature is exposed
- Local group demand is exposed
- Local group sensor availability is exposed
- Local group actuator availability is exposed

#### US-023 Keep configuration editable through an options flow

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

#### US-024 Detect open windows from zone disable patterns

As a home owner,
I want the integration to support smarter zone disable behavior,
so that open-window logic can be added later.

#### US-025 Provide richer fault entities and repair flows

As a home owner,
I want clearer fault reporting and recovery guidance,
so that I can diagnose failed sensors, failed actuators, and flow issues more easily.

#### US-026 Auto-suggest entities during setup

As an installer,
I want the integration to suggest likely matching sensors and actuators,
so that large systems are faster to configure.

#### US-027 Support numeric flow sensors with thresholds

As a home owner,
I want to use a numeric flow meter with a configurable threshold,
so that flow detection works with more hardware types.

#### US-028 Add richer top-level climate behavior

As a home owner,
I want the top-level climate entity to support a well-defined target and mode model,
so that whole-home control feels natural in Home Assistant.

## Suggested Version 1 Delivery Slice

The smallest coherent version 1 should include:

- UI-based setup
- Main relay control
- Optional numeric flow meter support with thresholding
- Zone definitions
- Climate-controlled zones
- Switch and number local control groups
- Demand calculation with global hysteresis
- Global and per-zone frost protection minimums
- Per-zone enable or disable
- Global force-off
- Zone and system demand entities
- Top-level climate entity with global override target and `heat`/`off`
- Warning state for demand without flow

## Open Questions Before Implementation

These stories are ready enough to guide implementation, but a few product details still need a final decision:

1. How should local control groups be edited in the options flow without becoming cumbersome?
