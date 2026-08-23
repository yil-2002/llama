"""Nginx boshqaruv xizmati."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger

from bot.services.base_service import BaseService
from bot.utils import safe_subprocess


class NginxService(BaseService):
    """Nginx saytlar va konfiguratsiyalarni boshqarish."""

    def __init__(self) -> None:
        super().__init__("Nginx")
        self.sites_available = Path("/etc/nginx/sites-available")
        self.sites_enabled = Path("/etc/nginx/sites-enabled")

    async def check_availability(self) -> bool:
        try:
            code, _, _ = await safe_subprocess(["nginx", "-v"], timeout=5)
            self._available = code == 0
            return self._available
        except Exception:
            self._available = False
            return False

    async def get_status(self) -> dict[str, Any]:
        try:
            code, out, _ = await safe_subprocess(["systemctl", "is-active", "nginx"], timeout=5)
            is_active = code == 0

            available = list(self.sites_available.glob("*")) if self.sites_available.exists() else []
            enabled = list(self.sites_enabled.glob("*")) if self.sites_enabled.exists() else []

            return {
                "success": True,
                "active": is_active,
                "available_sites": [s.name for s in available],
                "enabled_sites": [s.name for s in enabled],
                "total_sites": len(available),
                "active_count": len(enabled),
            }
        except Exception as e:
            return self.handle_error("get_status", e)

    async def get_site_config(self, site_name: str) -> dict[str, Any]:
        try:
            config_path = self.sites_available / site_name
            if not config_path.exists():
                return {"success": False, "error": "Sayt topilmadi"}
            content = config_path.read_text()
            return {"success": True, "content": content}
        except Exception as e:
            return self.handle_error("get_site_config", e)

    async def update_site_config(self, site_name: str, content: str) -> dict[str, Any]:
        try:
            config_path = self.sites_available / site_name
            config_path.write_text(content)
            # Test config
            code, _, err = await safe_subprocess(["sudo", "nginx", "-t"], timeout=10)
            if code != 0:
                return {"success": False, "error": f"Konfiguratsiya noto'g'ri: {err}"}
            return {"success": True, "message": "Konfiguratsiya yangilandi"}
        except Exception as e:
            return self.handle_error("update_site_config", e)

    async def enable_site(self, site_name: str) -> dict[str, Any]:
        try:
            available = self.sites_available / site_name
            enabled = self.sites_enabled / site_name
            if not available.exists():
                return {"success": False, "error": "Sayt topilmadi"}
            if enabled.exists():
                return {"success": True, "message": "Sayt allaqachon yoqilgan"}
            enabled.symlink_to(available)
            await safe_subprocess(["sudo", "nginx", "-s", "reload"], timeout=10)
            return {"success": True, "message": "Sayt yoqildi"}
        except Exception as e:
            return self.handle_error("enable_site", e)

    async def disable_site(self, site_name: str) -> dict[str, Any]:
        try:
            enabled = self.sites_enabled / site_name
            if not enabled.exists():
                return {"success": False, "error": "Sayt yoqilmagan"}
            enabled.unlink()
            await safe_subprocess(["sudo", "nginx", "-s", "reload"], timeout=10)
            return {"success": True, "message": "Sayt o'chirildi"}
        except Exception as e:
            return self.handle_error("disable_site", e)

    async def test_config(self) -> dict[str, Any]:
        try:
            code, out, err = await safe_subprocess(["sudo", "nginx", "-t"], timeout=10)
            return {
                "success": code == 0,
                "output": out + err,
            }
        except Exception as e:
            return self.handle_error("test_config", e)

    async def get_ssl_status(self) -> list[dict[str, Any]]:
        """SSL sertifikatlari holati."""
        try:
            certs = []
            cert_dir = Path("/etc/letsencrypt/live")
            if cert_dir.exists():
                for domain_dir in cert_dir.iterdir():
                    if domain_dir.is_dir():
                        cert_path = domain_dir / "cert.pem"
                        if cert_path.exists():
                            code, out, _ = await safe_subprocess(
                                ["openssl", "x509", "-in", str(cert_path), "-noout", "-dates"],
                                timeout=5,
                            )
                            expiry = "Noma'lum"
                            if code == 0:
                                for line in out.split("\n"):
                                    if "notAfter" in line:
                                        expiry = line.split("=")[1].strip()
                                        break
                            certs.append({
                                "domain": domain_dir.name,
                                "expiry": expiry,
                            })
            return certs
        except Exception as e:
            logger.error(f"SSL holatini olishda xatolik: {e}")
            return []

    async def renew_certs(self) -> dict[str, Any]:
        try:
            code, out, err = await safe_subprocess(["sudo", "certbot", "renew"], timeout=120)
            return {
                "success": code == 0,
                "output": out + err,
            }
        except Exception as e:
            return self.handle_error("renew_certs", e)
