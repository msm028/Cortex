# Projects

Machine-readable project infrastructure contracts live here.

These files describe how Cortex should provision, route, document, and operate project infrastructure without absorbing the project application code into the Cortex repo.

## Format

- Canonical repo format: JSON
- Validation command: `make project-manifests-validate`
- Catalog generation: `make project-catalog`
- Deployment planning artifact: `make project-deploy-plan`
- Bootstrap checklist artifact: `make project-bootstrap-checklist`
- Runtime skeleton artifact: `make project-runtime-skeleton`
- Env contract artifact: `make project-env-contract`
- Smoke-check artifact: `make project-smoke-check`

## Notes

- Keep secrets out of project manifests.
- Store only Vaultwarden item IDs or selectors, never secret values.
- One manifest should describe one deployable project environment.
