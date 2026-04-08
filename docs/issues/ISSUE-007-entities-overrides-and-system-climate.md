# ISSUE-007 Entities Overrides And System Climate

## Goal

Expose the integration through Home Assistant entities, including the top-level climate entity and override behavior.

## Scope

- Add `binary_sensor.py`
- Add `sensor.py`
- Add `switch.py`
- Add `climate.py`
- Expose:
  - one demand binary sensor per zone
  - one system demand binary sensor
  - relay state diagnostics
  - zone enable switches
  - global force-off switch
  - top-level climate entity
- Implement `clear_override` service or equivalent action
- Add top-level climate attributes:
  - `override_active`
  - `override_target_temperature`
  - `zones_calling_for_heat`
  - `global_force_off`

## Why

The integration needs a clear UI and automation surface for actual use.

## Related Stories

- US-016
- US-017
- US-018
- US-019

## Acceptance Criteria

- Per-zone enable or disable works through exposed entities
- Global force-off shuts down relay and downstream heating control
- Top-level climate entity supports `heat` and `off`
- Setting the top-level target creates a global override
- Override ends on zone-target change or explicit clear
- Override is preserved while HVAC mode is `off`

## Dependencies

- ISSUE-004
- ISSUE-005
- ISSUE-006

## Out Of Scope

- Options flow editing
- Full diagnostics export
