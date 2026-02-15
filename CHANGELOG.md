# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

## v0.1.0 - 2026-02-15

### Added

- Operator preflight and lifecycle commands: `make doctor`, `make smoke`, `make bootstrap-check`.
- Status plan templates: `stack-status` and `ingress-status`.
- Vaultwarden-backed command wrappers and checks: `vw-*` targets and `make bw-check`.
- CI smoke gate workflow: `CI Smoke (make smoke)`.

### Release Process Notes

- Generate release notes artifact: `make release-notes` (alias: `make notes`).
- Create an annotated tag: `make tag VERSION=0.2.0`.
- Push tags explicitly: `git push --tags`.
