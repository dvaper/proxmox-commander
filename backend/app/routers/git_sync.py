"""
Git Sync Router - API Endpoints für Repository-Synchronisation

Endpoints für:
- Repository-Status abfragen
- Manuellen Sync auslösen
- Commit-Historie anzeigen
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.auth.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.services.git_sync_service import get_git_sync_service

router = APIRouter(prefix="/api/git", tags=["git"])


# =============================================================================
# Schemas
# =============================================================================

class GitCommit(BaseModel):
    """Schema für Git-Commit"""
    hash: str
    full_hash: Optional[str] = None
    message: str
    date: str
    author: str


class GitStatus(BaseModel):
    """Schema für Git-Repository-Status"""
    repo_path: str
    repo_exists: bool
    last_sync: Optional[str] = None
    branch: Optional[str] = None
    remote_url: Optional[str] = None
    last_commit: Optional[GitCommit] = None
    local_changes: int = 0
    commits_behind: int = 0
    commits_ahead: int = 0


class GitSyncResult(BaseModel):
    """Schema für Sync-Ergebnis"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    warning: Optional[str] = None
    branch: Optional[str] = None
    commits_behind: int = 0
    commits_ahead: int = 0
    pull_output: Optional[str] = None
    timestamp: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/status", response_model=GitStatus)
async def get_git_status(
    current_user: User = Depends(get_current_active_user),
):
    """
    Gibt den aktuellen Status des Git-Repositories zurück.

    Enthält Informationen über:
    - Aktueller Branch
    - Letzter Commit
    - Lokale Änderungen
    - Commits hinter/vor Remote
    """
    service = get_git_sync_service()
    status = await service.get_status()

    # last_commit als GitCommit-Objekt konvertieren falls vorhanden
    if status.get("last_commit"):
        status["last_commit"] = GitCommit(**status["last_commit"])

    return GitStatus(**status)


@router.post("/sync", response_model=GitSyncResult)
async def sync_repository(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Synchronisiert das Repository (git pull).

    Nur für Admins verfügbar.
    Bei Konflikten wird ein Fehler zurückgegeben.
    """
    service = get_git_sync_service()
    result = await service.sync()
    return GitSyncResult(**result)


@router.post("/fetch", response_model=GitSyncResult)
async def fetch_repository(
    current_user: User = Depends(get_current_active_user),
):
    """
    Holt Änderungen vom Remote (git fetch), ohne zu mergen.

    Nützlich um zu prüfen, ob Updates verfügbar sind.
    """
    service = get_git_sync_service()
    result = await service.sync(fetch_only=True)
    return GitSyncResult(**result)


@router.get("/commits", response_model=List[GitCommit])
async def get_recent_commits(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
):
    """
    Gibt die letzten Commits zurück.

    Args:
        limit: Anzahl der Commits (max 50)
    """
    if limit > 50:
        limit = 50

    service = get_git_sync_service()
    commits = await service.get_recent_commits(limit)
    return [GitCommit(**c) for c in commits]
