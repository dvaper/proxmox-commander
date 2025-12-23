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
        # Migration: netbox_user_id Spalte zu users hinzufügen
        try:
            result = await conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]

            if "netbox_user_id" not in columns:
                logger.info("Migration: Füge netbox_user_id Spalte zu users hinzu...")
                await conn.execute(text("ALTER TABLE users ADD COLUMN netbox_user_id INTEGER"))
                logger.info("Migration erfolgreich: netbox_user_id hinzugefügt")
        except Exception as e:
            logger.debug(f"Migration übersprungen oder fehlgeschlagen: {e}")


async def create_default_admin():
    """Erstellt oder aktualisiert den Admin-User basierend auf Settings"""
    # Import hier um zirkulaere Imports zu vermeiden
    from app.models.user import User
    from app.auth.security import get_password_hash, verify_password

    async with async_session() as session:
        # Prüfe ob bereits User existieren
        result = await session.execute(select(func.count(User.id)))
        user_count = result.scalar()

        # Admin-Credentials aus Settings
        admin_user = settings.app_admin_user or "admin"
        admin_email = settings.app_admin_email or "admin@local"

        if user_count == 0:
            # Keine User vorhanden - neuen Admin erstellen
            if settings.app_admin_password:
                admin_password = settings.app_admin_password
                logger.info(f"Erstelle Admin-User '{admin_user}' mit konfiguriertem Passwort")
            else:
                # Fallback: Generiertes Passwort
                import secrets
                admin_password = secrets.token_urlsafe(12)
                logger.warning(f"Kein Admin-Passwort konfiguriert - generiere zufaelliges Passwort")
                logger.warning(f"ACHTUNG: Generiertes Admin-Passwort: {admin_password}")
                logger.warning("Bitte dieses Passwort notieren oder im Setup-Wizard ein eigenes setzen!")

            admin = User(
                username=admin_user,
                password_hash=get_password_hash(admin_password),
                email=admin_email,
                is_admin=True,
                is_super_admin=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info(f"Admin-User '{admin_user}' erfolgreich erstellt")

        elif settings.app_admin_password:
            # User existieren und Passwort ist in Settings gesetzt
            # Prüfe ob Admin-User aktualisiert werden muss
            result = await session.execute(
                select(User).where(User.is_super_admin == True)
            )
            super_admin = result.scalar_one_or_none()

            if super_admin:
                needs_update = False
                update_reasons = []

                # Prüfe ob Username geändert wurde
                if super_admin.username != admin_user:
                    super_admin.username = admin_user
                    needs_update = True
                    update_reasons.append("username")

                # Prüfe ob Email geändert wurde
                if super_admin.email != admin_email:
                    super_admin.email = admin_email
                    needs_update = True
                    update_reasons.append("email")

                # Prüfe ob Passwort geändert wurde
                if not verify_password(settings.app_admin_password, super_admin.password_hash):
                    super_admin.password_hash = get_password_hash(settings.app_admin_password)
                    needs_update = True
                    update_reasons.append("password")

                if needs_update:
                    await session.commit()
                    logger.info(f"Admin-User aktualisiert ({', '.join(update_reasons)})")
                else:
                    logger.debug("Admin-Credentials unveraendert")
            else:
                logger.warning("Kein Super-Admin gefunden, kann Credentials nicht aktualisieren")
        else:
            logger.debug(f"User existieren bereits ({user_count}), keine Admin-Credentials in Settings")
