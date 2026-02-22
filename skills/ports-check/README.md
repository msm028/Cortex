# ports-check

Detect local TCP listen port conflicts for common Cortex/dev ports.

## Usage

Check one or more ports:

```bash
python3 skills/ports-check/ports-check.py --ports "8000,5432"
```

Check default port set:

```bash
python3 skills/ports-check/ports-check.py --defaults
```

Fail if any checked port is already in use:

```bash
python3 skills/ports-check/ports-check.py --ports "8000,5432" --fail-on-used
```

JSON output:

```bash
python3 skills/ports-check/ports-check.py --defaults --json
```

Make wrapper:

```bash
make skill-ports-check
make skill-ports-check PORTS="8000,5432"
make skill-ports-check PORTS="8000,5432" FAIL=1 JSON=1
```
