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
    """Erstellt einen Default-Admin wenn keine User existieren"""
    # Import hier um zirkulaere Imports zu vermeiden
    from app.models.user import User
    from app.auth.security import get_password_hash

    async with async_session() as session:
        # Prüfe ob bereits User existieren
        result = await session.execute(select(func.count(User.id)))
        user_count = result.scalar()

        if user_count == 0:
            logger.info("Keine User gefunden - erstelle Default-Admin...")
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin"),
                email="admin@local",
                is_admin=True,
                is_super_admin=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("Default-Admin erstellt (username: admin, password: admin)")
            logger.warning("WICHTIG: Bitte das Admin-Passwort nach dem ersten Login aendern!")
        else:
            logger.debug(f"User existieren bereits ({user_count}), ueberspringe Default-Admin")
