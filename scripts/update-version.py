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
    chore: Wartung -> "Wartung"
    security/sec: Sicherheit -> "Sicherheit"
    ux: UX-Verbesserungen -> "UX"
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
    "chore": "Wartung",
    "build": "Build",
    "ci": "CI/CD",
    "security": "Sicherheit",
    "sec": "Sicherheit",
    "ux": "UX",
}


def run_git(args: list[str]) -> str:
    """Fuehrt einen Git-Befehl aus und gibt die Ausgabe zurueck"""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def get_previous_tag(current_tag: str) -> str | None:
    """Findet den vorherigen Tag"""
    try:
        tags = run_git(["tag", "--sort=-version:refname"]).split("\n")
        tags = [t for t in tags if t]  # Leere entfernen

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

            if category not in categorized:
                categorized[category] = []

            # Erste Zeile, kapitalisiert
            message = message[0].upper() + message[1:] if message else message
            categorized[category].append(message)
        else:
            # Commit ohne Prefix -> Sonstiges
            parts = commit.split(" ", 1)
            if len(parts) > 1:
                message = parts[1]
                if "Sonstiges" not in categorized:
                    categorized["Sonstiges"] = []
                categorized["Sonstiges"].append(message)

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


def update_changelog(version: str, changes: dict[str, list[str]], path: Path) -> bool:
    """Aktualisiert die changelog.json"""
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

    print(f"Updating to version {version}")

    # Projekt-Root finden
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Pfade zu den Dateien
    package_json = project_root / "frontend" / "package.json"
    main_py = project_root / "backend" / "app" / "main.py"
    changelog_json = project_root / "frontend" / "src" / "data" / "changelog.json"

    # Vorherigen Tag finden
    prev_tag = get_previous_tag(version)
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
    success &= update_changelog(version, changes, changelog_json)

    if success:
        print("\nVersion update complete!")
    else:
        print("\nVersion update completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
