# Proxmox Commander

VM-Management-Plattform fuer Proxmox VE mit integriertem NetBox (IPAM/DCIM), Ansible und Terraform.

## Features

- **VM-Deployment** via Terraform mit automatischer IP-Vergabe aus NetBox
- **Ansible Integration** mit Live-Output via WebSocket
- **NetBox IPAM** fuer IP-Adressverwaltung (integrierter Container)
- **Cloud-Init** mit 13 spezialisierten Profilen
- **Multi-Cluster** Unterstuetzung fuer mehrere Proxmox-Nodes
- **Theme-Auswahl** mit Hell/Dunkel/System-Modus

## Voraussetzungen

| Komponente | Minimum | Empfohlen |
|------------|---------|-----------|
| Docker | 20.10 | 24.x+ |
| Docker Compose | v2.0 | v2.20+ |
| RAM | 4 GB* | 8 GB |
| Disk | 10 GB | 20 GB |

*4 GB ist das absolute Minimum - NetBox kann bei wenig RAM langsam starten (bis zu 5 Min).

**Proxmox VE Anforderungen:**
- Proxmox VE 7.x oder 8.x
- API-Token mit folgenden Berechtigungen:

| Berechtigung | Beschreibung |
|--------------|--------------|
| `VM.Allocate` | VMs erstellen |
| `VM.Clone` | Templates klonen |
| `VM.Config.Disk` | Disks konfigurieren |
| `VM.Config.CPU` | CPU konfigurieren |
| `VM.Config.Memory` | RAM konfigurieren |
| `VM.Config.Network` | Netzwerk konfigurieren |
| `VM.Config.Cloudinit` | Cloud-Init konfigurieren |
| `VM.Config.Options` | VM-Optionen aendern |
| `VM.PowerMgmt` | Start/Stop/Reboot |
| `VM.Monitor` | Guest-Agent, Status |
| `VM.Audit` | VM-Konfiguration lesen |
| `VM.Snapshot` | Snapshots erstellen/loeschen |
| `VM.Snapshot.Rollback` | Snapshot-Rollback |
| `VM.Migrate` | VM-Migration |
| `Datastore.AllocateSpace` | Disk-Speicher anlegen |
| `Datastore.Audit` | Storage-Info lesen |
| `Sys.Audit` | Cluster-Ressourcen lesen |

**Empfohlene Rolle erstellen (Proxmox):**
```bash
pveum role add TerraformRole -privs "VM.Allocate VM.Clone VM.Config.Disk VM.Config.CPU VM.Config.Memory VM.Config.Network VM.Config.Cloudinit VM.Config.Options VM.PowerMgmt VM.Monitor VM.Audit VM.Snapshot VM.Snapshot.Rollback VM.Migrate Datastore.AllocateSpace Datastore.Audit Sys.Audit"
pveum user add terraform@pve
pveum aclmod / -user terraform@pve -role TerraformRole
pveum user token add terraform@pve terraform-token --privsep=0
```

**Weitere Anforderungen:**
- SSH-Zugang zu den Nodes (fuer Cloud-Init Snippets auf NAS)
- Cloud-Init faehiges VM-Template

## Installation

### 1. Repository klonen

```bash
git clone https://gitlab.newsxc.net/darthvaper/docker-proxmox-commander.git
cd docker-proxmox-commander
```

**Oder nur die benoetigten Dateien:**
```bash
mkdir proxmox-commander && cd proxmox-commander
curl -LO https://gitlab.newsxc.net/darthvaper/docker-proxmox-commander/-/raw/main/docker-compose.yml
curl -LO https://gitlab.newsxc.net/darthvaper/docker-proxmox-commander/-/raw/main/.env.example
cp .env.example .env
```

### 2. Container starten

```bash
docker compose up -d
```

**Erster Start dauert laenger** - NetBox muss initialisiert werden (ca. 2-5 Minuten).

### 3. Setup-Wizard durchfuehren

Oeffne im Browser:
```
http://<server-ip>:8080/setup
```

Der Setup-Wizard fragt folgende Informationen ab:

| Schritt | Erforderlich | Beschreibung |
|---------|--------------|--------------|
| Proxmox Host | Ja | URL zum Proxmox-Server (z.B. `https://proxmox.local:8006`) |
| Proxmox Token ID | Ja | Format: `user@realm!token-name` |
| Proxmox Token Secret | Ja | Das API-Token Secret |
| SSL verifizieren | Optional | Bei selbstsignierten Zertifikaten: Nein |
| SSH User | Ja | User fuer Ansible (z.B. `ansible`) |
| App-Admin User | Ja | Benutzername fuer die App |
| App-Admin Passwort | Ja | Mindestens 6 Zeichen |
| App-Admin E-Mail | Optional | E-Mail-Adresse |

