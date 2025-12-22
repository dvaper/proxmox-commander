# Proxmox Commander

VM-Management-Plattform fuer Proxmox VE mit integriertem NetBox, Ansible und Terraform.

## Schnellstart

### Voraussetzungen
- Docker >= 20.10
- Docker Compose >= 2.0
- 4 GB RAM (empfohlen)

### Installation

1. **Dateien herunterladen:**
   ```bash
   mkdir proxmox-commander && cd proxmox-commander
   curl -LO https://gitlab.newsxc.net/darthvaper/docker-proxmox-commander/-/raw/main/docker-compose.yml
   curl -LO https://gitlab.newsxc.net/darthvaper/docker-proxmox-commander/-/raw/main/.env.example
   ```

2. **Konfiguration erstellen:**
   ```bash
   cp .env.example .env
   ```

3. **Starten:**
   ```bash
   docker compose up -d
   ```

4. **Setup-Wizard oeffnen:**
   ```
   http://localhost:8080/setup
   ```

## Datenverzeichnisse

Nach dem Start werden automatisch erstellt:
- `./data/db/` - SQLite Datenbank
- `./data/inventory/` - Ansible Inventory
- `./data/playbooks/` - Ansible Playbooks
- `./data/roles/` - Ansible Roles
- `./data/terraform/` - Terraform Dateien
- `./data/ssh/` - SSH Keys

## Update

```bash
docker compose pull
docker compose up -d
```

## Lizenz

MIT
