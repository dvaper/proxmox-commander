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
from app.routers import auth_router, inventory_router, playbooks_router, executions_router, users_router, settings_router, terraform_router, vm_templates_router, cloud_init_router, setup_router, netbox_router
from app.routers.websocket import router as websocket_router
from app.routers.notifications import router as notifications_router
from app.routers.password_reset import router as password_reset_router
from app.routers.cloud_init_settings import router as cloud_init_settings_router
from app.routers.backup import router as backup_router
from app.services.inventory_sync_service import get_sync_service
from app.services.backup_scheduler import start_backup_scheduler, stop_backup_scheduler

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

    # Backup-Scheduler starten
    await start_backup_scheduler()
    logger.info("Backup-Scheduler gestartet")

    yield

    # Shutdown
    await stop_backup_scheduler()
    logger.info("Backup-Scheduler gestoppt")

    await sync_service.stop_background_sync()
    logger.info("Background Inventory-Sync gestoppt")


app = FastAPI(
    title=settings.app_name,
    description="Standalone VM-Management fuer Proxmox mit integriertem NetBox, Ansible und Terraform",
    version="0.3.39",
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
app.include_router(netbox_router)
app.include_router(websocket_router)
app.include_router(notifications_router)
app.include_router(password_reset_router)
app.include_router(cloud_init_settings_router)
app.include_router(backup_router)


@app.get("/")
async def root():
    """Health Check"""
    return {
        "app": settings.app_name,
        "version": "0.3.39",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    """Health Check für Monitoring - inkl. Service-Status"""
    import httpx

    services = {
        "api": {"status": "healthy", "message": "API running"},
        "netbox": {"status": "unknown", "message": "Checking..."},
    }

    # NetBox Status pruefen
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.netbox_url}/api/status/")
            if response.status_code == 200:
                services["netbox"] = {"status": "healthy", "message": "NetBox ready"}
            else:
                services["netbox"] = {"status": "degraded", "message": f"HTTP {response.status_code}"}
    except httpx.ConnectError:
        services["netbox"] = {"status": "starting", "message": "NetBox starting..."}
    except httpx.TimeoutException:
        services["netbox"] = {"status": "starting", "message": "NetBox starting (timeout)"}
    except Exception as e:
        services["netbox"] = {"status": "error", "message": str(e)[:50]}

    # Gesamtstatus ermitteln
    overall = "healthy"
    if any(s["status"] == "error" for s in services.values()):
        overall = "degraded"
    elif any(s["status"] == "starting" for s in services.values()):
        overall = "starting"

    return {
        "status": overall,
        "services": services,
    }
