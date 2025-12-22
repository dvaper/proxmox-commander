"""
Konfiguration fuer Proxmox Commander

Alle Einstellungen werden aus Umgebungsvariablen und .env Datei geladen.
Siehe .env.example fuer verfuegbare Optionen.

Hot-Reload: Nach Aenderungen an der .env Datei kann reload_settings()
aufgerufen werden. Alle Module die 'settings' importiert haben sehen
automatisch die neuen Werte (via SettingsProxy).
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional, Any
from dotenv import load_dotenv
import os


class Settings(BaseSettings):
    """Application Settings - geladen aus Umgebungsvariablen"""

    # ==========================================================================
    # App Einstellungen
    # ==========================================================================
    app_name: str = "Proxmox Commander"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # JWT Auth
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 Stunden

    # ==========================================================================
    # Datenbank
    # ==========================================================================
    # SQLite fuer App-Daten (Users, Executions, History)
    data_dir: str = "/data"

    @property
    def database_url(self) -> str:
        """SQLite Datenbank-Pfad"""
        return f"sqlite+aiosqlite:///{self.data_dir}/db/commander.db"

    # ==========================================================================
    # Pfade (aus DATA_DIR abgeleitet)
    # ==========================================================================
    inventory_dir: str = "/data/inventory"
    playbooks_dir: str = "/data/playbooks"
    roles_dir: str = "/data/roles"
    terraform_dir: str = "/data/terraform"
    ssh_key_path: str = "/data/ssh/id_ed25519"

    @property
    def ansible_inventory_path(self) -> str:
        """Hauptpfad zum Ansible Inventory"""
        return f"{self.inventory_dir}/hosts.yml"

    @property
    def ansible_playbook_dir(self) -> str:
        """Alias fuer playbooks_dir (Kompatibilitaet)"""
        return self.playbooks_dir

    # ==========================================================================
    # NetBox (interner Container)
    # ==========================================================================
    netbox_url: str = "http://netbox:8080"
    netbox_token: Optional[str] = None

    # ==========================================================================
    # Proxmox API
    # ==========================================================================
    proxmox_host: str = ""
    proxmox_user: str = "terraform@pve"
    proxmox_token_id: Optional[str] = None
    proxmox_token_secret: Optional[str] = None
    proxmox_verify_ssl: bool = False

    # Alias-Properties fuer Kompatibilitaet mit bestehendem Code
    @property
    def proxmox_token_name(self) -> Optional[str]:
        """Extrahiert Token-Name aus Token-ID (user@realm!token-name -> token-name)"""
        if self.proxmox_token_id and "!" in self.proxmox_token_id:
            return self.proxmox_token_id.split("!")[-1]
        return self.proxmox_token_id

    @property
    def proxmox_token_value(self) -> Optional[str]:
        """Alias fuer proxmox_token_secret"""
        return self.proxmox_token_secret

    # ==========================================================================
    # Proxmox Inventory Sync
    # ==========================================================================
    proxmox_inventory_sync: bool = False
    proxmox_sync_interval: int = 60  # Minuten
    proxmox_sync_tag: str = ""  # Nur VMs mit diesem Tag importieren

    # ==========================================================================
    # Ansible Einstellungen
    # ==========================================================================
    ansible_remote_user: str = "ansible"
    ansible_ssh_key: str = "id_ed25519"
    ansible_host_key_checking: bool = False

    # ==========================================================================
    # VM Deployment Defaults
    # ==========================================================================
    default_ssh_user: str = "ansible"
    default_template_id: int = 940001
    default_storage: str = "local-ssd"
    default_vlan: int = 60

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: list[str] = ["*"]  # Im Container: Frontend ist am gleichen Origin

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Case-insensitive environment variables
        case_sensitive = False
        # Extra Variablen ignorieren (z.B. fuer andere Container)
        extra = "ignore"


# =============================================================================
# Settings Proxy fuer Hot-Reload Support
# =============================================================================

class SettingsProxy:
    """
    Proxy-Klasse die alle Attributzugriffe an die aktuelle Settings-Instanz weiterleitet.

    Ermoeglicht Hot-Reload: Nach reload_settings() sehen alle Module die bereits
    'settings' importiert haben automatisch die neuen Werte.
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(_current_settings, name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(_current_settings, name, value)

    def __repr__(self) -> str:
        return f"SettingsProxy({_current_settings!r})"


def _load_initial_settings() -> Settings:
    """Laedt die initialen Settings aus der .env Datei."""
    env_file = os.getenv("ENV_FILE", "/app/.env")
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)
    return Settings()


# Interne Settings-Instanz (wird bei reload ersetzt)
_current_settings: Settings = _load_initial_settings()

# Oeffentlicher Proxy (bleibt immer das gleiche Objekt)
settings: SettingsProxy = SettingsProxy()


def reload_settings(env_file: str = None) -> Settings:
    """
    Laedt die Settings neu aus der .env Datei.

    Wird vom Setup-Wizard aufgerufen nachdem die Konfiguration gespeichert wurde.
    Alle Module die 'settings' importiert haben sehen automatisch die neuen Werte.
    """
    global _current_settings

    # Bestimme den Pfad zur .env Datei
    if env_file is None:
        env_file = os.getenv("ENV_FILE", "/app/.env")

    # Lade die .env Datei in die Umgebungsvariablen (override=True)
    if os.path.exists(env_file):
        load_dotenv(env_file, override=True)

    # Erstelle neue Settings-Instanz mit den aktualisierten Umgebungsvariablen
    _current_settings = Settings()

    return _current_settings


def get_settings() -> Settings:
    """Gibt die aktuelle Settings-Instanz zurueck."""
    return _current_settings
