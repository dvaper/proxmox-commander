"""
VM Schemas - Pydantic Modelle für VM-Deployment
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum
import re

from app.schemas.cloud_init import CloudInitProfile


class VMStatus(str, Enum):
    """Status einer VM-Konfiguration"""
    # Deployment-Status
    PLANNED = "planned"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    DESTROYING = "destroying"
    # Proxmox Live-Status (für deployed VMs)
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"


class AnsibleGroup(str, Enum):
    """Verfügbare Ansible-Inventar-Gruppen für neue VMs"""
    NONE = ""  # Nicht ins Inventory aufnehmen
    GITLAB_SERVERS = "gitlab_servers"
    DNS = "dns"
    PROXY = "proxy"
    DOCKER_HOSTS = "docker_hosts"
    DOCUMENTATION = "documentation"
    MEDIA = "media"
    DEVELOPMENT = "development"
    MONITORING = "monitoring"
    SECURITY = "security"
    APPS = "apps"
    LMS = "lms"
    WEBAPPS = "webapps"
    MISC = "misc"


class ProxmoxNode(str, Enum):
    """Verfügbare Proxmox-Nodes"""
    GANDALF = "gandalf"
    FRODO = "frodo"
    BOROMIR = "boromir"
    ARAGORN = "aragorn"
    LEGOLAS = "legolas"
    GIMLI = "gimli"


# Node-Informationen
PROXMOX_NODES = {
    "gandalf": {"ip": "192.168.60.10", "cpus": 32, "ram_gb": 92},
    "frodo": {"ip": "192.168.60.11", "cpus": 32, "ram_gb": 92},
    "boromir": {"ip": "192.168.60.12", "cpus": 20, "ram_gb": 63},
    "aragorn": {"ip": "192.168.60.13", "cpus": 16, "ram_gb": 62},
    "legolas": {"ip": "192.168.60.14", "cpus": 16, "ram_gb": 62},
    "gimli": {"ip": "192.168.60.15", "cpus": 16, "ram_gb": 31},
}


class VMConfigCreate(BaseModel):
    """Request-Schema für VM-Erstellung"""

    # Basis
    name: str = Field(..., min_length=1, max_length=63, description="VM-Name (Hostname)")
    description: str = Field(default="", max_length=500, description="Beschreibung")
    target_node: ProxmoxNode = Field(..., description="Proxmox-Node")

    # Template & Storage
    template_id: Optional[int] = Field(default=None, description="Template VMID (None = Standard 940001)")
    storage: str = Field(default="local-ssd", description="Storage-Pool für VM-Disk")

    # Ressourcen
    cores: int = Field(default=2, ge=1, le=32, description="CPU-Kerne")
    memory_gb: int = Field(default=2, ge=1, le=128, description="RAM in GB")
    disk_size_gb: int = Field(default=20, ge=10, le=1000, description="Disk-Größe in GB")

    # Netzwerk
    vlan: int = Field(default=60, description="VLAN-ID")
    ip_address: Optional[str] = Field(default=None, description="IP-Adresse (None = automatisch)")
    auto_reserve_ip: bool = Field(default=True, description="IP in NetBox reservieren")

    # Ansible Integration
    ansible_group: AnsibleGroup = Field(
        default=AnsibleGroup.NONE,
        description="Ansible-Inventar-Gruppe (leer = nicht ins Inventory aufnehmen)"
    )

    # Cloud-Init
    cloud_init_profile: CloudInitProfile = Field(
        default=CloudInitProfile.NONE,
        description="Cloud-Init Profil für automatische Konfiguration"
    )

    # Post-Deploy Provisioning
    post_deploy_playbook: Optional[str] = Field(
        default=None,
        description="Playbook das nach erfolgreichem Deploy ausgeführt wird"
    )
    post_deploy_extra_vars: Optional[dict] = Field(
        default=None,
        description="Extra-Variablen für das Post-Deploy Playbook"
    )
    wait_for_ssh: bool = Field(
        default=True,
        description="Vor Playbook-Ausführung auf SSH-Verbindung warten"
    )

    # Frontend-URL
    frontend_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL zur Web-Oberfläche der VM (z.B. https://app.example.com)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validiert VM-Namen (nur lowercase, Zahlen, Bindestriche)"""
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", v):
            raise ValueError(
                "Name muss mit Buchstabe/Zahl beginnen und enden, "
                "nur Kleinbuchstaben, Zahlen und Bindestriche erlaubt"
            )
        return v

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v):
        """Validiert IP-Adresse falls angegeben"""
        if v is None:
            return v
        pattern = r"^192\.168\.\d{1,3}\.\d{1,3}$"
        if not re.match(pattern, v):
            raise ValueError("Ungültige IP-Adresse (Format: 192.168.x.x)")
        return v


