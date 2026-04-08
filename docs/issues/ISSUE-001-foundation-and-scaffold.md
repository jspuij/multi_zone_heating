# ISSUE-001 Foundation And Scaffold

## Goal

Create the initial Home Assistant custom integration scaffold for `multi_zone_heating`.

## Scope

- Create `custom_components/multi_zone_heating/`
- Add `manifest.json`
- Add `__init__.py`
- Add `const.py`
- Add `models.py`
- Add placeholder platforms and package structure
- Implement config entry setup and unload skeleton
- Create initial test package layout

## Why

This gives the project a stable structure so the rest of the work can be added incrementally.

## Related Stories

- US-001
- US-002

## Acceptance Criteria

- Home Assistant can load the custom integration package
- The integration has a defined domain and manifest
- A config entry can be created and unloaded without runtime errors
- Shared constants and model placeholders exist for later milestones

## Dependencies

- None

## Out Of Scope

- Real config flow forms
- Control logic
- Runtime coordinator
- Entity behavior
