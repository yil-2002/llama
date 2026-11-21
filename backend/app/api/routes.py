import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import payments, prompts
from ..config import get_settings
from ..db import get_session
from ..models import LEVELS, ChatSession, Feedback, User
from ..queue import queue
from ..services import chat as chat_service
from ..services.dashboard import build_dashboard
from ..services.users import grant_premium, log_event, remaining_free_messages
from .deps import admin_user, current_user

router = APIRouter(prefix="/api")

MAX_AUDIO_BYTES = 5 * 1024 * 1024


# ---------- Profil ----------


class ProfileIn(BaseModel):
    level: str | None = Field(None, pattern="^(A1|A2|B1|B2|C1|C2)$")
    goal: str | None = Field(None, pattern="^(ielts|speaking)$")
    target_band: float | None = Field(None, ge=4, le=9)


def _me(user: User, remaining: int | None) -> dict:
    return {
        "id": user.id,
        "first_name": user.first_name,
        "level": user.level,
        "goal": user.goal,
        "target_band": user.target_band,
        "streak_days": user.streak_days,
        "is_premium": user.is_premium(),
        "premium_until": user.premium_until.isoformat() if user.premium_until else None,
        "trial_available": not user.trial_used,
        "remaining_free_messages": remaining,
        "is_admin": user.telegram_id in get_settings().admin_ids,
    }


@router.get("/me")
async def me(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    user = await session.merge(user)
    return _me(user, await remaining_free_messages(session, user))


@router.patch("/me")
async def update_me(body: ProfileIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    user = await session.merge(user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    await session.commit()
    return _me(user, await remaining_free_messages(session, user))


@router.post("/trial")
async def start_trial(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    user = await session.merge(user)
    if user.trial_used:
        raise HTTPException(409, "Sinov muddati allaqachon ishlatilgan")
    user.trial_used = True
    grant_premium(user, get_settings().trial_days)
    await session.commit()
    return _me(user, None)


# ---------- Suhbat ----------


class StartChatIn(BaseModel):
    mode: str = "free"
    topic: str | None = Field(None, max_length=200)


class SendIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


async def _own_chat(session: AsyncSession, user: User, chat_id: int) -> ChatSession:
    chat = await session.get(ChatSession, chat_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(404, "Suhbat topilmadi")
    if chat.finished_at:
        raise HTTPException(409, "Suhbat yakunlangan")
    return chat


async def _check_limit(session: AsyncSession, user: User) -> None:
    remaining = await remaining_free_messages(session, user)
    if remaining is not None and remaining <= 0:
        raise HTTPException(402, "Bugungi bepul limit tugadi. Premium bilan cheksiz gaplashing!")


@router.get("/modes")
async def modes():
    return [{"code": k, "title": v} for k, v in prompts.MODES.items()]


@router.post("/chats")
async def start_chat(body: StartChatIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    user = await session.merge(user)
    if body.mode.startswith("ielts") and not user.is_premium():
        raise HTTPException(402, "IELTS mock rejimi Premium uchun")
    try:
        chat = await chat_service.start_session(session, user, body.mode, body.topic)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    log_event(session, user, "session_start")
    await session.commit()
    first = await queue.run("chat_reply", chat_id=chat.id, text=None)
    return {"id": chat.id, "mode": chat.mode, "topic": chat.topic, **first}


@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: int, body: SendIn, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    await _own_chat(session, user, chat_id)
    await _check_limit(session, user)
    return await queue.run("chat_reply", chat_id=chat_id, text=body.text.strip())


@router.post("/chats/{chat_id}/voice")
async def send_voice(
    chat_id: int,
    audio: UploadFile = File(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    await _own_chat(session, user, chat_id)
    await _check_limit(session, user)
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio juda katta (5 MB gacha)")
    return await queue.run(
        "voice_reply", chat_id=chat_id, audio_b64=base64.b64encode(data).decode(), filename=audio.filename or "voice.webm"
    )


@router.post("/chats/{chat_id}/finish")
async def finish_chat(chat_id: int, user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    chat = await session.get(ChatSession, chat_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(404, "Suhbat topilmadi")
    try:
        return await queue.run("finish_chat", chat_id=chat_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/history")
async def history(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(ChatSession, Feedback)
        .join(Feedback, Feedback.session_id == ChatSession.id)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.id.desc())
        .limit(30)
    )
    return [
        {
            "session_id": c.id,
            "mode": c.mode,
            "topic": c.topic,
            "date": c.created_at.date().isoformat(),
            "overall_band": f.overall_band,
            "scores": f.data.get("scores", {}),
        }
        for c, f in rows.all()
    ]


# ---------- To'lov ----------


@router.get("/payments/plans")
async def plans():
    """Mini App faqat Telegram ichidagi provayderlarni (Stars) ko'rsatadi."""
    return [
        {"provider": p.name, **plan.__dict__}
        for p in payments.enabled_providers(in_telegram=True)
        for plan in p.plans()
    ]


class CheckoutIn(BaseModel):
    provider: str = "stars"
    plan: str = "premium_month"


@router.post("/payments/checkout")
async def checkout(body: CheckoutIn, user: User = Depends(current_user)):
    try:
        provider = payments.get_provider(body.provider)
    except payments.PaymentNotConfigured as e:
        raise HTTPException(400, str(e)) from e
    if not provider.in_telegram:
        raise HTTPException(400, "Bu to'lov usuli faqat tashqi saytda ishlaydi")
    plan = next((p for p in provider.plans() if p.code == body.plan), None)
    if plan is None:
        raise HTTPException(404, "Tarif topilmadi")
    result = await provider.create_checkout(user, plan)
    return {"provider": result.provider, "url": result.url}


# ---------- Admin ----------


@router.get("/admin/dashboard")
async def dashboard(days: int = 7, _: User = Depends(admin_user), session: AsyncSession = Depends(get_session)):
    return await build_dashboard(session, days=max(1, min(days, 90)))


@router.get("/levels")
async def levels():
    return list(LEVELS)
