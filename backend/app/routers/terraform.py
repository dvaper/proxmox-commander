"""
Terraform Router - VM-Management und NetBox-Integration

Endpoints für:
- VM-Konfigurationen erstellen/verwalten
- NetBox IPAM (freie IPs, Reservierungen)
- Proxmox-Node Informationen
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from app.auth.dependencies import get_current_active_user, get_current_admin_user
from app.models.user import User
from app.schemas.vm import (
    VMConfigCreate,
    VMConfigResponse,
    VMConfigListItem,
    VMValidationResult,
    TerraformPreview,
    AvailableIP,
    VLANInfo,
    UsedIP,
    NodeInfo,
    PROXMOX_NODES,
    VMMigrateRequest,
    VMMigrateResult,
    VMFrontendUrlUpdate,
    VMFrontendUrlResult,
)
from app.services.vm_deployment_service import vm_deployment_service
from app.services.netbox_service import netbox_service
from app.services.ansible_inventory_service import ansible_inventory_service
from app.services.proxmox_service import proxmox_service
from app.services.vm_history_service import vm_history_service

router = APIRouter(prefix="/api/terraform", tags=["terraform"])


# =============================================================================
# NetBox IPAM Endpoints
# =============================================================================

class IPAMStatus(BaseModel):
    """Status der NetBox IPAM-Konfiguration"""
    configured: bool
    prefixes_count: int = 0
    vlans_count: int = 0
    netbox_url: Optional[str] = None
    error: Optional[str] = None


@router.get("/ipam/status", response_model=IPAMStatus)
async def get_ipam_status(
    current_user: User = Depends(get_current_active_user),
):
    """
    Prüft ob NetBox IPAM konfiguriert ist.

    Gibt zurück ob Prefixes in NetBox vorhanden sind.
    Ohne Prefixes können keine freien IPs abgefragt werden.

    Die Konfiguration erfolgt direkt in der NetBox-Oberfläche.
    """
    result = await netbox_service.check_ipam_status()
    return IPAMStatus(**result)


@router.get("/vlans", response_model=list[VLANInfo])
async def get_vlans(
    current_user: User = Depends(get_current_active_user),
):
    """Liste aller verfügbaren VLANs"""
    vlans = await netbox_service.get_vlans()
    return [VLANInfo(**v) for v in vlans]


@router.get("/available-ips/{vlan}", response_model=list[AvailableIP])
async def get_available_ips(
    vlan: int,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
):
    """Freie IP-Adressen in einem VLAN"""
    try:
        ips = await netbox_service.get_available_ips(vlan, limit)
        return [AvailableIP(**ip) for ip in ips]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NetBox-Fehler: {str(e)}")


@router.get("/used-ips/{vlan}", response_model=list[UsedIP])
async def get_used_ips(
    vlan: int,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
):
    """Belegte IP-Adressen in einem VLAN"""
    try:
        ips = await netbox_service.get_used_ips(vlan, limit)
        return [UsedIP(**ip) for ip in ips]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NetBox-Fehler: {str(e)}")


@router.post("/reserve-ip")
async def reserve_ip(
    ip_address: str,
    description: str,
    dns_name: str = "",
    current_user: User = Depends(get_current_admin_user),
):
    """IP-Adresse in NetBox reservieren (nur Admin)"""
    try:
        result = await netbox_service.reserve_ip(ip_address, description, dns_name)
        return {"message": "IP reserviert", "ip": ip_address, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NetBox-Fehler: {str(e)}")


@router.delete("/release-ip/{ip_address}")
async def release_ip(
    ip_address: str,
    current_user: User = Depends(get_current_admin_user),
):
    """IP-Adresse in NetBox freigeben (nur Admin)"""
    try:
        success = await netbox_service.release_ip(ip_address)
        if success:
            return {"message": "IP freigegeben", "ip": ip_address}
        else:
            raise HTTPException(status_code=404, detail="IP nicht gefunden")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NetBox-Fehler: {str(e)}")


# =============================================================================
# Proxmox Endpoints
# =============================================================================

@router.get("/nodes", response_model=list[NodeInfo])
async def get_nodes(
    current_user: User = Depends(get_current_active_user),
):
    """Liste aller Proxmox-Nodes"""
    return [
        NodeInfo(name=name, **info)
        for name, info in PROXMOX_NODES.items()
    ]


class ProxmoxVMStatus(BaseModel):
    """Response-Schema für Proxmox VM-Status"""
    exists: Optional[bool] = None
    configured: bool = False
    node: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None
    vmid: Optional[int] = None
    error: Optional[str] = None


@router.get("/proxmox/vm/{vmid}", response_model=ProxmoxVMStatus)
async def check_vm_exists_in_proxmox(
    vmid: int,
    node: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Prüft ob eine VM mit der gegebenen VMID in Proxmox existiert.

    Durchsucht alle Cluster-Nodes oder nur den angegebenen Node.
    Gibt Status zurück: exists (true/false/null), node, status, name.
    """
    result = await proxmox_service.check_vm_exists(vmid, node)
    return ProxmoxVMStatus(**result)


# =============================================================================
# VM Power Control Endpoints
# =============================================================================

class PowerActionResult(BaseModel):
    """Response für Power-Aktionen"""
    success: bool
    action: Optional[str] = None
    vmid: Optional[int] = None
    node: Optional[str] = None
    upid: Optional[str] = None
    error: Optional[str] = None


