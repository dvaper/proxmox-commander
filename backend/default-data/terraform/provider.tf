# Proxmox Commander - Terraform Provider Konfiguration
# Automatisch verwaltet durch Proxmox Commander

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = "~> 2.9"
    }
  }
}

# Proxmox Provider - Credentials werden via Environment Variables gesetzt
# PM_API_URL, PM_API_TOKEN_ID, PM_API_TOKEN_SECRET
provider "proxmox" {
  pm_api_url          = var.proxmox_api_url
  pm_api_token_id     = var.proxmox_token_id
  pm_api_token_secret = var.proxmox_token_secret
  pm_tls_insecure     = var.proxmox_tls_insecure
  pm_parallel         = 2
  pm_timeout          = 600
}
