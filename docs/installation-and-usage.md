# Multi-Zone Heating Installation And Usage

This guide covers the current first version of the `multi_zone_heating` custom Home Assistant integration.

## What The Integration Does

The integration evaluates heat demand across multiple configured zones and coordinates a shared main relay for the whole heating system.

In version `0.3.1`, it can:

- read one or more temperature sensors per zone or local control group
- persist one owned target temperature per zone
- drive one or more climate actuators for a climate-based zone
- drive one or more switch actuators for a switch-based zone
- drive one or more number actuators for a number-based zone
- expose system-level control entities for master target fan-out and force-off behavior
- expose diagnostics for demand, relay state, and missing-flow warnings

## Before You Start

You should already have:

- a working Home Assistant installation
- the thermostat, valve, switch, number, and temperature-sensor entities you plan to use
- a shared relay entity that enables or disables water flow for the whole heating system

Optional but supported:

- a flow sensor entity

## Installation

The integration currently documents a manual installation flow.

1. Open your Home Assistant configuration directory.
2. Create `custom_components` if it does not already exist.
3. Copy this repository's `custom_components/multi_zone_heating` directory into your Home Assistant configuration so the final path is:

```text
config/custom_components/multi_zone_heating/
```

4. Restart Home Assistant.
5. In Home Assistant, go to `Settings -> Devices & services`.
6. Select `Add Integration`.
7. Search for `Multi-Zone Heating`.
8. Complete the config flow described below.

> Image placeholder: repository folder copied into `custom_components`
>
> Suggested screenshot: file browser view showing `config/custom_components/multi_zone_heating`

> Image placeholder: Add Integration screen
>
> Suggested screenshot: Home Assistant `Devices & services` page with `Multi-Zone Heating` selected

## Configuration Model

Setup happens in two layers:

- global system settings
- one or more zones

### Global Settings

During the first step, the integration asks for:

- `Main relay entity`
  - Must be a `switch` entity.
  - This is the shared relay for the heating system.
- `Flow sensor entity`
  - Optional.
  - May be a `sensor`, `number`, or `input_number`.
- `Flow detection threshold`
  - Required if you configure a flow sensor.
- `Missing flow timeout`
  - How long demand may remain active without detected flow before a warning is raised.
- `Default hysteresis`
  - Used when deciding whether a zone should continue calling for heat.
- `Minimum relay on time`
  - Prevents short cycling after the relay turns on.
- `Minimum relay off time`
  - Prevents short cycling after the relay turns off.
- `Relay off delay`
  - Keeps the relay on briefly after demand stops.
- `Frost protection minimum temperature`
  - Optional system-wide minimum target floor.

> Image placeholder: global settings form
>
> Suggested screenshot: config-flow page with relay, flow, hysteresis, and timing options

### Zone Types

Each zone has a name, an enabled flag, a control type, and an integration-owned target temperature.

Supported zone control types in `0.3.1`:

- `climate`
- `switch`
- `number`

New zones start at `20.0` degrees Celsius. If the global or zone frost minimum is higher than `20.0`, that higher value becomes the initial zone target instead.

### Temperature Aggregation

Where multiple sensors are configured, the integration supports:

- `average`
- `minimum`
- `primary`

If you choose `primary`, you must also select one of the configured sensors as the primary sensor.

## How To Configure Each Zone Type

### Climate Zone

Use a climate zone when Home Assistant climate entities represent the heating actuators you want the integration to control.

You will configure:

- one or more temperature sensors
- one or more climate actuator entities
- optional climate off fallback temperature
- aggregation mode
- optional primary sensor

Behavior:

- while the zone is enabled, the integration pushes the effective target temperature to the configured climate entities
- slave climate entities follow the virtual zone master for `heat` or `off`
- when demand stops, the zone becomes idle but slave climates do not switch `off` just because demand cleared
- when the zone is disabled, or global force-off is active, the integration turns the climate entity `off` if supported
- if `off` is not supported, it can instead write the configured fallback temperature when the zone is disabled or globally forced off

### Switch Zone

Use a switch zone when the controlled outputs are plain `switch` entities such as zone valves, relays, or similar on/off actuators.

A switch zone is built from one or more local control groups. For each group you configure:

- a group name
- one or more temperature sensors
- one or more switch actuators
- aggregation mode
- optional primary sensor

Behavior:

- if the local group demands heat, its switches are turned on
- if it does not demand heat, its switches are turned off

### Number Zone

Use a number zone when the actuator is driven by writing numeric values rather than on/off commands.

A number zone is also built from one or more local control groups. For each group you configure:

- a group name
- one or more temperature sensors
- one or more `number` or `input_number` actuators
- aggregation mode
- optional primary sensor
- number semantic type
- active value
- inactive value

In version `0.3.1`, both `active value` and `inactive value` are required.

Behavior:

- when the group demands heat, the integration writes the active value
- when the group stops demanding heat, it writes the inactive value

## Recommended Setup Flow

1. Configure the global relay and optional flow monitoring first.
2. Add one zone at a time.
3. Start with a single-room test zone before adding the full house.
4. Verify the created entities after setup.
5. Only then tune hysteresis and relay timing protections.

