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

    # Default-Admin erstellen falls keine User existieren
    await create_default_admin()


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
