"""Nginx boshqaruv handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.constants import Emoji, Messages
from bot.utils import log_execution
from bot.keyboards import get_back_keyboard, get_nginx_menu_keyboard
from bot.services import NginxService

nginx = NginxService()


@log_execution("nginx")
async def nginx_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/nginx buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "🌐 <b>Nginx Boshqaruvi</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_nginx_menu_keyboard(),
        parse_mode="HTML",
    )


async def nginx_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Nginx callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "sites":
        status = await nginx.get_status()
        if not status.get("success"):
            await query.edit_message_text(
                Messages.ERROR_OCCURRED.format(error=status.get("error", "Noma'lum")),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )
            return

        available = status.get("available_sites", [])
        enabled = status.get("enabled_sites", [])

        lines = []
        for site in available:
            status_icon = Emoji.ACTIVE if site in enabled else Emoji.ERROR
            lines.append(f"{status_icon} {site}")

        text = f"🌐 <b>Saytlar</b> ({len(enabled)}/{len(available)} faol)\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "ssl":
        certs = await nginx.get_ssl_status()
        if not certs:
            await query.edit_message_text("📭 SSL sertifikatlari topilmadi.", reply_markup=get_back_keyboard())
            return
        lines = [f"🔒 <b>{c['domain']}</b> - ⏰ {c['expiry']}" for c in certs]
        text = Messages.NGINX_CERT_STATUS.format(certs="\n".join(lines))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "renew":
        result = await nginx.renew_certs()
        if result.get("success"):
            await query.edit_message_text("✅ Sertifikatlar yangilandi.", reply_markup=get_back_keyboard())
        else:
            await query.edit_message_text(
                Messages.ERROR_OCCURRED.format(error=result.get("output", "Noma'lum")),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )


def register_nginx_handlers(application) -> None:
    application.add_handler(CommandHandler("nginx", nginx_command))
    application.add_handler(CallbackQueryHandler(nginx_callback, pattern="^nginx:"))
