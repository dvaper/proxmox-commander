# Offene Aufgaben - Proxmox Commander

## Setup-Wizard Verbesserungen

- [x] **App-Admin Panel nicht sichtbar genug**: Der "App Administrator" Bereich im Setup-Wizard ist in einem zugeklappten Expansion Panel versteckt. **Geloest**: Panel ist jetzt standardmaessig offen + Warnhinweis wenn Passwort fehlt.

- [x] **Pflichtfeld deutlicher kennzeichnen**: App-Admin Passwort ist Pflichtfeld (min. 6 Zeichen). **Geloest**: Warnung oben im Step + "Pflicht"/"OK" Chip am Panel + Error-Farbe.

- [x] **NetBox Token Laenge pruefen**: Der Setup-Wizard generiert ein NetBox API-Token mit 40 Zeichen hex. **Geprueft**: 40 hex chars ist NetBox Standard-Format (20 Bytes). SECRET_KEY braucht 50+, aber API-Token ist korrekt.

## Sicherheit

- [x] **Bestehende admin/admin Credentials**: Wenn App vor v0.2.3 eingerichtet wurde, existiert bereits ein Admin-User mit Passwort "admin". **Geloest**: `create_default_admin()` aktualisiert jetzt bestehende Super-Admins wenn Credentials in .env geaendert wurden.

## UX Verbesserungen

- [x] **NetBox Status-Anzeige**: Status-Badge im UI zeigt NetBox-Zustand (Starting/Ready/Error) - implementiert in v0.2.4

- [x] **Status-Badge Beschriftung**: Die Status-Badge in der Titel-Bar zeigt nur "Online/Starting/Error" ohne Kontext. **Geloest**: Label geaendert zu "Services: Online/Starting/Error".

## Technische Schulden (aus Sicherheitsaudit)

- [ ] **Hardcoded IPs entfernen**: `cloud_init_service.py` enthaelt hardcoded Proxmox Node IPs und Phone-Home URL
- [ ] **SSH Public Keys konfigurierbar machen**: Aktuell hardcoded in `cloud_init_service.py`
- [ ] **JWT Secret Validierung**: Warnung/Fehler wenn Default "change-me-in-production" verwendet wird

---

# Feature-Implementierung aus Referenzprojekt (Ansible Commander)

Dieses Dokument listet Features aus dem Referenzprojekt auf, die im Proxmox Commander noch nicht implementiert sind.

**Wichtige Designprinzipien:**
- Proxmox Commander wird als Docker-Image bereitgestellt
- Generischer Ansatz fuer unbekannte Zielumgebungen
- Keine Abhaengigkeiten zu spezifischer Infrastruktur (NAS-Pfade, etc.)
- Konfiguration ueber Umgebungsvariablen und Setup-Wizard

---

## Prioritaet 1: Kritische Fixes

### 1.1 VM-Loeschung robuster gestalten
**Status:** ✅ Getestet und funktioniert (2025-12-24)

Die `delete_vm_complete()` Methode existiert und funktioniert:
- [x] VM in Proxmox stoppen vor Loeschung
- [x] NetBox VM-Eintrag loeschen (wenn vorhanden)
- [x] NetBox IP freigeben
- [x] Terraform State bereinigen
- [x] TF-Datei loeschen
- [x] Ansible Inventory bereinigen
- [ ] Cloud-Init Snippet loeschen (NAS-unabhaengig machen)

---

### 1.2 NetBox VM-Objekt beim Deployment erstellen
**Status:** ✅ Implementiert (v0.2.18, 2025-12-24)

Beim Terraform-Deployment wird jetzt zusaetzlich ein **VM-Objekt** unter "Virtualization > Virtual Machines" erstellt.

**Implementiert:**
- [x] `netbox_service.create_vm()` Methode
- [x] `netbox_service.get_or_create_cluster()` - Cluster "Proxmox" wird automatisch angelegt
- [x] `netbox_service.assign_ip_to_vm()` - IP wird mit VM verknuepft (primary_ip4)
- [x] `netbox_service.create_vm_with_ip()` - Kombinierte Methode fuer Deploy
- [x] `netbox_service.delete_vm()` - VM-Objekt wird bei Loeschung mitgeloescht
- [x] Integration in `vm_deployment_service.on_deploy_success()`

---

## Prioritaet 2: Sinnvolle Erweiterungen

### 2.1 Erweiterte Playbook-Verwaltung
**Referenz:** `ansible-commander/backend/app/services/playbook_editor.py`

Der Ansible Commander hat erweiterte Features:
- Playbook-Vorlagen mit Kategorien
- Syntax-Validierung vor Speicherung
- Git-Integration (Commit nach Aenderung)

**Im Proxmox Commander bereits vorhanden:**
- Basis Playbook Editor
- Playbook Execution mit WebSocket Output
- Playbook Scanner

**Fehlend:**
- [ ] Playbook-Vorlagen-System mit Kategorien

---

### 2.2 Inventory Sync Service Erweiterungen
**Referenz:** `ansible-commander/backend/app/services/inventory_sync_service.py`

**Features im Ansible Commander:**
- Background-Sync mit Proxmox
- Automatische Host-Erkennung
- Sync-Intervall konfigurierbar

**Im Proxmox Commander vorhanden:** Basis-Sync

