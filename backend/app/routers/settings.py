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
