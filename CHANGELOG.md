# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

---

## [0.3.x] Backup & Restore (2025-12-26)

### Features
- Backup & Restore Feature für VMs und Container
- Zeitplan-basierte automatische Backups
- Restore-Funktionalität mit Fortschrittsanzeige

### Verbesserungen
- Auto-Refresh der Backup-Liste alle 30s bei aktivem Zeitplan
- Tooltips für Typ-Icons und Komponenten-Spalte
- Action-Buttons und Datum in Backup-Liste nowrap

---

## [0.3.x] VM Post-Boot Automation (2025-12-26)

### Features
- Post-Boot Playbook für VMs aus debian-13-proxmox Template
- Automatische Playbook-Synchronisation beim Container-Start
- Fastfetch mit Proxmox VE Logo

### Bugfixes
- vm-post-boot Playbook hosts: all statt linux

---

## [0.3.x] Einstellungen & Konfiguration (2025-12-26)

### Features
- Einstellungen-Menü reorganisiert
- Proxmox-Verbindungstest mit maskiertem Secret

### Bugfixes
- Docker-Socket für NetBox-Benutzerverwaltung hinzugefügt
- Setup-zsh.yml Docker-Alias Jinja2-Escaping
- Locale.yml verwendet localectl für systemd-Systeme

---

## [0.2.x] Benachrichtigungssystem (2025-12-24)

### Features
- E-Mail-Benachrichtigungen via SMTP mit Test-Mail-Funktion
- Gotify Push-Benachrichtigungen mit Test-Nachricht
- Webhook-Integration mit HMAC-Signatur und Event-Filter
- Passwort-Reset per E-Mail anfordern und zurücksetzen
- Admin-UI: Benachrichtigungseinstellungen unter Verwaltung
- Benutzer-Präferenzen: Ereignis-Benachrichtigungen im Profil
- Event-Integration: Automatische Benachrichtigungen bei VM-Deployment/Löschung und Ansible-Ausführung

### Sicherheit
- Verschlüsselte Speicherung von SMTP-Passwörtern und API-Tokens
- Rate-Limiting für Passwort-Reset Anfragen

### Bugfixes
- Notifications: API-Client mit JWT-Token (401 Fehler behoben)
- Gotify: Verbindungstest nutzt /message statt /application (App-Token kompatibel)

---

## [0.2.x] Theme & UI System (2025-12-24)

### Features
- 5 Farbthemes: Blau (Standard), Orange, Grün, Lila, Teal
- Light/Dark Mode mit System-Erkennung
- Theme wird im Benutzerprofil gespeichert
- Sofortige Vorschau beim Klick

### UI-Komponenten
- AppLogo-Komponente: Icon- und Banner-Variante mit Theme-Erkennung
- Hexagon-Logo mit Server-Rack und Netzwerk-Symbolen
- Wählbare Logo-Variante (Icon oder Banner) unter Mein Profil
- Dark/Light Mode: Automatische Anpassung der Banner-Textfarben

### Dashboard
- Re-Design mit 2-spaltigem Layout
- Proxmox Cluster-Nodes mit Live-Status in Externe Dienste
- Schnellzugriff: Playbook erstellen, Mit Proxmox abgleichen

---

## [0.2.x] Auto-Sync & Automatisierung (2025-12-24)

### Features
- Automatische Inventory-Synchronisation mit Proxmox
- Konfigurierbares Sync-Intervall (1-60 Minuten)
- Start/Stop-Steuerung über UI
- Status-Anzeige mit letztem Sync-Zeitpunkt

---

## [0.2.x] NetBox Integration (2025-12-23 - 2025-12-24)

### Features
- NetBox-Integration in Sidebar mit VLAN-Verwaltung
- Proxmox VLAN-Scan (Bridges und VLAN-Tags)
- VLAN-Import von Proxmox nach NetBox
- Komplett überarbeitete UI mit Workflow-Tabs (1. VLAN-Import, 2. Netzwerke, 3. IP-Adressen)
- Prefix-Auslastungsanzeige für IP-Prefixes
- IP-Sync: Proxmox VMs scannen und IPs nach NetBox synchronisieren
- VM-Objekt wird beim Deployment automatisch erstellt
- IP-Adresse wird mit VM verknüpft (primary_ip4)
- VM-Objekt wird bei VM-Löschung mitgelöscht

### Infrastruktur
- Terraform: Wechsel von Telmate/proxmox auf bpg/proxmox Provider
- Kompatibilität mit Proxmox VE 8.x und 9.x

### Bugfixes
- VLAN-Import zeigt automatisch gescannte VLANs beim Laden
- NetBox Default-Token verwenden (403 Forbidden Fix)

---

## [0.2.x] Setup & Konfiguration (2025-12-22 - 2025-12-23)

### Features
- Neuer Endpoint: terraform.tfvars ohne Wizard regenerieren
- Dashboard: Button 'Terraform tfvars regenerieren' im Schnellzugriff
- Setup-Wizard kann jederzeit erneut ausgeführt werden
- NetBox Status-Anzeige im UI (Starting/Ready/Error)
- Automatische Versionierung aus Git-Tags
- Automatische Changelog-Generierung aus Commits

### Infrastruktur
- Alle Volumes als Bind Mounts unter ./data/
- Terraform-Dateien werden beim Container-Start automatisch installiert
- proxmox-vm Modul hinzugefügt

### Bugfixes
- .env wird in /data/config/ gespeichert (Docker-Verzeichnis-Bug behoben)
- Sonderzeichen in Passwörtern werden korrekt gespeichert
- Admin-User wird nach Hot-Reload erstellt
- NETBOX_TOKEN wird korrekt aus env_file geladen

### Sicherheit
- Setup-Wizard generiert NETBOX_SECRET_KEY mit 50+ Zeichen
- NetBox SECRET_KEY Validierung (min. 50 Zeichen)
- Setup-Wizard aktualisiert bestehende Admin-Credentials beim Neustart

---

## [0.1.0] Initiale Version (2025-12-22)

### Infrastruktur
- Standalone Docker Compose Setup
- Integrierter NetBox Container (IPAM/DCIM)
- PostgreSQL und Redis für NetBox
- Konfiguration via .env Datei
- Persistente Volumes für alle Daten

### VM-Management
- VM-Deployment via Proxmox und Terraform
- NetBox IPAM Integration (automatische IP-Verwaltung)
- VM Power Control: Start, Stop, Shutdown, Reboot
- Snapshot Management: Erstellen, Löschen, Rollback
- VM Cloning: Full Clone und Linked Clone
- VM Migration zwischen Proxmox-Nodes
- VM-Vorlagen/Presets für wiederkehrende Konfigurationen
- Multi-VLAN Support
- Frontend-URL pro VM für direkten Zugriff

### Ansible Integration
- Playbook Execution mit Live-Output via WebSocket
- Inventory Browser und Editor
- Playbook Editor mit YAML-Syntax-Highlighting
- Playbook-Vorlagen für schnellen Start

### Cloud-Init
- 13 spezialisierte Profile (Docker, K8s, Web, DB, etc.)
- Phone-Home Callback nach VM-Boot
- SSH-Hardening und Security Best Practices

### Benutzerverwaltung
- Rollen-basierte Zugriffskontrolle
- JWT-Authentifizierung
