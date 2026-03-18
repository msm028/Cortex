# update-docs

Script-first utility to update `docs/CHANGELOG.md` and regenerate derived Governor docs such as `docs/inventory.md`.

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
