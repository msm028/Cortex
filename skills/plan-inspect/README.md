# plan-inspect

Quickly inspect and risk-summarise plan JSON files.

## Usage

List recent plans:

```bash
python3 skills/plan-inspect/plan-inspect.py --list 5
```

Inspect latest plan:

```bash
python3 skills/plan-inspect/plan-inspect.py --plan latest
```

Inspect explicit plan:

```bash
python3 skills/plan-inspect/plan-inspect.py --plan plans/plan-20260222T025510Z.json
```

Machine-readable JSON output:

```bash
python3 skills/plan-inspect/plan-inspect.py --plan latest --json
```

Make wrapper:

```bash
make skill-plan-inspect
make skill-plan-inspect LIST=1 N=20
make skill-plan-inspect PLAN="plans/plan-20260222T025510Z.json"
```
