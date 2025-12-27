# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

---

## [0.3.0] VM-Management & Automation (2025-12-26 - 2025-12-27)

### VM-Deployment
- Ansible-Gruppe direkt im VM-Dialog erstellen (+ Button)
- Dynamische Ansible-Gruppen aus Inventory statt hardcoded Enum
- VM-Vorlagen/Presets für wiederkehrende Konfigurationen
- Post-Boot Playbook für VMs aus debian-13-proxmox Template
- Automatische Playbook-Synchronisation beim Container-Start

### Backup & Restore
- Backup & Restore Feature für VMs und Container
- Zeitplan-basierte automatische Backups
- Restore-Funktionalität mit Fortschrittsanzeige

### CI/CD
- GitHub Actions: Releases nur bei stabilen Tags (ohne -dev, -rc)
- Automatische Versionierung aus Git-Tags
- Automatische Changelog-Generierung aus Commits

### Bugfixes
- Ansible-Gruppe Validierungsfehler behoben
- vm-post-boot Playbook hosts: all statt linux
- Docker-Socket für NetBox-Benutzerverwaltung

---

## [0.2.0] Benachrichtigungen & UI (2025-12-23 - 2025-12-24)

### Benachrichtigungssystem
- E-Mail-Benachrichtigungen via SMTP mit Test-Mail-Funktion
- Gotify Push-Benachrichtigungen mit Test-Nachricht
- Webhook-Integration mit HMAC-Signatur und Event-Filter
- Passwort-Reset per E-Mail
- Event-Integration: Automatische Benachrichtigungen bei VM-Deployment/Löschung

### Theme & UI
- 5 Farbthemes: Blau (Standard), Orange, Grün, Lila, Teal
- Light/Dark Mode mit System-Erkennung
- AppLogo-Komponente mit Theme-Erkennung
- Dashboard Re-Design mit 2-spaltigem Layout
- Proxmox Cluster-Nodes mit Live-Status

### NetBox Integration
- NetBox-Integration in Sidebar mit VLAN-Verwaltung
- Proxmox VLAN-Scan und Import nach NetBox
- IP-Sync: Proxmox VMs nach NetBox synchronisieren
- VM-Objekt wird beim Deployment automatisch erstellt

### Auto-Sync
- Automatische Inventory-Synchronisation mit Proxmox
- Konfigurierbares Sync-Intervall (1-60 Minuten)
- Start/Stop-Steuerung über UI

### Sicherheit
- Verschlüsselte Speicherung von SMTP-Passwörtern und API-Tokens
- Rate-Limiting für Passwort-Reset Anfragen

---

## [0.1.0] Initiale Version (2025-12-22)

### Infrastruktur
- Standalone Docker Compose Setup
- Integrierter NetBox Container (IPAM/DCIM)
- PostgreSQL und Redis für NetBox
- Terraform: bpg/proxmox Provider (Proxmox VE 8.x/9.x)

### VM-Management
- VM-Deployment via Proxmox und Terraform
- NetBox IPAM Integration (automatische IP-Verwaltung)
- VM Power Control: Start, Stop, Shutdown, Reboot
- Snapshot Management: Erstellen, Löschen, Rollback
- VM Cloning: Full Clone und Linked Clone
- VM Migration zwischen Proxmox-Nodes
- Multi-VLAN Support

### Ansible Integration
- Playbook Execution mit Live-Output via WebSocket
- Inventory Browser und Editor
- Playbook Editor mit YAML-Syntax-Highlighting

### Cloud-Init
- 13 spezialisierte Profile (Docker, K8s, Web, DB, etc.)
- Phone-Home Callback nach VM-Boot
- SSH-Hardening und Security Best Practices

### Benutzerverwaltung
- Rollen-basierte Zugriffskontrolle
- JWT-Authentifizierung
