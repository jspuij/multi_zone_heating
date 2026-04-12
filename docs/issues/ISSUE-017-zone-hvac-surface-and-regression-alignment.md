# ISSUE-017 Zone HVAC Surface And Regression Alignment

## Goal

Align entity surfaces, diagnostics, and regression coverage around the rule that zone `hvac_mode` represents zone enable or disable while slave climate HVAC mode follows that master state.

## Scope

- Add coordinator and entity tests for zone climate `heat` or `off` behavior
- Add tests that cover slave climate behavior for enabled, disabled, and global-force-off states
- Verify the zone-enabled switch and zone climate `hvac_mode` stay synchronized through shared zone state
- Update diagnostics where needed so `hvac_mode`, `hvac_action`, and demand are reported consistently

## Why

The behavior spans more than one surface. If tests and diagnostics keep the old demand-driven assumptions, the code can drift back into the wrong model even after the coordinator is fixed.

## Related Stories

- US-017
- US-018
- US-019
- US-020
- US-021

## Acceptance Criteria

- Setting zone climate `hvac_mode` to `off` disables the zone and updates downstream slave climate behavior
- Setting zone climate `hvac_mode` to `heat` re-enables the zone and restores normal slave climate master-following behavior
- The zone-enabled switch reflects the same enabled state as the zone climate `hvac_mode`
- Diagnostics distinguish zone disabled state from zone idle demand state
- Tests no longer expect slave climate entities to switch `off` when demand merely clears

## Dependencies

- ISSUE-016

## Out Of Scope

- Replacing the zone-enabled switch surface
- Redesigning the system climate entity
