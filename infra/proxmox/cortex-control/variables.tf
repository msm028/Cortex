variable "endpoint" {
  description = "Proxmox API endpoint, e.g. https://192.168.1.102:8006/api2/json"
  type        = string
}

variable "api_token" {
  description = "Proxmox API token. Do not commit secrets; export at runtime from Vaultwarden-mapped env vars."
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key injected via cloud-init"
  type        = string
}

variable "target_node" {
  description = "Proxmox node name where the VM will run"
  type        = string
}

variable "datastore" {
  description = "Datastore ID used for VM disk and cloud-init snippet"
  type        = string
}

variable "vm_id" {
  description = "VMID for cortex-control"
  type        = number
}

variable "vm_name" {
  description = "VM name"
  type        = string
  default     = "cortex-control"
}

variable "cores" {
  description = "vCPU core count"
  type        = number
  default     = 2
}

variable "memory_mb" {
  description = "Dedicated RAM in MB"
  type        = number
  default     = 4096
}

variable "disk_gb" {
  description = "Primary disk size in GB"
  type        = number
  default     = 40
}

variable "network_bridge" {
  description = "Bridge for primary NIC, e.g. vmbr0"
  type        = string
  default     = "vmbr0"
}

variable "template_vm_id" {
  description = "Cloud-init-enabled Ubuntu 22.04 template VMID to clone"
  type        = number
}
