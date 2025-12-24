# Feature-Vergleich: Ansible Commander vs. Proxmox Commander

Stand: 2025-12-24

## Uebersicht

| Kriterium | Ansible Commander | Proxmox Commander |
|-----------|-------------------|-------------------|
| **Deployment** | Direkt auf VM | Docker Compose |
| **Setup** | Manuelle .env Konfiguration | Setup-Wizard UI |
| **NetBox** | Optional (extern) | Integriert (eigener Container) |
| **VLAN-Verwaltung** | Hardcodiert | Dynamisch aus NetBox |
| **Git-Sync** | Integriert | Nicht noetig (Bind Mount) |
| **Terraform Provider** | bpg/proxmox | bpg/proxmox |

---

## Detaillierter Feature-Vergleich

### VM-Management

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| VM-Deployment via Terraform | ✅ | ✅ | Identisch |
| VM Power Control (Start/Stop/Reboot) | ✅ | ✅ | Identisch |
| Snapshot Management | ✅ | ✅ | Identisch |
| VM Cloning | ✅ | ✅ | Identisch |
| VM Migration | ✅ | ✅ | Identisch |
| VM-Vorlagen/Presets | ✅ | ✅ | Identisch |
| VM-Loeschung mit Cleanup | ✅ | ✅ | Proxmox Commander: auch NetBox VM |
| Multi-VLAN Support | ✅ | ✅ | PC: VLANs aus NetBox |
| Frontend-URL pro VM | ✅ | ✅ | Identisch |

### NetBox Integration (IPAM/DCIM)

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| IP-Reservierung beim Deploy | ✅ | ✅ | Identisch |
| IP-Freigabe bei Loeschung | ✅ | ✅ | Identisch |
| **VM-Objekt erstellen** | ❌ | ✅ | v0.2.18 |
| **VM mit IP verknuepfen (primary_ip4)** | ❌ | ✅ | v0.2.18 |
| **Cluster automatisch erstellen** | ❌ | ✅ | v0.2.18 |
| VLAN-Scan von Proxmox | ❌ | ✅ | v0.2.9 |
| VLAN-Import nach NetBox | ❌ | ✅ | v0.2.9 |
| IP-Sync mit Proxmox VMs | ❌ | ✅ | v0.2.10 |
| NetBox Status-Anzeige | ❌ | ✅ | v0.2.4 |
| Integrierter NetBox Container | ❌ | ✅ | Docker Compose |

### Ansible Integration

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| Playbook Execution | ✅ | ✅ | Identisch |
| Live-Output via WebSocket | ✅ | ✅ | Identisch |
| Inventory Browser | ✅ | ✅ | Identisch |
| Inventory Editor | ✅ | ✅ | Identisch |
| Playbook Editor | ✅ | ✅ | Identisch |
| Playbook-Vorlagen | ✅ | ✅ | Identisch (6 Templates) |
| YAML-Validierung | ✅ | ✅ | Identisch |
| Ansible-Syntax-Check | ✅ | ✅ | Identisch |
| Git-Versionierung | ✅ | ✅ | Identisch |
| Playbook-Historie/Rollback | ✅ | ✅ | Identisch |

### Inventory Sync

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| Manueller Sync von Proxmox | ✅ | ✅ | Identisch |
| **Background Auto-Sync** | ✅ | ✅ | PC: v0.2.20 |
| **Konfigurierbares Intervall (UI)** | ❌ | ✅ | v0.2.20 |
| **Start/Stop Steuerung (UI)** | ❌ | ✅ | v0.2.20 |
| IP via QEMU Guest Agent | ✅ | ✅ | Identisch |
| IP via Cloud-Init Config | ✅ | ✅ | Identisch |
| Proxmox-Node Gruppen | ✅ | ✅ | Identisch |

