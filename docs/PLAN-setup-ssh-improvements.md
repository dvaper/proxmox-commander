# Implementierungsplan: SSH-Konfiguration (Setup & Settings)

**GitHub Issue:** #1 - Setup-Wizard: SSH-Key Import und bessere Defaults
**Erstellt:** 2025-12-25
**Aktualisiert:** 2025-12-25

## Übersicht

Die SSH-Konfiguration soll an zwei Stellen möglich sein:

1. **Setup-Wizard** (Initial-Konfiguration bei Erstinstallation)
2. **Settings-Bereich** (Nachträgliche Anpassung durch Super-Admin)

Beide nutzen die gleichen Backend-Endpoints und Frontend-Komponenten.

## Aktueller Stand

### Backend (`backend/app/routers/setup.py`)
- `SetupConfig.default_ssh_user` und `ansible_remote_user` haben Default "ansible"
- Keine SSH-Key-Discovery oder -Generierung
- Keine SSH-Verbindungstests

### Backend (`backend/app/routers/settings.py`)
- Existiert bereits für andere Einstellungen (NetBox URL, Defaults)
- Nutzt `get_current_super_admin_user` für Authentifizierung
- Keine SSH-Konfiguration vorhanden

### Frontend - Bestehende Settings-Views
- `/settings/notifications` → NotificationSettingsView.vue
- `/settings/cloud-init` → CloudInitSettingsView.vue
- **Fehlt:** `/settings/ssh` für SSH-Konfiguration

### Frontend (`frontend/src/views/SetupWizardView.vue`)
- SSH-Sektion zeigt nur ein Textfeld für `ansible_remote_user`
- Hinweis: "SSH-Key muss unter data/ssh/id_ed25519 abgelegt werden"
- Kein Import, Upload, Generierung oder Verbindungstest

---

## Architektur-Entscheidung: Dual-Context Endpoints

Die SSH-Endpoints müssen in zwei Kontexten funktionieren:

| Kontext | Auth | Router | Anwendungsfall |
|---------|------|--------|----------------|
| Setup | Keine | `/api/setup/ssh-*` | Erstinstallation |
| Settings | Super-Admin | `/api/settings/ssh-*` | Nachträgliche Änderung |

**Lösung:** Gemeinsamer SSH-Service mit zwei Router-Einbindungen:

```python
# backend/app/services/ssh_service.py
class SSHService:
    """Gemeinsamer Service für SSH-Operationen"""
    async def list_available_keys() -> SSHKeyListResponse
    async def import_key(source_path: str) -> SSHKeyImportResponse
    async def upload_key(private_key: str, public_key: str) -> SSHKeyUploadResponse
    async def generate_key(key_type: str, comment: str) -> SSHKeyGenerateResponse
    async def test_connection(host: str, user: str, port: int) -> SSHTestResponse
    async def get_current_config() -> SSHConfigResponse
    async def update_config(user: str) -> SSHConfigResponse

# backend/app/routers/setup.py - Ohne Auth (für Erstinstallation)
@router.get("/ssh-keys")
async def setup_list_ssh_keys():
    return await ssh_service.list_available_keys()

# backend/app/routers/settings.py - Mit Super-Admin Auth
@router.get("/ssh")
async def settings_get_ssh_config(
    current_user: User = Depends(get_current_super_admin_user)
):
    return await ssh_service.get_current_config()
```

---

## Phase 1: Backend - SSH Service & Endpoints

### 1.0 Neuer SSH Service
**Datei:** `backend/app/services/ssh_service.py`

Zentraler Service für alle SSH-Operationen, genutzt von Setup und Settings.

### 1.1 SSH-Key Discovery Endpoint
**Endpoints:**
- `GET /api/setup/ssh-keys` (ohne Auth - Setup)
- `GET /api/settings/ssh/keys` (Super-Admin - Settings)

Listet verfügbare SSH-Keys auf, die importiert werden können.

