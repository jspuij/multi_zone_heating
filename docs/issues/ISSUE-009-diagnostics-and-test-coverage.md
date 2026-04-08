# ISSUE-009 Diagnostics And Test Coverage

## Goal

Add diagnostics, test coverage, and quality hardening for version 1 readiness.

## Scope

- Add `diagnostics.py`
- Expose structured diagnostics for config and runtime state
- Add unit tests for control logic
- Add integration tests for:
  - config flow
  - climate zones
  - local control groups
  - relay timing
  - flow warnings
  - global override behavior
- Integrate test coverage reporting into the GitHub Actions build pipeline
- Review config entry migration needs

## Why

The integration will be much easier to trust and maintain if behavior is covered by tests and observable through diagnostics.

## Related Stories

- US-015
- US-018
- US-022
- US-023

## Acceptance Criteria

- Diagnostics show useful configuration and runtime state
- Core logic has automated test coverage
- The most important end-to-end behaviors are integration-tested
- Version 1 behavior is reproducible in tests
- Test coverage is collected in CI and included in the build pipeline output

## Dependencies

- ISSUE-003
- ISSUE-004
- ISSUE-005
- ISSUE-006
- ISSUE-007
- ISSUE-008
- ISSUE-010

## Out Of Scope

- Version 2 features