**Fehlend:**
- [ ] Konfigurierbares Sync-Intervall ueber UI
- [ ] Background-Sync als optionaler Hintergrund-Task

---

### 2.3 Theme-Auswahl fuer Benutzer
**Status:** ✅ Implementiert (v0.2.19, 2025-12-24)

Ermoeglicht die Auswahl eines Farbthemas zur besseren Unterscheidung von anderen
Applikationen (z.B. Ansible Commander).

**Implementiert:**
- [x] Theme-Auswahl im Benutzerprofil speichern (`PATCH /api/auth/me/preferences`)
- [x] 5 verschiedene Themes: Blau, Orange, Gruen, Lila, Teal
- [x] Theme wird beim Login automatisch geladen
- [x] Vuetify Theme-System (`theme.global.name`)
- [x] Theme-Auswahl in Profil-Dialog mit sofortiger Vorschau

**Verfuegbare Themes:**
| Name | Primary Color | Beschreibung |
|------|---------------|--------------|
| blue | #1976D2 | Standard (wie Ansible Commander) |
| orange | #FF9800 | Proxmox-aehnlich |
| green | #4CAF50 | Frisch |
| purple | #9C27B0 | Unterscheidbar |
| teal | #009688 | Professionell |

---

## Prioritaet 3: Nice-to-Have

### 3.1 Git Sync Service
**Referenz:** `ansible-commander/backend/app/services/git_sync_service.py`

**Bewertung:** Niedriger Mehrwert fuer hohen Aufwand.

Da `./data/` bereits als Bind Mount existiert, kann der Benutzer seine Daten
**selbst** versionieren ohne integrierten Git Sync:

```bash
cd proxmox-commander/data
git init
git remote add origin git@gitlab.example.com:user/my-infra.git
git add . && git commit -m "Initial" && git push
```

**Zusaetzliche Konfiguration fuer Benutzer waere:**
- Git-Repository erstellen
- SSH-Key generieren und im Container verfuegbar machen
- docker-compose.yml anpassen (Volume-Mount)
- Known Hosts konfigurieren

**Fazit:** Aufwand/Nutzen-Verhaeltnis fragwuerdig fuer generischen Docker-Container.

---

### 3.2 Settings Service Erweiterungen
**Referenz:** `ansible-commander/backend/app/services/settings_service.py`

Erweiterte Einstellungsverwaltung:
- Runtime-Konfiguration aendern
- Settings in Datenbank persistieren
- Hot-Reload ohne Container-Neustart

**Aktuell:** Settings werden ueber .env und Umgebungsvariablen verwaltet

---

### 3.3 Permission Service Erweiterungen
**Referenz:** `ansible-commander/backend/app/services/permission_service.py`

Granulare Berechtigungen:
- Rollen-basierte Zugriffskontrolle
- Permissions pro Ressource (VM, Playbook, etc.)

**Aktuell:** Einfache Admin/User Unterscheidung

---

## Nicht uebernehmen

Diese Features aus dem Ansible Commander sind **nicht sinnvoll** fuer Proxmox Commander:

### VLAN Config (hardcodiert)
**Datei:** `ansible-commander/backend/app/services/vlan_config.py`

Hardcodierte VLAN-Konfiguration. Proxmox Commander laedt VLANs **dynamisch aus NetBox** - das ist der bessere Ansatz fuer einen generischen Container.

---

## Architektur-Unterschiede

| Aspekt | Ansible Commander | Proxmox Commander |
|--------|-------------------|-------------------|
| VLAN-Verwaltung | Hardcodiert in `vlan_config.py` | Dynamisch aus NetBox |
| Setup | Manuelle .env Konfiguration | Setup-Wizard UI |
| NetBox | Optional | Integriert (eigener Container) |
| Deployment | Direkt auf VM | Docker Compose |
| Git-Sync | Integriert | Nicht noetig (./data/ ist Bind Mount) |
| Terraform Provider | bpg/proxmox | bpg/proxmox |

---

## Implementierungs-Reihenfolge

1. ~~**VM-Loeschung testen**~~ - ✅ Erledigt (2025-12-24)
2. ~~**NetBox VM-Objekt beim Deployment**~~ - ✅ Erledigt (v0.2.18, 2025-12-24)
3. ~~**Theme-Auswahl**~~ - ✅ Erledigt (v0.2.19, 2025-12-24)
4. **Playbook-Vorlagen** - Verbessert UX
5. **Background Inventory Sync** - Automatisierung

---

## Notizen zur Docker-Kompatibilitaet

Bei der Implementierung neuer Features beachten:

1. **Keine absoluten Pfade** - Alles relativ zu gemounteten Volumes
2. **Umgebungsvariablen** - Konfiguration ueber ENV, nicht Dateien
3. **Graceful Degradation** - Features muessen optional sein
4. **Health Checks** - Neue Services in Health-Endpoint einbinden
5. **Logging** - Strukturiertes Logging fuer Container-Umgebung

```python
# Beispiel: Pfad-Handling fuer Docker
import os
from pathlib import Path

# Gut: Umgebungsvariable mit Fallback
REPO_PATH = Path(os.getenv("GIT_REPO_PATH", "/repo"))

# Schlecht: Hardcodierter Pfad
REPO_PATH = Path("/home/user/infrastructure")  # Funktioniert nicht im Container
```