```python
class SSHKeyInfo(BaseModel):
    """Information über einen SSH-Key"""
    name: str  # z.B. "id_ed25519", "id_rsa"
    path: str  # Vollständiger Pfad
    type: str  # "ed25519", "rsa", "ecdsa"
    has_public: bool  # Ob .pub Datei existiert
    fingerprint: Optional[str] = None

class SSHKeyListResponse(BaseModel):
    """Liste verfügbarer SSH-Keys"""
    available: bool  # Ob das SSH-Verzeichnis gemountet ist
    keys: list[SSHKeyInfo] = []
    current_key: Optional[str] = None  # Aktuell konfigurierter Key
    default_user: str  # Aktueller Systembenutzer
```

**Logik:**
1. Prüfe ob `/host-ssh/` Volume gemountet ist (aus ~/.ssh des Host-Systems)
2. Liste alle private Keys auf (id_*, kein .pub Suffix)
3. Bestimme Key-Typ durch Header-Analyse
4. Prüfe ob passender Public Key existiert
5. Ermittle aktuellen Systembenutzer als Default (statt "ansible")

### 1.2 SSH-Key Import Endpoint
**Endpoints:**
- `POST /api/setup/ssh-import` (ohne Auth - Setup)
- `POST /api/settings/ssh/import` (Super-Admin - Settings)

Kopiert einen Key aus dem gemounteten Verzeichnis.

```python
class SSHKeyImportRequest(BaseModel):
    """Request zum Importieren eines SSH-Keys"""
    source_path: str  # z.B. "/host-ssh/id_ed25519"

class SSHKeyImportResponse(BaseModel):
    """Ergebnis des Imports"""
    success: bool
    message: str
    target_path: Optional[str] = None
```

**Logik:**
1. Validiere source_path (muss in /host-ssh/ liegen)
2. Kopiere Private Key nach `data/ssh/id_ed25519`
3. Kopiere Public Key nach `data/ssh/id_ed25519.pub` (falls vorhanden)
4. Setze korrekte Berechtigungen (600 für Private, 644 für Public)

### 1.3 SSH-Key Upload Endpoint
**Endpoints:**
- `POST /api/setup/ssh-upload` (ohne Auth - Setup)
- `POST /api/settings/ssh/upload` (Super-Admin - Settings)

Speichert einen per Copy/Paste übermittelten Key.

```python
class SSHKeyUploadRequest(BaseModel):
    """Request zum Hochladen eines SSH-Keys"""
    private_key: str  # PEM-formatierter Private Key
    public_key: Optional[str] = None  # Optional: Public Key

class SSHKeyUploadResponse(BaseModel):
    """Ergebnis des Uploads"""
    success: bool
    message: str
    key_type: Optional[str] = None
    fingerprint: Optional[str] = None
```

**Logik:**
1. Validiere Key-Format (muss mit "-----BEGIN" beginnen)
2. Extrahiere Key-Typ
3. Speichere unter `data/ssh/id_ed25519` (bzw. id_rsa je nach Typ)
4. Wenn kein Public Key mitgeliefert, generiere ihn aus Private Key
5. Setze korrekte Berechtigungen

### 1.4 SSH-Key Generierung Endpoint
**Endpoints:**
- `POST /api/setup/ssh-generate` (ohne Auth - Setup)
- `POST /api/settings/ssh/generate` (Super-Admin - Settings)

Generiert ein neues SSH-Schlüsselpaar.

```python
class SSHKeyGenerateRequest(BaseModel):
    """Request zum Generieren eines neuen SSH-Keys"""
    key_type: str = "ed25519"  # "ed25519" oder "rsa"
    comment: str = ""  # Optionaler Kommentar

class SSHKeyGenerateResponse(BaseModel):
    """Ergebnis der Generierung"""
    success: bool
    message: str
    public_key: Optional[str] = None  # Zur Anzeige für den Benutzer
    fingerprint: Optional[str] = None
```

**Logik:**
1. Generiere Schlüsselpaar mit `ssh-keygen`
2. Speichere unter `data/ssh/id_ed25519`
3. Gib Public Key zurück (für authorized_keys auf Ziel-VMs)

### 1.5 SSH-Verbindungstest Endpoint
**Endpoints:**
- `POST /api/setup/ssh-test` (ohne Auth - Setup)
- `POST /api/settings/ssh/test` (Super-Admin - Settings)

