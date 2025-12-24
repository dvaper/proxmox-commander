# Benachrichtigungs-Feature - Implementierungsplan

## Uebersicht

Robustes Benachrichtigungssystem fuer Proxmox Commander mit mehreren Kanaelen:
- **E-Mail** (SMTP) - Passwort-Reset, System-Benachrichtigungen
- **Gotify** - Push-Benachrichtigungen auf Mobile/Desktop
- **Webhooks** - Integration mit externen Systemen (Slack, Discord, etc.)

---

## Phase 1: Datenmodell & Konfiguration

### 1.1 Neue Datenbank-Tabellen

```sql
-- Benachrichtigungseinstellungen (global)
CREATE TABLE notification_settings (
    id INTEGER PRIMARY KEY,
    -- SMTP
    smtp_enabled BOOLEAN DEFAULT FALSE,
    smtp_host VARCHAR(255),
    smtp_port INTEGER DEFAULT 587,
    smtp_user VARCHAR(255),
    smtp_password VARCHAR(255),  -- verschluesselt speichern!
    smtp_from_email VARCHAR(255),
    smtp_from_name VARCHAR(100) DEFAULT 'Proxmox Commander',
    smtp_use_tls BOOLEAN DEFAULT TRUE,
    smtp_use_ssl BOOLEAN DEFAULT FALSE,
    -- Gotify
    gotify_enabled BOOLEAN DEFAULT FALSE,
    gotify_url VARCHAR(255),
    gotify_token VARCHAR(255),  -- verschluesselt speichern!
    gotify_priority INTEGER DEFAULT 5,
    -- Allgemein
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Benutzer-Benachrichtigungspraeferenzen
CREATE TABLE user_notification_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    -- Kanaele aktivieren
    email_enabled BOOLEAN DEFAULT TRUE,
    gotify_enabled BOOLEAN DEFAULT FALSE,
    gotify_user_token VARCHAR(255),  -- optionaler User-spezifischer Token
    -- Ereignistypen
    notify_vm_created BOOLEAN DEFAULT TRUE,
    notify_vm_deleted BOOLEAN DEFAULT TRUE,
    notify_vm_state_change BOOLEAN DEFAULT FALSE,
    notify_ansible_completed BOOLEAN DEFAULT TRUE,
    notify_ansible_failed BOOLEAN DEFAULT TRUE,
    notify_system_alerts BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Passwort-Reset Tokens
CREATE TABLE password_reset_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook-Konfigurationen
CREATE TABLE webhooks (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(255),  -- fuer HMAC-Signatur
    enabled BOOLEAN DEFAULT TRUE,
    -- Ereignisse
    on_vm_created BOOLEAN DEFAULT FALSE,
    on_vm_deleted BOOLEAN DEFAULT FALSE,
    on_ansible_completed BOOLEAN DEFAULT FALSE,
    on_ansible_failed BOOLEAN DEFAULT FALSE,
    -- Metadaten
    last_triggered_at TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Benachrichtigungs-Log
CREATE TABLE notification_log (
    id INTEGER PRIMARY KEY,
    channel VARCHAR(20) NOT NULL,  -- 'email', 'gotify', 'webhook'
    recipient VARCHAR(255),
    subject VARCHAR(255),
    event_type VARCHAR(50),
    status VARCHAR(20),  -- 'sent', 'failed', 'pending'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.2 Umgebungsvariablen (.env)

```env
# SMTP Konfiguration (optional - kann auch in UI konfiguriert werden)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=secret
SMTP_FROM_EMAIL=noreply@example.com
SMTP_FROM_NAME=Proxmox Commander
SMTP_USE_TLS=true

# Gotify (optional)
GOTIFY_URL=https://gotify.example.com
GOTIFY_TOKEN=app-token-here
GOTIFY_PRIORITY=5

# Passwort-Reset
PASSWORD_RESET_EXPIRY_HOURS=24
APP_URL=http://localhost:8080  # fuer Links in E-Mails
```

---

## Phase 2: Backend-Services

### 2.1 Notification Service (`backend/app/services/notification.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import hashlib
import hmac

class NotificationChannel(ABC):
    """Abstrakte Basisklasse fuer Benachrichtigungskanaele"""

    @abstractmethod
    async def send(self, recipient: str, subject: str, message: str, **kwargs) -> bool:
        pass

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        pass


