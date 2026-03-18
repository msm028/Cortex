# Git And Host File Management Policy

## Purpose

Define a single source-of-truth workflow for Cortex Governor so development, deployment, and remote operations do not drift across hosts.

## Canonical Host Roles

- `majelis`: canonical development and Git authority for Cortex Governor
- `cortex-control`: deployment host for the hosted Governor wiki and control-plane services
- `cortex-data`: stateful services host

The core rule is simple:

`majelis` is where development starts.

## Repository Authority

### Canonical Development Checkout

Use `/home/maher/repos/cortex` on `majelis` as the authoritative working checkout.

Normal development happens there:

- create branches
- edit files
- run tests and docs builds
- commit and push
- review diffs
- prepare releases or deployment commits

### Deployment Checkout

Use `/opt/cortex` on `cortex-control` only as the deployed checkout.

Its normal responsibilities are:

- fast-forward or sync to approved commits
- rebuild the hosted wiki
- run host-local operational commands
- serve as the control-plane repo copy for live services

Do not use `/opt/cortex` as a normal feature-development workspace.

## Branch Policy

### On `majelis`

Normal Git work is allowed:

- `main`
- feature branches
- cleanup branches
- migration branches
- experimental branches

### On `cortex-control`

Normal Git work is not allowed.

Expected steady state:

- clean `main` at an approved commit

Allowed only for break-glass or preservation:

- `preserve/...`
- `hotfix/...`

Do not keep long-lived feature branches on `cortex-control`.

## File Management Policy

### Keep In Git

Keep these in the repo:

- source code
- docs and runbooks
- IaC
- policies
- project manifests
- queue definitions
- canonical examples

### Keep Generated Or Derived

These should be treated as generated outputs, not hand-maintained truth:

- `docs/projects.md`
- `docs/ops-status.md`
- generated project artifact pages
- inventory and other reference pages that should eventually derive from IaC and runtime facts

### Keep Off Git

Do not commit host-local or secret-bearing state:

- `/etc/cortex/*`
- runtime env files
- credentials
- local Docker volumes
- temporary publish directories
- local service overrides
- transient logs

## Deployment Sync Policy

Preferred normal flow:

1. develop on `majelis`
2. commit and push from `majelis`
3. sync `cortex-control` to a specific approved commit
4. rebuild or restart the affected services there

Good sync methods:

- normal Git fast-forward on the host
- a Git bundle copied from `majelis` when direct host GitHub access is inconvenient
- `ops/bin/sync_deployed_checkout.sh` on deployment hosts so generated files like `docs/ops-status.md` do not block fast-forwards

Avoid:

- hand-copying changed files without commit provenance
- editing live files in `/opt/cortex` and leaving them dirty

### Recommended Deployment-Host Sync Wrapper

When syncing `/opt/cortex`, prefer the repo wrapper:

```bash
cd /opt/cortex
ops/bin/sync_deployed_checkout.sh --bundle /tmp/cortex-main-<sha>.bundle --refresh-wiki
```

Or, if the deployment host can fetch directly:

```bash
cd /opt/cortex
ops/bin/sync_deployed_checkout.sh --remote origin --ref main --refresh-wiki
```

This wrapper:

- stashes generated host-local docs such as `docs/ops-status.md`
- fast-forwards the checkout
- optionally rebuilds the hosted wiki
- drops its temporary stash on success

The preferred steady state is even cleaner: host-generated live docs should go under `artifacts/generated/` and be overlaid into the hosted wiki build, rather than rewriting tracked files inside `/opt/cortex`.

## Remote Working Guidance

### Preferred Remote Mode

When working away from the homelab, prefer remoting into `majelis` rather than creating a second primary checkout somewhere else.

Recommended pattern:

- SSH into `majelis`
- use `tmux` or a persistent shell
- work in `/home/maher/repos/cortex`
- push from there

This preserves one canonical working tree.

### Secondary Remote Checkouts

If you must work from a laptop or another machine:

- treat that checkout as temporary
- branch there if needed
- push to origin
- reconcile on `majelis` before deployment

Do not let a secondary remote checkout become a second authority.

### Never Use `cortex-control` As The Remote Dev Box

Even when remote, do not treat `cortex-control` as the convenient place to “just make a quick change”.

Why:

- it is a live control-plane host
- it serves the hosted wiki and related services
- it creates split-brain Git state
- it increases recovery and review complexity

## Break-Glass Procedure

If an urgent host-local change must be made on `cortex-control`:

1. create a clearly named branch such as `hotfix/...` or `preserve/...`
2. commit the change immediately on that branch
3. capture the commit SHA and branch name
4. pull or recreate that change on `majelis`
5. reconcile it there
6. return `/opt/cortex` to a clean deployed branch state

Do not leave uncommitted mystery changes on the deployment host.

## Operational Rule Of Thumb

Nothing starts on `cortex-control`.

That means:

- no new feature branches
- no architecture work
- no docs rewrites
- no long-running experiments

The deployment host is for serving and controlled operational work, not for primary development.