### 4. Login

Nach dem Setup-Wizard:
```
http://<server-ip>:8080
```

Login mit den im Wizard angegebenen Credentials.

## Ports und Services

| Service | Port | Beschreibung |
|---------|------|--------------|
| Proxmox Commander | 8080 | Haupt-Webinterface |
| NetBox | 8081 | IPAM/DCIM Webinterface |

**Interne Services (nicht von aussen erreichbar):**
- PostgreSQL (NetBox Datenbank)
- Redis (NetBox Cache)
- API Backend

## Datenverzeichnisse

Nach dem Start werden unter `./data/` erstellt:

```
./data/
├── db/              # SQLite Datenbank (App)
├── inventory/       # Ansible Inventory (YAML)
├── playbooks/       # Ansible Playbooks
├── roles/           # Ansible Roles
├── terraform/       # Terraform Konfigurationen
├── ssh/             # SSH Keys
├── netbox/          # NetBox Daten
│   ├── media/       # Uploads
│   ├── reports/     # Reports
│   └── scripts/     # Custom Scripts
└── postgres/        # PostgreSQL Daten (NetBox)
```

## Update

```bash
cd proxmox-commander
docker compose pull
docker compose up -d
```

**Hinweis:** Datenbank-Migrationen werden automatisch beim Start ausgefuehrt.

## Konfiguration

### Umgebungsvariablen

Die wichtigsten Variablen in `.env`:

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `APP_PORT` | 8080 | Port fuer das Webinterface |
| `NETBOX_PORT` | 8081 | Port fuer NetBox |
| `PROXMOX_HOST` | - | Proxmox API URL |
| `PROXMOX_TOKEN_ID` | - | API Token ID |
| `PROXMOX_TOKEN_SECRET` | - | API Token Secret |
| `PROXMOX_VERIFY_SSL` | true | SSL-Zertifikat pruefen |
| `SECRET_KEY` | (generiert) | JWT Secret Key |
| `APP_ADMIN_USER` | admin | Admin-Benutzername |
| `APP_ADMIN_PASSWORD` | - | Admin-Passwort |

### Externes NetBox verwenden

Falls ein bestehendes NetBox verwendet werden soll:

1. In `.env` hinzufuegen:
   ```
   NETBOX_URL=http://external-netbox:8080
   NETBOX_TOKEN=<api-token>
   ```

2. NetBox-Container deaktivieren (optional):
   ```bash
   docker compose up -d dpc-frontend dpc-api
   ```

## Troubleshooting

### Container startet nicht

```bash
# Logs pruefen
docker compose logs dpc-api

# Haeufige Fehler:
# - "no such column: users.theme" -> Update auf v0.2.21+
# - "NetBox not ready" -> Warten, NetBox braucht Zeit zum Starten
```

### Login funktioniert nicht

1. `.env` pruefen - ist `APP_ADMIN_PASSWORD` gesetzt?
2. Container neu starten: `docker compose restart dpc-api`
3. Logs pruefen: `docker compose logs dpc-api | grep -i admin`

### NetBox zeigt Fehler

```bash
# NetBox-Status pruefen
docker compose logs netbox | tail -50

# NetBox neu starten
docker compose restart netbox netbox-worker netbox-housekeeping
```

### Proxmox-Verbindung fehlgeschlagen

1. API-Token Berechtigungen pruefen
2. Firewall-Regeln pruefen (Port 8006)
3. SSL-Einstellung pruefen (`PROXMOX_VERIFY_SSL=false` bei selbstsignierten Zertifikaten)

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Frontend   │  │   Backend    │  │     NetBox       │   │
│  │   (Nginx)    │──│   (FastAPI)  │──│   (Django)       │   │
│  │   :8080      │  │   :8000      │  │   :8081          │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                           │                   │              │
│                           │          ┌────────┴───────┐      │
│                           │          │                │      │
│                    ┌──────┴──────┐   │   PostgreSQL   │      │
│                    │   SQLite    │   │   Redis        │      │
│                    │   (App DB)  │   │   (NetBox)     │      │
│                    └─────────────┘   └────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────┴──────┐          ┌───────┴───────┐
       │  Proxmox    │          │   Ansible     │
       │  Cluster    │          │   Targets     │
       └─────────────┘          └───────────────┘
```

## Lizenz

MIT

## Changelog

Siehe [CHANGELOG](frontend/src/data/changelog.json) oder im UI unter dem Info-Icon.