class EmailChannel(NotificationChannel):
    """SMTP E-Mail Kanal"""

    def __init__(self, config: dict):
        self.host = config.get('smtp_host')
        self.port = config.get('smtp_port', 587)
        self.user = config.get('smtp_user')
        self.password = config.get('smtp_password')
        self.from_email = config.get('smtp_from_email')
        self.from_name = config.get('smtp_from_name', 'Proxmox Commander')
        self.use_tls = config.get('smtp_use_tls', True)

    async def send(self, recipient: str, subject: str, message: str,
                   html_message: Optional[str] = None, **kwargs) -> bool:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = recipient

        msg.attach(MIMEText(message, 'plain'))
        if html_message:
            msg.attach(MIMEText(html_message, 'html'))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=self.use_tls
            )
            return True
        except Exception as e:
            logger.error(f"E-Mail senden fehlgeschlagen: {e}")
            return False

    async def test_connection(self) -> tuple[bool, str]:
        try:
            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                start_tls=self.use_tls
            ) as smtp:
                await smtp.login(self.user, self.password)
                return True, "SMTP-Verbindung erfolgreich"
        except Exception as e:
            return False, str(e)


class GotifyChannel(NotificationChannel):
    """Gotify Push-Benachrichtigungen"""

    def __init__(self, config: dict):
        self.url = config.get('gotify_url', '').rstrip('/')
        self.token = config.get('gotify_token')
        self.priority = config.get('gotify_priority', 5)

    async def send(self, recipient: str, subject: str, message: str,
                   priority: Optional[int] = None, **kwargs) -> bool:
        if not self.url or not self.token:
            return False

        # recipient kann ein user-spezifischer Token sein
        token = recipient if recipient != 'default' else self.token

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.url}/message",
                    headers={"X-Gotify-Key": token},
                    json={
                        "title": subject,
                        "message": message,
                        "priority": priority or self.priority
                    }
                )
                return response.status_code == 200
            except Exception as e:
                logger.error(f"Gotify senden fehlgeschlagen: {e}")
                return False

    async def test_connection(self) -> tuple[bool, str]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.url}/application",
                    headers={"X-Gotify-Key": self.token}
                )
                if response.status_code == 200:
                    return True, "Gotify-Verbindung erfolgreich"
                return False, f"HTTP {response.status_code}"
            except Exception as e:
                return False, str(e)


class WebhookChannel(NotificationChannel):
    """Webhook-Benachrichtigungen"""

    def __init__(self, webhook_config: dict):
        self.url = webhook_config.get('url')
        self.secret = webhook_config.get('secret')
        self.name = webhook_config.get('name')

    async def send(self, recipient: str, subject: str, message: str,
                   event_type: str = None, payload: dict = None, **kwargs) -> bool:
        data = {
            "event": event_type,
            "title": subject,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "proxmox-commander",
            **(payload or {})
        }

        headers = {"Content-Type": "application/json"}

        # HMAC-Signatur hinzufuegen wenn Secret konfiguriert
        if self.secret:
            signature = hmac.new(
                self.secret.encode(),
                json.dumps(data).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.url,
                    json=data,
                    headers=headers,
                    timeout=10.0
                )
                return response.status_code < 400
            except Exception as e:
                logger.error(f"Webhook {self.name} fehlgeschlagen: {e}")
                return False


