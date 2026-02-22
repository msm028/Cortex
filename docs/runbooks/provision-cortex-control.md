# Provision Cortex-Control (Proxmox)

## Purpose

Provision the `cortex-control` Ubuntu 22.04 VM on Proxmox using OpenTofu/Terraform and the `bpg/proxmox` provider.

## Requirements

- OpenTofu `>= 1.6` (or Terraform `>= 1.5`)
- Proxmox VE API access token
- Cloud-init-capable Ubuntu 22.04 template VMID
- `bpg/proxmox` provider (supports current Proxmox VE releases including 9.x)

## Create Proxmox API Token (High-Level)

1. In Proxmox UI, create a service user for automation.
2. Create an API token for that user.
3. Grant the minimal role permissions needed on target node/datastore.
4. Store token securely in Vaultwarden; do not commit token values.

## Export Runtime Variables (No Secrets In Repo)

Use Vaultwarden item IDs and inject/export at runtime, for example:

```bash
export TF_VAR_endpoint="https://192.168.1.102:8006/api2/json"
export TF_VAR_api_token="$PROXMOX_API_TOKEN"
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_ed25519.pub)"
export TF_VAR_target_node="pve"
export TF_VAR_datastore="local-lvm"
export TF_VAR_vm_id="230"
export TF_VAR_vm_name="cortex-control"
export TF_VAR_cores="2"
export TF_VAR_memory_mb="4096"
export TF_VAR_disk_gb="40"
export TF_VAR_network_bridge="vmbr0"
export TF_VAR_template_vm_id="9000"
```

## Run Provisioning

```bash
cd infra/proxmox/cortex-control
tofu init
tofu plan
tofu apply
```

Terraform equivalent:

```bash
terraform init
terraform plan
terraform apply
```

## Rollback / Destroy

```bash
tofu destroy
# or
terraform destroy
```

## Notes

- Keep secrets out of `.tfvars` and git history.
- Prefer runtime env exports sourced from Vaultwarden-backed workflows.