### Cloud-Init

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| 13 spezialisierte Profile | ✅ | ✅ | Identisch |
| Phone-Home Callback | ✅ | ✅ | Identisch |
| SSH-Hardening | ✅ | ✅ | Identisch |
| Security Best Practices | ✅ | ✅ | Identisch |

### Benutzer-Verwaltung

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| Rollen-basierte Zugriffskontrolle | ✅ | ✅ | Identisch |
| JWT-Authentifizierung | ✅ | ✅ | Identisch |
| Passwort-Aenderung | ✅ | ✅ | Identisch |
| **Theme-Auswahl pro Benutzer** | ❌ | ✅ | v0.2.19 |
| NetBox User Sync | ❌ | ✅ | PC spezifisch |

### UI/UX

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| Dashboard | ✅ | ✅ | PC: 2-spaltig, mehr Info |
| Service Status-Badge | ❌ | ✅ | v0.2.5 |
| **5 Farbthemes** | ❌ | ✅ | v0.2.19 |
| Changelog-Anzeige | ❌ | ✅ | Im UI sichtbar |
| Setup-Wizard | ❌ | ✅ | Fuer Docker-Deployment |

### Git/Versionierung

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| Git-Sync Service | ✅ | ❌ | PC: Nicht noetig |
| Manueller Git Pull | ✅ | ❌ | PC: ./data/ ist Bind Mount |
| Auto-Sync beim Start | ✅ | ❌ | PC: Nicht noetig |

### Konfiguration

| Feature | Ansible Commander | Proxmox Commander | Bemerkung |
|---------|:-----------------:|:-----------------:|-----------|
| VLAN-Config | Hardcodiert | Dynamisch aus NetBox | PC: besserer Ansatz |
| Settings Service | ✅ | ✅ | Identisch |
| Umgebungsvariablen | .env manuell | .env via Wizard | PC: benutzerfreundlicher |

---

## Features nur in Ansible Commander

| Feature | Grund fuer Nicht-Implementierung in PC |
|---------|---------------------------------------|
| Git-Sync Service | Nicht noetig - ./data/ ist Bind Mount, User kann selbst versionieren |
| Hardcodierte VLANs | Schlechter Ansatz - PC laedt dynamisch aus NetBox |

---

## Features nur in Proxmox Commander

| Feature | Version | Beschreibung |
|---------|---------|--------------|
| Setup-Wizard | v0.1.0 | Grafische Erstkonfiguration |
| Integrierter NetBox Container | v0.1.0 | IPAM/DCIM out-of-the-box |
| NetBox VLAN-Import | v0.2.9 | VLANs von Proxmox nach NetBox |
| NetBox IP-Sync | v0.2.10 | IPs aus Proxmox nach NetBox |
| NetBox VM-Objekte | v0.2.18 | Vollstaendige DCIM-Integration |
| Theme-Auswahl | v0.2.19 | 5 Farbthemes zur Unterscheidung |
| Auto-Sync UI | v0.2.20 | Konfigurierbarer Background-Sync |
| Service Status-Badge | v0.2.5 | Zeigt Service-Zustand im Header |

---

## Fazit

**Proxmox Commander ist die modernere, Docker-optimierte Version** mit folgenden Vorteilen:

1. **Einfacheres Deployment** - Docker Compose + Setup-Wizard
2. **Tiefere NetBox-Integration** - Integrierter Container, VLAN/IP-Sync, VM-Objekte
3. **Dynamische VLAN-Verwaltung** - Keine hardcodierten Konfigurationen
4. **Bessere UX** - Theme-Auswahl, Status-Badge, Changelog-Anzeige
5. **Konfigurierbare Features** - Auto-Sync mit UI-Steuerung

**Ansible Commander bleibt sinnvoll fuer:**
- Bestehende VM-Installationen ohne Docker
- Umgebungen mit externem NetBox
- GitOps-Workflows mit integriertem Repository

**Empfehlung:** Fuer neue Installationen ist Proxmox Commander die bessere Wahl.
