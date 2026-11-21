"""Nutqni matnga (STT) va matnni nutqqa (TTS) aylantirish.

Provayder .env orqali tanlanadi. "openai" — OpenAI-mos /audio API (OpenAI, Groq Whisper,
lokal faster-whisper serverlari va h.k.). Yangi provayder qo'shish uchun STT/TTS
protokolini amalga oshirib, get_stt()/get_tts() ga qo'shing.
"""
from typing import Protocol

import httpx

from .config import get_settings


class SpeechNotConfigured(RuntimeError):
    pass


class STT(Protocol):
    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> str: ...


class TTS(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """OGG/Opus qaytaradi (Telegram ovozli xabari formati)."""
        ...


class NoSTT:
    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> str:
        raise SpeechNotConfigured("STT sozlanmagan (STT_PROVIDER)")


class NoTTS:
    async def synthesize(self, text: str) -> bytes:
        raise SpeechNotConfigured("TTS sozlanmagan (TTS_PROVIDER)")


class OpenAICompatibleSTT:
    def __init__(self, base_url: str, api_key: str, model: str):
        self._http = httpx.AsyncClient(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        self._model = model

    async def transcribe(self, audio: bytes, filename: str = "voice.ogg") -> str:
        resp = await self._http.post(
            "/audio/transcriptions",
            data={"model": self._model, "language": "en"},
            files={"file": (filename, audio)},
        )
        resp.raise_for_status()
        return resp.json()["text"].strip()


class OpenAICompatibleTTS:
    def __init__(self, base_url: str, api_key: str, model: str, voice: str):
        self._http = httpx.AsyncClient(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        self._model, self._voice = model, voice

    async def synthesize(self, text: str) -> bytes:
        resp = await self._http.post(
            "/audio/speech",
            json={"model": self._model, "voice": self._voice, "input": text, "response_format": "opus"},
        )
        resp.raise_for_status()
        return resp.content


def get_stt() -> STT:
    s = get_settings()
    if s.stt_provider == "openai":
        return OpenAICompatibleSTT(s.stt_base_url, s.stt_api_key, s.stt_model)
    return NoSTT()


def get_tts() -> TTS:
    s = get_settings()
    if s.tts_provider == "openai":
        return OpenAICompatibleTTS(s.tts_base_url, s.tts_api_key, s.tts_model, s.tts_voice)
    return NoTTS()
