# ISSUE-005 Zone Control Types

## Goal

Support all zone and actuator control types required for version 1.

## Scope

- Implement climate zone actuation
- Implement switch local control group actuation
- Implement number local control group actuation
- Support number semantics:
  - opening percentage
  - temperature-like value
- Support inactive fallback values for number groups
- Support climate fallback behavior when `off` is unsupported

## Why

The integration is only useful if it can drive the hardware combinations required by the design.

## Related Stories

- US-003
- US-004
- US-005
- US-009
- US-010
- US-011
- US-012

## Acceptance Criteria

- Climate-controlled zones drive all climate entities together
- Switch groups control only their own actuators
- Number groups write active and inactive values correctly
- Zones continue operating while at least one actuator remains available

## Dependencies

- ISSUE-003
- ISSUE-004

## Out Of Scope

- Top-level climate entity
- Diagnostic entity surface
