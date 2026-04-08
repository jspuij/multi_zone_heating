# ISSUE-008 Options Flow And Editing

## Goal

Make the configured system editable after initial setup through the Home Assistant UI.

## Scope

- Add options flow support
- Edit global timing settings
- Edit frost protection settings
- Edit zone definitions
- Edit local control groups
- Edit target source configuration
- Validate changes safely against runtime requirements

## Why

Users need to refine their system over time without deleting and recreating the integration.

## Related Stories

- US-023

## Acceptance Criteria

- Global settings can be edited after setup
- Zones can be added, updated, and removed
- Local groups can be added, updated, and removed
- Invalid edits are rejected with clear validation feedback

## Dependencies

- ISSUE-002
- ISSUE-007

## Out Of Scope

- Advanced repair flows
- Entity auto-discovery
