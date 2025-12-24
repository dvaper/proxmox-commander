"""
Password Reset Router - API-Endpunkte fuer Passwort-Zuruecksetzung
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.notification import (
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetValidate,
)
from app.services.notification_service import NotificationService
from app.services.password_reset_service import PasswordResetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Rate-Limiting (einfache In-Memory-Implementation)
# In Produktion sollte Redis oder aehnliches verwendet werden
_rate_limit_cache = {}


def _check_rate_limit(ip: str, limit: int = 3, window_seconds: int = 60) -> bool:
    """
    Prueft Rate-Limit fuer eine IP-Adresse.

    Args:
        ip: IP-Adresse
        limit: Max Anfragen pro Zeitfenster
        window_seconds: Zeitfenster in Sekunden

    Returns:
        True wenn Limit nicht erreicht, False wenn blockiert
    """
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    key = f"pwd_reset:{ip}"

    if key not in _rate_limit_cache:
        _rate_limit_cache[key] = []

    # Alte Eintraege entfernen
    cutoff = now - timedelta(seconds=window_seconds)
    _rate_limit_cache[key] = [t for t in _rate_limit_cache[key] if t > cutoff]

    # Pruefen
    if len(_rate_limit_cache[key]) >= limit:
        return False

    # Neuen Eintrag hinzufuegen
    _rate_limit_cache[key].append(now)
    return True


@router.post("/forgot-password")
async def forgot_password(
    data: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Passwort-Reset anfordern.

    Sendet eine E-Mail mit einem Reset-Link, falls die E-Mail existiert.
    Aus Sicherheitsgruenden wird immer eine Erfolgsmeldung zurueckgegeben.
    """
    # Rate-Limiting
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        logger.warning(f"Rate-Limit erreicht fuer Passwort-Reset von {client_ip}")
        raise HTTPException(
            429,
            "Zu viele Anfragen. Bitte versuchen Sie es in einer Minute erneut."
        )

    # Service erstellen
    notification_service = NotificationService(db)
    password_reset_service = PasswordResetService(db, notification_service)

    # Reset anfordern
    await password_reset_service.request_reset(data.email)

    # Immer Erfolg zurueckmelden (Sicherheit)
    return {
        "message": "Falls die E-Mail-Adresse existiert, wurde ein Reset-Link gesendet."
    }


@router.get("/validate-reset-token", response_model=PasswordResetValidate)
async def validate_reset_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Prueft ob ein Reset-Token gueltig ist.

    Wird vom Frontend verwendet, um zu pruefen ob der Token noch gueltig ist,
    bevor das Passwort-Formular angezeigt wird.
    """
    notification_service = NotificationService(db)
    password_reset_service = PasswordResetService(db, notification_service)

    validation = await password_reset_service.validate_token(token)

    if validation:
        return PasswordResetValidate(
            valid=True,
            expires_at=validation['expires_at']
        )
    else:
        return PasswordResetValidate(valid=False)


@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Passwort mit Token zuruecksetzen.

    Setzt das Passwort zurueck, wenn der Token gueltig ist.
    """
    notification_service = NotificationService(db)
    password_reset_service = PasswordResetService(db, notification_service)

    success = await password_reset_service.reset_password(
        token=data.token,
        new_password=data.new_password
    )

    if not success:
        raise HTTPException(
            400,
            "Ungueltiger oder abgelaufener Token. Bitte fordern Sie einen neuen Reset-Link an."
        )

    return {"message": "Passwort erfolgreich geaendert. Sie koennen sich jetzt einloggen."}
