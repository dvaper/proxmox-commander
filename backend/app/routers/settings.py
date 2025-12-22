"""
Settings Router - App-Einstellungen (nur Super-Admin)
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
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
