# ISSUE-016 Climate Slave HVAC Follows Virtual Zone Master

## Goal

Change climate-zone runtime dispatch so slave climate entities follow the virtual zone master for HVAC mode instead of switching `heat` or `off` on demand transitions.

## Scope

- Update `coordinator.py` climate-zone dispatch rules
- Keep slave climate entities in `heat` while the zone is enabled and global force-off is inactive
- Continue synchronizing slave climate target temperatures from the zone-owned target
- Stop turning slave climate entities `off` only because demand cleared
- Turn slave climate entities `off` only when the zone is disabled or global force-off is active
- Use the configured fallback target only when `off` is unsupported and the zone is disabled or globally forced off

## Why

The current implementation still treats slave climate entities like demand-switched actuators. That breaks the intended virtual-master model because the slave thermostat should keep its own setpoint logic active while the virtual zone decides whether the system is heating or idle.

## Related Stories

- US-010
- US-017
- US-018
- US-020
- US-021

## Acceptance Criteria

- When a climate zone is enabled and not globally forced off, slave climate entities are kept in `heat` where supported
- When zone demand clears, slave climate entities do not switch to `off` solely because demand became false
- When a climate zone is disabled, slave climate entities are set to `off` where supported
- When global force-off is active, slave climate entities are set to `off` where supported
- When `off` is unsupported, fallback target behavior is applied only for zone-disable or global-force-off cases
- Relay demand behavior remains based on zone demand rather than slave climate HVAC mode

## Dependencies

- ISSUE-014
- ISSUE-015

## Out Of Scope

- Config-flow changes
- New climate control types