class NotificationService:
    """Zentrale Verwaltung aller Benachrichtigungen"""

    def __init__(self, db_session):
        self.db = db_session
        self._email_channel = None
        self._gotify_channel = None

    async def _get_settings(self) -> dict:
        """Laedt globale Benachrichtigungseinstellungen"""
        result = await self.db.execute(
            select(NotificationSettings).limit(1)
        )
        settings = result.scalar_one_or_none()
        return settings.__dict__ if settings else {}

    async def notify(self, event_type: str, subject: str, message: str,
                     user_id: Optional[int] = None, payload: dict = None):
        """
        Sendet Benachrichtigungen an alle konfigurierten Kanaele

        Args:
            event_type: z.B. 'vm_created', 'ansible_failed'
            subject: Betreff/Titel
            message: Nachrichtentext
            user_id: Nur diesen Benutzer benachrichtigen (sonst alle)
            payload: Zusaetzliche Daten fuer Webhooks
        """
        settings = await self._get_settings()

        # Benutzer mit aktivierten Benachrichtigungen fuer diesen Event-Typ
        users = await self._get_subscribed_users(event_type, user_id)

        # E-Mail senden
        if settings.get('smtp_enabled'):
            email_channel = EmailChannel(settings)
            for user in users:
                if user.email and user.prefs.email_enabled:
                    success = await email_channel.send(
                        user.email, subject, message,
                        html_message=self._render_html_template(event_type, subject, message)
                    )
                    await self._log_notification('email', user.email, subject, event_type,
                                                  'sent' if success else 'failed')

        # Gotify senden
        if settings.get('gotify_enabled'):
            gotify_channel = GotifyChannel(settings)
            for user in users:
                if user.prefs.gotify_enabled:
                    token = user.prefs.gotify_user_token or 'default'
                    success = await gotify_channel.send(
                        token, subject, message,
                        priority=self._get_priority(event_type)
                    )
                    await self._log_notification('gotify', user.username, subject, event_type,
                                                  'sent' if success else 'failed')

        # Webhooks triggern
        webhooks = await self._get_webhooks_for_event(event_type)
        for webhook in webhooks:
            channel = WebhookChannel(webhook)
            success = await channel.send(
                webhook['url'], subject, message,
                event_type=event_type, payload=payload
            )
            await self._log_notification('webhook', webhook['name'], subject, event_type,
                                          'sent' if success else 'failed')
```

### 2.2 Passwort-Reset Service (`backend/app/services/password_reset.py`)

```python
import secrets
from datetime import datetime, timedelta

class PasswordResetService:
    def __init__(self, db_session, notification_service: NotificationService):
        self.db = db_session
        self.notifications = notification_service
        self.expiry_hours = int(os.getenv('PASSWORD_RESET_EXPIRY_HOURS', 24))
        self.app_url = os.getenv('APP_URL', 'http://localhost:8080')

    async def request_reset(self, email: str) -> bool:
        """Erstellt Reset-Token und sendet E-Mail"""
        # Benutzer finden
        user = await self._get_user_by_email(email)
        if not user:
            # Aus Sicherheitsgruenden keine Rueckmeldung ob E-Mail existiert
            return True

        # Alte Tokens invalidieren
        await self._invalidate_existing_tokens(user.id)

        # Neuen Token erstellen
        token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(hours=self.expiry_hours)

        await self.db.execute(
            insert(PasswordResetToken).values(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
        )
        await self.db.commit()

        # E-Mail senden
        reset_url = f"{self.app_url}/reset-password?token={token}"
        await self.notifications.notify(
            event_type='password_reset',
            subject='Passwort zuruecksetzen - Proxmox Commander',
            message=f"""
Hallo {user.username},

Sie haben das Zuruecksetzen Ihres Passworts angefordert.

Klicken Sie auf folgenden Link (gueltig fuer {self.expiry_hours} Stunden):
{reset_url}

Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.

Mit freundlichen Gruessen,
Proxmox Commander
            """,
            user_id=user.id
        )

        return True

    async def validate_token(self, token: str) -> Optional[int]:
        """Prueft Token und gibt User-ID zurueck"""
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == token,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > datetime.utcnow()
            )
        )
        reset_token = result.scalar_one_or_none()
        return reset_token.user_id if reset_token else None

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Setzt Passwort zurueck mit gueltigem Token"""
        user_id = await self.validate_token(token)
        if not user_id:
            return False

        # Passwort aendern
        hashed = get_password_hash(new_password)
        await self.db.execute(
            update(User).where(User.id == user_id).values(hashed_password=hashed)
        )

        # Token als verwendet markieren
        await self.db.execute(
            update(PasswordResetToken).where(
                PasswordResetToken.token == token
            ).values(used=True)
        )

        await self.db.commit()
        return True
```

---

## Phase 3: API-Endpunkte

### 3.1 Notification Router (`backend/app/routers/notifications.py`)

```python
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# --- Admin-Endpunkte (nur Super-Admin) ---

@router.get("/settings")
async def get_notification_settings(current_user: User = Depends(get_current_super_admin)):
    """Globale Benachrichtigungseinstellungen abrufen"""
    pass

@router.put("/settings")
async def update_notification_settings(
    settings: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_super_admin)
):
    """Globale Einstellungen aktualisieren (SMTP, Gotify)"""
    pass

@router.post("/settings/test-smtp")
async def test_smtp_connection(current_user: User = Depends(get_current_super_admin)):
    """SMTP-Verbindung testen"""
    pass

@router.post("/settings/test-gotify")
async def test_gotify_connection(current_user: User = Depends(get_current_super_admin)):
    """Gotify-Verbindung testen"""
    pass

# --- Webhook-Verwaltung ---

@router.get("/webhooks")
async def list_webhooks(current_user: User = Depends(get_current_super_admin)):
    """Alle Webhooks auflisten"""
    pass

@router.post("/webhooks")
async def create_webhook(
    webhook: WebhookCreate,
    current_user: User = Depends(get_current_super_admin)
):
    """Neuen Webhook erstellen"""
    pass

@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_super_admin)
):
    """Webhook loeschen"""
    pass

@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_super_admin)
):
    """Webhook mit Test-Payload ausloesen"""
    pass

# --- Benutzer-Praeferenzen ---

@router.get("/preferences")
async def get_my_preferences(current_user: User = Depends(get_current_user)):
    """Eigene Benachrichtigungspraeferenzen abrufen"""
    pass

@router.put("/preferences")
async def update_my_preferences(
    prefs: UserNotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user)
):
    """Eigene Praeferenzen aktualisieren"""
    pass

# --- Benachrichtigungs-Log ---

@router.get("/log")
async def get_notification_log(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_super_admin)
):
    """Benachrichtigungs-Log abrufen"""
    pass
```

### 3.2 Password Reset Router (`backend/app/routers/password_reset.py`)

```python
router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Passwort-Reset anfordern"""
    service = PasswordResetService(db, notification_service)
    await service.request_reset(email)
    # Immer Erfolg zurueckmelden (Sicherheit)
    return {"message": "Falls die E-Mail existiert, wurde ein Reset-Link gesendet"}

