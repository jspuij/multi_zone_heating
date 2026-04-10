# ISSUE-011 Input Boolean Global Relay

## Goal

Allow the global relay to be configured with an `input_boolean` entity in addition to a `switch`.

## Scope

- Accept `input_boolean` entities in the global relay config-flow selector
- Preserve relay runtime behavior for both `switch` and `input_boolean` domains
- Document the supported global relay entity types
- Add regression coverage for the new relay domain

## Why

Some Home Assistant installations expose the shared boiler enable control as an `input_boolean` helper instead of a native `switch`. The integration should support either on/off entity type for the global relay path.

## Related Stories

- US-013
- US-014

## Acceptance Criteria

- The initial config flow accepts either `switch.*` or `input_boolean.*` for the main relay entity
- A configured `input_boolean` global relay receives `turn_on` and `turn_off` service calls when demand changes
- Existing `switch`-based global relay behavior remains unchanged
- User-facing documentation states that the main relay may be a `switch` or `input_boolean`

## Dependencies

- ISSUE-002
- ISSUE-004

## Out Of Scope

- Supporting additional relay-like domains
- Changing zone actuator support beyond the existing behavior
