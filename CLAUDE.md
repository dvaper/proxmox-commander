# Proxmox Commander

## Projekt-Uebersicht

Standalone VM-Management-Plattform fuer Proxmox VE mit integriertem NetBox, Ansible und Terraform.

## Architektur

```
docker-compose.yml
├── dpc-web (Vue.js + Vuetify + Nginx)
├── dpc-api (FastAPI + SQLAlchemy)
├── netbox (NetBox Container)
├── netbox-worker (Background Jobs)
├── netbox-housekeeping (Cleanup)
├── postgres (PostgreSQL fuer NetBox)
└── redis (Cache fuer NetBox)
```

## Image-Namen

| Komponente | Image | Registry |
|------------|-------|----------|
| API | dpc-api | registry.gitlab.newsxc.net/darthvaper/docker-proxmox-commander/dpc-api |
| Web | dpc-web | registry.gitlab.newsxc.net/darthvaper/docker-proxmox-commander/dpc-web |

## Entwicklungs-Workflow

```bash
# Lokale Entwicklung (baut Images lokal)
docker compose -f docker-compose.dev.yml up -d --build

# Nur Backend/Frontend neu bauen
docker compose -f docker-compose.dev.yml build dpc-api
docker compose -f docker-compose.dev.yml up -d dpc-api

# Logs anzeigen
docker compose logs -f
```

## Release-Workflow

```bash
# Neuen Release erstellen
git tag v0.2.0
git push --tags

# GitLab CI baut automatisch:
# - dpc-api:v0.2.0 und dpc-api:latest
# - dpc-web:v0.2.0 und dpc-web:latest
```

## Daten-Verzeichnisse

- `data/db/` - SQLite (commander.db)
- `data/inventory/` - Ansible Inventory YAML
- `data/playbooks/` - Ansible Playbooks
- `data/roles/` - Ansible Roles
- `data/terraform/` - VM .tf Dateien
- `data/ssh/` - SSH Private Key

## API-Endpunkte

Backend laeuft auf Port 8000 (intern):

- `GET /api/health` - Health Check
- `POST /api/auth/token` - Login
- `GET /api/terraform/vms` - VM-Liste
- `POST /api/terraform/vms` - VM erstellen
- `GET /api/playbooks` - Playbook-Liste
- `POST /api/executions` - Playbook ausfuehren

## Umgebungsvariablen

Siehe `.env.example` fuer alle verfuegbaren Optionen.

Wichtigste:
- `PROXMOX_HOST` - Proxmox Node IP
- `PROXMOX_TOKEN_ID` - API Token ID
- `PROXMOX_TOKEN_SECRET` - API Token Secret
- `NETBOX_TOKEN` - NetBox API Token
- `SECRET_KEY` - JWT Secret

## Commit-Konventionen

- Commits in Deutsch (wie Rest des Projekts)
- Keine automatischen Signaturen
- Format: `<type>: <beschreibung>`
  - `feat:` Neues Feature
  - `fix:` Bugfix
  - `docs:` Dokumentation
  - `improve:` Verbesserung