Testet die SSH-Verbindung zu einem Host.

```python
class SSHTestRequest(BaseModel):
    """Request für SSH-Verbindungstest"""
    host: str  # IP oder Hostname
    user: str  # SSH-Benutzer
    port: int = 22

class SSHTestResponse(BaseModel):
    """Ergebnis des SSH-Tests"""
    success: bool
    message: str
    host_reachable: bool = False
    auth_successful: bool = False
    error_details: Optional[str] = None
```

**Logik:**
1. Prüfe ob Host erreichbar (Port 22 offen)
2. Versuche SSH-Verbindung mit konfiguriertem Key
3. Führe einfachen Befehl aus (`echo "test"`)
4. Gib detaillierte Fehlermeldung bei Problemen

### 1.6 SSH-Konfiguration Endpoint (nur Settings)
**Endpoints:**
- `GET /api/settings/ssh` (Super-Admin - aktuelle Konfiguration lesen)
- `PUT /api/settings/ssh` (Super-Admin - Konfiguration aktualisieren)

Liest und aktualisiert die SSH-Konfiguration.

```python
class SSHConfigResponse(BaseModel):
    """Aktuelle SSH-Konfiguration"""
    ssh_user: str  # Aktueller SSH-Benutzer
    has_key: bool  # Ob ein SSH-Key konfiguriert ist
    key_type: Optional[str] = None  # "ed25519", "rsa", etc.
    key_fingerprint: Optional[str] = None
    public_key: Optional[str] = None  # Für Anzeige

class SSHConfigUpdateRequest(BaseModel):
    """Request zum Aktualisieren der SSH-Konfiguration"""
    ssh_user: str  # Neuer SSH-Benutzer
```

**Logik:**
1. Lese aktuelle Konfiguration aus .env (ANSIBLE_REMOTE_USER)
2. Prüfe ob SSH-Key vorhanden
3. Bei Update: Schreibe neuen Wert in .env und löse Hot-Reload aus

---

## Phase 2: Frontend - Setup-Wizard Erweiterungen

### 2.1 Erweitertes SSH-Panel im Wizard

Das SSH/Ansible Panel erhält folgende neue Komponenten:

```
┌─────────────────────────────────────────────────────────────────┐
│  🔑 SSH Konfiguration                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SSH-Benutzer für Ansible                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ darthvaper              (auto-detected from system)         ││
│  └─────────────────────────────────────────────────────────────┘│
│  ⓘ Dieser Benutzer muss auf den Ziel-VMs existieren           │
│                                                                 │
│  SSH-Key                                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ◯ Bestehenden Key importieren                               ││
│  │ ◯ Key hochladen (Copy/Paste)                                ││
│  │ ◯ Neuen Key generieren                                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  [Bei "Importieren":]                                           │
│  Verfügbare Keys:                                               │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ▼ id_ed25519 (ED25519)                                      ││
│  │   id_rsa (RSA 4096)                                         ││
│  └─────────────────────────────────────────────────────────────┘│
│  ⓘ Keys werden aus ~/.ssh gelesen (Volume: /host-ssh)          │
│                                                                 │
│  [Bei "Hochladen":]                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ -----BEGIN OPENSSH PRIVATE KEY-----                         ││
│  │ b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAA...                      ││
│  │ -----END OPENSSH PRIVATE KEY-----                           ││
│  └─────────────────────────────────────────────────────────────┘│
│  ⚠️ Private Keys niemals teilen!                                │
│                                                                 │
│  [Bei "Generieren":]                                            │
│  Key-Typ: ED25519 ▼                                             │
│  [🔑 Neuen Key generieren]                                      │
│                                                                 │
│  Nach Generierung:                                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ssh-ed25519 AAAA... user@host                               ││
│  └─────────────────────────────────────────────────────────────┘│
│  ⓘ Diesen Public Key auf Ziel-VMs hinterlegen                  │
│  [📋 Kopieren]                                                  │
│                                                                 │
│  ────────────────────────────────────────────────────────────── │
│  Verbindungstest                                                │
│  Host: ┌─────────────────────────────────────────────────┐      │
│        │ 192.168.60.100                                  │      │
│        └─────────────────────────────────────────────────┘      │
│  [🔌 Verbindung testen]                                         │
│                                                                 │
│  ✅ Verbindung erfolgreich! Host: proxmox-node1                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Neue Reactive State-Variablen

```javascript
// SSH State
const sshMode = ref('import')  // 'import', 'upload', 'generate'
const availableKeys = ref([])  // Liste verfügbarer Keys
const selectedKey = ref(null)  // Ausgewählter Key zum Import
const uploadedKey = ref('')    // Per Textarea eingegebener Key
const generatedPublicKey = ref('')  // Nach Generierung anzeigen
const sshTestHost = ref('')    // Host für Verbindungstest
const sshTestResult = ref(null)  // Ergebnis des Tests
const sshKeyLoading = ref(false)  // Lade-Status
const defaultUser = ref('')    // Vom Backend ermittelter Default-User
```

### 2.3 Neue API-Aufrufe

```javascript
// Verfügbare Keys laden
async function loadAvailableKeys() {
  const response = await axios.get('/api/setup/ssh-keys')
  availableKeys.value = response.data.keys
  defaultUser.value = response.data.default_user
  config.value.ansible_remote_user = response.data.default_user
}

