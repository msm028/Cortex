# update-docs

Script-first utility to update `docs/CHANGELOG.md` and `docs/inventory.md` deterministically.

## Usage

Run with validation (default):

```bash
python3 skills/update-docs/update-docs.py --message "Your update message"
```

Run without validation:

```bash
python3 skills/update-docs/update-docs.py --message "Your update message" --no-validate
```

Make wrapper:

```bash
make skill-update-docs MSG="Your update message"
```
