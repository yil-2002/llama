"""WireGuard VPN xizmati."""
from __future__ import annotations

import base64
import ipaddress
import os
import re
from pathlib import Path
from typing import Any, Optional

import qrcode
from loguru import logger

from bot.config import settings
from bot.services.base_service import BaseService
from bot.utils import safe_subprocess


class WireguardService(BaseService):
    """WireGuard boshqaruvi."""

    def __init__(self) -> None:
        super().__init__("WireGuard")
        self.config_dir = settings.wireguard_config_dir
        self.interface = "wg0"

    async def check_availability(self) -> bool:
        try:
            code, _, _ = await safe_subprocess(["wg", "show"], timeout=5)
            self._available = code == 0
            return self._available
        except Exception as e:
            logger.warning(f"WireGuard mavjud emas: {e}")
            self._available = False
            return False

    async def get_status(self) -> dict[str, Any]:
        try:
            code, out, _ = await safe_subprocess(["wg", "show", self.interface], timeout=10)
            if code != 0:
                return {"success": False, "error": "Interface topilmadi"}

            peers = []
            rx_total = 0
            tx_total = 0
            current_peer = None

            for line in out.split("\n"):
                if line.startswith("peer:"):
                    current_peer = {"public_key": line.split(":")[1].strip()}
                    peers.append(current_peer)
                elif "endpoint:" in line and current_peer:
                    current_peer["endpoint"] = line.split(":", 1)[1].strip()
                elif "allowed ips:" in line and current_peer:
                    current_peer["allowed_ips"] = line.split(":", 1)[1].strip()
                elif "latest handshake:" in line and current_peer:
                    current_peer["handshake"] = line.split(":", 1)[1].strip()
                elif "transfer:" in line and current_peer:
                    parts = line.split(":", 1)[1].strip().split(",")
                    rx = self._parse_transfer(parts[0].strip())
                    tx = self._parse_transfer(parts[1].strip()) if len(parts) > 1 else 0
                    current_peer["rx"] = rx
                    current_peer["tx"] = tx
                    rx_total += rx
                    tx_total += tx

            return {
                "success": True,
                "peers": peers,
                "peer_count": len(peers),
                "rx_total": rx_total,
                "tx_total": tx_total,
            }
        except Exception as e:
            return self.handle_error("get_status", e)

    def _parse_transfer(self, text: str) -> int:
        """Parse transfer text like '1.23 MiB' to bytes."""
        match = re.match(r"([\d.]+)\s*(KiB|MiB|GiB|B)", text)
        if not match:
            return 0
        value = float(match.group(1))
        unit = match.group(2)
        multipliers = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
        return int(value * multipliers.get(unit, 1))

    async def add_peer(self, name: str) -> dict[str, Any]:
        """Yangi peer qo'shish va konfiguratsiya yaratish."""
        try:
            # Generate keys
            code, private_key, _ = await safe_subprocess(["wg", "genkey"], timeout=5)
            if code != 0:
                return {"success": False, "error": "Private key yaratishda xatolik"}

            private_key = private_key.strip()
            code, public_key, _ = await safe_subprocess(
                ["bash", "-c", f"echo '{private_key}' | wg pubkey"],
                timeout=5,
            )
            if code != 0:
                return {"success": False, "error": "Public key yaratishda xatolik"}

            public_key = public_key.strip()

            # Find next available IP
            ip = await self._get_next_ip()
            if not ip:
                return {"success": False, "error": "Bo'sh IP topilmadi"}

            # Add peer to interface
            code, _, err = await safe_subprocess(
                ["sudo", "wg", "set", self.interface, "peer", public_key, "allowed-ips", f"{ip}/32"],
                timeout=10,
            )
            if code != 0:
                return {"success": False, "error": f"Peer qo'shishda xatolik: {err}"}

            # Save config
            code, _, _ = await safe_subprocess(["sudo", "wg-quick", "save", self.interface], timeout=10)

            # Get server endpoint
            server_ip = await self._get_server_ip()
            server_port = await self._get_server_port()

            # Generate client config
            client_config = f"""[Interface]
PrivateKey = {private_key}
Address = {ip}/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {await self._get_server_public_key()}
Endpoint = {server_ip}:{server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(client_config)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")

            return {
                "success": True,
                "name": name,
                "ip": ip,
                "public_key": public_key,
                "config": client_config,
                "qr_image": qr_img,
            }
        except Exception as e:
            return self.handle_error("add_peer", e)

    async def remove_peer(self, public_key: str) -> dict[str, Any]:
        try:
            code, _, err = await safe_subprocess(
                ["sudo", "wg", "set", self.interface, "peer", public_key, "remove"],
                timeout=10,
            )
            if code != 0:
                return {"success": False, "error": err}
            await safe_subprocess(["sudo", "wg-quick", "save", self.interface], timeout=10)
            return {"success": True, "message": "Peer o'chirildi"}
        except Exception as e:
            return self.handle_error("remove_peer", e)

    async def _get_next_ip(self) -> Optional[str]:
        """Keyingi bo'sh IP manzilni topish."""
        try:
            config_path = self.config_dir / f"{self.interface}.conf"
            if not config_path.exists():
                return "10.0.0.2"

            content = config_path.read_text()
            used_ips = set()
            for line in content.split("\n"):
                if "AllowedIPs" in line:
                    ip_str = line.split("=")[1].strip().split("/")[0]
                    used_ips.add(ip_str)

            network = ipaddress.ip_network("10.0.0.0/24")
            for ip in network.hosts():
                ip_str = str(ip)
                if ip_str not in used_ips and ip_str != "10.0.0.1":
                    return ip_str
            return None
        except Exception:
            return "10.0.0.2"

    async def _get_server_ip(self) -> str:
        code, out, _ = await safe_subprocess(["curl", "-s", "-m", "5", "https://api.ipify.org"], timeout=10)
        return out.strip() if code == 0 else "YOUR_SERVER_IP"

    async def _get_server_port(self) -> str:
        try:
            config_path = self.config_dir / f"{self.interface}.conf"
            if config_path.exists():
                content = config_path.read_text()
                match = re.search(r"ListenPort\s*=\s*(\d+)", content)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return "51820"

    async def _get_server_public_key(self) -> str:
        try:
            code, out, _ = await safe_subprocess(["wg", "show", self.interface, "public-key"], timeout=5)
            return out.strip() if code == 0 else ""
        except Exception:
            return ""
