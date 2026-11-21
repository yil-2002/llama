"""Suhbat mantig'i. Bu funksiyalar worker ichida ishlaydi (LLM chaqiruvlari API'ni bloklamasligi uchun)."""
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import prompts
from ..llm import LLMClient, current_model
from ..models import ChatSession, Feedback, Message, User, utcnow

TOPICS = {
    "free": ["your weekend", "food in Uzbekistan", "travel", "movies", "your dream job", "technology"],
    "ielts_p1": ["hometown", "work or studies", "hobbies", "music", "weather", "reading"],
    "ielts_p2": [
        "a person who inspired you",
        "a memorable trip",
        "a skill you want to learn",
        "a place in your city you like",
    ],
    "ielts_p3": ["education", "technology and society", "environment", "work-life balance"],
}

HISTORY_LIMIT = 20  # LLM'ga yuboriladigan oxirgi xabarlar soni (xarajatni cheklash uchun)


async def start_session(session: AsyncSession, user: User, mode: str, topic: str | None = None) -> ChatSession:
    if mode not in prompts.MODES:
        raise ValueError(f"noma'lum rejim: {mode}")
    chat = ChatSession(user_id=user.id, mode=mode, topic=topic or random.choice(TOPICS[mode]))
    session.add(chat)
    await session.flush()
    return chat


async def _load(session: AsyncSession, chat_id: int) -> ChatSession:
    chat = await session.scalar(
        select(ChatSession).where(ChatSession.id == chat_id).options(selectinload(ChatSession.messages))
    )
    if chat is None:
        raise LookupError("suhbat topilmadi")
    return chat


async def generate_reply(
    session: AsyncSession, llm: LLMClient, chat_id: int, user_text: str | None, from_voice: bool = False
) -> str:
    """Foydalanuvchi xabarini saqlaydi va AI javobini qaytaradi. user_text=None — AI birinchi bo'lib gapiradi."""
    chat = await _load(session, chat_id)
    user = await session.get(User, chat.user_id)
    if user_text:
        chat.messages.append(Message(role="user", text=user_text, from_voice=from_voice))

    history = [{"role": m.role, "content": m.text} for m in chat.messages[-HISTORY_LIMIT:]]
    if not history:
        history = [{"role": "user", "content": "Hi! Let's start."}]
    messages = [
        {"role": "system", "content": prompts.conversation_system_prompt(chat.mode, user.level, chat.topic)},
        *history,
    ]
    reply = await llm.chat(await current_model(session), messages)
    chat.messages.append(Message(role="assistant", text=reply))
    await session.commit()
    return reply


async def finish_session(session: AsyncSession, llm: LLMClient, chat_id: int) -> Feedback:
    chat = await _load(session, chat_id)
    existing = await session.scalar(select(Feedback).where(Feedback.session_id == chat_id))
    if existing:
        return existing

    user_turns = [m for m in chat.messages if m.role == "user"]
    if not user_turns:
        raise ValueError("baholash uchun javoblar yo'q")

    transcript = [(m.role, m.text) for m in chat.messages]
    typed = not any(m.from_voice for m in user_turns)
    data = await llm.chat_json(await current_model(session), prompts.feedback_messages(transcript, typed))

    try:
        band = float(data.get("overall_band"))
    except (TypeError, ValueError):
        band = None
    fb = Feedback(session_id=chat.id, overall_band=band, data=data)
    session.add(fb)
    chat.finished_at = utcnow()

    user = await session.get(User, chat.user_id)
    if not user.level and data.get("estimated_level") in ("A1", "A2", "B1", "B2", "C1", "C2"):
        user.level = data["estimated_level"]
    await session.commit()
    return fb
