# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

---

## [0.3.x] VM-Management & Automation

### 0.3.55 (2025-12-27)
- Automatische Changelog-Bereinigung bei stabilen Releases
- Dev-Versionen und Zwischen-Patches werden konsolidiert

### 0.3.54 (2025-12-27)
- Changelog mit Major-Versionen und konkreten Releases strukturiert
- Dev-Tags (z.B. v0.3.54-dev.1) für iterative Entwicklung ohne Release

### 0.3.53 (2025-12-27)
- Ansible-Gruppe direkt im VM-Dialog erstellen (+ Button)
- Dynamische Ansible-Gruppen aus Inventory statt hardcoded Enum
- GitHub Actions: Releases nur bei stabilen Tags (ohne -dev, -rc)

### 0.3.44 (2025-12-26)
- Backup & Restore Feature für VMs und Container
- Zeitplan-basierte automatische Backups
- Restore-Funktionalität mit Fortschrittsanzeige
- VM-Vorlagen/Presets für wiederkehrende Konfigurationen
- Post-Boot Playbook für VMs aus debian-13-proxmox Template

---

## [0.2.x] Benachrichtigungen & UI

### 0.2.0 (2025-12-24)
- E-Mail-Benachrichtigungen via SMTP
- Gotify Push-Benachrichtigungen
- Webhook-Integration mit HMAC-Signatur
- Passwort-Reset per E-Mail
- 5 Farbthemes mit Light/Dark Mode
- Dashboard Re-Design mit 2-spaltigem Layout
- NetBox-Integration mit VLAN-Verwaltung
- IP-Sync: Proxmox VMs nach NetBox synchronisieren
- Automatische Inventory-Synchronisation mit Proxmox

---

## [0.1.x] Initiale Version

### 0.1.0 (2025-12-22)
- Standalone Docker Compose Setup
- Integrierter NetBox Container (IPAM/DCIM)
- VM-Deployment via Proxmox und Terraform
- VM Power Control, Snapshots, Cloning, Migration
- Ansible Integration mit Live-Output via WebSocket
- 13 Cloud-Init Profile (Docker, K8s, Web, DB, etc.)
- Rollen-basierte Zugriffskontrolle mit JWT
