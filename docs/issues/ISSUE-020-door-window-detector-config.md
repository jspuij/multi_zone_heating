# ISSUE-020 Door/Window Detector Configuration

## Goal

Add per-zone configuration for open door/window detection through the Home Assistant UI.

## Scope

- Extend the zone config model with optional open-detector entity IDs
- Update config flow zone creation to select open-detector entities
- Update options flow zone editing to add, remove, or change open-detector entities
- Use Home Assistant entity selectors for `binary_sensor` entities
- Prefer UI filtering or explanatory labels for door, window, and opening device classes where supported
- Validate that configured detector entities are binary sensors
- Keep detector membership as structural config-entry data
- Update translations for all new form fields and validation messages

## Why

Users need to select the sensors that indicate whether a zone is open to the outside before runtime logic can safely pause heating in that zone.

## Related Stories

- US-002
- US-026
- US-027

## Acceptance Criteria

- A zone can be saved with zero or more open-detector entities
- Config flow and options flow both expose the detector selection
- Door/window detector selections survive reload and restart as part of structural zone configuration
- Invalid detector entity IDs are rejected or reported clearly
- Changing detector membership through the options flow follows normal structural reload behavior
- New strings are present in both `strings.json` and `translations/en.json`

## Dependencies

- ISSUE-002
- ISSUE-008

## Out Of Scope

- Runtime demand inhibition
- Diagnostics beyond config validation errors
