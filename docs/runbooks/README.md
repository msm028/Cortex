# Cortex Governor Runbooks

## Available Runbooks

- [Agent Loop](./agent-loop.md): supervised unattended queue runner with explicit approval gates and wiki-visible status.
- [Git And Host File Management Policy](./git-and-host-management.md): source-of-truth rules for `majelis`, deployment checkout rules for `cortex-control`, and remote-working guidance.
- [Repository Validator](./validator.md): deterministic repository checks used by `make validate`.
- [Doctor Diagnostics](./doctor.md): quick operator diagnostics for git/docker/compose/files/env readiness.
- [Bitwarden CLI](./bw-cli.md): install and configure bw CLI for Vaultwarden-backed env injection.
- [Environment Variables](./env-vars.md): compose-derived env variable manifest with required/secret hints.
- [Ops Commands](./ops-commands.md): deterministic make wrappers for up/down/restart/logs operations.
- [Inventory](../inventory.md): generated host, port, project-target, and endpoint inventory for Cortex Governor.
- [Ports And Service Map](./ports-and-service-map.md): shared port ownership map and pre-start conflict checks.
- [Project Manifests](./project-manifests.md): validate machine-readable project contracts and generate the catalog, route preview, deployment plan, bootstrap checklist, runtime skeleton, env contract, smoke-check, and handoff packet artifacts.
- [Deploy Wiki](./deploy-wiki.md): deploy and update hosted MkDocs wiki service on `cortex-control`.
- [Deploy Uptime Kuma](./deploy-uptime-kuma.md): deploy the first live service-health dashboard on `cortex-control`.
- [Hosted Ops Status Refresh](./hosted-ops-status-refresh.md): automate live Uptime Kuma snapshot refresh and hosted wiki rebuild on `cortex-control`.
- [Publish Wiki With Cloudflare Access](./publish-wiki-cloudflare-access.md): expose wiki via Cloudflare Tunnel + Access with token runtime auth.
- [How To Use Cortex Governor](./how-to-use-cortex.md): detailed operator workflow and common best-use scenarios.
- [IaC Provisioning Index](./provisioning-iac.md): single entry for OpenTofu/Terraform provisioning flows.
- [Provision Cortex-Control](./provision-cortex-control.md): create/update the Proxmox VM with OpenTofu/Terraform + bpg/proxmox.
- [Provision Cortex-Data](./provision-cortex-data.md): create/update the Proxmox data-plane VM with OpenTofu/Terraform + bpg/proxmox.
- [Vaultwarden Env](./vaultwarden-env.md): bw-based env injection for required runtime variables.
- [Vaultwarden Recovery](./vaultwarden.md): crashloop triage and sqlite recovery procedure for missing `twofactor`.
- [Backups And Restore Test](./backups.md): restic backup to MinIO and non-destructive restore verification.
- [Plan Validate Execute](./plans.md): deterministic plan lifecycle and execution audit flow.
- [Edge Access](./edge-access.md): cloudflared + Caddy ingress flow and dry-run validation.
- [Smoke Preflight](./smoke.md): deterministic preflight checks with fail-fast final PASS/FAIL.

## Archive

- [Archive Index](../archive/README.md): historical and transitional runbooks removed from the primary operating surface.

## Validation

- `make validate-codex-config`: validates `.codex/config.toml` by running Python 3.11 in Docker and parsing TOML with `tomllib`.

## Repo Skills Location

Project-level Codex guidance lives in:

- `.agents/skills/00-cortex-operating-rules.md`
- `.agents/skills/01-build-chunk-template.md`
