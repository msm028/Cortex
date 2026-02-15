# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added

- Operator preflight and lifecycle commands: `make doctor`, `make smoke`, `make bootstrap-check`.
- Status plan templates: `stack-status` and `ingress-status`.
- Vaultwarden-backed command wrappers and checks: `vw-*` targets and `make bw-check`.
- CI smoke gate workflow: `CI Smoke (make smoke)`.
