"""
NetBox Service - Integration mit NetBox IPAM für IP-Management

Alle VLANs und Prefixes werden dynamisch aus NetBox geladen.
Die Konfiguration erfolgt direkt in NetBox (nicht in der Applikation).
"""
import httpx
from typing import Optional
from app.config import settings


class NetBoxService:
    """Service für NetBox IPAM Integration"""

    def __init__(self):
        self.base_url = settings.netbox_url
        self.token = settings.netbox_token
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    def _check_token(self):
        """Prüft ob NetBox-Token konfiguriert ist"""
        if not self.token:
            raise ValueError("NetBox API Token nicht konfiguriert (NETBOX_TOKEN)")

    async def get_vlans(self) -> list[dict]:
        """
        Holt alle VLANs aus NetBox.

        Gibt VLANs zurück die einen zugehörigen Prefix haben.
        """
        self._check_token()

        async with httpx.AsyncClient() as client:
            # Alle Prefixes mit zugehörigen VLANs laden
            response = await client.get(
                f"{self.base_url}/api/ipam/prefixes/",
                params={"limit": 100},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            result = []
            for prefix_info in data["results"]:
                vlan_info = prefix_info.get("vlan")
                if vlan_info:
                    vlan_id = vlan_info.get("vid", 0)
                    prefix = prefix_info.get("prefix", "")

                    # Bridge und Gateway aus VLAN-ID ableiten
                    bridge = f"vmbr{vlan_id}"
                    gateway = self._gateway_from_prefix(prefix)

                    result.append({
                        "id": vlan_id,
                        "name": vlan_info.get("name", f"VLAN{vlan_id}"),
                        "prefix": prefix,
                        "bridge": bridge,
                        "gateway": gateway,
                    })

            return sorted(result, key=lambda x: x["id"])

    def _gateway_from_prefix(self, prefix: str) -> str:
        """Leitet Gateway aus Prefix ab (erstes IP im Subnet)"""
        if not prefix:
            return ""
        # prefix ist z.B. "192.168.60.0/24"
        network = prefix.split("/")[0]
        octets = network.split(".")
        if len(octets) == 4:
            octets[3] = "1"  # Gateway ist typischerweise .1
            return ".".join(octets)
        return ""

    async def get_prefix_for_vlan(self, vlan: int) -> Optional[str]:
        """Holt den Prefix aus NetBox für ein VLAN"""
        self._check_token()

        async with httpx.AsyncClient() as client:
            # Prefix mit VLAN-ID suchen
            response = await client.get(
                f"{self.base_url}/api/ipam/prefixes/",
                params={"vlan_vid": vlan},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if data["count"] > 0:
                return data["results"][0]["prefix"]
            return None

    async def get_prefix_id(self, vlan: int) -> Optional[int]:
        """Holt die Prefix-ID aus NetBox für ein VLAN"""
        self._check_token()

        async with httpx.AsyncClient() as client:
            # Prefix mit VLAN-ID suchen
            response = await client.get(
                f"{self.base_url}/api/ipam/prefixes/",
                params={"vlan_vid": vlan},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if data["count"] > 0:
                return data["results"][0]["id"]
            return None

    async def get_available_ips(self, vlan: int, limit: int = 10) -> list[dict]:
        """Holt freie IPs aus NetBox für ein VLAN"""
        self._check_token()

        prefix_id = await self.get_prefix_id(vlan)
        if not prefix_id:
            raise ValueError(f"Prefix für VLAN {vlan} nicht in NetBox gefunden")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/ipam/prefixes/{prefix_id}/available-ips/",
                params={"limit": limit},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            result = []
            for ip_info in data:
                address = ip_info["address"].split("/")[0]
                octets = address.split(".")
                vmid = int(octets[2]) * 1000 + int(octets[3])

                result.append({
                    "address": address,
                    "vmid": vmid,
                    "vlan": vlan,
                })

            return result

    async def get_used_ips(self, vlan: int, limit: int = 100) -> list[dict]:
        """Holt belegte IPs aus NetBox für ein VLAN"""
        self._check_token()

        prefix = await self.get_prefix_for_vlan(vlan)
        if not prefix:
            raise ValueError(f"VLAN {vlan} nicht in NetBox konfiguriert")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/ipam/ip-addresses/",
                params={"parent": prefix, "limit": limit},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            result = []
            for ip_info in data["results"]:
                address = ip_info["address"].split("/")[0]
                result.append({
                    "address": address,
                    "description": ip_info.get("description", ""),
                    "status": ip_info.get("status", {}).get("value", "active"),
                    "dns_name": ip_info.get("dns_name", ""),
                })

            return sorted(result, key=lambda x: int(x["address"].split(".")[-1]))

    async def reserve_ip(self, ip_address: str, description: str, dns_name: str = "") -> dict:
        """Reserviert eine IP-Adresse in NetBox"""
        self._check_token()

        async with httpx.AsyncClient() as client:
            # Prüfen ob IP bereits existiert
            check_response = await client.get(
                f"{self.base_url}/api/ipam/ip-addresses/",
                params={"address": ip_address},
                headers=self.headers,
                timeout=10.0,
            )
            check_response.raise_for_status()
            existing = check_response.json()

            if existing["count"] > 0:
                # IP existiert bereits - aktualisieren
                ip_id = existing["results"][0]["id"]
                response = await client.patch(
                    f"{self.base_url}/api/ipam/ip-addresses/{ip_id}/",
                    json={
                        "description": description,
                        "dns_name": dns_name,
                        "status": "reserved",
                    },
                    headers=self.headers,
                    timeout=10.0,
                )
            else:
                # Neue IP erstellen
                response = await client.post(
                    f"{self.base_url}/api/ipam/ip-addresses/",
                    json={
                        "address": f"{ip_address}/24",
                        "description": description,
                        "dns_name": dns_name,
                        "status": "reserved",
                    },
                    headers=self.headers,
                    timeout=10.0,
                )

            response.raise_for_status()
            return response.json()

    async def activate_ip(self, ip_address: str) -> dict:
        """Setzt IP-Status auf 'active' (nach erfolgreichem Deploy)"""
        self._check_token()

        async with httpx.AsyncClient() as client:
            # IP finden
            check_response = await client.get(
                f"{self.base_url}/api/ipam/ip-addresses/",
                params={"address": ip_address},
                headers=self.headers,
                timeout=10.0,
            )
            check_response.raise_for_status()
            existing = check_response.json()

            if existing["count"] == 0:
                raise ValueError(f"IP {ip_address} nicht in NetBox gefunden")

            ip_id = existing["results"][0]["id"]

            # Status auf active setzen
            response = await client.patch(
                f"{self.base_url}/api/ipam/ip-addresses/{ip_id}/",
                json={"status": "active"},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def release_ip(self, ip_address: str) -> bool:
        """Gibt eine IP-Adresse frei (löscht sie aus NetBox)"""
        self._check_token()

        async with httpx.AsyncClient() as client:
            # IP finden
            check_response = await client.get(
                f"{self.base_url}/api/ipam/ip-addresses/",
                params={"address": ip_address},
                headers=self.headers,
                timeout=10.0,
            )
            check_response.raise_for_status()
            existing = check_response.json()

            if existing["count"] == 0:
                return False

            ip_id = existing["results"][0]["id"]

            # IP löschen
            response = await client.delete(
                f"{self.base_url}/api/ipam/ip-addresses/{ip_id}/",
                headers=self.headers,
                timeout=10.0,
            )
            return response.status_code == 204

    async def check_ip_available(self, ip_address: str) -> bool:
        """Prüft ob eine IP-Adresse verfügbar ist"""
        self._check_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/ipam/ip-addresses/",
                params={"address": ip_address},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            return data["count"] == 0

    async def delete_vm(self, name: str) -> bool:
        """
        Löscht eine VM aus NetBox (virtualization/virtual-machines).

        Args:
            name: Name der VM

        Returns:
            True bei Erfolg, False wenn VM nicht gefunden
        """
        self._check_token()

        async with httpx.AsyncClient() as client:
            # VM finden
            response = await client.get(
                f"{self.base_url}/api/virtualization/virtual-machines/",
                params={"name": name},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            if data["count"] == 0:
                return False

            vm_id = data["results"][0]["id"]

            # VM löschen
            delete_response = await client.delete(
                f"{self.base_url}/api/virtualization/virtual-machines/{vm_id}/",
                headers=self.headers,
                timeout=10.0,
            )
            return delete_response.status_code == 204

    async def delete_vm_and_ip(self, name: str, ip_address: str) -> dict:
        """
        Löscht eine VM und deren IP aus NetBox.

        Args:
            name: Name der VM
            ip_address: IP-Adresse der VM

        Returns:
            dict mit vm_deleted und ip_deleted Status
        """
        vm_deleted = False
        ip_deleted = False

        try:
            vm_deleted = await self.delete_vm(name)
        except Exception:
            pass

        try:
            ip_deleted = await self.release_ip(ip_address)
        except Exception:
            pass

        return {
            "vm_deleted": vm_deleted,
            "ip_deleted": ip_deleted,
        }

    async def check_ipam_status(self) -> dict:
        """
        Prüft den IPAM-Status in NetBox.

        Gibt zurück ob Prefixes konfiguriert sind.
        Ohne Prefixes können keine freien IPs abgefragt werden.

        Returns:
            dict mit Status-Informationen
        """
        self._check_token()

        result = {
            "configured": False,
            "prefixes_count": 0,
            "vlans_count": 0,
            "netbox_url": self.base_url,
        }

        try:
            async with httpx.AsyncClient() as client:
                # Prefixes zählen
                response = await client.get(
                    f"{self.base_url}/api/ipam/prefixes/",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                result["prefixes_count"] = response.json()["count"]

                # VLANs zählen
                response = await client.get(
                    f"{self.base_url}/api/ipam/vlans/",
                    headers=self.headers,
                    timeout=10.0,
                )
                response.raise_for_status()
                result["vlans_count"] = response.json()["count"]

                # Konfiguriert wenn mindestens ein Prefix existiert
                result["configured"] = result["prefixes_count"] > 0

        except Exception as e:
            result["error"] = str(e)

        return result


# Singleton-Instanz
netbox_service = NetBoxService()
