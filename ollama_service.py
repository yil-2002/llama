"""Ollama AI xizmati."""
from __future__ import annotations

import json
from typing import Any, Optional

import aiohttp
from loguru import logger

from bot.config import settings
from bot.services.base_service import BaseService


class OllamaService(BaseService):
    """Ollama API mijozi."""

    def __init__(self) -> None:
        super().__init__("Ollama")
        self.base_url = settings.ollama_host.rstrip("/")
        self.default_model = settings.ollama_default_model

    async def check_availability(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    self._available = resp.status == 200
                    return self._available
        except Exception as e:
            logger.warning(f"Ollama mavjud emas: {e}")
            self._available = False
            return False

    async def list_models(self) -> list[dict[str, Any]]:
        """Mavjud modellarni ro'yxatlash."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("models", [])
                    return []
        except Exception as e:
            logger.error(f"Modellarni olishda xatolik: {e}")
            return []

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        context: Optional[list[str]] = None,
        json_mode: bool = False,
        system: Optional[str] = None,
    ) -> dict[str, Any]:
        """AI javob generatsiya qilish.

        json_mode=True bo'lsa, Ollama'dan faqat valid JSON qaytarishni
        so'raydi (agentic tool-routing uchun ishlatiladi).
        """
        model = model or self.default_model
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"
        if context:
            # Ollama does not natively support conversation context in generate API
            # We concatenate previous context
            full_prompt = "\n\n".join(context[-5:]) + f"\n\n{prompt}"
            payload["prompt"] = full_prompt

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "success": True,
                            "response": data.get("response", ""),
                            "model": model,
                            "total_duration": data.get("total_duration", 0),
                        }
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return self.handle_error("generate", e)

    async def get_model_info(self, model_name: str) -> dict[str, Any]:
        """Model haqida ma'lumot."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/show",
                    json={"name": model_name},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        return {"success": True, "info": await resp.json()}
                    return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return self.handle_error("get_model_info", e)
