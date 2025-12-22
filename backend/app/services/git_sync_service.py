"""
Git Sync Service - Synchronisiert das Homelab-Repository

Funktionen:
- Git pull beim App-Start
- Manueller Sync via API
- Status-Abfrage (letzter Sync, Branch, etc.)
"""
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class GitSyncService:
    """Service für Git-Repository-Synchronisation"""

    def __init__(self):
        # Repository-Pfad: /repo im Container (gemountet von Host)
        # Fallback auf Parent von terraform_dir für lokale Entwicklung
        container_repo_path = Path("/repo")
        if container_repo_path.exists() and (container_repo_path / ".git").exists():
            self.repo_path = container_repo_path
        else:
            # Lokale Entwicklung: Parent von ansible/ (also homelab/)
            self.repo_path = Path(settings.terraform_dir).parent

        self.last_sync: Optional[datetime] = None
        self.last_sync_result: Optional[dict] = None

    def _run_git_command(self, *args: str, cwd: Optional[Path] = None) -> dict:
        """
        Führt einen Git-Befehl aus.

        Returns:
            dict mit success, output, error
        """
        work_dir = cwd or self.repo_path

        try:
            result = subprocess.run(
                ["git", *args],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.returncode != 0 else None,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Git-Befehl Timeout (60s)",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "",
                "error": "Git nicht installiert",
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }

    async def sync(self, fetch_only: bool = False) -> dict:
        """
        Synchronisiert das Repository.

        Args:
            fetch_only: Nur fetch, kein pull (für Status-Check)

        Returns:
            dict mit Sync-Ergebnis
        """
        result = {
            "success": False,
            "message": "",
            "branch": None,
            "commits_behind": 0,
            "commits_ahead": 0,
            "changed_files": [],
            "timestamp": datetime.now().isoformat(),
        }

        # Prüfen ob Repo existiert
        if not (self.repo_path / ".git").exists():
            result["error"] = f"Kein Git-Repository unter {self.repo_path}"
            return result

        # Aktuellen Branch ermitteln
        branch_result = self._run_git_command("branch", "--show-current")
        if branch_result["success"]:
            result["branch"] = branch_result["output"]

        # Fetch (immer)
        fetch_result = self._run_git_command("fetch", "--all")
        if not fetch_result["success"]:
            result["error"] = f"Fetch fehlgeschlagen: {fetch_result['error']}"
            return result

        # Status prüfen (ahead/behind)
        status_result = self._run_git_command("status", "-sb")
        if status_result["success"]:
            status_line = status_result["output"].split("\n")[0]
            # Parse "## main...origin/main [behind 3]" oder "[ahead 2, behind 1]"
            if "[behind " in status_line:
                try:
                    behind_part = status_line.split("[behind ")[1].split("]")[0].split(",")[0]
                    result["commits_behind"] = int(behind_part)
                except (IndexError, ValueError):
                    pass
            if "[ahead " in status_line:
                try:
                    ahead_part = status_line.split("[ahead ")[1].split("]")[0].split(",")[0]
                    result["commits_ahead"] = int(ahead_part)
                except (IndexError, ValueError):
                    pass

        if fetch_only:
            result["success"] = True
            result["message"] = "Fetch erfolgreich"
            return result

        # Lokale Änderungen prüfen
        diff_result = self._run_git_command("status", "--porcelain")
        if diff_result["success"] and diff_result["output"]:
            # Es gibt lokale Änderungen
            local_changes = diff_result["output"].split("\n")
            result["local_changes"] = local_changes
            result["warning"] = f"{len(local_changes)} lokale Änderungen vorhanden"

        # Pull ausführen
        pull_result = self._run_git_command("pull", "--ff-only")

        if pull_result["success"]:
            result["success"] = True
            if "Already up to date" in pull_result["output"]:
                result["message"] = "Bereits aktuell"
            else:
                # Geänderte Dateien aus Pull-Output extrahieren
                result["message"] = "Sync erfolgreich"
                result["pull_output"] = pull_result["output"]

                # Anzahl geänderter Dateien ermitteln
                if "files changed" in pull_result["output"]:
                    result["message"] = pull_result["output"].split("\n")[-1]
        else:
            result["error"] = pull_result["error"] or "Pull fehlgeschlagen"

            # Bei Merge-Konflikten hilfreiche Meldung
            if "CONFLICT" in (pull_result["error"] or ""):
                result["error"] = "Merge-Konflikt - manuelle Auflösung erforderlich"
            elif "would be overwritten" in (pull_result["error"] or ""):
                result["error"] = "Lokale Änderungen würden überschrieben - erst committen oder stashen"

        self.last_sync = datetime.now()
        self.last_sync_result = result

        return result

    async def get_status(self) -> dict:
        """
        Gibt den aktuellen Repository-Status zurück.

        Returns:
            dict mit Status-Informationen
        """
        status = {
            "repo_path": str(self.repo_path),
            "repo_exists": (self.repo_path / ".git").exists(),
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_sync_result": self.last_sync_result,
            "branch": None,
            "remote_url": None,
            "last_commit": None,
            "local_changes": 0,
            "commits_behind": 0,
            "commits_ahead": 0,
        }

        if not status["repo_exists"]:
            return status

        # Branch
        branch_result = self._run_git_command("branch", "--show-current")
        if branch_result["success"]:
            status["branch"] = branch_result["output"]

        # Remote URL
        remote_result = self._run_git_command("remote", "get-url", "origin")
        if remote_result["success"]:
            status["remote_url"] = remote_result["output"]

        # Letzter Commit
        log_result = self._run_git_command(
            "log", "-1", "--format=%H|%s|%ai|%an"
        )
        if log_result["success"] and log_result["output"]:
            parts = log_result["output"].split("|")
            if len(parts) >= 4:
                status["last_commit"] = {
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "date": parts[2],
                    "author": parts[3],
                }

        # Lokale Änderungen
        porcelain_result = self._run_git_command("status", "--porcelain")
        if porcelain_result["success"]:
            changes = [l for l in porcelain_result["output"].split("\n") if l.strip()]
            status["local_changes"] = len(changes)

        # Fetch für ahead/behind (ohne pull)
        await self.sync(fetch_only=True)
        if self.last_sync_result:
            status["commits_behind"] = self.last_sync_result.get("commits_behind", 0)
            status["commits_ahead"] = self.last_sync_result.get("commits_ahead", 0)

        return status

    async def get_recent_commits(self, limit: int = 10) -> list:
        """
        Gibt die letzten Commits zurück.

        Args:
            limit: Anzahl der Commits

        Returns:
            Liste von Commit-Informationen
        """
        log_result = self._run_git_command(
            "log", f"-{limit}", "--format=%H|%s|%ai|%an"
        )

        if not log_result["success"]:
            return []

        commits = []
        for line in log_result["output"].split("\n"):
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:8],
                    "full_hash": parts[0],
                    "message": parts[1],
                    "date": parts[2],
                    "author": parts[3],
                })

        return commits


# Singleton-Instanz
_git_sync_service: Optional[GitSyncService] = None


def get_git_sync_service() -> GitSyncService:
    """Gibt die Singleton-Instanz des Git-Sync-Service zurück"""
    global _git_sync_service
    if _git_sync_service is None:
        _git_sync_service = GitSyncService()
    return _git_sync_service
