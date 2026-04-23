# ISSUE-021 Door/Window Runtime Inhibition

## Goal

Disable zone heating automatically while one or more configured door/window detectors in that zone are open.

## Scope

- Subscribe to configured open-detector entity state changes
- Include detector states in the coordinator runtime snapshot
- Treat a configured detector as open when its `binary_sensor` state is `on`
- Compute per-zone opening inhibition before demand contributes to system demand
- Suppress zone demand while any configured detector in the zone is open
- Dispatch climate, switch, and number actuators using the same inactive behavior used for an effective zone disable
- Remove the inhibition automatically when the last open detector closes
- Preserve the persisted manual zone enabled state while automatic inhibition is active
- Keep runtime detector state changes away from config-entry update and reload paths

## Why

Heating an open room wastes energy. The runtime behavior needs to pause only the affected zone and resume it automatically without changing the user's manual enable or disable preference.

## Related Stories

- US-014
- US-017
- US-027

## Acceptance Criteria

- Opening any configured detector disables heat demand for only that detector's zone
- Opening multiple detectors keeps the zone inhibited until all configured open detectors are closed
- Closing the last open detector resumes normal control when the zone is manually enabled and global force-off is inactive
- A manually disabled zone remains disabled after all detectors close
- Inhibited zones do not contribute to system demand or relay-on decisions
- Climate actuators are set to `off` or fallback target while inhibited, matching zone-disable behavior
- Switch actuators turn off while inhibited
- Number actuators receive inactive values while inhibited
- Detector state changes reevaluate the coordinator without unloading entities or updating config entries
- Unavailable detector entities do not count as open

## Dependencies

- ISSUE-003
- ISSUE-004
- ISSUE-005
- ISSUE-016
- ISSUE-020

## Out Of Scope

- Config flow and options flow UI
- Rich repair flows for unavailable detectors
- Debounce, grace periods, or configurable open-delay behavior
