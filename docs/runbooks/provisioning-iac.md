# IaC Provisioning (OpenTofu / Terraform)

## Purpose

Single entry point for provisioning Cortex VMs on Proxmox using the `bpg/proxmox` provider.

## Scope

- Control plane VM: [Provision Cortex-Control](./provision-cortex-control.md)
- Data plane VM: [Provision Cortex-Data](./provision-cortex-data.md)

## Tooling

- OpenTofu `>= 1.6` (preferred)
- Terraform `>= 1.5` (compatible)

## Common Runtime Inputs

Use runtime env vars only (no secrets in repo):

```bash
export TF_VAR_endpoint="https://192.168.1.102:8006/api2/json"
export TF_VAR_api_token="$PROXMOX_API_TOKEN"
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_ed25519.pub)"
export TF_VAR_target_node="pve"
export TF_VAR_datastore="local-lvm"
export TF_VAR_template_vm_id="9000"
```

## Standard Flow

```bash
cd infra/proxmox/<stack>
tofu init -backend=false
tofu plan
tofu apply
```

Rollback:

```bash
tofu destroy
```

## Notes

- Keep secrets in Vaultwarden and inject/export at runtime.
- Use dedicated `vm_id` per stack to avoid collisions.
- Validate config before apply: `tofu validate`.
