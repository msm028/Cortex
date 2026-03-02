# ops-status

Generates a wiki-friendly operations status page from local repo artifacts.

It summarizes:

- latest plan file
- latest audit result
- latest backup status
- latest restore-test status
- key endpoints from `docs/inventory.md`

## Usage

```bash
python3 skills/ops-status/update-ops-status.py
```

Write to a custom output path:

```bash
python3 skills/ops-status/update-ops-status.py --output docs/ops-status.md
```

Make wrapper:

```bash
make skill-ops-status
```
