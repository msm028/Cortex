output "vm_id" {
  description = "Provisioned VMID"
  value       = proxmox_virtual_environment_vm.cortex_control.vm_id
}

output "vm_name" {
  description = "Provisioned VM name"
  value       = proxmox_virtual_environment_vm.cortex_control.name
}

output "ip" {
  description = "Best-effort first IPv4 address reported by the guest agent"
  value = try(
    proxmox_virtual_environment_vm.cortex_control.ipv4_addresses[1][0],
    proxmox_virtual_environment_vm.cortex_control.ipv4_addresses[0][0],
    null
  )
}