@router.post("/vms/{name}/power/{action}", response_model=PowerActionResult)
async def vm_power_action(
    name: str,
    action: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Power-Aktion auf einer VM ausführen (nur Admin).

    Actions:
    - start: VM starten
    - stop: VM sofort stoppen (force)
    - shutdown: VM sauber herunterfahren (ACPI)
    - reboot: VM neu starten (ACPI)
    - reset: Hard-Reset
    """
    valid_actions = ["start", "stop", "shutdown", "reboot", "reset"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültige Aktion. Erlaubt: {', '.join(valid_actions)}"
        )

    # VM-Konfiguration holen für VMID und Node
    vm_config = vm_deployment_service.get_vm_config(name)
    if not vm_config:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    # Proxmox-Status prüfen um Node zu ermitteln
    proxmox_status = await proxmox_service.check_vm_exists(vm_config.vmid)
    if not proxmox_status.get("exists"):
        raise HTTPException(
            status_code=404,
            detail=f"VM '{name}' (VMID {vm_config.vmid}) existiert nicht in Proxmox"
        )

    node = proxmox_status.get("node")

    # Power-Aktion ausführen
    if action == "start":
        result = await proxmox_service.start_vm(vm_config.vmid, node)
    elif action == "stop":
        result = await proxmox_service.stop_vm(vm_config.vmid, node)
    elif action == "shutdown":
        result = await proxmox_service.shutdown_vm(vm_config.vmid, node)
    elif action == "reboot":
        result = await proxmox_service.reboot_vm(vm_config.vmid, node)
    elif action == "reset":
        result = await proxmox_service.reset_vm(vm_config.vmid, node)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Power-Aktion fehlgeschlagen")
        )

    return PowerActionResult(**result)


# =============================================================================
# Templates Endpoints
# =============================================================================

class VMTemplate(BaseModel):
    """Schema für VM-Template"""
    vmid: int
    name: str
    node: str
    status: str = "stopped"
    maxdisk: int = 0
    maxmem: int = 0


@router.get("/templates", response_model=list[VMTemplate])
async def get_templates(
    current_user: User = Depends(get_current_active_user),
):
    """Liste aller verfügbaren VM-Templates (VMID >= 900000)"""
    templates = await proxmox_service.get_templates()
    return [VMTemplate(**t) for t in templates]


# =============================================================================
# Storage Endpoints
# =============================================================================

class StoragePool(BaseModel):
    """Schema für Storage-Pool"""
    id: str
    node: str
    type: str
    status: str = "unknown"
    total: int = 0
    used: int = 0
    available: int = 0
    content: list[str] = []


@router.get("/storage", response_model=list[StoragePool])
async def get_storage_pools(
    node: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Liste aller verfügbaren Storage-Pools für VM-Disks.

    Optional nach Node filtern.
    """
    storages = await proxmox_service.get_storage_pools(node)
    return [StoragePool(**s) for s in storages]


# =============================================================================
# Cloud-Init Profile Endpoints
# =============================================================================

class CloudInitProfileInfo(BaseModel):
    """Schema für Cloud-Init Profil-Information"""
    id: str
    name: str
    description: str
    packages: list[str] = []


@router.get("/cloud-init/profiles", response_model=list[CloudInitProfileInfo])
async def get_cloud_init_profiles(
    current_user: User = Depends(get_current_active_user),
):
    """Verfügbare Cloud-Init Profile"""
    from app.services.cloud_init_service import cloud_init_service
    profiles = cloud_init_service.get_profiles()
    return [CloudInitProfileInfo(**p) for p in profiles]


# =============================================================================
# Cluster Stats Endpoints
# =============================================================================

class NodeStats(BaseModel):
    """Schema für Node-Statistiken"""
    name: str
    status: str = "unknown"
    cpu_usage: float = 0.0
    cpu_total: int = 0
    memory_used: int = 0
    memory_total: int = 0
    memory_percent: float = 0.0
    uptime: int = 0


class ClusterStats(BaseModel):
    """Schema für Cluster-Statistiken"""
    nodes_online: int = 0
    nodes_total: int = 0
    cpu_total: int = 0
    cpu_usage_avg: float = 0.0
    memory_total: int = 0
    memory_used: int = 0
    memory_percent: float = 0.0
    vms_running: int = 0
    vms_total: int = 0
    nodes: list[NodeStats] = []


@router.get("/cluster/stats", response_model=ClusterStats)
async def get_cluster_stats(
    current_user: User = Depends(get_current_active_user),
):
    """Aggregierte Cluster-Statistiken (CPU, RAM, VMs)"""
    stats = await proxmox_service.get_cluster_stats()
    return ClusterStats(**stats)


@router.get("/nodes/stats", response_model=list[NodeStats])
async def get_node_stats(
    current_user: User = Depends(get_current_active_user),
):
    """CPU/RAM-Statistiken pro Node"""
    nodes = await proxmox_service.get_node_stats()
    return [NodeStats(**n) for n in nodes]


# =============================================================================
# Ansible Integration Endpoints
# =============================================================================

class AnsibleGroupInfo(BaseModel):
    """Schema für Ansible-Gruppen-Information"""
    value: str
    label: str


@router.get("/ansible-groups", response_model=list[AnsibleGroupInfo])
async def get_ansible_groups(
    current_user: User = Depends(get_current_active_user),
):
    """Liste aller verfügbaren Ansible-Inventar-Gruppen (dynamisch aus Inventory)"""
    groups = [
        AnsibleGroupInfo(value="", label="Nicht ins Inventory aufnehmen"),
    ]

    # Gruppen dynamisch aus dem echten Ansible-Inventory lesen
    inventory_groups = ansible_inventory_service.get_groups()

    for group_name in inventory_groups:
        # Label aus value generieren (underscore zu space, capitalize)
        label = group_name.replace("_", " ").title()
        groups.append(AnsibleGroupInfo(value=group_name, label=label))

    return groups


# =============================================================================
# VM Management Endpoints
# =============================================================================

@router.get("/vms", response_model=list[VMConfigListItem])
async def list_vms(
    current_user: User = Depends(get_current_active_user),
):
    """Liste aller VM-Konfigurationen mit Status aus Terraform State"""
    return await vm_deployment_service.get_vm_configs_with_status()


@router.get("/vms/{name}", response_model=VMConfigResponse)
async def get_vm(
    name: str,
    current_user: User = Depends(get_current_active_user),
):
    """Einzelne VM-Konfiguration"""
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")
    return vm


@router.post("/vms/validate", response_model=VMValidationResult)
async def validate_vm_config(
    config: VMConfigCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Validiert eine VM-Konfiguration ohne sie zu erstellen"""
    return await vm_deployment_service.validate_config(config)


@router.post("/vms/preview", response_model=TerraformPreview)
async def preview_vm_config(
    config: VMConfigCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Erstellt eine Vorschau der Terraform-Konfiguration"""
    try:
        return await vm_deployment_service.preview_config(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vms", response_model=VMConfigResponse)
async def create_vm(
    config: VMConfigCreate,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Neue VM-Konfiguration erstellen (nur Admin).

    Erstellt die Terraform-Datei und reserviert optional die IP in NetBox.
    Führt noch kein terraform apply aus!
    """
    try:
        return await vm_deployment_service.create_vm_config(config, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler: {str(e)}")


@router.post("/vms/{name}/plan")
async def plan_vm(
    name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Terraform Plan für eine VM ausführen (nur Admin).

    Zeigt was erstellt/geändert würde.
    """
    try:
        execution_id = await vm_deployment_service.plan_vm(name, current_user.id)
        return {"message": "Plan gestartet", "execution_id": execution_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler: {str(e)}")


class PostDeployPlaybook(BaseModel):
    """Schema für Post-Deploy Playbook"""
    name: str
    description: str = ""


@router.get("/post-deploy-playbooks", response_model=list[PostDeployPlaybook])
async def get_post_deploy_playbooks(
    current_user: User = Depends(get_current_active_user),
):
    """Liste verfügbarer Playbooks für Post-Deploy Provisioning"""
    from pathlib import Path
    from app.config import settings

    playbook_dir = Path(settings.ansible_playbook_dir)
    playbooks = []

    # Playbook-Dateien suchen (nur .yml/.yaml)
    for pattern in ["*.yml", "*.yaml"]:
        for playbook_file in playbook_dir.glob(pattern):
            name = playbook_file.stem  # Dateiname ohne Endung
            # Beschreibung aus erster Kommentarzeile extrahieren
            description = ""
            try:
                with open(playbook_file, "r") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#"):
                        description = first_line[1:].strip()
            except Exception:
                pass

            playbooks.append(PostDeployPlaybook(name=name, description=description))

    return sorted(playbooks, key=lambda p: p.name)


class PostDeployOptions(BaseModel):
    """Optionale Post-Deploy Parameter"""
    post_deploy_playbook: Optional[str] = None
    post_deploy_extra_vars: Optional[dict] = None
    wait_for_ssh: bool = True


@router.post("/vms/{name}/apply")
async def apply_vm(
    name: str,
    options: Optional[PostDeployOptions] = None,
    current_user: User = Depends(get_current_admin_user),
):
    """
    VM deployen (terraform apply) - nur Admin.

    Erstellt die VM tatsächlich in Proxmox.
    Prüft vorher ob die IP noch verfügbar ist (IP-Konflikt-Erkennung).

    Optional: Post-Deploy Playbook ausführen nach erfolgreichem Deploy.
    """
    # VM-Konfiguration holen
    vm_config = vm_deployment_service.get_vm_config(name)
    if not vm_config:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    # IP-Konflikt-Check: Ist die IP noch verfügbar?
    try:
        is_available = await netbox_service.check_ip_available(vm_config.ip_address)
        if not is_available:
            raise HTTPException(
                status_code=409,  # Conflict
                detail=f"IP {vm_config.ip_address} wurde inzwischen belegt"
            )
    except HTTPException:
        raise
    except Exception as e:
        # NetBox-Fehler als Warnung loggen, aber nicht blockieren
        pass

    try:
        execution_id = await vm_deployment_service.deploy_vm(
            name=name,
            user_id=current_user.id,
            post_deploy_playbook=options.post_deploy_playbook if options else None,
            post_deploy_extra_vars=options.post_deploy_extra_vars if options else None,
            wait_for_ssh=options.wait_for_ssh if options else True,
        )
        return {"message": "Deploy gestartet", "execution_id": execution_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler: {str(e)}")


@router.post("/vms/{name}/destroy")
async def destroy_vm(
    name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    VM zerstören (terraform destroy) - nur Admin.

    Löscht die VM aus Proxmox.
    """
    try:
        execution_id = await vm_deployment_service.destroy_vm(name, current_user.id)
        return {"message": "Destroy gestartet", "execution_id": execution_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler: {str(e)}")


@router.post("/vms/{name}/release-ip")
async def release_vm_ip(
    name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    IP einer VM in NetBox freigeben (nur Admin).

    Gibt die IP-Adresse frei ohne die VM oder TF-Datei zu löschen.
    Nützlich wenn eine VM nie deployed wurde und die IP wieder freigegeben werden soll.
    """
    vm_config = vm_deployment_service.get_vm_config(name)
    if not vm_config:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    try:
        success = await netbox_service.release_ip(vm_config.ip_address)
        if success:
            return {"message": f"IP {vm_config.ip_address} freigegeben"}
        else:
            return {"message": f"IP {vm_config.ip_address} war nicht in NetBox reserviert"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Freigabe fehlgeschlagen: {str(e)}")


@router.delete("/vms/{name}")
async def delete_vm_config(
    name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    VM-Konfiguration löschen (nur Admin).

    Löscht nur die Terraform-Datei, nicht die VM selbst!
    Zuerst terraform destroy ausführen falls VM deployed ist.
    """
    success = vm_deployment_service.delete_vm_config(name)
    if success:
        return {"message": f"VM-Konfiguration '{name}' gelöscht"}
    else:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")


# =============================================================================
# Complete VM Deletion (alle Systeme)
# =============================================================================

class VMDeleteCompleteResult(BaseModel):
    """Ergebnis der vollständigen VM-Löschung"""
    success: bool
    vm_name: str
    message: str
    proxmox: dict
    netbox_vm: dict
    netbox_ip: dict
    terraform_state: dict
    terraform_file: dict
    ansible_inventory: dict


@router.delete("/vms/{name}/complete", response_model=VMDeleteCompleteResult)
async def delete_vm_complete(
    name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    VM vollständig löschen (nur Admin).

    Löscht die VM aus allen Systemen:
    - Proxmox (VM selbst)
    - NetBox (VM-Eintrag + IP-Adresse)
    - Terraform State
    - Terraform-Datei (.tf)
    - Ansible Inventory

    Gibt detailliertes Ergebnis pro System zurück.
    """
    try:
        result = await vm_deployment_service.delete_vm_complete(name, current_user.id)
        return VMDeleteCompleteResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Löschung fehlgeschlagen: {str(e)}")


# =============================================================================
# Batch Operations - Schemas
# =============================================================================

class BatchOperation(BaseModel):
    """Request-Schema für Batch-Operationen"""
    vm_names: List[str]


class BatchFailedItem(BaseModel):
    """Fehlgeschlagene VM in Batch-Operation"""
    name: str
    error: str


class BatchResult(BaseModel):
    """Response-Schema für Batch-Operationen"""
    successful: List[str]
    failed: List[BatchFailedItem]


# =============================================================================
# Batch Operations - Endpoints
# =============================================================================

@router.post("/vms/batch/plan", response_model=BatchResult)
async def batch_plan(
    batch: BatchOperation,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Terraform Plan für mehrere VMs ausführen (nur Admin).

    Startet parallel Plan-Operationen für alle angegebenen VMs.
    """
    successful = []
    failed = []

    for name in batch.vm_names:
        try:
            await vm_deployment_service.plan_vm(name, current_user.id)
            successful.append(name)
        except Exception as e:
            failed.append(BatchFailedItem(name=name, error=str(e)))

    return BatchResult(successful=successful, failed=failed)


@router.post("/vms/batch/apply", response_model=BatchResult)
async def batch_apply(
    batch: BatchOperation,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Mehrere VMs gleichzeitig deployen (nur Admin).

    Prüft vor jedem Deploy ob die IP noch verfügbar ist.
    """
    successful = []
    failed = []

    for name in batch.vm_names:
        try:
            # VM-Konfiguration holen und IP-Konflikt prüfen
            vm_config = vm_deployment_service.get_vm_config(name)
            if not vm_config:
                failed.append(BatchFailedItem(name=name, error=f"VM '{name}' nicht gefunden"))
                continue

            # IP-Konflikt-Check
            try:
                is_available = await netbox_service.check_ip_available(vm_config.ip_address)
                if not is_available:
                    failed.append(BatchFailedItem(
                        name=name,
                        error=f"IP {vm_config.ip_address} belegt"
                    ))
                    continue
            except Exception:
                # NetBox-Fehler ignorieren, Deploy trotzdem versuchen
                pass

            await vm_deployment_service.deploy_vm(name, current_user.id)
            successful.append(name)
        except Exception as e:
            failed.append(BatchFailedItem(name=name, error=str(e)))

    return BatchResult(successful=successful, failed=failed)


@router.post("/vms/batch/destroy", response_model=BatchResult)
async def batch_destroy(
    batch: BatchOperation,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Mehrere VMs gleichzeitig zerstören (nur Admin).

    Gibt bei erfolgreichem Destroy automatisch die IPs in NetBox frei.
    """
    successful = []
    failed = []

    for name in batch.vm_names:
        try:
            await vm_deployment_service.destroy_vm(name, current_user.id)
            successful.append(name)
        except Exception as e:
            failed.append(BatchFailedItem(name=name, error=str(e)))

    return BatchResult(successful=successful, failed=failed)


# =============================================================================
# VM Cloning Endpoints
# =============================================================================

class VMCloneRequest(BaseModel):
    """Request für VM-Klonen"""
    target_name: str = Field(..., min_length=1, max_length=63, description="Name des Klons")
    full_clone: bool = Field(default=True, description="Full Clone (True) oder Linked Clone (False)")


class VMCloneResult(BaseModel):
    """Ergebnis des Klon-Vorgangs"""
    success: bool
    message: str
    target_name: Optional[str] = None
    target_vmid: Optional[int] = None
    target_ip: Optional[str] = None


@router.post("/vms/{name}/clone", response_model=VMCloneResult)
async def clone_vm(
    name: str,
    request: VMCloneRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Klont eine bestehende VM.

    Erstellt einen Klon der Quell-VM mit neuer IP-Adresse und VMID.
    Nur für deployed VMs verfügbar.
    """
    try:
        result = await vm_deployment_service.clone_vm(
            source_name=name,
            target_name=request.target_name,
            full_clone=request.full_clone,
            user_id=current_user.id,
        )
        return VMCloneResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Klonen fehlgeschlagen: {str(e)}")


# =============================================================================
# Migration Endpoints
# =============================================================================

class MigrationStartResult(BaseModel):
    """Ergebnis des Migration-Starts"""
    success: bool
    message: str
    vm_name: str
    vmid: int
    source_node: str
    target_node: str
    upid: Optional[str] = None
    was_running: bool = False
    error: Optional[str] = None


class MigrationStatusResult(BaseModel):
    """Status einer laufenden Migration"""
    success: bool
    finished: bool
    task_success: Optional[bool] = None
    status: str = "unknown"
    exitstatus: Optional[str] = None
    error: Optional[str] = None


class MigrationCompleteRequest(BaseModel):
    """Request zum Abschließen einer Migration"""
    target_node: str
    was_running: bool = False


@router.post("/vms/{name}/migrate/start", response_model=MigrationStartResult)
async def start_migration(
    name: str,
    request: VMMigrateRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Startet eine VM-Migration (asynchron).

    Gibt sofort die UPID zurück. Frontend pollt dann den Status.
    """
    # 1. VM-Konfiguration prüfen
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    # 2. VM muss deployed sein
    deployed_modules = await vm_deployment_service.terraform_service.get_deployed_modules()
    module_name = vm_deployment_service._sanitize_module_name(name)
    if module_name not in deployed_modules:
        raise HTTPException(status_code=400, detail="VM muss deployed sein um migriert zu werden")

    # 3. Prüfen ob VM in Proxmox existiert
    proxmox_status = await proxmox_service.check_vm_exists(vm.vmid)
    if not proxmox_status.get("exists"):
        raise HTTPException(status_code=400, detail="VM existiert nicht in Proxmox")

    source_node = proxmox_status.get("node")
    target_node = request.target_node

    if source_node == target_node:
        raise HTTPException(status_code=400, detail="VM befindet sich bereits auf diesem Node")

    # 4. Migration starten (non-blocking)
    result = await proxmox_service.start_migration(
        vmid=vm.vmid,
        source_node=source_node,
        target_node=target_node,
    )

    if not result.get("success"):
        return MigrationStartResult(
            success=False,
            message=f"Migration konnte nicht gestartet werden: {result.get('error')}",
            vm_name=name,
            vmid=vm.vmid,
            source_node=source_node,
            target_node=target_node,
            error=result.get("error"),
        )

    return MigrationStartResult(
        success=True,
        message="Migration gestartet",
        vm_name=name,
        vmid=vm.vmid,
        source_node=source_node,
        target_node=target_node,
        upid=result.get("upid"),
        was_running=result.get("was_running", False),
    )


@router.get("/tasks/{node}/{upid:path}/status", response_model=MigrationStatusResult)
async def get_task_status(
    node: str,
    upid: str,
    current_user: User = Depends(get_current_active_user),
):
    """Holt den Status eines Proxmox-Tasks."""
    result = await proxmox_service.get_task_status(node, upid)

    if not result.get("success"):
        return MigrationStatusResult(
            success=False,
            finished=False,
            error=result.get("error"),
        )

    return MigrationStatusResult(
        success=True,
        finished=result.get("finished", False),
        task_success=result.get("task_success"),
        status=result.get("status", "unknown"),
        exitstatus=result.get("exitstatus"),
    )


@router.post("/vms/{name}/migrate/complete", response_model=VMMigrateResult)
async def complete_migration(
    name: str,
    request: MigrationCompleteRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Schließt eine Migration ab (nach erfolgreichem Task).

    - Startet VM neu (wenn sie vorher lief)
    - Aktualisiert TF-Datei
    - Erstellt History-Eintrag
    """
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    target_node = request.target_node

    # 1. VM neu starten wenn sie vorher lief
    restarted = False
    if request.was_running:
        start_result = await proxmox_service.start_vm(vm.vmid, target_node)
        restarted = start_result.get("success", False)

    # 2. TF-Datei aktualisieren
    tf_update = vm_deployment_service.update_target_node(name, target_node)

    # 3. Aktuellen Source-Node ermitteln (für History)
    source_node = vm.target_node  # Alter Wert aus TF

    # 4. History-Eintrag
    try:
        await vm_history_service.log_change(
            vm_name=name,
            action="migrated",
            user_id=current_user.id,
            metadata={
                "vmid": vm.vmid,
                "source_node": source_node,
                "target_node": target_node,
                "was_running": request.was_running,
                "restarted": restarted,
            },
        )
    except Exception as e:
        print(f"Warnung: History-Eintrag konnte nicht erstellt werden: {e}")

    return VMMigrateResult(
        success=True,
        message=f"VM '{name}' erfolgreich nach {target_node} migriert",
        vm_name=name,
        source_node=source_node,
        target_node=target_node,
        vmid=vm.vmid,
        was_running=request.was_running,
        restarted=restarted,
        tf_updated=tf_update.get("success", False),
    )


# Legacy-Endpoint für Kompatibilität (blockierend)
@router.post("/vms/{name}/migrate", response_model=VMMigrateResult)
async def migrate_vm(
    name: str,
    request: VMMigrateRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Migriert eine VM (blockierend, wartet auf Abschluss).

    HINWEIS: Für lange Migrationen besser /migrate/start verwenden.
    """
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    deployed_modules = await vm_deployment_service.terraform_service.get_deployed_modules()
    module_name = vm_deployment_service._sanitize_module_name(name)
    if module_name not in deployed_modules:
        raise HTTPException(status_code=400, detail="VM muss deployed sein um migriert zu werden")

    proxmox_status = await proxmox_service.check_vm_exists(vm.vmid)
    if not proxmox_status.get("exists"):
        raise HTTPException(status_code=400, detail="VM existiert nicht in Proxmox")

    source_node = proxmox_status.get("node")
    target_node = request.target_node

    if source_node == target_node:
        raise HTTPException(status_code=400, detail="VM befindet sich bereits auf diesem Node")

    migrate_result = await proxmox_service.migrate_vm(
        vmid=vm.vmid,
        source_node=source_node,
        target_node=target_node,
        restart_after=True,
    )

    if not migrate_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Migration fehlgeschlagen: {migrate_result.get('error')}",
        )

    tf_update = vm_deployment_service.update_target_node(name, target_node)

    try:
        await vm_history_service.log_change(
            vm_name=name,
            action="migrated",
            user_id=current_user.id,
            metadata={
                "vmid": vm.vmid,
                "source_node": source_node,
                "target_node": target_node,
                "was_running": migrate_result.get("was_running"),
                "restarted": migrate_result.get("restarted"),
            },
        )
    except Exception as e:
        print(f"Warnung: History-Eintrag konnte nicht erstellt werden: {e}")

    return VMMigrateResult(
        success=True,
        message=f"VM '{name}' erfolgreich von {source_node} nach {target_node} migriert",
        vm_name=name,
        source_node=source_node,
        target_node=target_node,
        vmid=vm.vmid,
        upid=migrate_result.get("upid"),
        was_running=migrate_result.get("was_running"),
        restarted=migrate_result.get("restarted"),
        tf_updated=tf_update.get("success", False),
        warning=migrate_result.get("warning"),
    )


# =============================================================================
# Snapshot Endpoints
# =============================================================================

class VMSnapshot(BaseModel):
    """Schema für VM-Snapshot"""
    name: str
    description: str = ""
    snaptime: Optional[int] = None
    parent: Optional[str] = None
    vmstate: bool = False


class SnapshotCreateRequest(BaseModel):
    """Request für Snapshot-Erstellung"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=40,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="Snapshot-Name (Buchstaben, Zahlen, Unterstriche; muss mit Buchstabe beginnen)"
    )
    description: str = Field(default="", max_length=255, description="Beschreibung")
    include_ram: bool = Field(default=False, description="RAM-State mit sichern")


class SnapshotResult(BaseModel):
    """Ergebnis einer Snapshot-Operation"""
    success: bool
    message: str


# =============================================================================
# Frontend-URL Endpoint
# =============================================================================


@router.patch("/vms/{name}/frontend-url", response_model=VMFrontendUrlResult)
async def update_frontend_url(
    name: str,
    request: VMFrontendUrlUpdate,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Aktualisiert die Frontend-URL einer VM (nur Admin).

    Die URL wird als Kommentar in der TF-Datei gespeichert.
    Null/leerer String entfernt die URL.
    """
    # VM existiert?
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    # URL aktualisieren
    result = vm_deployment_service.update_frontend_url(name, request.frontend_url)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Frontend-URL konnte nicht aktualisiert werden"),
        )

    return VMFrontendUrlResult(
        success=True,
        message=result.get("message", "Frontend-URL aktualisiert"),
        vm_name=name,
        frontend_url=request.frontend_url,
    )


@router.get("/vms/{name}/snapshots", response_model=list[VMSnapshot])
async def list_snapshots(
    name: str,
    current_user: User = Depends(get_current_active_user),
):
    """Liste aller Snapshots einer VM"""
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    snapshots = await proxmox_service.list_snapshots(vm.vmid, vm.target_node)
    return [VMSnapshot(**s) for s in snapshots]


@router.post("/vms/{name}/snapshots", response_model=SnapshotResult)
async def create_snapshot(
    name: str,
    request: SnapshotCreateRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Erstellt einen neuen Snapshot"""
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    result = await proxmox_service.create_snapshot(
        vmid=vm.vmid,
        node=vm.target_node,
        name=request.name,
        description=request.description,
        include_ram=request.include_ram,
    )

    if result.get("success"):
        return SnapshotResult(success=True, message=f"Snapshot '{request.name}' wird erstellt")
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Snapshot-Erstellung fehlgeschlagen"))


@router.delete("/vms/{name}/snapshots/{snapshot_name}", response_model=SnapshotResult)
async def delete_snapshot(
    name: str,
    snapshot_name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """Löscht einen Snapshot (nur Admin)"""
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    result = await proxmox_service.delete_snapshot(vm.vmid, vm.target_node, snapshot_name)

    if result.get("success"):
        return SnapshotResult(success=True, message=f"Snapshot '{snapshot_name}' wird gelöscht")
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Snapshot-Löschung fehlgeschlagen"))


@router.post("/vms/{name}/snapshots/{snapshot_name}/rollback", response_model=SnapshotResult)
async def rollback_snapshot(
    name: str,
    snapshot_name: str,
    current_user: User = Depends(get_current_admin_user),
):
    """Rollt eine VM auf einen Snapshot zurück (nur Admin)"""
    vm = vm_deployment_service.get_vm_config(name)
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{name}' nicht gefunden")

    result = await proxmox_service.rollback_snapshot(vm.vmid, vm.target_node, snapshot_name)

    if result.get("success"):
        return SnapshotResult(success=True, message=f"Rollback auf '{snapshot_name}' wird ausgeführt")
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Rollback fehlgeschlagen"))


# =============================================================================
# Terraform State Endpoints
# =============================================================================

from app.services.terraform_service import TerraformService

terraform_service = TerraformService()


class StateResource(BaseModel):
    """Schema für Terraform State Ressource"""
    address: str
    module: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None


class StateResourceDetail(BaseModel):
    """Schema für detaillierte Ressourcen-Informationen"""
    success: bool
    address: Optional[str] = None
    data: Optional[dict] = None
    raw: Optional[str] = None
    error: Optional[str] = None


class StateOperationResult(BaseModel):
    """Schema für State-Operationen"""
    success: bool
    message: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


@router.get("/state", response_model=list[StateResource])
async def list_state_resources(
    current_user: User = Depends(get_current_active_user),
):
    """
    Liste aller Ressourcen im Terraform State.

    Gibt alle verwalteten Ressourcen mit Modul, Typ und Name zurück.
    """
    resources = await terraform_service.state_list()

    result = []
    for address in resources:
        # Adresse parsen: module.vm_test.proxmox_virtual_environment_vm.vm
        parts = address.split(".")
        module = None
        resource_type = None
        resource_name = None

        if address.startswith("module."):
            # module.vm_test.resource_type.resource_name
            if len(parts) >= 2:
                module = parts[1]
            if len(parts) >= 3:
                resource_type = parts[2]
            if len(parts) >= 4:
                resource_name = parts[3]
        else:
            # resource_type.resource_name
            if len(parts) >= 1:
                resource_type = parts[0]
            if len(parts) >= 2:
                resource_name = parts[1]

        result.append(StateResource(
            address=address,
            module=module,
            type=resource_type,
            name=resource_name,
        ))

    return result


@router.get("/state/{address:path}", response_model=StateResourceDetail)
async def show_state_resource(
    address: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Details einer Ressource im Terraform State.

    Gibt die vollständige Konfiguration und Attribute einer Ressource zurück.
    """
    result = await terraform_service.state_show(address)
    return StateResourceDetail(**result)


@router.delete("/state/{address:path}", response_model=StateOperationResult)
async def remove_state_resource(
    address: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Entfernt eine Ressource aus dem Terraform State (nur Admin).

    Die Ressource wird nur aus dem State entfernt, nicht aus der Infrastruktur!
    Nützlich für manuelle Bereinigung oder Import-Vorbereitung.
    """
    result = await terraform_service.state_remove(address)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "State-Entfernung fehlgeschlagen"))

    return StateOperationResult(**result)


@router.post("/state/refresh", response_model=StateOperationResult)
async def refresh_state(
    current_user: User = Depends(get_current_admin_user),
):
    """
    Aktualisiert den Terraform State (nur Admin).

    Synchronisiert den State mit dem aktuellen Infrastruktur-Zustand.
    """
    result = await terraform_service.state_refresh()

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "State-Refresh fehlgeschlagen"))

    return StateOperationResult(**result)


# =============================================================================
# VM Import Endpoints
# =============================================================================

class ProxmoxVMInfo(BaseModel):
    """Schema für Proxmox VM-Information"""
    vmid: int
    name: str
    node: str
    status: str = "unknown"
    maxcpu: int = 1
    maxmem: int = 0
    maxdisk: int = 0


class VMImportRequest(BaseModel):
    """Request für VM-Import"""
    vmid: int = Field(..., description="Proxmox VM-ID")
    node: str = Field(..., description="Proxmox-Node")
    vm_name: str = Field(..., min_length=1, max_length=63, description="Neuer VM-Name")
    ansible_group: str = Field(default="", description="Ansible-Inventar-Gruppe")
    register_netbox: bool = Field(default=True, description="IP in NetBox registrieren")


class VMImportResult(BaseModel):
    """Ergebnis des VM-Imports"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    vm_name: Optional[str] = None
    vmid: Optional[int] = None
    ip_address: Optional[str] = None
    node: Optional[str] = None
    cores: Optional[int] = None
    memory_gb: Optional[int] = None
    disk_size_gb: Optional[int] = None


@router.get("/proxmox/vms", response_model=list[ProxmoxVMInfo])
async def list_proxmox_vms(
    current_user: User = Depends(get_current_active_user),
):
    """
    Liste aller VMs im Proxmox-Cluster.

    Gibt alle VMs zurück (inkl. Templates und bereits verwaltete).
    """
    vms = await proxmox_service.get_all_vms()
    return [ProxmoxVMInfo(**vm) for vm in vms]


@router.get("/proxmox/vms/unmanaged", response_model=list[ProxmoxVMInfo])
async def list_unmanaged_vms(
    current_user: User = Depends(get_current_active_user),
):
    """
    Liste aller VMs die nicht von Terraform verwaltet werden.

    Filtert:
    - Templates (VMID >= 900000)
    - Bereits verwaltete VMs (im Terraform State oder als TF-Datei)
    """
    vms = await vm_deployment_service.get_unmanaged_vms()
    return [ProxmoxVMInfo(**vm) for vm in vms]


@router.post("/import", response_model=VMImportResult)
async def import_vm(
    request: VMImportRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Importiert eine existierende Proxmox-VM in die Terraform-Verwaltung (nur Admin).

    Schritte:
    1. VM-Konfiguration aus Proxmox lesen
    2. TF-Datei generieren
    3. terraform import ausführen
    4. Optional: In Ansible-Inventory eintragen
    5. Optional: IP in NetBox registrieren
    """
    result = await vm_deployment_service.import_existing_vm(
        vmid=request.vmid,
        node=request.node,
        vm_name=request.vm_name,
        ansible_group=request.ansible_group,
        register_netbox=request.register_netbox,
        user_id=current_user.id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Import fehlgeschlagen"))

    return VMImportResult(**result)


# =============================================================================
# VM History Endpoints
# =============================================================================

from app.services.vm_history_service import vm_history_service


class VMHistoryEntry(BaseModel):
    """Schema für VM-History-Eintrag"""
    id: int
    vm_name: str
    action: str
    user_id: int
    execution_id: Optional[int] = None
    created_at: Optional[str] = None
    metadata: dict = {}
    has_config_diff: bool = False


class VMHistoryDetail(BaseModel):
    """Schema für detaillierten VM-History-Eintrag"""
    id: int
    vm_name: str
    action: str
    user_id: int
    execution_id: Optional[int] = None
    created_at: Optional[str] = None
    metadata: dict = {}
    tf_config_before: Optional[str] = None
    tf_config_after: Optional[str] = None


class RollbackResult(BaseModel):
    """Schema für Rollback-Ergebnis"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    vm_name: Optional[str] = None
    rollback_history_id: Optional[int] = None


@router.get("/history", response_model=list[VMHistoryEntry])
async def get_global_history(
    limit: int = 100,
    action: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """
    Globaler VM-Änderungsverlauf.

    Zeigt die letzten Änderungen an allen VMs.
    Optional nach Aktion filtern (created, deployed, destroyed, imported, config_changed, rollback).
    """
    entries = await vm_history_service.get_global_history(
        limit=limit,
        action_filter=action,
    )
    return [VMHistoryEntry(**e) for e in entries]


@router.get("/vms/{name}/history", response_model=list[VMHistoryEntry])
async def get_vm_history(
    name: str,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
):
    """
    Änderungsverlauf einer bestimmten VM.

    Zeigt alle Änderungen an der VM in chronologischer Reihenfolge.
    """
    entries = await vm_history_service.get_vm_history(
        vm_name=name,
        limit=limit,
    )
    return [VMHistoryEntry(**e) for e in entries]


@router.get("/history/{history_id}", response_model=VMHistoryDetail)
async def get_history_entry(
    history_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    Details eines History-Eintrags inkl. TF-Konfigurationen.

    Enthält die vollständigen Terraform-Konfigurationen vor und nach der Änderung.
    """
    entry = await vm_history_service.get_history_entry(history_id)

    if not entry:
        raise HTTPException(status_code=404, detail="History-Eintrag nicht gefunden")

    return VMHistoryDetail(**entry)


@router.post("/history/{history_id}/rollback", response_model=RollbackResult)
async def rollback_to_history(
    history_id: int,
    current_user: User = Depends(get_current_admin_user),
):
    """
    Rollt eine VM auf einen früheren Konfigurationsstand zurück (nur Admin).

    Setzt die Terraform-Konfiguration auf den Stand vor der angegebenen Änderung.
    Die VM wird nicht automatisch neu deployed - dafür muss terraform apply ausgeführt werden.
    """
    result = await vm_history_service.rollback_to_entry(
        history_id=history_id,
        user_id=current_user.id,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Rollback fehlgeschlagen"))

    return RollbackResult(**result)
