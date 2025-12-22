"""
Users Router - Benutzerverwaltung (nur Super-Admin)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.user_group_access import UserGroupAccess
from app.models.user_playbook_access import UserPlaybookAccess
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserResponseWithAccess,
    UserListResponse,
    UserGroupAccessCreate,
    UserGroupAccessRead,
    UserPlaybookAccessCreate,
    UserPlaybookAccessRead,
    PasswordResetRequest,
)
from app.auth.security import get_password_hash
from app.auth.dependencies import get_current_super_admin_user
from app.services.settings_service import get_settings_service

router = APIRouter(prefix="/api/users", tags=["users"])


# ==================== User CRUD ====================

@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Liste aller Benutzer (nur Super-Admin).

    - Pagination über skip/limit
    - Optional: Suche nach Username
    """
    query = select(User).options(
        selectinload(User.group_access),
        selectinload(User.playbook_access),
    )

    # Suche
    if search:
        query = query.where(User.username.ilike(f"%{search}%"))

    # Sortierung
    query = query.order_by(User.username)

    # Total count
    count_query = select(func.count()).select_from(User)
    if search:
        count_query = count_query.where(User.username.ilike(f"%{search}%"))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Pagination
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    users = list(result.scalars().all())

    return UserListResponse(items=users, total=total)


@router.get("/{user_id}", response_model=UserResponseWithAccess)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Benutzer-Details abrufen (nur Super-Admin)"""
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.group_access),
            selectinload(User.playbook_access),
        )
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    return UserResponseWithAccess(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        group_access=user.group_access,
        playbook_access=user.playbook_access,
        accessible_groups=[g.group_name for g in user.group_access],
        accessible_playbooks=[p.playbook_name for p in user.playbook_access],
    )


@router.post("", response_model=UserResponseWithAccess, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """
    Neuen Benutzer erstellen (nur Super-Admin).

    Wendet automatisch Default-Gruppen und -Playbooks an.
    """
    # Prüfen ob Username existiert
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benutzername existiert bereits",
        )

    # User erstellen
    user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        email=user_data.email,
        is_admin=user_data.is_super_admin,  # Legacy-Kompatibilität
        is_super_admin=user_data.is_super_admin,
        is_active=True,
    )

    db.add(user)
    await db.flush()  # ID generieren

    # Default-Zugriffe anwenden (nur für Nicht-Super-Admins)
    if not user_data.is_super_admin:
        settings_service = get_settings_service(db)
        default_groups = await settings_service.get_default_groups()
        default_playbooks = await settings_service.get_default_playbooks()

        for group_name in default_groups:
            access = UserGroupAccess(user_id=user.id, group_name=group_name)
            db.add(access)

        for playbook_name in default_playbooks:
            access = UserPlaybookAccess(user_id=user.id, playbook_name=playbook_name)
            db.add(access)

    await db.commit()

    # Refresh mit Relationships
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.group_access),
            selectinload(User.playbook_access),
        )
        .where(User.id == user.id)
    )
    user = result.scalar_one()

    return UserResponseWithAccess(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        group_access=user.group_access,
        playbook_access=user.playbook_access,
        accessible_groups=[g.group_name for g in user.group_access],
        accessible_playbooks=[p.playbook_name for p in user.playbook_access],
    )


@router.put("/{user_id}", response_model=UserResponseWithAccess)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Benutzer aktualisieren (nur Super-Admin)"""
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.group_access),
            selectinload(User.playbook_access),
        )
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Kann nicht den letzten Super-Admin deaktivieren
    if user_data.is_active is False and user.is_super_admin:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.is_super_admin == True,
                User.is_active == True,
                User.id != user_id,
            )
        )
        if count_result.scalar() == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kann den letzten aktiven Super-Admin nicht deaktivieren",
            )

    # Felder aktualisieren
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.is_super_admin is not None:
        user.is_super_admin = user_data.is_super_admin
        user.is_admin = user_data.is_super_admin  # Legacy
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponseWithAccess(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login,
        group_access=user.group_access,
        playbook_access=user.playbook_access,
        accessible_groups=[g.group_name for g in user.group_access],
        accessible_playbooks=[p.playbook_name for p in user.playbook_access],
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Benutzer löschen (nur Super-Admin)"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Kann sich nicht selbst löschen
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kann sich nicht selbst löschen",
        )

    # Kann nicht den letzten Super-Admin löschen
    if user.is_super_admin:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(
                User.is_super_admin == True,
                User.id != user_id,
            )
        )
        if count_result.scalar() == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kann den letzten Super-Admin nicht löschen",
            )

    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    password_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Passwort eines Benutzers zurücksetzen (nur Super-Admin)"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Passwort erfolgreich zurückgesetzt"}


# ==================== Group Access ====================