@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """Passwort mit Token zuruecksetzen"""
    service = PasswordResetService(db, notification_service)
    success = await service.reset_password(token, new_password)
    if not success:
        raise HTTPException(400, "Ungueltiger oder abgelaufener Token")
    return {"message": "Passwort erfolgreich geaendert"}

@router.get("/validate-reset-token")
async def validate_reset_token(token: str):
    """Prueft ob Token gueltig ist (fuer Frontend)"""
    service = PasswordResetService(db, notification_service)
    user_id = await service.validate_token(token)
    return {"valid": user_id is not None}
```

---

## Phase 4: Frontend-Komponenten

### 4.1 Neue Views

| Datei | Beschreibung |
|-------|--------------|
| `views/ForgotPasswordView.vue` | "Passwort vergessen" Formular |
| `views/ResetPasswordView.vue` | Neues Passwort setzen (mit Token) |
| `views/NotificationSettingsView.vue` | Admin: SMTP/Gotify/Webhooks konfigurieren |

### 4.2 Komponenten

| Datei | Beschreibung |
|-------|--------------|
| `components/NotificationPreferences.vue` | Benutzer-Praeferenzen im Profil-Dialog |
| `components/WebhookManager.vue` | CRUD fuer Webhooks |
| `components/NotificationLog.vue` | Log-Anzeige mit Filtern |

### 4.3 Login-View erweitern

```vue
<!-- In LoginView.vue -->
<v-card-actions>
  <router-link to="/forgot-password" class="text-caption">
    Passwort vergessen?
  </router-link>
</v-card-actions>
```

---

## Phase 5: Integration mit bestehenden Features

### 5.1 Event-Trigger hinzufuegen

| Modul | Event | Wann |
|-------|-------|------|
| Terraform | `vm_created` | Nach erfolgreichem `terraform apply` |
| Terraform | `vm_deleted` | Nach erfolgreichem `terraform destroy` |
| Ansible | `ansible_completed` | Playbook erfolgreich beendet |
| Ansible | `ansible_failed` | Playbook mit Fehler beendet |
| System | `system_alert` | Kritische Fehler, Service-Probleme |

### 5.2 Beispiel-Integration (Ansible)

```python
# In routers/ansible.py nach Playbook-Ausfuehrung

