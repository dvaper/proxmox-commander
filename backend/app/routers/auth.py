"""
Auth Router - Login, Profil, Passwort-Änderung
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserResponseWithAccess,
    Token,
    PasswordChangeRequest,
    UserAccessSummary,
)
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.dependencies import get_current_user, get_current_active_user
from app.services.permission_service import get_permission_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login und JWT Token erhalten"""
    # User suchen
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falscher Benutzername oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Prüfen ob User aktiv ist
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Benutzer ist deaktiviert",
        )

    # Last Login aktualisieren
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponseWithAccess)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Aktuellen User mit Berechtigungen abrufen.

    Gibt alle Details inkl. zugewiesener Gruppen und Playbooks zurück.
    """
    return UserResponseWithAccess(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
        is_super_admin=current_user.is_super_admin,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        group_access=current_user.group_access,
        playbook_access=current_user.playbook_access,
        accessible_groups=[g.group_name for g in current_user.group_access],
        accessible_playbooks=[p.playbook_name for p in current_user.playbook_access],
    )


@router.get("/me/access", response_model=UserAccessSummary)
async def get_my_access(current_user: User = Depends(get_current_active_user)):
    """
    Berechtigungsübersicht für den aktuellen User.

    Gibt eine Zusammenfassung zurück, was der User sehen/tun darf.
    """
    perm_service = get_permission_service(current_user)
    summary = perm_service.get_access_summary()

    return UserAccessSummary(
        is_super_admin=summary["is_super_admin"],
        is_active=summary["is_active"],
        accessible_groups=summary["accessible_groups"],
        accessible_playbooks=summary["accessible_playbooks"],
        can_manage_users=summary["can_manage_users"],
    )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Eigenes Passwort ändern.

    Erfordert das aktuelle Passwort zur Bestätigung.
    """
    # Aktuelles Passwort verifizieren
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aktuelles Passwort ist falsch",
        )

    # Neues Passwort setzen
    current_user.password_hash = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "Passwort erfolgreich geändert"}


@router.post("/init", response_model=UserResponse)
async def init_admin(
    db: AsyncSession = Depends(get_db),
):
    """
    Initialen Admin-User erstellen.
    Nur möglich wenn noch kein User existiert.
    """
    # Prüfen ob User existieren
    result = await db.execute(select(User))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin-User existiert bereits. Verwende /api/auth/login",
        )

    # Initialen Super-Admin erstellen
    admin = User(
        username="admin",
        password_hash=get_password_hash("admin"),
        email="admin@local",
        is_admin=True,  # Legacy
        is_super_admin=True,
        is_active=True,
    )

    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    return admin
