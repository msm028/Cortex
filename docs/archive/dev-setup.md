# Development Setup

## Python Version

This repo pins Python with `.python-version`:

- `3.11`

## Install Dependencies

Create local virtualenv and install available requirements files:

```bash
make deps
```

`make deps` is install-only. It does not run validation or tests.

## Preflight Checks

Run deterministic smoke preflight:

```bash
make smoke
```
