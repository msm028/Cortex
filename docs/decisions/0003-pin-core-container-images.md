# ADR 0003: Pin Core Container Images (No `:latest`)

## Status

Accepted

## Context

Core bootstrap services originally used mutable image tags (`:latest`) for MinIO and Vaultwarden. Mutable tags make rollbacks and incident response harder because the same tag can point to different image contents over time.

## Decision

We pin all core compose image references to explicit tags and enforce a repository check that fails when any tracked compose file uses `:latest`.

Current core pins:

- `postgres:16`
- `minio/minio:RELEASE.2024-10-29T16-01-48Z`
- `vaultwarden/server:1.32.2`

## MinIO Distribution Caveat

`minio/minio` is an upstream-distributed container image. We treat this as an external supply-chain dependency and accept that risk for now.

## Consequences

- Bootstrap behavior is reproducible across runs.
- Image upgrades are intentional and visible in code review.
- Operators must bump tags deliberately during upgrades instead of relying on floating tags.

## Future Plan

Move toward one of these options for MinIO image sourcing:

- self-build and sign an internal image from upstream source, or
- use an alternate vetted distribution source with clear provenance controls.
