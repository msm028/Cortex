# CI Governance

## Required Check

CI required check: `CI Smoke (make smoke)`

This workflow runs the deterministic preflight gate via:

- `make smoke`

## Operator Note

Set branch protection on `main` to require the check:

- `CI Smoke (make smoke)`
