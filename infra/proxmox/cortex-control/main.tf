locals {
  disk_size_gb = max(var.disk_gb, 20)
}

resource "proxmox_virtual_environment_vm" "cortex_control" {
  vm_id     = var.vm_id
  name      = var.vm_name
  node_name = var.target_node

  clone {
    vm_id = var.template_vm_id
    full  = true
  }

  cpu {
    cores = var.cores
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = var.memory_mb
  }

  disk {
    datastore_id = var.datastore
    interface    = "scsi0"
    size         = local.disk_size_gb
    discard      = "on"
    iothread     = true
  }

  network_device {
    bridge = var.network_bridge
  }

  initialization {
    datastore_id = var.datastore

    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }

    user_account {
      username = "ubuntu"
      keys     = [var.ssh_public_key]
    }
  }

  agent {
    enabled = true
  }

  operating_system {
    type = "l26"
  }
}
