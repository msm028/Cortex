# Testing Runbook

## Run Unit Tests

Run all Python `unittest` suites:

```bash
make test
```

This executes:

```bash
python3 -m unittest -v
```

## Governance Test Coverage

`ops/tests/test_governance.py` verifies deterministic behavior for:

- Policy deny decisions (`rm -rf` pattern).
- Missing approval enforcement for destructive actions.
- Approval hash binding (`plan_sha256` must match current canonical plan hash).
- Plan execution audit creation under `artifacts/audit/`.
