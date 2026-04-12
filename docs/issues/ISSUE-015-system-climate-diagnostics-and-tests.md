# ISSUE-015 System Climate Diagnostics And Tests

## Goal

Align the system climate, diagnostics, and tests with the zone-owned climate model.

## Scope

- Redefine top-level climate semantics so they do not reintroduce external target ownership
- Update diagnostics to report zone climate state and owned targets
- Update or remove stale global-override assumptions where needed
- Add and update tests for migration, zone climate restore state, aggregated `current_temperature`, and master / slave dispatch

## Why

The redesign is incomplete unless the system climate surface, diagnostics, and tests reflect the new ownership model.

## Related Stories

- US-019
- US-020
- US-021
- US-024
- US-025

## Acceptance Criteria

- The top-level climate behavior is documented and tested against the new model
- Diagnostics expose zone climate target and temperature information
- Tests cover `average`, `minimum`, and `primary` zone climate temperatures
- Tests cover migration away from target entities
- No remaining documentation or tests rely on old target-source behavior without an explicit reason

## Dependencies

- ISSUE-013
- ISSUE-014

## Out Of Scope

- New hardware control types
