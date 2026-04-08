# ISSUE-006 Relay Flow And Safety

## Goal

Implement whole-system relay behavior, flow monitoring, and warning conditions.

## Scope

- Implement main relay desired-state handling
- Enforce minimum relay on and off times
- Enforce relay off-delay
- Delay relay-off until numeric flow drops below threshold
- Raise warning when demand exists but flow stays below threshold after relay-on
- Respect domestic-water-shared-meter limitation in logic

## Why

Stable relay and flow behavior is central to safe and predictable heating control.

## Related Stories

- US-013
- US-014
- US-015

## Acceptance Criteria

- Relay turns on when any enabled zone demands heat
- Relay does not short-cycle under normal demand changes
- Relay-off waits for timing and flow conditions
- Missing-flow warning can be surfaced for automations and UI

## Dependencies

- ISSUE-003
- ISSUE-004

## Out Of Scope

- Per-zone controls
- Top-level climate entity
