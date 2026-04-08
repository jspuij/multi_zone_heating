# ISSUE-002 Config Flow And Schema

## Goal

Implement the initial configuration model and UI flows for creating a heating system and defining zones.

## Scope

- Create `config_flow.py`
- Define config-entry schema
- Implement initial setup flow
- Support selecting:
  - main relay
  - optional numeric flow meter
  - flow threshold
  - global hysteresis
  - relay timing defaults
  - global frost minimum
- Support creating zones with:
  - name
  - control type
  - target source
  - zone-level sensors for climate zones
  - local control groups for switch and number zones

## Why

The integration needs a clear and validated configuration model before runtime logic can be trusted.

## Related Stories

- US-001
- US-002
- US-003
- US-004
- US-005

## Acceptance Criteria

- A user can configure the system from the UI
- Climate zones can be created with sensor aggregation settings
- Switch and number zones can be created with at least one local control group
- Each local control group must have sensors and actuators
- Config validation rejects incomplete zones and groups

## Dependencies

- ISSUE-001

## Out Of Scope

- Editing existing config through options flow
- Runtime control
