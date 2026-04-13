# ISSUE-018 Runtime State Persistence Without Reload

## Goal

Persist runtime-owned thermostat state without reloading the integration when users operate the virtual climate entities.

## Scope

- Introduce integration-managed persistence for per-zone target temperature
- Introduce integration-managed persistence for per-zone enabled state
- Restore that runtime-owned state during startup before entity setup completes
- Update coordinator write paths so zone climate and system climate actions no longer call config-entry update flows for runtime state
- Keep entity state updates local and immediate after runtime writes

## Why

Zone climate writes currently persist through config-entry updates, and the config-entry update listener reloads the whole integration. That unloads the climate platforms and causes the UI to show `Unavailable` for several seconds after a thermostat adjustment.

## Related Stories

- US-005
- US-017
- US-020
- US-021

## Acceptance Criteria

- Changing a zone virtual climate target does not reload the config entry
- Changing zone `hvac_mode` between `heat` and `off` does not reload the config entry
- Changing the system climate target does not reload the config entry
- Runtime-owned zone target and enabled state survive Home Assistant restart
- Virtual climate entities remain available while runtime-owned state is being updated

## Dependencies

- ISSUE-013
- ISSUE-017

## Out Of Scope

- Redesigning the options flow
- Changing slave climate dispatch semantics
