"""
Datenbank-Setup mit SQLAlchemy Async
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, func
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


# Stelle sicher, dass das data-Verzeichnis existiert
db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
db_path.parent.mkdir(parents=True, exist_ok=True)

# Async Engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

# Session Factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Basis-Klasse für alle Models"""
    pass


async def get_db():
    """Dependency für Datenbank-Session"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialisiert die Datenbank (erstellt Tabellen und Default-Admin)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Migrationen für existierende Datenbanken
    await run_migrations()

    # Default-Admin erstellen falls keine User existieren
    await create_default_admin()


async def run_migrations():
    """Führt manuelle Schema-Migrationen für SQLite durch"""
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Spalten der users-Tabelle ermitteln
        try:
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Konnte Tabellen-Info nicht lesen: {e}")
            return

        # Migration: netbox_user_id Spalte zu users hinzufügen
        if "netbox_user_id" not in columns:
            try:
                logger.info("Migration: Füge netbox_user_id Spalte zu users hinzu...")
                await conn.execute(text("ALTER TABLE users ADD COLUMN netbox_user_id INTEGER"))
                logger.info("Migration erfolgreich: netbox_user_id hinzugefügt")
            except Exception as e:
                logger.debug(f"Migration netbox_user_id fehlgeschlagen: {e}")

        # Migration: theme Spalte zu users hinzufügen (v0.2.19)
        if "theme" not in columns:
            try:
                logger.info("Migration: Füge theme Spalte zu users hinzu...")
                await conn.execute(text("ALTER TABLE users ADD COLUMN theme VARCHAR(20) DEFAULT 'blue' NOT NULL"))
                logger.info("Migration erfolgreich: theme hinzugefügt")
            except Exception as e:
                logger.debug(f"Migration theme fehlgeschlagen: {e}")

        # Migration: dark_mode Spalte zu users hinzufügen (v0.2.22)
        if "dark_mode" not in columns:
            try:
                logger.info("Migration: Füge dark_mode Spalte zu users hinzu...")
                await conn.execute(text("ALTER TABLE users ADD COLUMN dark_mode VARCHAR(10) DEFAULT 'dark' NOT NULL"))
                logger.info("Migration erfolgreich: dark_mode hinzugefügt")
            except Exception as e:
                logger.debug(f"Migration dark_mode fehlgeschlagen: {e}")

        # Migration: sidebar_logo Spalte zu users hinzufügen (v0.2.34)
        if "sidebar_logo" not in columns:
            try:
                logger.info("Migration: Füge sidebar_logo Spalte zu users hinzu...")
                await conn.execute(text("ALTER TABLE users ADD COLUMN sidebar_logo VARCHAR(10) DEFAULT 'icon' NOT NULL"))
                logger.info("Migration erfolgreich: sidebar_logo hinzugefügt")
            except Exception as e:
                logger.debug(f"Migration sidebar_logo fehlgeschlagen: {e}")


async def create_default_admin():
    """Erstellt oder aktualisiert den Admin-User basierend auf Settings (fuer App-Start)"""
    # Verwendet Settings - fuer normalen App-Start
    await ensure_admin_exists(
        username=settings.app_admin_user,
        password=settings.app_admin_password,
        email=settings.app_admin_email,
    )


async def ensure_admin_exists(
    username: str = None,
    password: str = None,
    email: str = None,
) -> dict:
    """
    Stellt sicher, dass ein Admin-User mit den angegebenen Credentials existiert.

    Diese Funktion ist robuster als create_default_admin() weil sie:
    - Explizite Credentials als Parameter akzeptiert (nicht nur aus Settings)
    - Immer einen Admin erstellt/aktualisiert wenn Credentials angegeben sind
    - Detailliertes Ergebnis zurueckgibt

    Args:
        username: Admin-Benutzername (default: "admin")
        password: Admin-Passwort (wenn None, wird keiner erstellt/aktualisiert)
        email: Admin-E-Mail (default: "admin@local")

    Returns:
        dict mit: success, action ("created"/"updated"/"skipped"), message
    """
    from app.models.user import User
    from app.auth.security import get_password_hash, verify_password

    # Defaults
    admin_user = username or "admin"
    admin_email = email or "admin@local"

    # Ohne Passwort koennen wir nichts tun
    if not password:
        logger.debug("Kein Admin-Passwort angegeben, ueberspringe Admin-Erstellung")
        return {
            "success": True,
            "action": "skipped",
            "message": "Kein Passwort angegeben"
        }

    async with async_session() as session:
        # Prüfe ob Super-Admin existiert
        result = await session.execute(
            select(User).where(User.is_super_admin == True)
        )
        super_admin = result.scalar_one_or_none()

        if super_admin is None:
            # Kein Super-Admin vorhanden - neuen erstellen
            logger.info(f"Erstelle neuen Admin-User '{admin_user}'")

            admin = User(
                username=admin_user,
                password_hash=get_password_hash(password),
                email=admin_email,
                is_admin=True,
                is_super_admin=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()

            logger.info(f"Admin-User '{admin_user}' erfolgreich erstellt")
            return {
                "success": True,
                "action": "created",
                "message": f"Admin-User '{admin_user}' erstellt"
            }

        else:
            # Super-Admin existiert - aktualisieren falls noetig
            needs_update = False
            update_reasons = []

            # Username pruefen/aktualisieren
            if super_admin.username != admin_user:
                logger.info(f"Aktualisiere Admin-Username: {super_admin.username} -> {admin_user}")
                super_admin.username = admin_user
                needs_update = True
                update_reasons.append("username")

            # Email pruefen/aktualisieren
            if super_admin.email != admin_email:
                super_admin.email = admin_email
                needs_update = True
                update_reasons.append("email")

            # Passwort pruefen/aktualisieren
            if not verify_password(password, super_admin.password_hash):
                super_admin.password_hash = get_password_hash(password)
                needs_update = True
                update_reasons.append("password")

            if needs_update:
                await session.commit()
                msg = f"Admin-User aktualisiert ({', '.join(update_reasons)})"
                logger.info(msg)
                return {
                    "success": True,
                    "action": "updated",
                    "message": msg,
                    "updated_fields": update_reasons
                }
            else:
                logger.debug("Admin-Credentials unveraendert")
                return {
                    "success": True,
                    "action": "unchanged",
                    "message": "Admin-Credentials unveraendert"
                }
