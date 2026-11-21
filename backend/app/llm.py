"""OpenAI-mos chat API mijozi (DeepSeek va boshqalar).

Model nomi tartibi: AppSetting("llm_model") > .env LLM_MODEL. Shunday qilib modelni
qayta deploy qilmasdan bot ichidagi /setmodel buyrug'i bilan almashtirish mumkin.
"""
import json
import re

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .models import AppSetting

LLM_MODEL_KEY = "llm_model"


async def current_model(session: AsyncSession) -> str:
    row = await session.get(AppSetting, LLM_MODEL_KEY)
    return row.value if row else get_settings().llm_model


async def set_model(session: AsyncSession, model: str) -> None:
    row = await session.get(AppSetting, LLM_MODEL_KEY)
    if row:
        row.value = model
    else:
        session.add(AppSetting(key=LLM_MODEL_KEY, value=model))
    await session.commit()


class LLMClient:
    def __init__(self, http: httpx.AsyncClient | None = None):
        s = get_settings()
        self._http = http or httpx.AsyncClient(
            base_url=s.llm_base_url,
            headers={"Authorization": f"Bearer {s.llm_api_key}"},
            timeout=s.llm_timeout,
        )

    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 400,
        json_mode: bool = False,
    ) -> str:
        payload: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = await self._http.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    async def chat_json(self, model: str, messages: list[dict], max_tokens: int = 1200) -> dict:
        raw = await self.chat(model, messages, temperature=0.2, max_tokens=max_tokens, json_mode=True)
        return parse_json_loose(raw)

    async def aclose(self) -> None:
        await self._http.aclose()


def parse_json_loose(raw: str) -> dict:
    """Model ba'zan JSON'ni ```json ... ``` ichida qaytaradi — shuni ham qabul qilamiz."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            raise
        return json.loads(match.group(0))
