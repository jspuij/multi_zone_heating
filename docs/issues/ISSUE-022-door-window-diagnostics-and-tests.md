# ISSUE-022 Door/Window Diagnostics And Tests

## Goal

Expose open door/window inhibition clearly and cover the behavior with focused tests.

## Scope

- Add diagnostics for configured detector entities per zone
- Report currently open detector entities per zone
- Report unavailable detector entities per zone
- Report whether a zone is inhibited by an open detector
- Add unit tests for pure open-detector inhibition decisions
- Add coordinator tests for detector state subscriptions and reevaluation
- Add integration tests for climate, switch, and number zone inhibition behavior
- Add regression coverage that detector state changes do not reload the config entry
- Add tests for manual-disable preservation while detector inhibition starts and clears
- Update user-facing documentation where needed for the new behavior

## Why

Automatic zone inhibition changes heating behavior without a direct manual command. Users and maintainers need clear status and regression coverage so the feature is predictable and diagnosable.

## Related Stories

- US-019
- US-025
- US-027

## Acceptance Criteria

- Diagnostics identify detector configuration, open detector state, unavailable detector state, and effective zone inhibition
- Tests cover one detector open, multiple detectors open, all detectors closed, and detector unavailable cases
- Tests cover that inhibited zones do not contribute to system demand
- Tests cover that manual zone disable state is preserved when detector inhibition clears
- Tests cover no config-entry reload for detector state changes
- Documentation describes how to configure and interpret open door/window detection

## Dependencies

- ISSUE-009
- ISSUE-020
- ISSUE-021

## Out Of Scope

- New repair issue flows
- Persistent notifications for unavailable detector entities
- Auto-suggesting likely door/window sensors
