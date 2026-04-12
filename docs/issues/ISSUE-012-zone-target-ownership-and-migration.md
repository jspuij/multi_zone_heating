# ISSUE-012 Zone Target Ownership And Migration

## Goal

Replace external zone target configuration with integration-owned zone target state and migrate existing entries safely.

## Scope

- Remove `target_source` and `target_entity_id` from core zone schema
- Update config flow and options flow to stop asking for target entities
- Add config-entry migration for older entries
- Define how initial zone target defaults are created
- Update translations and validation rules

## Why

The current target-entity model creates split ownership and subtle state drift. Zone targets must be owned by the integration to support a strict master / slave design.

## Related Stories

- US-002
- US-005
- US-024

## Acceptance Criteria

- New zones can be created without `target_source` or `target_entity_id`
- Existing entries are migrated or rejected with a clear user-visible reason
- The resulting config model is consistent across setup, options, diagnostics, and tests
- Migration behavior is documented in the repo

## Migration Notes

- New zones start with an integration-owned target of `20.0` C
- If a global or zone frost minimum is higher than `20.0` C, that higher value becomes the initial target
- Existing entries migrate by reading the current target from the old external target entity at migration time
- If the old target entity has no usable current target state, migration fails so the entry is not silently changed

## Dependencies

- ISSUE-001

## Out Of Scope

- Runtime slave actuator dispatch
- Zone climate entity implementation
