# ISSUE-003 Core Models And Control Logic

## Goal

Implement the pure Python logic that decides temperatures, demand, overrides, frost protection, and relay timing.

## Scope

- Finalize dataclasses in `models.py`
- Create `control_logic.py`
- Implement:
  - sensor aggregation: `average`, `minimum`, `primary`
  - climate zone demand
  - local group demand
  - zone demand aggregation
  - global hysteresis behavior
  - frost protection target clamping
  - global override target resolution
  - relay minimum on/off timing
  - relay off-delay decisions
  - flow-threshold evaluation

## Why

Keeping this logic pure and testable will reduce regressions and make runtime behavior easier to reason about.

## Related Stories

- US-006
- US-007
- US-008
- US-013
- US-014
- US-020
- US-021

## Acceptance Criteria

- Pure functions exist for all core state decisions
- Demand retains state correctly inside hysteresis band
- Global override and frost protection are applied consistently
- Relay timing and flow decisions are deterministic and testable

## Dependencies

- ISSUE-001
- ISSUE-002

## Out Of Scope

- Home Assistant state subscriptions
- Entity classes
