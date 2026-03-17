# Changelog And Release Notes

## Generate Release Notes

Create deterministic release notes artifact:

```bash
make release-notes
```

The command writes:

- `artifacts/release-notes/release-notes-<UTC timestamp>.md`

and ends with:

- `RELEASE-NOTES: OK`

## Update CHANGELOG

Use top-level `CHANGELOG.md` as the human-curated summary.

At each Day boundary:

1. Review recent commits or generated release notes.
2. Update `## [Unreleased]` with concise operator-facing additions/fixes.
3. Keep entries free of secret values.
