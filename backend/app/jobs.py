"""Navbat ishlari (Redis + arq). API ularni navbatga qo'yadi, worker'lar bajaradi.

Gorizontal masshtab: `arq app.worker.WorkerSettings` ni istalgancha nusxada ishga tushiring.
"""
import base64

from .db import SessionLocal
from .llm import LLMClient
from .models import ChatSession, User
from .services import chat as chat_service
from .services.users import log_event, touch_streak
from .speech import get_stt, get_tts


def build_ctx() -> dict:
    return {"llm": LLMClient(), "stt": get_stt(), "tts": get_tts()}


def _feedback_dict(fb) -> dict:
    return {"session_id": fb.session_id, "overall_band": fb.overall_band, **fb.data}


async def _mark_activity(session, chat_id: int, kind: str) -> None:
    chat = await session.get(ChatSession, chat_id)
    user = await session.get(User, chat.user_id)
    touch_streak(user)
    log_event(session, user, kind)


async def chat_reply(ctx: dict, chat_id: int, text: str | None) -> dict:
    async with SessionLocal() as session:
        if text:
            await _mark_activity(session, chat_id, "message")
        reply = await chat_service.generate_reply(session, ctx["llm"], chat_id, text)
    return {"reply": reply, "audio_b64": await _maybe_tts(ctx, reply)}


async def voice_reply(ctx: dict, chat_id: int, audio_b64: str, filename: str = "voice.ogg") -> dict:
    text = await ctx["stt"].transcribe(base64.b64decode(audio_b64), filename)
    async with SessionLocal() as session:
        await _mark_activity(session, chat_id, "voice")
        reply = await chat_service.generate_reply(session, ctx["llm"], chat_id, text, from_voice=True)
    return {"transcript": text, "reply": reply, "audio_b64": await _maybe_tts(ctx, reply)}


async def finish_chat(ctx: dict, chat_id: int) -> dict:
    async with SessionLocal() as session:
        fb = await chat_service.finish_session(session, ctx["llm"], chat_id)
        chat = await session.get(ChatSession, chat_id)
        user = await session.get(User, chat.user_id)
        log_event(session, user, "feedback")
        await session.commit()
        return _feedback_dict(fb)


async def _maybe_tts(ctx: dict, text: str) -> str | None:
    try:
        audio = await ctx["tts"].synthesize(text)
    except Exception:  # TTS ixtiyoriy: ishlamasa matn yetarli
        return None
    return base64.b64encode(audio).decode()


FUNCTIONS = [chat_reply, voice_reply, finish_chat]
