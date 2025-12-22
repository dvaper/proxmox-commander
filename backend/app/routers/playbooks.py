"""
Playbooks Router - Playbook-Liste, Details und CRUD-Operationen

Berechtigungsfilterung:
- Super-Admins sehen alle Playbooks
- Reguläre User sehen nur zugewiesene Playbooks

Schreiboperationen (nur Super-Admin):
- Playbooks erstellen/aktualisieren/löschen
- Nur custom-* Playbooks können bearbeitet werden
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import List
import re

from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.playbook import (
    PlaybookInfo,
    PlaybookDetail,
    PlaybookCreate,
    PlaybookUpdate,
    PlaybookValidationRequest,
    PlaybookValidationResult,
    PlaybookParsedInfo,
    PlaybookTemplate,
    PlaybookHistoryEntry,
    PlaybookOperationResponse,
)
from app.services.playbook_scanner import PlaybookScanner
from app.services.playbook_editor import get_playbook_editor, PlaybookEditor, CUSTOM_PREFIX
from app.services.permission_service import get_permission_service
from app.config import settings

router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])

# Scanner als Singleton
_scanner = None


def get_scanner() -> PlaybookScanner:
    """Gibt den Playbook-Scanner zurück"""
    global _scanner
    if _scanner is None:
        _scanner = PlaybookScanner(settings.ansible_playbook_dir)
    return _scanner


def get_editor() -> PlaybookEditor:
    """Gibt den Playbook-Editor zurück"""
    return get_playbook_editor(settings.ansible_playbook_dir)


def require_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency: Nur Super-Admin erlaubt"""
    perm_service = get_permission_service(current_user)
    if not perm_service.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="Nur Super-Admins können Playbooks bearbeiten"
        )
    return current_user


# =============================================================================
# Lese-Operationen (alle authentifizierten User)
# =============================================================================

@router.get("", response_model=List[PlaybookInfo])
async def get_playbooks(
    current_user: User = Depends(get_current_active_user),
    scanner: PlaybookScanner = Depends(get_scanner),
    editor: PlaybookEditor = Depends(get_editor),
):
    """
    Alle verfügbaren Playbooks.

    Gefiltert nach Berechtigungen:
    - Super-Admin: Alle Playbooks
    - Regulärer User: Nur zugewiesene Playbooks

    Enthält is_system Flag für Schreibschutz-Anzeige.
    """
    perm_service = get_permission_service(current_user)
    all_playbooks = scanner.get_playbooks()

    # is_system Flag hinzufügen
    for playbook in all_playbooks:
        playbook.is_system = editor.is_system_playbook(playbook.name)

    # Super-Admin sieht alles
    if perm_service.is_super_admin:
        return all_playbooks

    # Nur zugängliche Playbooks
    accessible_playbooks = perm_service.get_accessible_playbooks()
    return [
        playbook for playbook in all_playbooks
        if playbook.name in accessible_playbooks
    ]


@router.get("/templates", response_model=List[PlaybookTemplate])
async def get_templates(
    current_user: User = Depends(get_current_active_user),
    editor: PlaybookEditor = Depends(get_editor),
):
    """
    Verfügbare Playbook-Vorlagen.

    Gibt Basis-Templates für schnellen Einstieg zurück.
    """
    return [PlaybookTemplate(**t) for t in editor.get_templates()]


@router.get("/{playbook_name}", response_model=PlaybookDetail)
async def get_playbook(
    playbook_name: str,
    current_user: User = Depends(get_current_active_user),
    scanner: PlaybookScanner = Depends(get_scanner),
    editor: PlaybookEditor = Depends(get_editor),
):
    """Playbook-Details inkl. Content (mit Berechtigungsprüfung)"""
    perm_service = get_permission_service(current_user)
    playbook = scanner.get_playbook_detail(playbook_name)

    if not playbook:
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_name}' nicht gefunden")

    # is_system Flag hinzufügen
    playbook.is_system = editor.is_system_playbook(playbook_name)

    # Berechtigungsprüfung (wenn nicht Super-Admin)
    if not perm_service.is_super_admin:
        if not perm_service.can_access_playbook(playbook_name):
            raise HTTPException(status_code=403, detail="Keine Berechtigung für dieses Playbook")

    return playbook


@router.post("/reload")
async def reload_playbooks(
    current_user: User = Depends(get_current_active_user),
    scanner: PlaybookScanner = Depends(get_scanner),
):
    """Playbooks neu scannen"""
    scanner.reload()
    return {"message": "Playbooks neu gescannt", "count": len(scanner.get_playbooks())}


# =============================================================================
# Validierung (alle authentifizierten User)
# =============================================================================

@router.post("/validate", response_model=PlaybookValidationResult)
async def validate_playbook(
    data: PlaybookValidationRequest,
    current_user: User = Depends(get_current_active_user),
    editor: PlaybookEditor = Depends(get_editor),
):
    """
    Validiert Playbook-Inhalt ohne zu speichern.

    Führt YAML- und Ansible-Validierung durch.
    Gibt detaillierte Fehlermeldungen mit Zeilennummern zurück.
    """
    result = editor.validate_full(data.content)

    # parsed_info in Schema konvertieren
    parsed_info = None
    if result.get("parsed_info"):
        parsed_info = PlaybookParsedInfo(**result["parsed_info"])

    return PlaybookValidationResult(
        valid=result["valid"],
        yaml_valid=result["yaml_valid"],
        yaml_error=result["yaml_error"],
        ansible_valid=result["ansible_valid"],
        ansible_error=result["ansible_error"],
        warnings=result["warnings"],
        parsed_info=parsed_info,
    )