class VMConfigResponse(BaseModel):
    """Response-Schema für VM-Konfiguration"""
    name: str
    vmid: int
    ip_address: str
    target_node: str
    description: str
    cores: int
    memory_gb: int
    disk_size_gb: int
    vlan: int
    status: VMStatus
    tf_file: str
    execution_id: Optional[int] = None
    ansible_group: str = ""  # Ansible-Inventar-Gruppe
    frontend_url: Optional[str] = None  # URL zur Web-Oberfläche


class VMConfigListItem(BaseModel):
    """Kurzform für VM-Liste"""
    name: str
    vmid: int
    ip_address: str
    target_node: str
    cores: int
    memory_gb: int
    disk_size_gb: int
    status: VMStatus
    ansible_group: str = ""  # Ansible-Inventar-Gruppe
    frontend_url: Optional[str] = None  # URL zur Web-Oberfläche


class AvailableIP(BaseModel):
    """Schema für verfügbare IP-Adresse"""
    address: str
    vmid: int
    vlan: int


class VLANInfo(BaseModel):
    """Schema für VLAN-Information"""
    id: int
    name: str
    prefix: str


class UsedIP(BaseModel):
    """Schema für belegte IP-Adresse"""
    address: str
    description: str
    status: str
    dns_name: str


class NodeInfo(BaseModel):
    """Schema für Proxmox-Node Information"""
    name: str
    ip: str
    cpus: int
    ram_gb: int


class VMValidationResult(BaseModel):
    """Ergebnis der VM-Konfigurationsvalidierung"""
    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class TerraformPreview(BaseModel):
    """Preview des generierten Terraform-Codes"""
    filename: str
    content: str
    vmid: int
    ip_address: str


def calculate_vmid(ip_address: str) -> int:
    """
    Berechnet VMID aus IP-Adresse

    192.168.60.198 → 60198
    192.168.30.42  → 30042
    """
    octets = ip_address.split(".")
    vlan = int(octets[2])
    last_octet = int(octets[3])
    return vlan * 1000 + last_octet


# ========== VM Migration Schemas ==========


class VMMigrateRequest(BaseModel):
    """Request-Schema für VM-Migration"""
    target_node: str = Field(..., description="Ziel-Node für die Migration")

    @field_validator("target_node")
    @classmethod
    def validate_target_node(cls, v):
        """Validiert, dass der Ziel-Node existiert"""
        valid_nodes = [node.value for node in ProxmoxNode]
        if v not in valid_nodes:
            raise ValueError(f"Unbekannter Node: {v}. Gültige Nodes: {', '.join(valid_nodes)}")
        return v


class VMMigrateResult(BaseModel):
    """Response-Schema für VM-Migration"""
    success: bool
    message: str
    vm_name: str
    source_node: str
    target_node: str
    vmid: Optional[int] = None
    upid: Optional[str] = None
    was_running: Optional[bool] = None
    restarted: Optional[bool] = None
    tf_updated: Optional[bool] = None
    warning: Optional[str] = None


# ========== VM Frontend-URL Schemas ==========


class VMFrontendUrlUpdate(BaseModel):
    """Request-Schema für Frontend-URL Update"""
    frontend_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL zur Web-Oberfläche (None zum Entfernen)"
    )


class VMFrontendUrlResult(BaseModel):
    """Response-Schema für Frontend-URL Update"""
    success: bool
    message: str
    vm_name: str
    frontend_url: Optional[str] = None
