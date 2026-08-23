"""VPN handlerlari."""
from __future__ import annotations

from io import BytesIO

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import ButtonText, Emoji, Messages
from bot.keyboards import get_back_keyboard, get_vpn_menu_keyboard
from bot.services import WireguardService
from bot.utils import log_execution, bytes_to_human

vpn = WireguardService()


@log_execution("vpn")
async def vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/vpn buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "🔒 <b>WireGuard VPN</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_vpn_menu_keyboard(),
        parse_mode="HTML",
    )


async def vpn_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """VPN holatini ko'rsatish."""
    if not update.effective_message:
        return

    status = await vpn.get_status()
    if not status.get("success"):
        await update.effective_message.reply_text(
            Messages.ERROR_OCCURRED.format(error=status.get("error", "Noma'lum")),
            parse_mode="HTML",
        )
        return

    text = Messages.VPN_STATUS.format(
        server=settings.wireguard_config_dir,
        peers=status["peer_count"],
        rx=bytes_to_human(status["rx_total"]),
        tx=bytes_to_human(status["tx_total"]),
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def vpn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """VPN callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "status":
        status = await vpn.get_status()
        if not status.get("success"):
            await query.edit_message_text(
                Messages.ERROR_OCCURRED.format(error=status.get("error", "Noma'lum")),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )
            return
        text = Messages.VPN_STATUS.format(
            server=settings.wireguard_config_dir,
            peers=status["peer_count"],
            rx=bytes_to_human(status["rx_total"]),
            tx=bytes_to_human(status["tx_total"]),
        )
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "add":
        # Ask for peer name
        await query.edit_message_text(
            "📝 <b>Yangi peer nomini kiriting:</b>\n\nMasalan: telefon_ali",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )
        context.user_data["awaiting_vpn_peer_name"] = True

    elif action == "remove":
        # Show peer list for removal
        status = await vpn.get_status()
        if not status.get("success") or not status.get("peers"):
            await query.edit_message_text("📭 Peerlar yo'q.", reply_markup=get_back_keyboard())
            return

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        for peer in status["peers"]:
            pk = peer.get("public_key", "")[:16] + "..."
            keyboard.append([InlineKeyboardButton(f"🗑 {pk}", callback_data=f"vpn:del:{peer['public_key']}")])
        keyboard.append([InlineKeyboardButton(ButtonText.BACK, callback_data="vpn:back")])
        await query.edit_message_text("🔒 <b>O'chiriladigan peerni tanlang:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif action == "del" and len(data) > 2:
        public_key = data[2]
        result = await vpn.remove_peer(public_key)
        if result.get("success"):
            await query.edit_message_text("🗑 Peer o'chirildi.", reply_markup=get_back_keyboard())
        else:
            await query.edit_message_text(
                Messages.ERROR_OCCURRED.format(error=result.get("error", "Noma'lum")),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )


def register_vpn_handlers(application) -> None:
    application.add_handler(CommandHandler("vpn", vpn_command))
    application.add_handler(CallbackQueryHandler(vpn_callback, pattern="^vpn:"))
