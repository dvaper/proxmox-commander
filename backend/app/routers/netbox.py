"""
NetBox Router - VLANs und Prefixes verwalten, Import von Proxmox
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.services.netbox_service import netbox_service
from app.services.proxmox_service import proxmox_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/netbox", tags=["netbox"])


# =============================================================================
# Schemas
# =============================================================================

class VLANInfo(BaseModel):
    """VLAN-Information aus NetBox"""
    id: int
    name: str
    prefix: Optional[str] = None
    bridge: str


class PrefixInfo(BaseModel):
    """Prefix-Information aus NetBox"""
    prefix: str
    vlan: Optional[int] = None
    description: Optional[str] = None
    utilization: Optional[int] = None


class ProxmoxVLAN(BaseModel):
    """VLAN aus Proxmox-Scan"""
    vlan_id: int
    bridge: str
    nodes: list[str]
    vm_count: int
    exists_in_netbox: bool


class VLANImportItem(BaseModel):
    """Einzelnes VLAN zum Importieren"""
    vlan_id: int
    prefix: Optional[str] = None  # None = kein Prefix erstellen


class VLANImportRequest(BaseModel):
    """Import-Anfrage"""
    vlans: list[VLANImportItem]


class VLANImportResult(BaseModel):
    """Import-Ergebnis"""
    imported: list[int]
    skipped: list[int]
    errors: list[str]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/vlans", response_model=list[VLANInfo])
async def get_vlans(
    current_user: User = Depends(get_current_active_user)
):
    """
    Alle VLANs aus NetBox abrufen.
    """
    try:
        vlans = await netbox_service.get_vlans()
        return [VLANInfo(**v) for v in vlans]
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der VLANs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prefixes", response_model=list[PrefixInfo])
async def get_prefixes(
    current_user: User = Depends(get_current_active_user)
):
    """
    Alle Prefixes aus NetBox abrufen.
    """
    try:
        prefixes = await netbox_service.get_prefixes_with_utilization()
        return [PrefixInfo(**p) for p in prefixes]
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Prefixes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxmox-vlans", response_model=list[ProxmoxVLAN])
async def scan_proxmox_vlans(
    current_user: User = Depends(get_current_active_user)
):
    """
    Proxmox-Cluster nach VLANs scannen.

    Findet:
    - Bridges mit VLAN-Namen (vmbr60 -> VLAN 60)
    - VLAN-Tags in VM-Konfigurationen
    """
    try:
        # Proxmox scannen
        proxmox_vlans = await proxmox_service.scan_network_vlans()

        # NetBox VLANs abrufen zum Abgleich
        netbox_vlans = await netbox_service.get_vlans()
        netbox_vlan_ids = {v['id'] for v in netbox_vlans}

        # Ergebnis zusammenstellen
        result = []
        for vlan in proxmox_vlans:
            result.append(ProxmoxVLAN(
                vlan_id=vlan['vlan_id'],
                bridge=vlan['bridge'],
                nodes=vlan['nodes'],
                vm_count=vlan.get('vm_count', 0),
                exists_in_netbox=vlan['vlan_id'] in netbox_vlan_ids
            ))

        return sorted(result, key=lambda x: x.vlan_id)

    except Exception as e:
        logger.error(f"Fehler beim Scannen der Proxmox VLANs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import-vlans", response_model=VLANImportResult)
async def import_vlans(
    request: VLANImportRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    VLANs nach NetBox importieren.

    Erfordert Admin-Rechte.
    """
    imported = []
    skipped = []
    errors = []

    for item in request.vlans:
        try:
            # Pruefen ob VLAN bereits existiert
            if await netbox_service.vlan_exists(item.vlan_id):
                skipped.append(item.vlan_id)
                continue

            # VLAN erstellen
            vlan_result = await netbox_service.create_vlan(
                vlan_id=item.vlan_id,
                name=f"VLAN{item.vlan_id}"
            )

            if not vlan_result:
                errors.append(f"VLAN {item.vlan_id}: Erstellung fehlgeschlagen")
                continue

            # Prefix erstellen (wenn angegeben)
            if item.prefix:
                prefix_result = await netbox_service.create_prefix_for_vlan(
                    vlan_id=item.vlan_id,
                    prefix=item.prefix
                )
                if not prefix_result:
                    errors.append(f"VLAN {item.vlan_id}: Prefix-Erstellung fehlgeschlagen")
                    # VLAN wurde trotzdem erstellt
                    imported.append(item.vlan_id)
                    continue

            imported.append(item.vlan_id)
            logger.info(f"VLAN {item.vlan_id} erfolgreich importiert")

        except Exception as e:
            errors.append(f"VLAN {item.vlan_id}: {str(e)}")
            logger.error(f"Fehler beim Import von VLAN {item.vlan_id}: {e}")

    return VLANImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors
    )