# =============================================================================
# Schreib-Operationen (nur Super-Admin)
# =============================================================================

@router.post("", response_model=PlaybookOperationResponse)
async def create_playbook(
    data: PlaybookCreate,
    current_user: User = Depends(require_super_admin),
    editor: PlaybookEditor = Depends(get_editor),
    scanner: PlaybookScanner = Depends(get_scanner),
):
    """
    Neues Playbook erstellen (nur Super-Admin).

    - Name muss mit 'custom-' beginnen
    - YAML- und Ansible-Validierung vor Speicherung
    - Git-Commit für Versionierung
    """
    # Name validieren
    name = data.name.lower().strip()

    if not name.startswith(CUSTOM_PREFIX):
        raise HTTPException(
            status_code=400,
            detail=f"Playbook-Name muss mit '{CUSTOM_PREFIX}' beginnen"
        )

    if not re.match(r'^[a-z0-9_-]+$', name):
        raise HTTPException(
            status_code=400,
            detail="Name darf nur Kleinbuchstaben, Zahlen, _ und - enthalten"
        )

    # Playbook erstellen
    success, message = editor.create_playbook(
        name=name,
        content=data.content,
        username=current_user.username
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Scanner neu laden
    scanner.reload()

    # Details abrufen
    playbook = scanner.get_playbook_detail(name)
    if playbook:
        playbook.is_system = False

    return PlaybookOperationResponse(
        success=True,
        message=message,
        playbook=playbook
    )


@router.put("/{playbook_name}", response_model=PlaybookOperationResponse)
async def update_playbook(
    playbook_name: str,
    data: PlaybookUpdate,
    current_user: User = Depends(require_super_admin),
    editor: PlaybookEditor = Depends(get_editor),
    scanner: PlaybookScanner = Depends(get_scanner),
):
    """
    Playbook aktualisieren (nur Super-Admin).

    - System-Playbooks sind schreibgeschützt
    - YAML- und Ansible-Validierung vor Speicherung
    - Git-Commit für Versionierung
    """
    # System-Playbook-Schutz
    if editor.is_system_playbook(playbook_name):
        raise HTTPException(
            status_code=400,
            detail=f"System-Playbook '{playbook_name}' kann nicht bearbeitet werden"
        )

    # Playbook aktualisieren
    success, message = editor.update_playbook(
        name=playbook_name,
        content=data.content,
        username=current_user.username
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Scanner neu laden
    scanner.reload()

    # Details abrufen
    playbook = scanner.get_playbook_detail(playbook_name)
    if playbook:
        playbook.is_system = False

    return PlaybookOperationResponse(
        success=True,
        message=message,
        playbook=playbook
    )


@router.delete("/{playbook_name}")
async def delete_playbook(
    playbook_name: str,
    current_user: User = Depends(require_super_admin),
    editor: PlaybookEditor = Depends(get_editor),
    scanner: PlaybookScanner = Depends(get_scanner),
):
    """
    Playbook löschen (nur Super-Admin).

    - System-Playbooks können nicht gelöscht werden
    - Git-Commit für Versionierung
    """
    # System-Playbook-Schutz
    if editor.is_system_playbook(playbook_name):
        raise HTTPException(
            status_code=400,
            detail=f"System-Playbook '{playbook_name}' kann nicht gelöscht werden"
        )

    # Playbook löschen
    success, message = editor.delete_playbook(
        name=playbook_name,
        username=current_user.username
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Scanner neu laden
    scanner.reload()

    return {"success": True, "message": message}


# =============================================================================
# Git-Historie (nur Super-Admin)
# =============================================================================

@router.get("/{playbook_name}/history", response_model=List[PlaybookHistoryEntry])
async def get_playbook_history(
    playbook_name: str,
    limit: int = 20,
    current_user: User = Depends(require_super_admin),
    editor: PlaybookEditor = Depends(get_editor),
):
    """
    Git-Historie eines Playbooks (nur Super-Admin).

    Gibt die letzten Commits zurück die dieses Playbook betreffen.
    """
    if not editor.playbook_exists(playbook_name):
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_name}' nicht gefunden")

    history = editor.get_history(playbook_name, limit=limit)
    return [PlaybookHistoryEntry(**entry) for entry in history]


@router.post("/{playbook_name}/restore/{commit_hash}")
async def restore_playbook_version(
    playbook_name: str,
    commit_hash: str,
    current_user: User = Depends(require_super_admin),
    editor: PlaybookEditor = Depends(get_editor),
    scanner: PlaybookScanner = Depends(get_scanner),
):
    """
    Playbook auf eine frühere Version zurücksetzen (nur Super-Admin).

    - System-Playbooks sind schreibgeschützt
    - Erstellt neuen Commit mit wiederhergestellter Version
    """
    # System-Playbook-Schutz
    if editor.is_system_playbook(playbook_name):
        raise HTTPException(
            status_code=400,
            detail=f"System-Playbook '{playbook_name}' kann nicht bearbeitet werden"
        )

    # Version wiederherstellen
    success, message = editor.restore_version(
        name=playbook_name,
        commit_hash=commit_hash,
        username=current_user.username
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # Scanner neu laden
    scanner.reload()

    return {"success": True, "message": message}
