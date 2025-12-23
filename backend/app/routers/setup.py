"""
Setup Router - Web-basierter Setup-Wizard

Endpoints fuer die initiale Konfiguration beim ersten App-Start.
Diese Endpoints sind ohne Authentifizierung zugaenglich.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/setup", tags=["setup"])


# =============================================================================
# Schemas
# =============================================================================

class SetupStatus(BaseModel):
    """Status der App-Konfiguration"""
    setup_complete: bool
    has_proxmox_config: bool
    has_secret_key: bool
    has_ssh_key: bool
    missing_items: list[str] = []


class ProxmoxConfig(BaseModel):
    """Proxmox-Verbindungskonfiguration"""
    host: str = Field(..., min_length=1, description="Proxmox Host (IP oder Hostname)")
    token_id: str = Field(..., min_length=1, description="API Token ID (user@realm!token-name)")
    token_secret: str = Field(..., min_length=1, description="API Token Secret")
    verify_ssl: bool = Field(default=False, description="SSL-Zertifikat verifizieren")


class ProxmoxValidationResult(BaseModel):
    """Ergebnis der Proxmox-Verbindungspruefung"""
    success: bool
    message: str
    version: Optional[str] = None
    cluster_name: Optional[str] = None
    node_count: Optional[int] = None
    error: Optional[str] = None


class SetupConfig(BaseModel):
    """Vollstaendige Setup-Konfiguration"""
    # Proxmox
    proxmox_host: str = Field(..., min_length=1)
    proxmox_token_id: str = Field(..., min_length=1)
    proxmox_token_secret: str = Field(..., min_length=1)
    proxmox_verify_ssl: bool = False

    # NetBox Admin Credentials (fuer integriertes NetBox)
    netbox_admin_user: str = Field(default="admin", description="NetBox Admin-Benutzername")
    netbox_admin_password: str = Field(default="admin", min_length=4, description="NetBox Admin-Passwort")
    netbox_admin_email: str = Field(default="admin@example.com", description="NetBox Admin E-Mail")

    # App Admin Credentials
    app_admin_user: str = Field(default="admin", description="App Admin-Benutzername")
    app_admin_password: str = Field(default="", min_length=0, description="App Admin-Passwort (min. 6 Zeichen)")
    app_admin_email: str = Field(default="admin@local", description="App Admin E-Mail")

    # Optionale Einstellungen
    secret_key: Optional[str] = None  # Wird generiert wenn nicht angegeben
    netbox_token: Optional[str] = None
    netbox_url: Optional[str] = None  # Fuer externes NetBox
    default_ssh_user: str = "ansible"
    ansible_remote_user: str = "ansible"


class SetupSaveResult(BaseModel):
    """Ergebnis des Setup-Speicherns"""
    success: bool
    message: str
    restart_required: bool = True
    env_file_path: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def get_env_file_path() -> Path:
    """Gibt den Pfad zur .env Datei zurueck"""
    # ENV_FILE wird per docker-compose auf /app/.env gesetzt,
    # welches zur Root .env gemountet ist
    from app.config import settings
    env_file = os.getenv("ENV_FILE", f"{settings.data_dir}/config/.env")
    return Path(env_file)


def check_setup_status() -> SetupStatus:
    """Prueft ob die App bereits konfiguriert ist"""
    from app.config import settings

    missing = []

    # Proxmox-Konfiguration
    has_proxmox = bool(
        settings.proxmox_host and
        settings.proxmox_token_id and
        settings.proxmox_token_secret
    )
    if not has_proxmox:
        if not settings.proxmox_host:
            missing.append("Proxmox Host")
        if not settings.proxmox_token_id:
            missing.append("Proxmox Token ID")
        if not settings.proxmox_token_secret:
            missing.append("Proxmox Token Secret")

    # Secret Key (fuer JWT)
    has_secret = settings.secret_key != "change-me-in-production"
    if not has_secret:
        missing.append("Secret Key")

    # SSH Key
    ssh_key_path = Path(settings.ssh_key_path)
    has_ssh = ssh_key_path.exists()
    if not has_ssh:
        missing.append("SSH Key")

    # Setup ist komplett wenn Proxmox konfiguriert ist
    # (Secret Key wird generiert, SSH Key ist optional)
    setup_complete = has_proxmox

    return SetupStatus(
        setup_complete=setup_complete,
        has_proxmox_config=has_proxmox,
        has_secret_key=has_secret,
        has_ssh_key=has_ssh,
        missing_items=missing,
    )


def generate_secret_key() -> str:
    """Generiert einen sicheren Secret Key (64 hex chars)"""
    import secrets
    return secrets.token_hex(32)


def generate_netbox_secret_key() -> str:
    """Generiert einen sicheren NetBox Secret Key (mind. 50 Zeichen)"""
    import secrets
    # NetBox erfordert mind. 50 Zeichen - wir generieren 60 fuer Sicherheit
    charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return ''.join(secrets.choice(charset) for _ in range(60))


async def validate_proxmox_connection(config: ProxmoxConfig) -> ProxmoxValidationResult:
    """Testet die Proxmox-Verbindung mit den angegebenen Credentials"""
    import httpx
    import ssl
    from urllib.parse import urlparse

    # API URL bauen - unterstuetzt:
    # - 192.168.1.100 (IP ohne Port -> https + :8006)
    # - 192.168.1.100:8006 (IP mit Port -> https)
    # - proxmox.example.com (Hostname ohne Port -> https + :8006)
    # - proxmox.example.com:8006 (Hostname mit Port -> https)
    # - https://proxmox.example.com (HTTPS ohne Port -> bleibt, kein :8006)
    # - https://proxmox.example.com:443 (Reverse Proxy -> bleibt)
    host = config.host.strip().rstrip("/")

    # Pruefen ob bereits ein Schema vorhanden ist
    if not host.startswith("http://") and not host.startswith("https://"):
        # Kein Schema - pruefen ob Port vorhanden
        if ":" in host.split("/")[0]:
            # Port vorhanden (z.B. 192.168.1.100:8006)
            host = f"https://{host}"
        else:
            # Kein Port - Standard Proxmox Port hinzufuegen
            host = f"https://{host}:8006"
    else:
        # Schema vorhanden - pruefen ob Port noetig
        parsed = urlparse(host)
        if not parsed.port:
            # Kein expliziter Port - bei HTTPS Standard-Port verwenden (kein :8006!)
            # Benutzer hat bewusst Schema angegeben, vermutlich Reverse Proxy
            pass
        # Sonst: Port ist explizit angegeben, nichts aendern

    # Token Header
    auth_header = f"PVEAPIToken={config.token_id}={config.token_secret}"

    try:
        # SSL-Kontext konfigurieren
        ssl_context = None
        if config.verify_ssl:
            ssl_context = ssl.create_default_context()
        else:
            ssl_context = False

        async with httpx.AsyncClient(verify=ssl_context, timeout=15.0) as client:
            # Version abfragen
            version_response = await client.get(
                f"{host}/api2/json/version",
                headers={"Authorization": auth_header}
            )

            if version_response.status_code == 401:
                return ProxmoxValidationResult(
                    success=False,
                    message="Authentifizierung fehlgeschlagen",
                    error="Ungueltige Token-Credentials. Bitte Token ID und Secret pruefen."
                )

            if version_response.status_code != 200:
                return ProxmoxValidationResult(
                    success=False,
                    message=f"Proxmox API Fehler: {version_response.status_code}",
                    error=version_response.text
                )

            version_data = version_response.json().get("data", {})
            version = version_data.get("version", "unbekannt")

            # Cluster-Info abfragen
            cluster_response = await client.get(
                f"{host}/api2/json/cluster/status",
                headers={"Authorization": auth_header}
            )

            cluster_name = None
            node_count = 0

            if cluster_response.status_code == 200:
                cluster_data = cluster_response.json().get("data", [])
                for item in cluster_data:
                    if item.get("type") == "cluster":
                        cluster_name = item.get("name")
                    if item.get("type") == "node":
                        node_count += 1

            return ProxmoxValidationResult(
                success=True,
                message=f"Verbindung erfolgreich! Proxmox VE {version}",
                version=version,
                cluster_name=cluster_name,
                node_count=node_count,
            )

    except ssl.SSLCertVerificationError as e:
        return ProxmoxValidationResult(
            success=False,
            message="SSL-Zertifikatsfehler",
            error=f"Zertifikat konnte nicht verifiziert werden: {str(e)}. "
                  "Versuchen Sie 'SSL-Zertifikat verifizieren' zu deaktivieren, "
                  "oder stellen Sie sicher, dass das Zertifikat gueltig ist."
        )
    except ssl.SSLError as e:
        return ProxmoxValidationResult(
            success=False,
            message="SSL-Fehler",
            error=f"SSL-Verbindungsfehler: {str(e)}"
        )
    except httpx.ConnectError as e:
        error_str = str(e).upper()
        original_error = str(e)

        # Erweiterte SSL-Fehlererkennung - httpx wrapped SSL-Fehler oft in ConnectError
        ssl_keywords = ["SSL", "TLS", "CERTIFICATE", "CERT", "VERIFY", "HANDSHAKE", "SECURE"]
        if any(keyword in error_str for keyword in ssl_keywords):
            return ProxmoxValidationResult(
                success=False,
                message="SSL-Verbindungsfehler",
                error=f"SSL/TLS-Fehler beim Verbinden: {original_error}. "
                      "Versuchen Sie 'SSL-Zertifikat verifizieren' zu deaktivieren."
            )

        # Connection refused = Host erreichbar aber Port geschlossen
        if "CONNECTION REFUSED" in error_str or "ERRNO 111" in error_str:
            return ProxmoxValidationResult(
                success=False,
                message="Port nicht erreichbar",
                error=f"Verbindung zu {host} abgelehnt. "
                      "Der Host ist erreichbar, aber Port 8006 ist nicht offen. "
                      "Bei Reverse Proxy: Verwende 'https://hostname' (ohne :8006)."
            )

        return ProxmoxValidationResult(
            success=False,
            message="Verbindung fehlgeschlagen",
            error=f"Host nicht erreichbar: {config.host}. Pruefen Sie die IP/Hostname und Firewall."
        )
    except httpx.TimeoutException:
        return ProxmoxValidationResult(
            success=False,
            message="Timeout",
            error="Verbindung zum Proxmox-Server hat zu lange gedauert (15 Sekunden)."
        )
    except Exception as e:
        error_str = str(e).upper()
        # Erweiterte SSL-Fehlererkennung
        ssl_keywords = ["SSL", "TLS", "CERTIFICATE", "CERT", "VERIFY", "HANDSHAKE", "SECURE"]
        if any(keyword in error_str for keyword in ssl_keywords):
            return ProxmoxValidationResult(
                success=False,
                message="SSL-Fehler",
                error=f"SSL-Problem: {str(e)}. "
                      "Versuchen Sie 'SSL-Zertifikat verifizieren' zu deaktivieren."
            )
        return ProxmoxValidationResult(
            success=False,
            message="Unbekannter Fehler",
            error=str(e)
        )


async def generate_terraform_tfvars(config: SetupConfig) -> None:
    """
    Generiert die terraform.tfvars Datei aus der Setup-Konfiguration.

    Die tfvars enthaelt die Proxmox-Credentials und Default-Werte.
    """
    from pathlib import Path
    from app.config import settings

    terraform_dir = Path(settings.terraform_dir)
    tfvars_path = terraform_dir / "terraform.tfvars"

    # SSH Public Key lesen (falls vorhanden)
    ssh_public_key = ""
    ssh_key_path = Path(settings.ssh_key_path)
    ssh_pub_path = ssh_key_path.with_suffix(".pub")
    if ssh_pub_path.exists():
        try:
            ssh_public_key = ssh_pub_path.read_text().strip()
        except Exception:
            pass

    # Proxmox API URL zusammenbauen
    host = config.proxmox_host
    if not host.startswith("http"):
        api_url = f"https://{host}:8006/api2/json"
    elif ":8006" not in host and not host.endswith("/api2/json"):
        api_url = f"{host.rstrip('/')}/api2/json"
    else:
        api_url = f"{host.rstrip('/')}/api2/json" if not host.endswith("/api2/json") else host

    # tfvars Inhalt
    tfvars_content = f'''# Proxmox Commander - Terraform Variablen
# Automatisch generiert durch Setup-Wizard
# Erstellt: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# Proxmox API
proxmox_api_url      = "{api_url}"
proxmox_token_id     = "{config.proxmox_token_id}"
proxmox_token_secret = "{config.proxmox_token_secret}"
proxmox_tls_insecure = {str(not config.proxmox_verify_ssl).lower()}

# VM-Defaults
default_template      = 940001
default_template_node = "gandalf"
ssh_user              = "{config.default_ssh_user}"
ssh_public_key        = "{ssh_public_key}"
default_dns           = ["192.168.2.1", "1.1.1.1"]
'''

    # Schreiben
    terraform_dir.mkdir(parents=True, exist_ok=True)
    tfvars_path.write_text(tfvars_content)
    logger.info(f"Terraform tfvars generiert: {tfvars_path}")


async def save_env_config(config: SetupConfig) -> SetupSaveResult:
    """Speichert die Konfiguration in die .env Datei"""
    env_path = get_env_file_path()

    # Verzeichnis erstellen falls nicht vorhanden
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Secret Key generieren falls nicht angegeben
    secret_key = config.secret_key or generate_secret_key()

    # Bestehende .env lesen falls vorhanden
    existing_lines = []
    existing_keys = set()
    existing_values = {}

    if env_path.exists():
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key = line.split("=", 1)[0]
                        value = line.split("=", 1)[1] if "=" in line else ""
                        existing_keys.add(key)
                        existing_values[key] = value
                    existing_lines.append(line)
        except Exception as e:
            logger.warning(f"Konnte bestehende .env nicht lesen: {e}")

    # NetBox Secret Key pruefen/generieren (mind. 50 Zeichen erforderlich)
    netbox_secret_key = existing_values.get("NETBOX_SECRET_KEY", "")
    if len(netbox_secret_key) < 50:
        netbox_secret_key = generate_netbox_secret_key()
        logger.info("Neuer NETBOX_SECRET_KEY generiert (mind. 50 Zeichen)")

    # Neue Werte
    new_values = {
        "PROXMOX_HOST": config.proxmox_host,
        "PROXMOX_TOKEN_ID": config.proxmox_token_id,
        "PROXMOX_TOKEN_SECRET": config.proxmox_token_secret,
        "PROXMOX_VERIFY_SSL": str(config.proxmox_verify_ssl).lower(),
        "SECRET_KEY": secret_key,
        "DEFAULT_SSH_USER": config.default_ssh_user,
        "ANSIBLE_REMOTE_USER": config.ansible_remote_user,
        # NetBox Admin Credentials
        "NETBOX_ADMIN_USER": config.netbox_admin_user,
        "NETBOX_ADMIN_PASSWORD": config.netbox_admin_password,
        "NETBOX_ADMIN_EMAIL": config.netbox_admin_email,
        # App Admin Credentials
        "APP_ADMIN_USER": config.app_admin_user,
        "APP_ADMIN_PASSWORD": config.app_admin_password,
        "APP_ADMIN_EMAIL": config.app_admin_email,
        # NetBox Secret Key (mind. 50 Zeichen)
        "NETBOX_SECRET_KEY": netbox_secret_key,
    }

    if config.netbox_token:
        new_values["NETBOX_TOKEN"] = config.netbox_token

    if config.netbox_url:
        new_values["NETBOX_URL"] = config.netbox_url

    try:
        # Header mit Erstellungsdatum
        from datetime import datetime
        header = f"# Proxmox Commander - Setup-Konfiguration\n# Erstellt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        # .env Datei schreiben
        with open(env_path, "w") as f:
            # Header nur bei neuer Datei
            if not existing_lines:
                f.write(header)

            # Bestehende Zeilen aktualisieren
            written_keys = set()
            for line in existing_lines:
                if line and not line.startswith("#") and "=" in line:
                    key = line.split("=")[0]
                    if key in new_values:
                        f.write(f"{key}={new_values[key]}\n")
                        written_keys.add(key)
                    else:
                        f.write(f"{line}\n")
                else:
                    f.write(f"{line}\n")

            # Neue Werte hinzufuegen
            for key, value in new_values.items():
                if key not in written_keys:
                    f.write(f"{key}={value}\n")

        logger.info(f"Setup-Konfiguration gespeichert in {env_path}")

        # Terraform tfvars generieren
        try:
            await generate_terraform_tfvars(config)
        except Exception as e:
            logger.warning(f"Terraform tfvars konnte nicht erstellt werden: {e}")

        return SetupSaveResult(
            success=True,
            message="Konfiguration erfolgreich gespeichert. Bitte Container neu starten.",
            restart_required=True,
            env_file_path=str(env_path),
        )

    except PermissionError:
        return SetupSaveResult(
            success=False,
            message="Keine Schreibberechtigung",
            error=f"Kann nicht in {env_path} schreiben. Pruefen Sie die Berechtigungen.",
            restart_required=False,
        )
    except Exception as e:
        return SetupSaveResult(
            success=False,
            message="Speichern fehlgeschlagen",
            error=str(e),
            restart_required=False,
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=SetupStatus)
async def get_setup_status():
    """
    Prueft ob die App bereits konfiguriert ist.

    Gibt zurueck welche Konfigurationselemente fehlen.
    Dieser Endpoint ist ohne Authentifizierung zugaenglich.
    """
    return check_setup_status()


@router.post("/validate/proxmox", response_model=ProxmoxValidationResult)
async def validate_proxmox(config: ProxmoxConfig):
    """
    Testet die Proxmox-Verbindung mit den angegebenen Credentials.

    Prueft:
    - Erreichbarkeit des Hosts
    - Gueltigkeit der API-Credentials
    - Liest Cluster-Informationen

    Dieser Endpoint ist ohne Authentifizierung zugaenglich.
    """
    return await validate_proxmox_connection(config)


@router.post("/save", response_model=SetupSaveResult)
async def save_setup(config: SetupConfig, force: bool = False):
    """
    Speichert die Setup-Konfiguration.

    Schreibt die Werte in die .env Datei.
    Nach dem Speichern muss der Container neu gestartet werden.

    Dieser Endpoint ist ohne Authentifizierung zugaenglich.

    Query-Parameter:
    - force: Wenn true, wird das Setup auch bei bereits abgeschlossener
             Konfiguration erneut durchgefuehrt (fuer Tests)
    """
    # Pruefen ob Setup bereits abgeschlossen
    status = check_setup_status()
    if status.setup_complete and not force:
        raise HTTPException(
            status_code=403,
            detail="Setup bereits abgeschlossen. Mit ?force=true kann das Setup erneut durchgefuehrt werden."
        )

    # Proxmox-Verbindung validieren
    proxmox_config = ProxmoxConfig(
        host=config.proxmox_host,
        token_id=config.proxmox_token_id,
        token_secret=config.proxmox_token_secret,
        verify_ssl=config.proxmox_verify_ssl,
    )

    validation = await validate_proxmox_connection(proxmox_config)
    if not validation.success:
        raise HTTPException(
            status_code=400,
            detail=f"Proxmox-Verbindung fehlgeschlagen: {validation.error}"
        )

    # Konfiguration speichern
    result = await save_env_config(config)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    # Settings neu laden (Hot-Reload via SettingsProxy)
    # Da PROXMOX_* nicht mehr in docker-compose.yml stehen, werden sie
    # direkt aus der .env Datei gelesen und koennen hot-reloaded werden.
    from app.config import reload_settings
    try:
        reload_settings(str(get_env_file_path()))
        result.restart_required = False
        result.message = "Konfiguration erfolgreich gespeichert und aktiviert."
        logger.info("Settings wurden nach Setup neu geladen (Hot-Reload)")
    except Exception as e:
        logger.warning(f"Hot-Reload fehlgeschlagen: {e} - Container-Restart erforderlich")
        # Fallback: restart_required bleibt True

    return result


@router.get("/generate-secret")
async def generate_secret():
    """
    Generiert einen neuen Secret Key.

    Kann im Frontend verwendet werden um einen sicheren Key zu generieren.
    """
    return {"secret_key": generate_secret_key()}
