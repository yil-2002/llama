"""Media server handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Messages
from bot.utils import log_execution
from bot.keyboards import get_back_keyboard, get_media_menu_keyboard
from bot.services import JellyfinService

jellyfin = JellyfinService()


@log_execution("jellyfin")
async def jellyfin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/jellyfin buyrug'i."""
    if not update.effective_message:
        return

    if not settings.is_jellyfin_enabled:
        await update.effective_message.reply_text(Messages.SERVICE_DISABLED.format(service="Jellyfin"))
        return

    await update.effective_message.reply_text(
        "🎬 <b>Jellyfin Media Server</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_media_menu_keyboard(),
        parse_mode="HTML",
    )


async def media_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Media callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    if not settings.is_jellyfin_enabled:
        await query.edit_message_text(Messages.SERVICE_DISABLED.format(service="Jellyfin"), reply_markup=get_back_keyboard())
        return

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "libs":
        libraries = await jellyfin.get_libraries()
        if not libraries:
            await query.edit_message_text("📭 Kutubxonalar yo'q.", reply_markup=get_back_keyboard())
            return
        lines = [f"📚 <b>{lib.get('Name', 'Noma\'lum')}</b>" for lib in libraries]
        text = "📚 <b>Kutubxonalar</b>\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "recent":
        items = await jellyfin.get_recent_items(limit=10)
        if not items:
            await query.edit_message_text("📭 Hech narsa topilmadi.", reply_markup=get_back_keyboard())
            return
        lines = [f"🆕 {item.get('Name', 'Noma\'lum')} ({item.get('Type', '')})" for item in items]
        text = Messages.JELLYFIN_RECENT.format(items="\n".join(lines))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "scan":
        result = await jellyfin.scan_library()
        if result.get("success"):
            await query.edit_message_text("🔍 Skanerlash boshlandi.", reply_markup=get_back_keyboard())
        else:
            await query.edit_message_text(
                Messages.ERROR_OCCURRED.format(error=result.get("error", "Noma'lum")),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )

    elif action == "users":
        users = await jellyfin.get_users()
        sessions = await jellyfin.get_sessions()
        text = Messages.JELLYFIN_STATUS.format(
            status="🟢 Ishlayapti",
            libraries=len(await jellyfin.get_libraries()),
            users=len(users),
            sessions=len(sessions),
        )
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


def register_media_handlers(application) -> None:
    application.add_handler(CommandHandler("jellyfin", jellyfin_command))
    application.add_handler(CallbackQueryHandler(media_callback, pattern="^media:"))