> Image placeholder: zone setup flow
>
> Suggested screenshot: one image for zone basics, one for climate zone details, one for local group details

## Entities Created By The Integration

After setup, the integration creates several runtime entities.

### Climate

- `climate.<entry>_<zone>`
  - exposed as the virtual climate entity for one zone
  - setting its target temperature updates the integration-owned zone target
  - setting HVAC mode to `off` disables that zone
  - setting HVAC mode to `heat` re-enables that zone
- `climate.<entry>_system`
  - exposed as the system climate entity
  - setting its target temperature fans the same setpoint out to every zone climate
  - setting HVAC mode to `off` activates global force-off
  - setting HVAC mode to `heat` clears global force-off
  - if zone targets differ, its displayed `target_temperature` is empty instead of becoming a separate source of truth

Attributes include:

- `zones_calling_for_heat`
- `zone_target_temperatures`
- `global_force_off`

### Binary Sensors

- `binary_sensor.<entry>_system_demand`
  - `on` when any enabled zone demands heat
- `binary_sensor.<entry>_<zone>_demand`
  - one per zone
  - `on` when that zone currently demands heat

### Switches

- `switch.<entry>_global_force_off`
  - forces the system not to call for heat
- `switch.<entry>_<zone>_enabled`
  - enables or disables one configured zone

Zone target and enabled state are runtime-owned integration state. They should survive restart, but changing them should not reload the integration or make the virtual climate briefly unavailable.

### Sensor

- `sensor.<entry>_relay_state`
  - reports relay state as:
    - `on`
    - `off`
    - `pending_off`
    - `forced_off`

Diagnostic attributes include:

- `desired_on`
- `hold_reason`
- `missing_flow_warning`
- `missing_flow_warning_since`
- `flow_detected`
- `flow_value`
- `zones_calling_for_heat`

## Day-To-Day Usage

Typical runtime usage is:

1. Leave each zone target at its normal room target.
2. Let the integration decide which zones currently demand heat.
3. Use the system climate entity when you want to push one setpoint to every zone at once.
4. Use the global force-off switch when you want the whole system disabled without reconfiguring zones.
5. Disable individual zones with their zone climate HVAC mode or the mirrored zone-enabled switch when needed.

## Example Scenarios

### Example 1: Climate-Based Radiator Zones

- Each room has one or more temperature sensors.
- Each room has one or more climate TRV entities.
- Each room target is owned by the integration.
- The integration writes effective target temperatures to the TRVs, keeps them aligned to the virtual zone master state, and runs the shared boiler relay when any room demands heat.

### Example 2: Switch-Driven Zone Valves

- Each zone has temperature sensors.
- Each zone uses one or more switch-controlled valves.
- Zone targets are owned by the integration and shared across local groups.
- The integration opens the right valves and enables the main relay only when needed.

### Example 3: Number-Driven Actuators

- Each zone has temperature sensors.
- Each actuator is a `number` entity that expects one value when heating and another when idle.
- The integration writes those values automatically based on demand.

## First-Version Limitations

Version `0.3.1` is usable, but it is still an early release. Current limits to document clearly:

- installation is documented as manual copy-based setup
- the integration manages a single config entry for one heating system
- zone targets are stored by the integration instead of external helper or climate entities
- structural configuration edits still reload the integration, but runtime thermostat actions update in place without unloading entities
- dedicated `number` platform entities are not exposed yet, even though number actuators are supported
- documentation screenshots are placeholders for now

### Reload Boundaries

The integration uses a runtime-versus-structural boundary:

- structural options edits reload the integration because they change topology, subscriptions, or coordinator wiring
- runtime thermostat actions update in place and persist without reloading the config entry

Structural examples:

- adding, removing, or renaming zones
- changing zone control type
- changing configured sensors, actuators, local groups, relay, or flow sensor bindings
- changing global timing, flow, frost, or failsafe settings through the options flow

Runtime examples:

- setting a zone climate target temperature
- setting a zone climate `hvac_mode` to enable or disable a zone
- setting the system climate target and fanning it out to zones
- toggling global force-off

## Troubleshooting

### The Integration Does Not Appear In Home Assistant

- confirm the final path is `config/custom_components/multi_zone_heating`
- confirm Home Assistant was restarted after copying files
- check `Settings -> System -> Logs` for manifest or import errors

### A Zone Never Calls For Heat

- verify the zone is enabled
- verify the zone has a valid target temperature
- verify the configured sensor entities have usable states
- if using `primary` aggregation, confirm the chosen primary sensor is one of the configured sensors

### The Relay Does Not Turn Off Immediately

This can be expected if you configured:

- minimum relay on time
- relay off delay

Check the relay-state sensor attributes, especially `hold_reason`.

### Missing Flow Warning Is Active

- verify the flow sensor entity is updating
- verify the configured threshold matches the units and range of your sensor
- confirm the relay is actually on and the physical system is circulating water

## Suggested Documentation Images To Add Later

- installation folder structure
- add-integration flow
- global settings form
- climate-zone setup
- switch-group setup
- number-group setup
- created entities in the device page
- example dashboard card showing system fan-out and diagnostics