if execution.status == 'success':
    await notification_service.notify(
        event_type='ansible_completed',
        subject=f'Playbook "{playbook_name}" erfolgreich',
        message=f'Das Playbook wurde auf {host_count} Hosts ausgefuehrt.',
        payload={
            'playbook': playbook_name,
            'hosts': hosts,
            'duration_seconds': duration
        }
    )
elif execution.status == 'failed':
    await notification_service.notify(
        event_type='ansible_failed',
        subject=f'Playbook "{playbook_name}" fehlgeschlagen',
        message=f'Fehler: {error_message}',
        payload={
            'playbook': playbook_name,
            'error': error_message
        }
    )
```

---

## Phase 6: E-Mail-Templates

### 6.1 Template-Struktur (`backend/app/templates/email/`)

```
templates/email/
├── base.html           # Basis-Layout mit Logo, Footer
├── password_reset.html
├── vm_created.html
├── vm_deleted.html
├── ansible_completed.html
├── ansible_failed.html
└── system_alert.html
```

### 6.2 Beispiel: Basis-Template

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5; }
    .container { max-width: 600px; margin: 0 auto; background: white; }
    .header { background: #1565C0; color: white; padding: 20px; text-align: center; }
    .content { padding: 30px; }
    .footer { background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; color: #666; }
    .button { display: inline-block; padding: 12px 24px; background: #1976D2; color: white; text-decoration: none; border-radius: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Proxmox Commander</h1>
    </div>
    <div class="content">
      {{ content }}
    </div>
    <div class="footer">
      Diese E-Mail wurde automatisch generiert.<br>
      &copy; {{ year }} Proxmox Commander
    </div>
  </div>
</body>
</html>
```

---

## Phase 7: Sicherheit

### 7.1 Credentials verschluesseln

```python
from cryptography.fernet import Fernet

# Verschluesselungskey aus SECRET_KEY ableiten
def get_encryption_key():
    secret = os.getenv('SECRET_KEY')
    # Key muss 32 Bytes sein
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())

def encrypt_credential(value: str) -> str:
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode()).decode()

def decrypt_credential(encrypted: str) -> str:
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted.encode()).decode()
```

### 7.2 Rate-Limiting fuer Password-Reset

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/forgot-password")
@limiter.limit("3/minute")  # Max 3 Anfragen pro Minute
async def forgot_password(request: Request, email: EmailStr):
    pass
```

---

## Implementierungs-Reihenfolge

| Schritt | Beschreibung | Aufwand |
|---------|--------------|---------|
| 1 | Datenmodell & Migrationen | ~2h |
| 2 | NotificationService Grundgeruest | ~3h |
| 3 | SMTP E-Mail-Kanal | ~2h |
| 4 | Passwort-Reset Backend + Frontend | ~4h |
| 5 | Admin-UI fuer SMTP-Einstellungen | ~3h |
| 6 | Gotify-Integration | ~2h |
| 7 | Webhook-System | ~3h |
| 8 | Benutzer-Praeferenzen UI | ~2h |
| 9 | Event-Integration (VM, Ansible) | ~3h |
| 10 | E-Mail-Templates | ~2h |
| 11 | Tests & Dokumentation | ~3h |

**Gesamt: ca. 29 Stunden**

---

## Abhaengigkeiten (requirements.txt)

```
aiosmtplib>=2.0.0     # Async SMTP
httpx>=0.24.0          # Async HTTP (Gotify, Webhooks)
jinja2>=3.1.0          # E-Mail Templates
cryptography>=41.0.0   # Credential-Verschluesselung
slowapi>=0.1.8         # Rate-Limiting
```

---

## Testplan

1. **SMTP-Tests**
   - Verbindung mit gueltigem/ungueltigem Server
   - E-Mail-Versand (TLS, SSL, Plain)
   - Template-Rendering

2. **Passwort-Reset**
   - Token-Generierung
   - Token-Validierung (gueltig, abgelaufen, verwendet)
   - Passwort-Aenderung
   - Rate-Limiting

3. **Gotify**
   - Push-Nachricht senden
   - User-spezifische Tokens
   - Fehlerbehandlung

4. **Webhooks**
   - HMAC-Signatur
   - Retry-Logik bei Fehlern
   - Verschiedene Payloads

5. **Integration**
   - VM-Events triggern Benachrichtigungen
   - Ansible-Events triggern Benachrichtigungen
   - Benutzer-Praeferenzen werden respektiert
