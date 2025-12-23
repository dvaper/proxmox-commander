# Proxmox VM Modul - VM-Erstellung
# Automatisch verwaltet durch Proxmox Commander

terraform {
  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = "~> 2.9"
    }
  }
}

resource "proxmox_vm_qemu" "vm" {
  name        = var.name
  vmid        = var.vmid
  target_node = var.target_node
  desc        = var.description

  # Template-Clone
  clone      = var.template_id
  clone_wait = 30
  full_clone = true

  # Ressourcen
  cores   = var.cores
  sockets = 1
  cpu     = "host"
  memory  = var.memory
  balloon = var.memory

  # Boot
  boot     = "order=scsi0;ide2;net0"
  bootdisk = "scsi0"
  agent    = 1
  onboot   = true

  # SCSI Controller
  scsihw = "virtio-scsi-single"

  # Disk (2.9.x Syntax)
  disk {
    type     = "scsi"
    storage  = var.disk_storage
    size     = "${var.disk_size}G"
    cache    = "writeback"
    discard  = "on"
    iothread = 1
    slot     = 0
  }

  # Netzwerk
  network {
    model  = "virtio"
    bridge = var.bridge
  }

  # Cloud-Init
  os_type    = "cloud-init"
  ciuser     = var.ssh_user
  sshkeys    = join("\n", var.ssh_keys)
  ipconfig0  = "ip=${var.ip_address}/${var.netmask},gw=${var.gateway}"
  nameserver = join(" ", var.dns_servers)

  # Custom Cloud-Init User-Data (optional)
  cicustom = var.cloud_init_user_data != "" ? "user=local:snippets/${var.name}-cloud-init.yaml" : ""

  # Timeouts
  timeouts {
    create = "10m"
    update = "10m"
    delete = "5m"
  }

  lifecycle {
    ignore_changes = [
      network,
      ciuser,
      sshkeys,
      disk,
      clone,
    ]
  }
}
