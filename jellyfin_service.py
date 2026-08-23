"""Jellyfin media server xizmati."""
from __future__ import annotations

from typing import Any, Optional

import aiohttp
from loguru import logger

from bot.config import settings
from bot.services.base_service import BaseService


class JellyfinService(BaseService):
    """Jellyfin API mijozi."""

    def __init__(self) -> None:
        super().__init__("Jellyfin")
        self.url = settings.jellyfin_url.rstrip("/") if settings.jellyfin_url else ""
        self.api_key = settings.jellyfin_api_key or ""
        self.headers = {
            "X-Emby-Token": self.api_key,
            "Content-Type": "application/json",
        }

    async def check_availability(self) -> bool:
        if not self.url:
            self._available = False
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/System/Info", headers=self.headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    self._available = resp.status == 200
                    return self._available
        except Exception as e:
            logger.warning(f"Jellyfin mavjud emas: {e}")
            self._available = False
            return False

    async def get_system_info(self) -> dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/System/Info", headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return {"success": True, "data": await resp.json()}
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return self.handle_error("get_system_info", e)

    async def get_libraries(self) -> list[dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/Library/VirtualFolders", headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as e:
            logger.error(f"Kutubxonalarni olishda xatolik: {e}")
            return []

    async def get_recent_items(self, limit: int = 10) -> list[dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.url}/Users/Me/Items/Latest",
                    headers=self.headers,
                    params={"Limit": limit},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as e:
            logger.error(f"So'nggi elementlarni olishda xatolik: {e}")
            return []

    async def get_users(self) -> list[dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/Users", headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as e:
            logger.error(f"Foydalanuvchilarni olishda xatolik: {e}")
            return []

    async def get_sessions(self) -> list[dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/Sessions", headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as e:
            logger.error(f"Sessiyalarni olishda xatolik: {e}")
            return []

    async def scan_library(self, library_id: Optional[str] = None) -> dict[str, Any]:
        try:
            url = f"{self.url}/Library/Refresh"
            if library_id:
                url = f"{self.url}/Items/{library_id}/Refresh"
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    return {"success": resp.status in (200, 204), "status": resp.status}
        except Exception as e:
            return self.handle_error("scan_library", e)
