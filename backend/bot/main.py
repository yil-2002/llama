"""Telegram bot (aiogram 3). Ishga tushirish: `python -m bot.main`"""
import asyncio
import base64
import io
import logging
import os
from datetime import timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BufferedInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)
from sqlalchemy import select

from app import payments
from app.config import get_settings
from app.db import SessionLocal, init_db
from app.llm import current_model, set_model
from app.models import ChatSession, User
from app.payments.stars import SUBSCRIPTION_PERIOD, make_payload, parse_payload
from app.queue import queue
from app.services import chat as chat_service
from app.services.dashboard import build_dashboard, format_dashboard_text
from app.services.users import get_or_create_user, remaining_free_messages
from app.speech import SpeechNotConfigured

from . import texts

log = logging.getLogger(__name__)
router = Router()
settings = get_settings()

# Maskot stikerlari: @Stickers orqali yuklab, file_id larni .env ga qo'ying
STICKERS = {
    "hello": os.getenv("STICKER_HELLO"),
    "think": os.getenv("STICKER_THINK"),
    "praise": os.getenv("STICKER_PRAISE"),
    "sad": os.getenv("STICKER_SAD"),
}


def app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=texts.OPEN_APP, web_app=WebAppInfo(url=settings.webapp_url))]]
    )


async def send_sticker(message: Message, key: str) -> None:
    if STICKERS.get(key):
        try:
            await message.answer_sticker(STICKERS[key])
        except Exception:
            log.warning("stiker yuborilmadi: %s", key)


async def _user(session, message: Message) -> User:
    u = message.from_user
    user = await get_or_create_user(session, u.id, u.first_name or "", u.username)
    await session.commit()
    return user


async def _bot_chat(session, user: User) -> ChatSession:
    """Bot chatidagi joriy erkin suhbat (yakunlanmagan oxirgisi) yoki yangisi."""
    chat = await session.scalar(
        select(ChatSession)
        .where(ChatSession.user_id == user.id, ChatSession.mode == "free", ChatSession.finished_at.is_(None))
        .order_by(ChatSession.id.desc())
    )
    if chat is None:
        chat = await chat_service.start_session(session, user, "free")
        await session.commit()
    return chat


@router.message(CommandStart())
async def start(message: Message):
    async with SessionLocal() as session:
        user = await _user(session, message)
        free = await remaining_free_messages(session, user)
    await send_sticker(message, "hello")
    await message.answer(
        texts.WELCOME.format(name=message.from_user.first_name or "do'stim", free="cheksiz" if free is None else free),
        reply_markup=app_keyboard(),
    )


async def _reply_to(message: Message, job: str, **kwargs) -> None:
    async with SessionLocal() as session:
        user = await _user(session, message)
        remaining = await remaining_free_messages(session, user)
        if remaining is not None and remaining <= 0:
            await send_sticker(message, "sad")
            await message.answer(texts.LIMIT_REACHED)
            return
        chat = await _bot_chat(session, user)
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        result = await queue.run(job, chat_id=chat.id, **kwargs)
    except SpeechNotConfigured:
        await message.answer(texts.NO_STT)
        return
    except Exception:
        log.exception("javob xatosi")
        await message.answer(texts.ERROR)
        return
    if result.get("transcript"):
        await message.answer(f"🗣 <i>{texts._esc(result['transcript'])}</i>")
    if result.get("audio_b64"):
        await message.answer_voice(BufferedInputFile(base64.b64decode(result["audio_b64"]), "owly.ogg"))
    await message.answer(texts._esc(result["reply"]))


@router.message(F.voice)
async def on_voice(message: Message):
    buf = io.BytesIO()
    await message.bot.download(message.voice, destination=buf)
    await _reply_to(message, "voice_reply", audio_b64=base64.b64encode(buf.getvalue()).decode(), filename="voice.ogg")


@router.message(Command("feedback"))
async def feedback(message: Message):
    async with SessionLocal() as session:
        user = await _user(session, message)
        chat = await session.scalar(
            select(ChatSession)
            .where(ChatSession.user_id == user.id, ChatSession.mode == "free", ChatSession.finished_at.is_(None))
            .order_by(ChatSession.id.desc())
        )
    if chat is None:
        await message.answer(texts.NO_CHAT)
        return
    await message.answer(texts.FEEDBACK_WAIT)
    try:
        fb = await queue.run("finish_chat", chat_id=chat.id)
    except ValueError:
        await message.answer(texts.NO_CHAT)
        return
    except Exception:
        log.exception("feedback xatosi")
        await message.answer(texts.ERROR)
        return
    await send_sticker(message, "praise")
    await message.answer(texts.format_feedback(fb), reply_markup=app_keyboard())


@router.message(Command("premium"))
async def premium(message: Message):
    plan = payments.get_provider("stars").plans()[0]
    async with SessionLocal() as session:
        user = await _user(session, message)
    await message.answer(texts.PREMIUM_INFO.format(price=plan.price))
    # Bot ichida Stars obunasi: invoice link (subscription_period bilan)
    link = await message.bot.create_invoice_link(
        title="Owly Premium",
        description="Cheksiz AI suhbat, IELTS mock va o'zbekcha feedback",
        payload=make_payload(user, plan),
        currency="XTR",
        prices=[LabeledPrice(label=plan.title, amount=plan.price)],
        subscription_period=SUBSCRIPTION_PERIOD,
    )
    await message.answer(
        "👇",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=f"⭐ {plan.price} Stars bilan obuna", url=link)]]
        ),
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message):
    sp = message.successful_payment
    data = parse_payload(sp.invoice_payload)
    plan = next(p for p in payments.get_provider("stars").plans() if p.code == data["p"])
    async with SessionLocal() as session:
        user = await _user(session, message)
        await payments.record_payment(
            session, user, "stars", sp.telegram_payment_charge_id, sp.total_amount, sp.currency, plan.days
        )
        until = (user.premium_until + timedelta(hours=settings.tz_offset_hours)).strftime("%d.%m.%Y")
    await send_sticker(message, "praise")
    await message.answer(texts.PAID.format(date=until), reply_markup=app_keyboard())


# ---------- Admin buyruqlari ----------


def _is_admin(message: Message) -> bool:
    return message.from_user.id in settings.admin_ids


@router.message(Command("stats"))
async def stats(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    days = int(command.args) if command.args and command.args.isdigit() else 7
    async with SessionLocal() as session:
        d = await build_dashboard(session, days=days)
    await message.answer(format_dashboard_text(d), reply_markup=app_keyboard())


@router.message(Command("model"))
async def model(message: Message):
    if not _is_admin(message):
        return
    async with SessionLocal() as session:
        await message.answer(f"Joriy model: <code>{await current_model(session)}</code>\nO'zgartirish: /setmodel nom")


@router.message(Command("setmodel"))
async def setmodel(message: Message, command: CommandObject):
    if not _is_admin(message):
        return
    if not command.args:
        await message.answer("Foydalanish: /setmodel deepseek-...")
        return
    async with SessionLocal() as session:
        await set_model(session, command.args.strip())
    await message.answer(f"✅ Model o'zgardi: <code>{command.args.strip()}</code>")


# Matnli xabarlar eng oxirida (buyruqlardan keyin)
@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message):
    await _reply_to(message, "chat_reply", text=message.text[:2000])


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
