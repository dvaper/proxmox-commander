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
