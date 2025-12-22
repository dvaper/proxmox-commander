"""
VLAN Configuration - Zentrale VLAN-Konfiguration für das Homelab

Alle VLAN-bezogenen Mappings werden hier verwaltet:
- VLAN-ID zu Name
- VLAN-ID zu Netzwerk-Prefix
- VLAN-ID zu Bridge
- VLAN-ID zu Gateway
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class VLANInfo:
    """Vollständige Information zu einem VLAN"""
    id: int
    name: str
    prefix: str
    bridge: str
    gateway: str


# Zentrale VLAN-Konfiguration
VLANS: Dict[int, VLANInfo] = {
    2: VLANInfo(
        id=2,
        name="LAN",
        prefix="192.168.2.0/24",
        bridge="vmbr2",
        gateway="192.168.2.1",
    ),
    20: VLANInfo(
        id=20,
        name="LAB",
        prefix="192.168.20.0/25",
        bridge="vmbr20",
        gateway="192.168.20.1",
    ),
    30: VLANInfo(
        id=30,
        name="IOT",
        prefix="192.168.30.0/24",
        bridge="vmbr30",
        gateway="192.168.30.1",
    ),
    40: VLANInfo(
        id=40,
        name="DMZ",
        prefix="192.168.40.0/24",
        bridge="vmbr40",
        gateway="192.168.40.1",
    ),
    50: VLANInfo(
        id=50,
        name="GUEST",
        prefix="192.168.50.0/24",
        bridge="vmbr50",
        gateway="192.168.50.1",
    ),
    60: VLANInfo(
        id=60,
        name="SERVER",
        prefix="192.168.60.0/24",
        bridge="vmbr60",
        gateway="192.168.60.1",
    ),
    70: VLANInfo(
        id=70,
        name="CLUSTER",
        prefix="192.168.70.0/24",
        bridge="vmbr70",
        gateway="192.168.70.1",
    ),
    85: VLANInfo(
        id=85,
        name="AUTH",
        prefix="192.168.85.0/24",
        bridge="vmbr85",
        gateway="192.168.85.1",
    ),
    95: VLANInfo(
        id=95,
        name="BACKUP",
        prefix="192.168.95.0/24",
        bridge="vmbr95",
        gateway="192.168.95.1",
    ),
    99: VLANInfo(
        id=99,
        name="MGMT",
        prefix="192.168.99.0/24",
        bridge="vmbr99",
        gateway="192.168.99.1",
    ),
}

# Default VLAN für neue VMs
DEFAULT_VLAN = 60


def get_vlan(vlan_id: int) -> Optional[VLANInfo]:
    """Gibt VLAN-Info für eine VLAN-ID zurück"""
    return VLANS.get(vlan_id)


def get_bridge(vlan_id: int) -> str:
    """Gibt die Bridge für ein VLAN zurück"""
    vlan = VLANS.get(vlan_id)
    if vlan:
        return vlan.bridge
    return f"vmbr{vlan_id}"


def get_gateway(vlan_id: int) -> str:
    """Gibt das Gateway für ein VLAN zurück"""
    vlan = VLANS.get(vlan_id)
    if vlan:
        return vlan.gateway
    return f"192.168.{vlan_id}.1"


def get_prefix(vlan_id: int) -> Optional[str]:
    """Gibt das Netzwerk-Prefix für ein VLAN zurück"""
    vlan = VLANS.get(vlan_id)
    if vlan:
        return vlan.prefix
    return None


def get_name(vlan_id: int) -> str:
    """Gibt den Namen für ein VLAN zurück"""
    vlan = VLANS.get(vlan_id)
    if vlan:
        return vlan.name
    return f"VLAN{vlan_id}"


def get_all_vlans() -> list[dict]:
    """Gibt alle VLANs als Liste zurück (für API-Responses)"""
    return sorted(
        [
            {
                "id": v.id,
                "name": v.name,
                "prefix": v.prefix,
                "bridge": v.bridge,
                "gateway": v.gateway,
            }
            for v in VLANS.values()
        ],
        key=lambda x: x["id"],
    )


def vlan_id_from_ip(ip_address: str) -> int:
    """Extrahiert VLAN-ID aus IP-Adresse (3. Oktett)"""
    try:
        octets = ip_address.split(".")
        return int(octets[2])
    except (IndexError, ValueError):
        return DEFAULT_VLAN
