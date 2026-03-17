# Project Manifests

## Purpose

Define and validate machine-readable project infrastructure contracts that Cortex can use to provision, route, document, and operate future projects.

Each manifest describes one deployable project environment. The manifest keeps project app code out of the Cortex repo while still giving the platform enough structure to automate infrastructure and wiki generation.

## Canonical Format

- directory: `projects/`
- format: JSON
- validation command: `make project-manifests-validate`
- catalog command: `make project-catalog`
- route preview command: `python3 ops/bin/project_manifest.py route-preview`
- deployment plan command: `make project-deploy-plan`
- bootstrap checklist command: `make project-bootstrap-checklist`
- runtime skeleton command: `make project-runtime-skeleton`
- env contract command: `make project-env-contract`
- smoke-check contract command: `make project-smoke-check`
- handoff packet command: `make project-handoff-packet`

## Commands

Validate every manifest:

```bash
make project-manifests-validate
```

Render the wiki-facing catalog:

```bash
make project-catalog
```

Render the generated route preview artifact:

```bash
python3 ops/bin/project_manifest.py route-preview
```

Render the generated deployment plan artifact:

```bash
make project-deploy-plan
```

Render the generated bootstrap checklist artifact:

```bash
make project-bootstrap-checklist
```

Render the generated runtime skeleton artifact:

```bash
make project-runtime-skeleton
```

Render the generated env contract artifact:

```bash
make project-env-contract
```

Render the generated smoke-check contract artifact:

```bash
make project-smoke-check
```

Render the generated handoff packet artifact:

```bash
make project-handoff-packet
```

Print the raw preview Caddyfile to stdout:

```bash
python3 ops/bin/project_manifest.py route-preview --output -
```

Print the deployment plan markdown to stdout:

```bash
python3 ops/bin/project_manifest.py deploy-plan --output -
```

Print the bootstrap checklist markdown to stdout:

```bash
python3 ops/bin/project_manifest.py bootstrap-checklist --output -
```

Print the runtime skeleton markdown to stdout:

```bash
python3 ops/bin/project_manifest.py runtime-skeleton --output -
```

Print the env contract markdown to stdout:

```bash
python3 ops/bin/project_manifest.py env-contract --output -
```

Print the smoke-check contract markdown to stdout:

```bash
python3 ops/bin/project_manifest.py smoke-check --output -
```

Print the handoff packet markdown to stdout:

```bash
python3 ops/bin/project_manifest.py handoff-packet --output -
```

Validate one manifest directly:

```bash
python3 ops/bin/project_manifest.py validate --manifest projects/examples/sample-app.json
```

## Manifest Shape

Each manifest must define:

- `schema_version`
- `project`
- `targets`
- `services`
- `routes`
- `secrets`

Optional sections:

- `domains`

Validation currently enforces:

- deterministic JSON parsing
- required keys and types
- `project.environment` is one of `dev`, `staging`, or `prod`
- route hosts are unique
- routes only target defined, enabled services
- route hosts match `domains.public` when that field is present
- Vaultwarden item references are non-empty strings
- generated planning artifacts stay deterministic for the same validated input

## Catalog Output

`make project-catalog` rewrites:

- `docs/projects.md`

Treat `docs/projects.md` as generated output. Edit manifests in `projects/`, then rerun the catalog command.

## Route Preview Output

`python3 ops/bin/project_manifest.py route-preview` rewrites:

- `docs/runbooks/generated/project-route-preview.md`

The generated page embeds a deterministic Caddyfile-style preview derived from validated manifests. It is documentation only and does not change live routing under `bootstrap/compose/edge/`.

## Deployment Plan Output

`make project-deploy-plan` rewrites:

- `docs/runbooks/generated/project-deploy-plan.md`

The generated page summarizes target hosts, enabled services, routes, Vaultwarden secret references, and operator checkpoints for each validated manifest. It is planning/documentation only and does not provision hosts, deploy services, or change live routing.

## Bootstrap Checklist Output

`make project-bootstrap-checklist` rewrites:

- `docs/runbooks/generated/project-bootstrap-checklist.md`

The generated page summarizes the first single-VM runtime host target, required runtime prerequisites, requested services, secret references, route dependencies, and explicit human approval checkpoints for each validated manifest. It is planning/documentation only and does not bootstrap hosts, render compose changes, or change live routing.

## Runtime Skeleton Output

`make project-runtime-skeleton` rewrites:

- `docs/runbooks/generated/project-runtime-skeleton.md`

The generated page summarizes a planning-only single-VM runtime layout for each validated manifest. It shows runtime-host services, shared dependency attachments, and a YAML-like deployment scaffold that operators can refine later in project-specific deployment assets. It does not create compose files, deploy containers, or change live routing.

## Env Contract Output

`make project-env-contract` rewrites:

- `docs/runbooks/generated/project-env-contract.md`

The generated page summarizes a planning-only runtime env and secret contract for each validated manifest. It maps runtime services to expected environment variables, shared dependency attachment placeholders, and Vaultwarden reference usage without exposing secret values or performing any live secret action.

## Smoke Check Output

`make project-smoke-check` rewrites:

- `docs/runbooks/generated/project-smoke-check.md`

The generated page summarizes a planning-only first-deployment smoke-check contract for each validated manifest. It describes which runtime services, public routes, shared dependencies, and operator-visible verification points should be checked after deployment without performing any live health check or mutating deployment state.

## Handoff Packet Output

`make project-handoff-packet` rewrites:

- `docs/runbooks/generated/project-handoff-packet.md`

The generated page summarizes the operator-facing planning outputs already available for each validated manifest: route preview, deploy plan, bootstrap checklist, runtime skeleton, env contract, and smoke-check contract. It stays documentation-only and does not bootstrap hosts, deploy services, resolve secrets, or run health checks.

## Sample

See:

- `projects/examples/sample-app.json`

Use that file as the starting point for new project environments.
