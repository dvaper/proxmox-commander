"""
Settings Router - App-Einstellungen (nur Super-Admin)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    AppSettingRead,
    AppSettingUpdate,
    DefaultAccessSettings,
)
from app.auth.dependencies import get_current_super_admin_user
from app.services.settings_service import get_settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ==================== Schemas ====================

class NetBoxUrlUpdate(BaseModel):
    """Schema fuer NetBox URL Update"""
    url: Optional[str] = None


class NetBoxUrlResponse(BaseModel):
    """Schema fuer NetBox URL Response"""
    url: Optional[str] = None


@router.get("", response_model=List[AppSettingRead])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Alle Einstellungen abrufen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    settings = await settings_service.get_all_settings()
    return settings


@router.get("/defaults", response_model=DefaultAccessSettings)
async def get_default_access(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Default-Zugriffseinstellungen abrufen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    defaults = await settings_service.get_default_access()
    return DefaultAccessSettings(
        default_groups=defaults["default_groups"],
        default_playbooks=defaults["default_playbooks"],
    )


@router.put("/defaults", response_model=DefaultAccessSettings)
async def set_default_access(
    defaults: DefaultAccessSettings,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Default-Zugriffseinstellungen setzen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    await settings_service.set_default_access(
        groups=defaults.default_groups,
        playbooks=defaults.default_playbooks,
    )
    return defaults


@router.get("/defaults/groups", response_model=List[str])
async def get_default_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Default-Gruppen abrufen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    return await settings_service.get_default_groups()


@router.put("/defaults/groups", response_model=List[str])
async def set_default_groups(
    groups: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Default-Gruppen setzen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    await settings_service.set_default_groups(groups)
    return groups


@router.get("/defaults/playbooks", response_model=List[str])
async def get_default_playbooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Default-Playbooks abrufen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    return await settings_service.get_default_playbooks()


@router.put("/defaults/playbooks", response_model=List[str])
async def set_default_playbooks(
    playbooks: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Default-Playbooks setzen (nur Super-Admin)"""
    settings_service = get_settings_service(db)
    await settings_service.set_default_playbooks(playbooks)
    return playbooks


# ==================== NetBox External URL ====================

@router.get("/netbox-url", response_model=NetBoxUrlResponse)
async def get_netbox_url(
    db: AsyncSession = Depends(get_db),
):
    """
    Externe NetBox URL abrufen (public - fuer Frontend).

    Gibt die konfigurierte externe URL zurueck, ueber die NetBox
    im Browser erreichbar ist.
    """
    settings_service = get_settings_service(db)
    url = await settings_service.get_netbox_external_url()
    return NetBoxUrlResponse(url=url)