// Key importieren
async function importKey() {
  const response = await axios.post('/api/setup/ssh-import', {
    source_path: selectedKey.value.path
  })
  // Handle response
}

// Key hochladen
async function uploadKey() {
  const response = await axios.post('/api/setup/ssh-upload', {
    private_key: uploadedKey.value
  })
  // Handle response
}

// Neuen Key generieren
async function generateKey() {
  const response = await axios.post('/api/setup/ssh-generate', {
    key_type: 'ed25519',
    comment: config.value.ansible_remote_user + '@proxmox-commander'
  })
  generatedPublicKey.value = response.data.public_key
}

// SSH-Verbindung testen
async function testSSHConnection() {
  const response = await axios.post('/api/setup/ssh-test', {
    host: sshTestHost.value,
    user: config.value.ansible_remote_user
  })
  sshTestResult.value = response.data
}
```

---

## Phase 3: Frontend - SSH Settings View (Neu)

### 3.1 Neue View-Datei
**Datei:** `frontend/src/views/SSHSettingsView.vue`
**Route:** `/settings/ssh`

Diese View ermöglicht die nachträgliche Konfiguration von SSH-Einstellungen.

### 3.2 Navigation
Erweiterung des Settings-Menüs im Layout:

```javascript
// router/index.js
{
  path: '/settings/ssh',
  name: 'SSHSettings',
  component: () => import('@/views/SSHSettingsView.vue'),
  meta: { requiresAuth: true, requiresSuperAdmin: true }
},
```

### 3.3 SSHSettingsView.vue Struktur

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙️ SSH-Einstellungen                              [Super-Admin] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Aktuelle Konfiguration ──────────────────────────────────┐  │
│  │                                                           │  │
│  │  SSH-Benutzer: darthvaper                    [✏️ Ändern]  │  │
│  │  SSH-Key:      ✅ Konfiguriert (ED25519)                  │  │
│  │  Fingerprint:  SHA256:xxxxxx...                           │  │
│  │                                                           │  │
│  │  Public Key:                                              │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │ ssh-ed25519 AAAA... user@host                      │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  │  [📋 Kopieren]                                            │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ SSH-Key verwalten ───────────────────────────────────────┐  │
│  │                                                           │  │
│  │  ⚠️ Achtung: Das Ändern des SSH-Keys erfordert, dass     │  │
│  │     der neue Public Key auf allen Ziel-VMs hinterlegt    │  │
│  │     wird!                                                 │  │
│  │                                                           │  │
│  │  ◯ Bestehenden Key importieren                            │  │
│  │  ◯ Key hochladen (Copy/Paste)                             │  │
│  │  ◯ Neuen Key generieren                                   │  │
│  │                                                           │  │
│  │  [... wie im Setup-Wizard ...]                            │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ Verbindungstest ─────────────────────────────────────────┐  │
│  │                                                           │  │
│  │  Host aus Inventory wählen:                               │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │ ▼ proxmox-node1 (192.168.60.10)                    │   │  │
│  │  │   proxmox-node2 (192.168.60.11)                    │   │  │
│  │  │   vm-webserver (192.168.60.100)                    │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  Oder manuell eingeben:                                   │  │
│  │  ┌────────────────────────────────────────────────────┐   │  │
│  │  │ 192.168.60.100                                     │   │  │
│  │  └────────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  [🔌 Verbindung testen]                                   │  │
│  │                                                           │  │
│  │  ✅ Verbindung erfolgreich!                               │  │
│  │     Host: proxmox-node1                                   │  │
│  │     User: darthvaper                                      │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Unterschiede zum Setup-Wizard

| Feature | Setup-Wizard | SSH Settings |
|---------|-------------|--------------|
| Auth | Keine | Super-Admin |
| Kontext | Erstinstallation | Nachträgliche Änderung |
| Host-Auswahl | Manuell | Aus Inventory wählbar |
| Warnungen | Minimal | Hinweise auf Auswirkungen |
| Key-Anzeige | Nur bei Generierung | Immer (aktueller Key) |

### 3.5 Shared Components

Um Code-Duplikation zu vermeiden, wird eine gemeinsame Komponente erstellt:

**Datei:** `frontend/src/components/SSHKeyManager.vue`

```vue
<template>
  <div>
    <!-- SSH-Benutzer -->
    <v-text-field v-model="sshUser" ... />

    <!-- Key-Modus Auswahl -->
    <v-radio-group v-model="keyMode">
      <v-radio value="import" label="Bestehenden Key importieren" />
      <v-radio value="upload" label="Key hochladen" />
      <v-radio value="generate" label="Neuen Key generieren" />
    </v-radio-group>

    <!-- Conditional Content based on mode -->
    ...
  </div>