@router.get("/{user_id}/groups", response_model=List[UserGroupAccessRead])
async def get_user_groups(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Gruppen-Zuordnungen eines Benutzers abrufen"""
    result = await db.execute(
        select(UserGroupAccess).where(UserGroupAccess.user_id == user_id)
    )
    return list(result.scalars().all())


@router.post("/{user_id}/groups", response_model=UserGroupAccessRead, status_code=status.HTTP_201_CREATED)
async def add_user_group(
    user_id: int,
    access_data: UserGroupAccessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Gruppen-Zuordnung hinzufügen"""
    # Prüfen ob User existiert
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Prüfen ob Zuordnung existiert
    result = await db.execute(
        select(UserGroupAccess).where(
            UserGroupAccess.user_id == user_id,
            UserGroupAccess.group_name == access_data.group_name,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gruppen-Zuordnung existiert bereits",
        )

    access = UserGroupAccess(
        user_id=user_id,
        group_name=access_data.group_name,
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)

    return access


@router.delete("/{user_id}/groups/{group_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_group(
    user_id: int,
    group_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Gruppen-Zuordnung entfernen"""
    result = await db.execute(
        select(UserGroupAccess).where(
            UserGroupAccess.user_id == user_id,
            UserGroupAccess.group_name == group_name,
        )
    )
    access = result.scalar_one_or_none()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gruppen-Zuordnung nicht gefunden",
        )

    await db.delete(access)
    await db.commit()


@router.put("/{user_id}/groups", response_model=List[UserGroupAccessRead])
async def set_user_groups(
    user_id: int,
    group_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Alle Gruppen-Zuordnungen setzen (ersetzt bestehende)"""
    # Prüfen ob User existiert
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Bestehende löschen
    result = await db.execute(
        select(UserGroupAccess).where(UserGroupAccess.user_id == user_id)
    )
    for access in result.scalars().all():
        await db.delete(access)

    # Neue hinzufügen
    new_accesses = []
    for group_name in group_names:
        access = UserGroupAccess(user_id=user_id, group_name=group_name)
        db.add(access)
        new_accesses.append(access)

    await db.commit()

    # Refresh
    for access in new_accesses:
        await db.refresh(access)

    return new_accesses


# ==================== Playbook Access ====================

@router.get("/{user_id}/playbooks", response_model=List[UserPlaybookAccessRead])
async def get_user_playbooks(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Playbook-Zuordnungen eines Benutzers abrufen"""
    result = await db.execute(
        select(UserPlaybookAccess).where(UserPlaybookAccess.user_id == user_id)
    )
    return list(result.scalars().all())


@router.post("/{user_id}/playbooks", response_model=UserPlaybookAccessRead, status_code=status.HTTP_201_CREATED)
async def add_user_playbook(
    user_id: int,
    access_data: UserPlaybookAccessCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Playbook-Zuordnung hinzufügen"""
    # Prüfen ob User existiert
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Prüfen ob Zuordnung existiert
    result = await db.execute(
        select(UserPlaybookAccess).where(
            UserPlaybookAccess.user_id == user_id,
            UserPlaybookAccess.playbook_name == access_data.playbook_name,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playbook-Zuordnung existiert bereits",
        )

    access = UserPlaybookAccess(
        user_id=user_id,
        playbook_name=access_data.playbook_name,
    )
    db.add(access)
    await db.commit()
    await db.refresh(access)

    return access


@router.delete("/{user_id}/playbooks/{playbook_name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_playbook(
    user_id: int,
    playbook_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Playbook-Zuordnung entfernen"""
    result = await db.execute(
        select(UserPlaybookAccess).where(
            UserPlaybookAccess.user_id == user_id,
            UserPlaybookAccess.playbook_name == playbook_name,
        )
    )
    access = result.scalar_one_or_none()

    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook-Zuordnung nicht gefunden",
        )

    await db.delete(access)
    await db.commit()


@router.put("/{user_id}/playbooks", response_model=List[UserPlaybookAccessRead])
async def set_user_playbooks(
    user_id: int,
    playbook_names: List[str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_super_admin_user),
):
    """Alle Playbook-Zuordnungen setzen (ersetzt bestehende)"""
    # Prüfen ob User existiert
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benutzer nicht gefunden",
        )

    # Bestehende löschen
    result = await db.execute(
        select(UserPlaybookAccess).where(UserPlaybookAccess.user_id == user_id)
    )
    for access in result.scalars().all():
        await db.delete(access)

    # Neue hinzufügen
    new_accesses = []
    for playbook_name in playbook_names:
        access = UserPlaybookAccess(user_id=user_id, playbook_name=playbook_name)
        db.add(access)
        new_accesses.append(access)

    await db.commit()

    # Refresh
    for access in new_accesses:
        await db.refresh(access)

    return new_accesses
