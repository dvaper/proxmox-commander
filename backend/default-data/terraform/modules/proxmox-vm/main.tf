# Proxmox VM Modul - VM-Erstellung (bpg/proxmox Provider)
# Automatisch verwaltet durch Proxmox Commander

terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.70"
    }
  }
}

resource "proxmox_virtual_environment_vm" "vm" {
  name        = var.name
  vm_id       = var.vmid
  node_name   = var.target_node
  description = var.description

  # Template-Clone
  clone {
    vm_id = var.template_id
    full  = true
  }

  # CPU
  cpu {
    cores   = var.cores
    sockets = 1
    type    = "host"
  }

  # Memory
  memory {
    dedicated = var.memory
  }

  # Boot
  boot_order = ["scsi0", "ide2", "net0"]
  agent {
    enabled = true
  }
  on_boot = true

  # Disk
  disk {
    interface    = "scsi0"
    size         = var.disk_size
    datastore_id = var.disk_storage
    cache        = "writeback"
    discard      = "on"
    iothread     = true
    ssd          = true
  }

  # Netzwerk
  network_device {
    model  = "virtio"
    bridge = var.bridge
  }

  # Cloud-Init
  initialization {
    user_account {
      username = var.ssh_user
      keys     = var.ssh_keys
    }
    ip_config {
      ipv4 {
        address = "${var.ip_address}/${var.netmask}"
        gateway = var.gateway
      }
    }
    dns {
      servers = var.dns_servers
    }
  }

  lifecycle {
    ignore_changes = [
      network_device,
      initialization,
      disk,
      clone,
    ]
  }
}