</template>

<script setup>
const props = defineProps({
  initialUser: { type: String, default: '' },
  showWarnings: { type: Boolean, default: false },
  apiPrefix: { type: String, default: '/api/setup' }
})

const emit = defineEmits(['key-changed', 'user-changed'])
</script>
```

Diese Komponente wird dann in beiden Views verwendet:

```vue
<!-- SetupWizardView.vue -->
<SSHKeyManager
  :initial-user="config.ansible_remote_user"
  api-prefix="/api/setup"
  @key-changed="handleKeyChange"
/>

<!-- SSHSettingsView.vue -->
<SSHKeyManager
  :initial-user="currentConfig.ssh_user"
  :show-warnings="true"
  api-prefix="/api/settings/ssh"
  @key-changed="handleKeyChange"
/>
```

---

## Phase 4: Docker-Compose Anpassungen

### 4.1 Host-SSH Volume Mount

Neues Volume für Zugriff auf Host-SSH-Keys:

```yaml
services:
  backend:
    volumes:
      - ~/.ssh:/host-ssh:ro  # Readonly-Zugriff auf Host SSH-Keys
      - ./data/ssh:/app/data/ssh  # Bestehender Mount
```

**Hinweis:** Der Mount ist optional. Wenn nicht vorhanden, zeigt der Wizard
nur "Upload" und "Generieren" Optionen an.

---

## Phase 5: Migrations-/Upgrade-Überlegungen

### 5.1 Bestehende Installationen

- Bestehende Konfigurationen bleiben unverändert
- Neue Funktionen sind optional und abwärtskompatibel
- Kein Datenverlust bei Update

### 5.2 Breaking Changes

Keine Breaking Changes. Alle Erweiterungen sind additiv.

### 5.3 Upgrade-Pfad

Für bestehende Installationen:

1. **Automatisch:** Settings-Bereich ist nach Update verfügbar
2. **Optional:** Host-SSH Volume in docker-compose.yml hinzufügen für Key-Import
3. **Empfohlen:** SSH-Verbindung über Settings testen nach Update

---

## Implementierungsreihenfolge

### Schritt 1: Backend-Grundlagen
1. **SSH Service erstellen** (`backend/app/services/ssh_service.py`)
2. **SSH-Key Discovery** (`GET /api/setup/ssh-keys`, `GET /api/settings/ssh/keys`)
3. **SSH-Verbindungstest** (`POST /api/setup/ssh-test`, `POST /api/settings/ssh/test`)
4. **SSH-Konfiguration lesen/schreiben** (`GET/PUT /api/settings/ssh`)

### Schritt 2: Frontend-Komponenten
5. **SSHKeyManager Komponente** (`frontend/src/components/SSHKeyManager.vue`)
6. **Setup-Wizard erweitern** (SSHKeyManager einbinden)
7. **SSH Settings View** (`frontend/src/views/SSHSettingsView.vue`)
8. **Router-Erweiterung** (Route `/settings/ssh` hinzufügen)

### Schritt 3: Erweiterte Key-Operationen
9. **Key-Generierung** (`POST /api/setup/ssh-generate`, `POST /api/settings/ssh/generate`)
10. **Key-Import** (`POST /api/setup/ssh-import`, `POST /api/settings/ssh/import`)
11. **Key-Upload** (`POST /api/setup/ssh-upload`, `POST /api/settings/ssh/upload`)

### Schritt 4: Integration
12. **Docker-Compose** (Volume-Mount für Host-SSH)
13. **Navigation** (Settings-Menü erweitern)
14. **Dokumentation** (README aktualisieren)

---

## Geschätzter Aufwand

| Komponente | Dateien | Komplexität |
|------------|---------|-------------|
| SSH Service | ssh_service.py (neu) | Mittel |
| Backend Setup-Endpoints | setup.py (erweitern) | Gering |
| Backend Settings-Endpoints | settings.py (erweitern) | Gering |
| SSHKeyManager Komponente | SSHKeyManager.vue (neu) | Mittel |
| Setup-Wizard Anpassung | SetupWizardView.vue | Gering |
| SSH Settings View | SSHSettingsView.vue (neu) | Mittel |
| Router/Navigation | router/index.js, Layout | Gering |
| Docker-Compose | docker-compose.yml | Gering |
| Tests | test_ssh_service.py (neu) | Mittel |
| Dokumentation | README.md | Gering |

---

## Akzeptanzkriterien

### Aus Issue #1 (Setup-Wizard)
- [x] Plan erstellt
- [x] Benutzer kann bestehenden SSH-Key importieren
- [x] Benutzer kann neuen SSH-Key generieren
- [x] Default SSH-User ist nicht mehr hardcoded "ansible"
- [x] SSH-Verbindung kann vor Abschluss des Setups getestet werden
- [x] Klare Fehlermeldungen bei SSH-Problemen

### Zusätzlich (Settings-Bereich)
- [x] SSH-Einstellungen unter `/settings/ssh` erreichbar
- [x] Super-Admin kann SSH-Benutzer nachträglich ändern
- [x] Super-Admin kann SSH-Key nachträglich ändern
- [x] Aktuelle Konfiguration wird angezeigt (User, Key-Typ, Fingerprint)
- [x] Public Key kann kopiert werden
- [x] Verbindungstest mit Hosts aus Inventory möglich
- [x] Warnhinweise bei Änderungen (Key muss auf VMs hinterlegt werden)

---

## Implementiert am 2025-12-25

### Erstellte Dateien

**Backend:**
- `backend/app/services/ssh_service.py` - Zentraler SSH-Service

**Frontend:**
- `frontend/src/components/SSHKeyManager.vue` - Wiederverwendbare Komponente
- `frontend/src/views/SSHSettingsView.vue` - Settings-Seite

### Geänderte Dateien

**Backend:**
- `backend/app/routers/setup.py` - SSH-Endpoints hinzugefügt
- `backend/app/routers/settings.py` - SSH-Endpoints hinzugefügt

**Frontend:**
- `frontend/src/views/SetupWizardView.vue` - SSHKeyManager integriert
- `frontend/src/router/index.js` - Route hinzugefügt
- `frontend/src/App.vue` - Navigation erweitert

**Config:**
- `docker-compose.yml` - Optionales Host-SSH Volume dokumentiert
