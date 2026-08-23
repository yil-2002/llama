"""Gitea git server xizmati."""
from __future__ import annotations

from typing import Any, Optional

import aiohttp
from loguru import logger

from bot.config import settings
from bot.services.base_service import BaseService


class GiteaService(BaseService):
    """Gitea API mijozi."""

    def __init__(self) -> None:
        super().__init__("Gitea")
        self.url = settings.gitea_url.rstrip("/") if settings.gitea_url else ""
        self.token = settings.gitea_token or ""
        self.headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    async def check_availability(self) -> bool:
        if not self.url:
            self._available = False
            return False
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/api/v1/version", headers=self.headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    self._available = resp.status == 200
                    return self._available
        except Exception as e:
            logger.warning(f"Gitea mavjud emas: {e}")
            self._available = False
            return False

    async def get_version(self) -> dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/api/v1/version", headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return {"success": True, "data": await resp.json()}
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return self.handle_error("get_version", e)

    async def list_repos(self, page: int = 1, limit: int = 20) -> list[dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.url}/api/v1/repos/search",
                    headers=self.headers,
                    params={"limit": limit, "page": page},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("data", [])
                    return []
        except Exception as e:
            logger.error(f"Repositoriyalarni olishda xatolik: {e}")
            return []

    async def create_repo(self, name: str, private: bool = True, description: str = "") -> dict[str, Any]:
        try:
            payload = {
                "name": name,
                "private": private,
                "description": description,
                "auto_init": True,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/v1/user/repos",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 201:
                        return {"success": True, "data": await resp.json()}
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return self.handle_error("create_repo", e)

    async def list_users(self) -> list[dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/api/v1/admin/users", headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return []
        except Exception as e:
            logger.error(f"Foydalanuvchilarni olishda xatolik: {e}")
            return []

    async def create_user(self, username: str, email: str, password: str, full_name: str = "") -> dict[str, Any]:
        try:
            payload = {
                "username": username,
                "email": email,
                "password": password,
                "full_name": full_name,
                "must_change_password": False,
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.url}/api/v1/admin/users",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 201:
                        return {"success": True, "data": await resp.json()}
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return self.handle_error("create_user", e)