@router.put("/netbox-url", response_model=NetBoxUrlResponse)
async def set_netbox_url(
    data: NetBoxUrlUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Externe NetBox URL setzen (nur Super-Admin).

    Diese URL wird im Frontend verwendet, um Links zu NetBox anzuzeigen.
    Beispiel: https://netbox.example.com oder http://192.168.1.100:8081
    """
    settings_service = get_settings_service(db)
    await settings_service.set_netbox_external_url(data.url)
    return NetBoxUrlResponse(url=data.url)


# ==================== SSH Einstellungen ====================

from app.services.ssh_service import (
    get_ssh_service,
    SSHKeyListResponse,
    SSHKeyImportRequest,
    SSHKeyImportResponse,
    SSHKeyUploadRequest,
    SSHKeyUploadResponse,
    SSHKeyGenerateRequest,
    SSHKeyGenerateResponse,
    SSHKeyActivateRequest,
    SSHKeyActivateResponse,
    SSHKeyDeleteRequest,
    SSHKeyDeleteResponse,
    SSHTestRequest,
    SSHTestResponse,
    SSHConfigResponse,
    SSHConfigUpdateRequest,
)


@router.get("/ssh", response_model=SSHConfigResponse)
async def get_ssh_config(
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Aktuelle SSH-Konfiguration abrufen (nur Super-Admin).

    Gibt den konfigurierten SSH-Benutzer und Key-Informationen zurueck.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.get_config()


@router.put("/ssh", response_model=SSHConfigResponse)
async def update_ssh_config(
    request: SSHConfigUpdateRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    SSH-Konfiguration aktualisieren (nur Super-Admin).

    Aendert den SSH-Benutzer fuer Ansible-Verbindungen.
    Die Aenderung wird sofort wirksam (Hot-Reload).
    """
    ssh_service = get_ssh_service()
    return await ssh_service.update_config(request)


@router.get("/ssh/keys", response_model=SSHKeyListResponse)
async def list_ssh_keys(
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Verfuegbare SSH-Keys auflisten (nur Super-Admin).

    Zeigt Keys aus dem gemounteten Host-SSH-Verzeichnis (/host-ssh)
    sowie den aktuell konfigurierten Key.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.list_available_keys()


@router.post("/ssh/import", response_model=SSHKeyImportResponse)
async def import_ssh_key(
    request: SSHKeyImportRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    SSH-Key aus Host-SSH-Verzeichnis importieren (nur Super-Admin).

    Der Key wird nach data/ssh/ kopiert.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.import_key(request)


@router.post("/ssh/upload", response_model=SSHKeyUploadResponse)
async def upload_ssh_key(
    request: SSHKeyUploadRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    SSH-Key per Copy/Paste hochladen (nur Super-Admin).

    Der Private Key wird validiert und gespeichert.
    Falls kein Public Key mitgeliefert wird, wird dieser automatisch generiert.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.upload_key(request)


@router.post("/ssh/generate", response_model=SSHKeyGenerateResponse)
async def generate_ssh_key(
    request: SSHKeyGenerateRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Neues SSH-Schluesselpaar generieren (nur Super-Admin).

    Unterstuetzte Key-Typen: ed25519 (empfohlen), rsa (4096 bit).
    Der Public Key muss auf den Ziel-VMs hinterlegt werden.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.generate_key(request)


@router.post("/ssh/test", response_model=SSHTestResponse)
async def test_ssh_connection(
    request: SSHTestRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    SSH-Verbindung zu einem Host testen (nur Super-Admin).

    Prueft Erreichbarkeit und Authentifizierung.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.test_connection(request)


@router.post("/ssh/activate", response_model=SSHKeyActivateResponse)
async def activate_ssh_key(
    request: SSHKeyActivateRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    SSH-Key aktivieren (nur Super-Admin).

    Setzt den angegebenen Key als aktiven Key fuer SSH-Verbindungen.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.activate_key(request)


@router.post("/ssh/delete", response_model=SSHKeyDeleteResponse)
async def delete_ssh_key(
    request: SSHKeyDeleteRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    SSH-Key loeschen (nur Super-Admin).

    Loescht den angegebenen Key. Der aktive Key kann nicht geloescht werden.
    """
    ssh_service = get_ssh_service()
    return await ssh_service.delete_key(request)


# ==================== Proxmox Einstellungen ====================

from app.config import settings as app_settings, reload_settings
from app.services.proxmox_service import get_proxmox_service
import os
import subprocess


class ProxmoxConfigResponse(BaseModel):
    """Schema fuer Proxmox Konfiguration"""
    proxmox_host: str = ""
    proxmox_token_id: Optional[str] = None
    proxmox_token_secret: Optional[str] = None
    proxmox_verify_ssl: bool = False


class ProxmoxConfigUpdate(BaseModel):
    """Schema fuer Proxmox Konfiguration Update"""
    proxmox_host: str
    proxmox_token_id: str
    proxmox_token_secret: Optional[str] = None  # Optional - nur wenn geaendert
    proxmox_verify_ssl: bool = False


class ProxmoxTestRequest(BaseModel):
    """Schema fuer Verbindungstest"""
    host: str
    token_id: str
    token_secret: str
    verify_ssl: bool = False


class ProxmoxTestResponse(BaseModel):
    """Schema fuer Verbindungstest Ergebnis"""
    success: bool
    message: str
    version: Optional[str] = None
    cluster_name: Optional[str] = None
    node_count: Optional[int] = None
    error: Optional[str] = None


@router.get("/proxmox", response_model=ProxmoxConfigResponse)
async def get_proxmox_config(
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Proxmox-Konfiguration abrufen (nur Super-Admin).

    Gibt die aktuelle Proxmox-API-Konfiguration zurueck.
    Das Token Secret wird maskiert zurueckgegeben.
    """
    return ProxmoxConfigResponse(
        proxmox_host=app_settings.proxmox_host or "",
        proxmox_token_id=app_settings.proxmox_token_id or "",
        proxmox_token_secret="********" if app_settings.proxmox_token_secret else "",
        proxmox_verify_ssl=app_settings.proxmox_verify_ssl,
    )


@router.put("/proxmox", response_model=ProxmoxConfigResponse)
async def update_proxmox_config(
    config: ProxmoxConfigUpdate,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Proxmox-Konfiguration aktualisieren (nur Super-Admin).

    Speichert die Konfiguration in der .env Datei und fuehrt einen Hot-Reload durch.
    Die Aenderungen werden sofort wirksam - kein Container-Neustart erforderlich.
    """
    import logging
    logger = logging.getLogger(__name__)

    # .env Datei finden
    env_file = os.getenv("ENV_FILE", "/app/.env")

    # Falls .env nicht existiert aber Symlink-Ziel existiert, dort schreiben
    if not os.path.exists(env_file):
        config_env = "/data/config/.env"
        if os.path.exists(config_env):
            env_file = config_env

    # Existierende .env lesen
    env_content = {}
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_content[key.strip()] = value.strip()

    # Neue Werte setzen
    env_content["PROXMOX_HOST"] = config.proxmox_host
    env_content["PROXMOX_TOKEN_ID"] = config.proxmox_token_id
    env_content["PROXMOX_VERIFY_SSL"] = str(config.proxmox_verify_ssl).lower()

    # Token Secret nur aktualisieren wenn nicht maskiert
    if config.proxmox_token_secret and config.proxmox_token_secret != "********":
        env_content["PROXMOX_TOKEN_SECRET"] = config.proxmox_token_secret

    # .env schreiben
    with open(env_file, "w") as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")

    # Hot-Reload durchfuehren
    reload_settings(env_file)

    # Proxmox Service Cache invalidieren (falls vorhanden)
    try:
        proxmox_service = get_proxmox_service()
        if hasattr(proxmox_service, 'reload'):
            proxmox_service.reload()
    except Exception as e:
        logger.debug(f"Proxmox Service Reload: {e}")

    logger.info(f"Proxmox-Konfiguration aktualisiert: {config.proxmox_host}")

    return ProxmoxConfigResponse(
        proxmox_host=config.proxmox_host,
        proxmox_token_id=config.proxmox_token_id,
        proxmox_token_secret="********" if config.proxmox_token_secret else "",
        proxmox_verify_ssl=config.proxmox_verify_ssl,
    )


@router.post("/proxmox/test", response_model=ProxmoxTestResponse)
async def test_proxmox_connection(
    request: ProxmoxTestRequest,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Proxmox-Verbindung testen (nur Super-Admin).

    Testet die Verbindung mit den angegebenen Credentials.
    """
    import httpx

    try:
        # Host normalisieren
        host = request.host.strip()
        original_had_scheme = host.startswith("http")

        if not original_had_scheme:
            # Kein Schema angegeben -> direkter Zugriff, Port 8006 hinzufuegen
            if ":" not in host:  # Kein Port angegeben
                host = f"https://{host}:8006"
            else:
                host = f"https://{host}"
        # Wenn Schema angegeben (https://...) -> Reverse Proxy, keinen Port hinzufuegen

        # Token-Name extrahieren
        if "!" in request.token_id:
            user_part, token_name = request.token_id.rsplit("!", 1)
        else:
            return ProxmoxTestResponse(
                success=False,
                message="Ungueltige Token-ID",
                error="Token-ID muss das Format user@realm!token-name haben"
            )

        # API-Aufruf
        url = f"{host}/api2/json/version"
        headers = {
            "Authorization": f"PVEAPIToken={request.token_id}={request.token_secret}"
        }

        async with httpx.AsyncClient(verify=request.verify_ssl, timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json().get("data", {})

                # Cluster-Info abrufen
                cluster_name = None
                node_count = None
                try:
                    cluster_url = f"{host}/api2/json/cluster/status"
                    cluster_response = await client.get(cluster_url, headers=headers)
                    if cluster_response.status_code == 200:
                        cluster_data = cluster_response.json().get("data", [])
                        for item in cluster_data:
                            if item.get("type") == "cluster":
                                cluster_name = item.get("name")
                            if item.get("type") == "node":
                                node_count = (node_count or 0) + 1
                except:
                    pass

                return ProxmoxTestResponse(
                    success=True,
                    message="Verbindung erfolgreich",
                    version=data.get("version"),
                    cluster_name=cluster_name,
                    node_count=node_count,
                )
            elif response.status_code == 401:
                return ProxmoxTestResponse(
                    success=False,
                    message="Authentifizierung fehlgeschlagen",
                    error="Token-ID oder Secret ist ungueltig"
                )
            else:
                return ProxmoxTestResponse(
                    success=False,
                    message=f"HTTP-Fehler {response.status_code}",
                    error=response.text[:200]
                )

    except httpx.ConnectError as e:
        return ProxmoxTestResponse(
            success=False,
            message="Verbindung fehlgeschlagen",
            error=f"Host nicht erreichbar: {request.host}"
        )
    except httpx.TimeoutException:
        return ProxmoxTestResponse(
            success=False,
            message="Timeout",
            error="Server antwortet nicht innerhalb von 10 Sekunden"
        )
    except Exception as e:
        return ProxmoxTestResponse(
            success=False,
            message="Fehler",
            error=str(e)[:200]
        )


# ==================== NetBox Benutzer ====================

class NetBoxUserResponse(BaseModel):
    """Schema fuer NetBox Benutzer"""
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class NetBoxUserCreate(BaseModel):
    """Schema fuer neuen NetBox Benutzer"""
    username: str
    password: str
    email: Optional[str] = None
    is_superuser: bool = False
    is_active: bool = True


class NetBoxUserUpdate(BaseModel):
    """Schema fuer NetBox Benutzer Update"""
    email: Optional[str] = None
    is_superuser: Optional[bool] = None
    is_active: Optional[bool] = None


class NetBoxPasswordChange(BaseModel):
    """Schema fuer Passwort-Aenderung"""
    password: str


def run_netbox_command(python_script: str) -> dict:
    """
    Fuehrt ein Python-Script im NetBox-Container aus.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Pruefen ob Container laeuft
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=proxmox-commander-netbox", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )

        if "proxmox-commander-netbox" not in result.stdout:
            raise HTTPException(
                status_code=503,
                detail="NetBox-Container nicht aktiv"
            )

        # Script ausfuehren
        result = subprocess.run(
            ["docker", "exec", "proxmox-commander-netbox",
             "python", "/opt/netbox/netbox/manage.py", "shell", "-c", python_script],
            capture_output=True, text=True, timeout=30
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="NetBox-Container Timeout")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Docker nicht verfuegbar")
    except Exception as e:
        logger.error(f"NetBox Befehl fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/netbox-users", response_model=List[NetBoxUserResponse])
async def list_netbox_users(
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    NetBox-Benutzer auflisten (nur Super-Admin).
    """
    script = '''
import json
from django.contrib.auth import get_user_model
User = get_user_model()
users = []
for u in User.objects.all():
    users.append({
        "id": u.id,
        "username": u.username,
        "email": u.email or "",
        "is_active": u.is_active,
        "is_superuser": u.is_superuser
    })
print("JSON_START" + json.dumps(users) + "JSON_END")
'''

    result = run_netbox_command(script)

    if result["returncode"] != 0:
        raise HTTPException(
            status_code=500,
            detail=f"NetBox-Fehler: {result['stderr'][:200]}"
        )

    # JSON aus Output extrahieren
    output = result["stdout"]
    try:
        start = output.index("JSON_START") + len("JSON_START")
        end = output.index("JSON_END")
        json_str = output[start:end]
        users = json.loads(json_str)
        return [NetBoxUserResponse(**u) for u in users]
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Parsen der NetBox-Antwort: {str(e)}"
        )


import json


@router.post("/netbox-users", response_model=NetBoxUserResponse)
async def create_netbox_user(
    user_data: NetBoxUserCreate,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Neuen NetBox-Benutzer erstellen (nur Super-Admin).
    """
    # Escape fuer Python-String
    username = user_data.username.replace("'", "\\'")
    password = user_data.password.replace("'", "\\'")
    email = (user_data.email or "").replace("'", "\\'")

    script = f'''
import json
from django.contrib.auth import get_user_model
User = get_user_model()

# Pruefen ob Benutzer existiert
if User.objects.filter(username='{username}').exists():
    print("ERROR:Benutzer existiert bereits")
else:
    user = User.objects.create_user(
        username='{username}',
        password='{password}',
        email='{email}',
        is_superuser={str(user_data.is_superuser)},
        is_active={str(user_data.is_active)}
    )
    print("JSON_START" + json.dumps({{
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        "is_active": user.is_active,
        "is_superuser": user.is_superuser
    }}) + "JSON_END")
'''

    result = run_netbox_command(script)

    if "ERROR:" in result["stdout"]:
        error_msg = result["stdout"].split("ERROR:")[1].strip().split("\n")[0]
        raise HTTPException(status_code=400, detail=error_msg)

    if result["returncode"] != 0:
        raise HTTPException(
            status_code=500,
            detail=f"NetBox-Fehler: {result['stderr'][:200]}"
        )

    # JSON aus Output extrahieren
    output = result["stdout"]
    try:
        start = output.index("JSON_START") + len("JSON_START")
        end = output.index("JSON_END")
        json_str = output[start:end]
        return NetBoxUserResponse(**json.loads(json_str))
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Parsen der NetBox-Antwort: {str(e)}"
        )


@router.put("/netbox-users/{user_id}", response_model=NetBoxUserResponse)
async def update_netbox_user(
    user_id: int,
    user_data: NetBoxUserUpdate,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    NetBox-Benutzer aktualisieren (nur Super-Admin).
    """
    updates = []
    if user_data.email is not None:
        email = user_data.email.replace("'", "\\'")
        updates.append(f"user.email = '{email}'")
    if user_data.is_superuser is not None:
        updates.append(f"user.is_superuser = {str(user_data.is_superuser)}")
    if user_data.is_active is not None:
        updates.append(f"user.is_active = {str(user_data.is_active)}")

    if not updates:
        raise HTTPException(status_code=400, detail="Keine Aenderungen angegeben")

    updates_code = "\n    ".join(updates)

    script = f'''
import json
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    user = User.objects.get(id={user_id})
    {updates_code}
    user.save()
    print("JSON_START" + json.dumps({{
        "id": user.id,
        "username": user.username,
        "email": user.email or "",
        "is_active": user.is_active,
        "is_superuser": user.is_superuser
    }}) + "JSON_END")
except User.DoesNotExist:
    print("ERROR:Benutzer nicht gefunden")
'''

    result = run_netbox_command(script)

    if "ERROR:" in result["stdout"]:
        error_msg = result["stdout"].split("ERROR:")[1].strip().split("\n")[0]
        raise HTTPException(status_code=404, detail=error_msg)

    if result["returncode"] != 0:
        raise HTTPException(
            status_code=500,
            detail=f"NetBox-Fehler: {result['stderr'][:200]}"
        )

    output = result["stdout"]
    try:
        start = output.index("JSON_START") + len("JSON_START")
        end = output.index("JSON_END")
        json_str = output[start:end]
        return NetBoxUserResponse(**json.loads(json_str))
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler beim Parsen der NetBox-Antwort: {str(e)}"
        )


@router.put("/netbox-users/{user_id}/password")
async def change_netbox_password(
    user_id: int,
    password_data: NetBoxPasswordChange,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    NetBox-Benutzer Passwort aendern (nur Super-Admin).
    """
    password = password_data.password.replace("'", "\\'")

    script = f'''
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    user = User.objects.get(id={user_id})
    user.set_password('{password}')
    user.save()
    print("SUCCESS")
except User.DoesNotExist:
    print("ERROR:Benutzer nicht gefunden")
'''

    result = run_netbox_command(script)

    if "ERROR:" in result["stdout"]:
        error_msg = result["stdout"].split("ERROR:")[1].strip().split("\n")[0]
        raise HTTPException(status_code=404, detail=error_msg)

    if "SUCCESS" not in result["stdout"]:
        raise HTTPException(
            status_code=500,
            detail=f"NetBox-Fehler: {result['stderr'][:200]}"
        )

    return {"success": True, "message": "Passwort geaendert"}


@router.delete("/netbox-users/{user_id}")
async def delete_netbox_user(
    user_id: int,
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    NetBox-Benutzer loeschen (nur Super-Admin).

    Der letzte Superuser kann nicht geloescht werden.
    """
    script = f'''
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    user = User.objects.get(id={user_id})

    # Pruefen ob letzter Superuser
    if user.is_superuser:
        superuser_count = User.objects.filter(is_superuser=True).count()
        if superuser_count <= 1:
            print("ERROR:Letzter Superuser kann nicht geloescht werden")
        else:
            user.delete()
            print("SUCCESS")
    else:
        user.delete()
        print("SUCCESS")
except User.DoesNotExist:
    print("ERROR:Benutzer nicht gefunden")
'''

    result = run_netbox_command(script)

    if "ERROR:" in result["stdout"]:
        error_msg = result["stdout"].split("ERROR:")[1].strip().split("\n")[0]
        raise HTTPException(status_code=400, detail=error_msg)

    if "SUCCESS" not in result["stdout"]:
        raise HTTPException(
            status_code=500,
            detail=f"NetBox-Fehler: {result['stderr'][:200]}"
        )

    return {"success": True, "message": "Benutzer geloescht"}
