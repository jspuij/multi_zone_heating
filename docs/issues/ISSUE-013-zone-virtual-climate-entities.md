# ISSUE-013 Zone Virtual Climate Entities

## Goal

Add one virtual climate entity per zone and make it the authoritative interface for zone targets.

## Scope

- Extend `climate.py` with one climate entity per zone
- Expose zone target temperature through the zone climate
- Persist and restore zone target temperature in integration-owned state
- Expose zone `current_temperature` from zone aggregation logic
- Support `average`, `minimum`, and `primary` presentation rules

## Why

Each zone needs a single master entity that represents both the target and the actual measured zone temperature used by the coordinator.

## Related Stories

- US-005
- US-008
- US-020

## Acceptance Criteria

- The integration exposes one climate entity per configured zone
- Setting a zone climate target updates the persisted zone-owned target
- Restart restores the last zone target
- Zone climate `current_temperature` reflects the configured aggregation mode
- `primary` uses the configured primary sensor directly

## Dependencies

- ISSUE-012

## Out Of Scope

- Top-level climate behavior redesign
- Relay logic
