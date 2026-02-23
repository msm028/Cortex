# Provision Cortex-Data (Proxmox)

## Purpose

Provision the `cortex-data` VM on Proxmox using OpenTofu/Terraform and the `bpg/proxmox` provider.

## Baseline Parameters

- Target node: `pve`
- Cloud-init template VMID: `9000` (`ubuntu-2404-cloudinit`)
- OpenTofu `>= 1.6` (or Terraform `>= 1.5`)

## Secrets Policy

- No secrets in repo.
- No `.tfvars` with secret values.
- Export runtime `TF_VAR_*` values from Vaultwarden-backed secrets (reference Vaultwarden item IDs in operator notes only).

## Export Runtime Variables

```bash
export TF_VAR_endpoint="https://192.168.1.102:8006/api2/json"
export TF_VAR_api_token="$PROXMOX_API_TOKEN"
export TF_VAR_ssh_public_key="$(cat ~/.ssh/id_ed25519.pub)"
export TF_VAR_target_node="pve"
export TF_VAR_datastore="local-lvm"
export TF_VAR_vm_id="240"
export TF_VAR_vm_name="cortex-data"
export TF_VAR_cores="4"
export TF_VAR_memory_mb="16384"
export TF_VAR_disk_gb="200"
export TF_VAR_network_bridge="vmbr0"
export TF_VAR_template_vm_id="9000"
```

## Plan / Apply

```bash
cd infra/proxmox/cortex-data
tofu init -backend=false
tofu plan
tofu apply
```

Terraform equivalent:

```bash
terraform init -backend=false
terraform plan
terraform apply
```

## Rollback

```bash
tofu destroy
# or
terraform destroy
```
