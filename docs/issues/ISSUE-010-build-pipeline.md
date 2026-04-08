# ISSUE-010 Build Pipeline

## Goal

Create the GitHub Actions build pipeline for validating and packaging the integration.

## Scope

- Add a pull request workflow to run tests automatically
- Add a main-branch workflow to run tests before packaging
- Build the release archive in CI
- Upload the built archive as a workflow artifact
- Publish a GitHub release from the packaged artifact

## Why

The project needs automated validation and packaging so changes can be verified consistently and releases can be produced reliably.

## Related Stories

- US-022
- US-023

## Acceptance Criteria

- Pull requests trigger an automated test workflow
- Main branch changes trigger a release workflow
- The release workflow runs tests before packaging
- A release archive is created automatically in CI
- The generated archive is uploaded and used for GitHub release publishing

## Dependencies

- ISSUE-001

## Out Of Scope

- Test coverage reporting
- Additional deployment targets
