# ISSUE-004 Runtime Coordinator And Dispatch

## Goal

Implement the runtime coordinator that reads Home Assistant state, evaluates system state, and dispatches commands.

## Scope

- Create `coordinator.py`
- Subscribe to relevant entity state changes
- Build runtime snapshots from HA entity states
- Track sensor and actuator availability
- Schedule reevaluations for relay timing and delayed transitions
- Dispatch actuator and relay commands only when needed

## Why

This is the operational core that turns the pure logic into actual system control.

## Related Stories

- US-008
- US-012
- US-013
- US-014
- US-015

## Acceptance Criteria

- Relevant state changes trigger reevaluation
- Missing or unavailable entities are tracked in runtime state
- Commands are deduplicated and not spammed repeatedly
- Deferred relay transitions can complete without additional manual input

## Dependencies

- ISSUE-003

## Out Of Scope

- UI entities
- Top-level climate entity behavior
