# Multi-Zone Heating

`multi_zone_heating` is a custom Home Assistant integration for coordinating multiple heating zones behind a shared main relay.

Version `0.3.1` is the current release. It supports UI-based setup, climate- and actuator-driven zones, a shared relay, optional flow diagnostics, and a small set of runtime control entities for master commands and operations.

## Current Capabilities

- One Home Assistant config entry that manages the full heating system
- Multiple zones with independent demand evaluation
- A shared main relay that follows aggregate demand and may be backed by a `switch` or `input_boolean`
- Zone control via `climate`, `switch`, or `number` actuators
- Integration-owned zone targets
- Temperature aggregation using `average`, `minimum`, or `primary` sensor selection
- Optional relay timing protections:
  - minimum relay on time
  - minimum relay off time
  - relay off delay
- Optional flow monitoring with missing-flow warnings
- System climate target fan-out and global force-off control
- Per-zone enable and disable control

## Documentation

- [Installation and usage guide](docs/installation-and-usage.md)
- [Integration design](docs/integration-design.md)
- [Implementation plan](docs/implementation-plan.md)
- [User stories](docs/user-stories.md)

## Install

The first-version installation path is manual:

1. Copy `custom_components/multi_zone_heating` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to `Settings -> Devices & services -> Add Integration`.
4. Search for `Multi-Zone Heating`.

Full setup and usage details are in the [installation and usage guide](docs/installation-and-usage.md).

## Runtime Entities

Once configured, the integration creates:

- One system climate entity for master target commands
- One system demand binary sensor
- One zone demand binary sensor per configured zone
- One global force-off switch
- One zone enabled switch per configured zone
- One relay-state diagnostic sensor

## Development

- Project Python tooling lives in `.venv/`.
- Use the virtualenv executables directly for local checks, for example `.venv/bin/pytest`.
- Run tests with the repository root on `PYTHONPATH` so `custom_components` imports resolve correctly.
- Example: `PYTHONPATH=. .venv/bin/pytest -q`

## Notes

- Home Assistant expects `custom_components/multi_zone_heating/strings.json` and `custom_components/multi_zone_heating/translations/en.json` to stay in sync. Update both files together when config-flow copy changes.
- Version `0.3.1` is still intentionally narrow. The integration is usable, but the documentation also calls out current limits so users know what is and is not implemented yet.
