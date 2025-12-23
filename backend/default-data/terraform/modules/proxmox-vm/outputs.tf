# Proxmox VM Modul - Outputs
# Automatisch verwaltet durch Proxmox Commander

output "vmid" {
  description = "VM-ID in Proxmox"
  value       = proxmox_vm_qemu.vm.vmid
}

output "name" {
  description = "VM-Name"
  value       = proxmox_vm_qemu.vm.name
}

output "target_node" {
  description = "Proxmox-Node"
  value       = proxmox_vm_qemu.vm.target_node
}

output "ip_address" {
  description = "IP-Adresse der VM"
  value       = var.ip_address
}

output "ssh_host" {
  description = "SSH-Host (IP)"
  value       = var.ip_address
}

output "ssh_user" {
  description = "SSH-Benutzer"
  value       = var.ssh_user
}
