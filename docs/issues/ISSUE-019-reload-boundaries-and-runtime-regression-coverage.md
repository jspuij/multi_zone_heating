# ISSUE-019 Reload Boundaries And Runtime Regression Coverage

## Goal

Define and enforce which edits should reload the integration and add regression coverage so runtime thermostat actions never regress back to reload-driven behavior.

## Scope

- Document the structural edits that require config-entry reload
- Restrict reload-triggering behavior to structural config changes
- Keep options-flow edits that change topology or wiring on the reload path
- Add tests that prove runtime thermostat actions do not unload entity platforms
- Add tests that prove structural options edits still reload the integration
- Add diagnostics or debug output where helpful to distinguish structural reloads from runtime state writes

## Why

Without explicit reload boundaries, runtime-owned climate actions can accidentally reuse config-entry update machinery and reintroduce temporary entity unavailability. The integration needs both a policy and regression tests that lock the intended behavior in place.

## Related Stories

- US-017
- US-020
- US-026

## Acceptance Criteria

- Structural options edits still reload the integration
- Runtime thermostat actions do not reload the integration
- Tests cover zone target updates, zone enable or disable updates, and system target fan-out without entity unload
- Tests cover at least one structural edit path that still reloads correctly
- Documentation and diagnostics use the same runtime-versus-structural terminology

## Dependencies

- ISSUE-008
- ISSUE-018

## Out Of Scope

- New user-facing control entities
- Broader diagnostics redesign beyond what is needed for reload-boundary visibility
