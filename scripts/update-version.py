#!/usr/bin/env python3
"""
Automatische Versionierung und Changelog-Generierung

Dieses Script:
1. Liest die Version aus dem Git-Tag
2. Generiert Changelog-Eintraege aus Commits seit dem letzten Tag
3. Aktualisiert package.json, main.py und changelog.json

Verwendung:
    python scripts/update-version.py v0.2.7

Commit-Konventionen (Conventional Commits):
    feat: Neue Features -> "Features"
    fix: Bugfixes -> "Bugfixes"
    docs: Dokumentation -> "Dokumentation"
    style: Styling -> "Styling"
    refactor: Refactoring -> "Refactoring"
    perf: Performance -> "Performance"
    test: Tests -> "Tests"
    security/sec: Sicherheit -> "Sicherheit"
    ux: UX-Verbesserungen -> "UX"

    Folgende Prefixe werden NICHT ins Changelog aufgenommen:
    chore: Wartungsarbeiten (Repo-Setup, Konfiguration)
    build: Build-Aenderungen
    ci: CI/CD Pipeline-Aenderungen
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


# Mapping von Commit-Prefixes zu Changelog-Kategorien
COMMIT_CATEGORIES = {
    "feat": "Features",
    "feature": "Features",
    "fix": "Bugfixes",
    "bugfix": "Bugfixes",
    "docs": "Dokumentation",
    "doc": "Dokumentation",
    "style": "Styling",
    "refactor": "Refactoring",
    "perf": "Performance",
    "test": "Tests",
    "chore": None,  # Nicht ins Changelog
    "build": None,  # Nicht ins Changelog
    "ci": None,     # Nicht ins Changelog
    "security": "Sicherheit",
    "sec": "Sicherheit",
    "ux": "UX",
}

# Kategorien die nicht ins Changelog aufgenommen werden
SKIP_CATEGORIES = {None, "Sonstiges"}


def run_git(args: list[str]) -> str:
    """Fuehrt einen Git-Befehl aus und gibt die Ausgabe zurueck"""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def is_stable_release(version: str) -> bool:
    """Prueft ob es ein stabiler Release ist (ohne -dev, -rc, etc.)"""
    return "-" not in version


def get_previous_tag(current_tag: str, stable_only: bool = False) -> str | None:
    """Findet den vorherigen Tag

    Args:
        current_tag: Aktueller Tag
        stable_only: Wenn True, nur stabile Releases beruecksichtigen
    """
    try:
        tags = run_git(["tag", "--sort=-version:refname"]).split("\n")
        tags = [t for t in tags if t]  # Leere entfernen

        if stable_only:
            tags = [t for t in tags if is_stable_release(t)]

        if current_tag in tags:
            idx = tags.index(current_tag)
            if idx + 1 < len(tags):
                return tags[idx + 1]
        elif tags:
            return tags[0]
        return None
    except subprocess.CalledProcessError:
        return None


def get_commits_since_tag(tag: str | None) -> list[str]:
    """Holt alle Commits seit einem Tag"""
    try:
        if tag:
            commits = run_git(["log", f"{tag}..HEAD", "--oneline", "--no-merges"])
        else:
            commits = run_git(["log", "--oneline", "--no-merges", "-50"])

        return [c for c in commits.split("\n") if c]
    except subprocess.CalledProcessError:
        return []


def parse_commits(commits: list[str]) -> dict[str, list[str]]:
    """Parst Commits und kategorisiert sie"""
    categorized = {}

    # Pattern: hash prefix: message oder hash prefix(scope): message
    pattern = re.compile(r"^[a-f0-9]+ (\w+)(?:\([^)]+\))?: (.+)$", re.IGNORECASE)

    for commit in commits:
        match = pattern.match(commit)
        if match:
            prefix = match.group(1).lower()
            message = match.group(2)

            category = COMMIT_CATEGORIES.get(prefix, "Sonstiges")

            # Kategorien ueberspringen die nicht ins Changelog gehoeren
            if category in SKIP_CATEGORIES:
                continue

            if category not in categorized:
                categorized[category] = []

            # Erste Zeile, kapitalisiert
            message = message[0].upper() + message[1:] if message else message
            categorized[category].append(message)
        # Commits ohne Conventional-Commits-Prefix werden ignoriert

    return categorized


def update_package_json(version: str, path: Path) -> bool:
    """Aktualisiert die Version in package.json"""
    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Version ohne 'v' Prefix
        clean_version = version.lstrip("v")
        data["version"] = clean_version

        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"  Updated {path} -> {clean_version}")
        return True
    except Exception as e:
        print(f"  Error updating {path}: {e}")
        return False


def update_main_py(version: str, path: Path) -> bool:
    """Aktualisiert die Version in main.py"""
    try:
        content = path.read_text()
        clean_version = version.lstrip("v")

        # Pattern fuer version="x.y.z"
        content = re.sub(
            r'version="[^"]*"',
            f'version="{clean_version}"',
            content
        )

        # Pattern fuer "version": "x.y.z"
        content = re.sub(
            r'"version": "[^"]*"',
            f'"version": "{clean_version}"',
            content
        )

        path.write_text(content)
        print(f"  Updated {path} -> {clean_version}")
        return True
    except Exception as e:
        print(f"  Error updating {path}: {e}")
        return False


def get_version_base(version: str) -> str:
    """Extrahiert die Basis-Version (z.B. v0.3.54 aus v0.3.54-dev.1)"""
    return version.split("-")[0]


def cleanup_changelog_for_stable(changelog: list, current_version: str, last_stable: str | None) -> list:
    """Entfernt Dev-Versionen und Zwischen-Patches fuer einen stabilen Release

    Bei einem stabilen Release (z.B. v0.3.54) werden entfernt:
    - Alle dev-Versionen dieser Version (v0.3.54-dev.1, v0.3.54-dev.2, ...)
    - Alle Patch-Versionen seit dem letzten stabilen Release
    """
    current_base = get_version_base(current_version)

    # Versionen die behalten werden sollen
    kept = []

    for entry in changelog:
        entry_version = entry.get("version", "")

        # Dev-Versionen der aktuellen Version entfernen
        if entry_version.startswith(current_base + "-"):
            print(f"    Removing dev version: {entry_version}")
            continue

        # Patch-Versionen zwischen letztem stable und aktuellem entfernen
        if last_stable and is_stable_release(entry_version):
            # Versionen zwischen last_stable und current_version entfernen
            # z.B. v0.3.50, v0.3.51, v0.3.52, v0.3.53 wenn last_stable=v0.3.44
            if entry_version != last_stable and entry_version != current_version:
                # Vergleiche Major.Minor
                try:
                    entry_parts = entry_version.lstrip("v").split(".")
                    current_parts = current_version.lstrip("v").split(".")
                    last_parts = last_stable.lstrip("v").split(".")

                    # Gleiche Major.Minor Version?
                    if (entry_parts[0] == current_parts[0] and
                        entry_parts[1] == current_parts[1]):
                        entry_patch = int(entry_parts[2]) if len(entry_parts) > 2 else 0
                        current_patch = int(current_parts[2]) if len(current_parts) > 2 else 0
                        last_patch = int(last_parts[2]) if len(last_parts) > 2 else 0

                        # Zwischen last_stable und current?
                        if last_patch < entry_patch < current_patch:
                            print(f"    Removing intermediate version: {entry_version}")
                            continue
                except (ValueError, IndexError):
                    pass

        kept.append(entry)

    return kept


def update_changelog(version: str, changes: dict[str, list[str]], path: Path, is_stable: bool = False, last_stable: str | None = None) -> bool:
    """Aktualisiert die changelog.json

    Args:
        version: Die neue Version
        changes: Die Aenderungen
        path: Pfad zur changelog.json
        is_stable: Ob es ein stabiler Release ist
        last_stable: Der letzte stabile Release (fuer Bereinigung)
    """
    try:
        # Bestehenden Changelog laden
        if path.exists():
            with open(path, "r") as f:
                changelog = json.load(f)
        else:
            changelog = []

        # Pruefen ob Version bereits existiert
        existing_versions = [entry.get("version") for entry in changelog]
        if version in existing_versions:
            print(f"  Version {version} already in changelog, skipping")
            return True

        # Bei stabilem Release: Changelog bereinigen
        if is_stable:
            print(f"  Cleaning up changelog for stable release...")
            changelog = cleanup_changelog_for_stable(changelog, version, last_stable)

        # Neuen Eintrag erstellen
        new_entry = {
            "version": version,
            "date": date.today().isoformat(),
            "changes": changes
        }

        # Am Anfang einfuegen
        changelog.insert(0, new_entry)

        # Speichern
        with open(path, "w") as f:
            json.dump(changelog, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"  Updated {path} with {len(changes)} categories")
        return True
    except Exception as e:
        print(f"  Error updating {path}: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python update-version.py <version>")
        print("Example: python update-version.py v0.2.7")
        sys.exit(1)

    version = sys.argv[1]
    if not version.startswith("v"):
        version = f"v{version}"

    is_stable = is_stable_release(version)
    print(f"Updating to version {version} ({'stable' if is_stable else 'dev'})")

    # Projekt-Root finden
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Pfade zu den Dateien
    package_json = project_root / "frontend" / "package.json"
    main_py = project_root / "backend" / "app" / "main.py"
    changelog_json = project_root / "frontend" / "src" / "data" / "changelog.json"

    # Fuer stabile Releases: Letzten stabilen Tag finden
    # Fuer dev Releases: Vorherigen Tag (egal ob stable oder dev)
    if is_stable:
        prev_tag = get_previous_tag(version, stable_only=True)
        last_stable = prev_tag
        print(f"Last stable release: {last_stable or 'none'}")
    else:
        prev_tag = get_previous_tag(version, stable_only=False)
        last_stable = None
        print(f"Previous tag: {prev_tag or 'none'}")

    # Commits seit letztem Tag holen
    commits = get_commits_since_tag(prev_tag)
    print(f"Found {len(commits)} commits since {prev_tag or 'beginning'}")

    # Commits parsen und kategorisieren
    changes = parse_commits(commits)

    if not changes:
        print("No categorized changes found, creating placeholder")
        changes = {"Wartung": ["Version aktualisiert"]}

    print(f"Categories: {list(changes.keys())}")

    # Dateien aktualisieren
    print("\nUpdating files:")
    success = True
    success &= update_package_json(version, package_json)
    success &= update_main_py(version, main_py)
    success &= update_changelog(version, changes, changelog_json, is_stable=is_stable, last_stable=last_stable)

    if success:
        print("\nVersion update complete!")
    else:
        print("\nVersion update completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
