"""Ma'lumotlar bazasi boshqaruv handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Emoji, Messages
from bot.utils import log_execution
from bot.keyboards import get_back_keyboard, get_db_menu_keyboard
from bot.services import SystemService

system = SystemService()


@log_execution("db")
async def db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/db buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "🗄 <b>Ma'lumotlar Bazasi</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_db_menu_keyboard(),
        parse_mode="HTML",
    )


async def db_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """DB callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    pgsql_status = "🟢" if settings.is_postgres_enabled else "🔴 O'chirilgan"
    mysql_status = "🟢" if settings.is_mysql_enabled else "🔴 O'chirilgan"
    redis_status = "🟢" if settings.is_redis_enabled else "🔴 O'chirilgan"

    if action == "pgsql":
        if not settings.is_postgres_enabled:
            await query.edit_message_text(Messages.SERVICE_DISABLED.format(service="PostgreSQL"), reply_markup=get_back_keyboard())
            return
        await query.edit_message_text(
            "🐘 <b>PostgreSQL</b>\n\nBu funksiya tez orada qo'shiladi.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif action == "mysql":
        if not settings.is_mysql_enabled:
            await query.edit_message_text(Messages.SERVICE_DISABLED.format(service="MySQL"), reply_markup=get_back_keyboard())
            return
        await query.edit_message_text(
            "🐬 <b>MySQL</b>\n\nBu funksiya tez orada qo'shiladi.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif action == "redis":
        if not settings.is_redis_enabled:
            await query.edit_message_text(Messages.SERVICE_DISABLED.format(service="Redis"), reply_markup=get_back_keyboard())
            return
        await query.edit_message_text(
            "🔴 <b>Redis</b>\n\nBu funksiya tez orada qo'shiladi.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    else:
        text = Messages.DB_STATUS.format(
            pgsql_status=pgsql_status,
            mysql_status=mysql_status,
            redis_status=redis_status,
        )
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


def register_db_handlers(application) -> None:
    application.add_handler(CommandHandler("db", db_command))
    application.add_handler(CallbackQueryHandler(db_callback, pattern="^db:"))
