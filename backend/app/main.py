"""
Proxmox Commander - FastAPI Backend

Standalone VM-Management fuer Proxmox mit integriertem NetBox
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth_router, inventory_router, playbooks_router, executions_router, users_router, settings_router, terraform_router, vm_templates_router, cloud_init_router, setup_router
from app.routers.websocket import router as websocket_router
from app.services.inventory_sync_service import get_sync_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Events"""
    # Startup
    await init_db()

    # Background Inventory-Sync starten
    sync_service = get_sync_service()
    await sync_service.start_background_sync()
    logger.info("Background Inventory-Sync gestartet")

    yield

    # Shutdown
    await sync_service.stop_background_sync()
    logger.info("Background Inventory-Sync gestoppt")


app = FastAPI(
    title=settings.app_name,
    description="Standalone VM-Management fuer Proxmox mit integriertem NetBox, Ansible und Terraform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router einbinden
app.include_router(auth_router)
app.include_router(inventory_router)
app.include_router(playbooks_router)
app.include_router(executions_router)
app.include_router(users_router)
app.include_router(settings_router)
app.include_router(terraform_router)
app.include_router(vm_templates_router)
app.include_router(cloud_init_router)
app.include_router(setup_router)
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Health Check"""
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    """Health Check für Monitoring"""
    return {"status": "healthy"}
