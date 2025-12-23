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


class ProxmoxIP(BaseModel):
    """IP aus Proxmox-Scan"""
    vmid: int
    name: str
    node: str
    ip: str
    status: str
    source: str  # 'guest-agent' | 'cloud-init'
    exists_in_netbox: bool = False
    prefix: Optional[str] = None


class IPSyncResult(BaseModel):
    """IP-Sync Ergebnis"""
    scanned: int
    created: int
    skipped: int
    errors: list[str]
    ips: list[ProxmoxIP]


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


@router.post("/sync-ips", response_model=IPSyncResult)
async def sync_ips_from_proxmox(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Scannt Proxmox VMs und synchronisiert IPs nach NetBox.

    - Neue IPs werden in NetBox angelegt
    - Existierende IPs werden uebersprungen
    - Erfordert Admin-Rechte
    """
    created = 0
    skipped = 0
    errors = []
    result_ips = []

    try:
        # 1. Proxmox VMs scannen
        proxmox_ips = await proxmox_service.scan_vm_ips()

        # 2. Prefixes aus NetBox holen fuer Zuordnung
        prefixes = await netbox_service.get_prefixes_with_utilization()

        for vm_ip in proxmox_ips:
            ip = vm_ip.get("ip")
            if not ip:
                continue

            # Prefix fuer diese IP finden
            matching_prefix = None
            for prefix in prefixes:
                if _ip_in_prefix(ip, prefix.get("prefix", "")):
                    matching_prefix = prefix.get("prefix")
                    break

            # Pruefen ob IP bereits in NetBox existiert
            try:
                ip_exists = not await netbox_service.check_ip_available(ip)
            except Exception:
                ip_exists = False

            result_ips.append(ProxmoxIP(
                vmid=vm_ip.get("vmid"),
                name=vm_ip.get("name", ""),
                node=vm_ip.get("node", ""),
                ip=ip,
                status=vm_ip.get("status", "unknown"),
                source=vm_ip.get("source", "unknown"),
                exists_in_netbox=ip_exists,
                prefix=matching_prefix,
            ))

            if ip_exists:
                skipped += 1
                continue

            # IP in NetBox anlegen
            try:
                await netbox_service.reserve_ip(
                    ip_address=ip,
                    description=f"{vm_ip.get('name', '')} (VMID: {vm_ip.get('vmid')})",
                    dns_name=vm_ip.get("name", ""),
                )
                # Status auf active setzen (VM laeuft ja)
                if vm_ip.get("status") == "running":
                    await netbox_service.activate_ip(ip)
                created += 1
                logger.info(f"IP {ip} fuer VM {vm_ip.get('name')} in NetBox angelegt")
            except Exception as e:
                errors.append(f"{ip}: {str(e)}")
                logger.error(f"Fehler beim Anlegen von IP {ip}: {e}")

        return IPSyncResult(
            scanned=len(proxmox_ips),
            created=created,
            skipped=skipped,
            errors=errors,
            ips=result_ips,
        )

    except Exception as e:
        logger.error(f"Fehler beim IP-Sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _ip_in_prefix(ip: str, prefix: str) -> bool:
    """Prueft ob eine IP in einem Prefix liegt."""
    import ipaddress
    try:
        ip_obj = ipaddress.ip_address(ip)
        network = ipaddress.ip_network(prefix, strict=False)
        return ip_obj in network
    except Exception:
        return False
