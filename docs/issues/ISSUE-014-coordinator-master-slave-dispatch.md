# ISSUE-014 Coordinator Master Slave Dispatch

## Goal

Update the runtime coordinator so zone targets come only from integration-owned zone climate state and all actuators behave as slaves.

## Scope

- Remove coordinator reads from external zone target entities
- Read zone targets from owned zone climate state only
- Keep zone and local-group demand evaluation working with the new target model
- Dispatch commands to slave `climate`, `switch`, and `number` actuators only
- Ensure command deduplication and availability handling remain correct

## Why

The coordinator is where split ownership currently becomes runtime drift. This issue makes the master / slave model real.

## Related Stories

- US-006
- US-007
- US-010
- US-011
- US-012
- US-013

## Acceptance Criteria

- The coordinator no longer depends on `target_source` or `target_entity_id`
- Zone demand uses the persisted zone-owned target
- Slave climate actuators never act as target sources
- Switch and number groups still share the same zone target
- Commands are only sent when required

## Dependencies

- ISSUE-012
- ISSUE-013

## Out Of Scope

- Config flow migration
- Top-level climate UX details
