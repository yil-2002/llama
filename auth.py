"""Session management commands (/logout, /sessions, /change_password).

Replaces the old role-based admin.py (approve/reject/promote/ban), which
no longer applies now that the bot uses a single shared password instead
of per-user roles.
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.constants import ButtonText, Messages
from bot.database import Database
from bot.services.auth_service import AuthService

db = Database()
auth_service = AuthService()


def _format_session_line(s) -> str:
    status = "🟢" if not s.is_revoked else "🔴"
    return f"{status} <b>{s.display_name}</b>  (id {s.id}) — {s.last_seen}"


async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/logout - revoke every session belonging to this telegram account."""
    if not update.effective_message or not update.effective_user:
        return
    await auth_service.logout(update.effective_user.id)
    await update.effective_message.reply_text(Messages.LOGOUT_SUCCESS, parse_mode="HTML")


async def sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/sessions - list every currently active login (account/device)."""
    if not update.effective_message:
        return
    sessions = await db.get_all_sessions(active_only=True)
    if not sessions:
        await update.effective_message.reply_text(Messages.NO_SESSIONS)
        return

    lines = [_format_session_line(s) for s in sessions]
    keyboard = [
        [InlineKeyboardButton(f"{ButtonText.REVOKE} #{s.id} ({s.display_name})", callback_data=f"session:revoke:{s.id}")]
        for s in sessions
    ]
    await update.effective_message.reply_text(
        Messages.SESSION_LIST.format(sessions="\n".join(lines)),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def sessions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the "Yakunlash #N" buttons from /sessions."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 3 or parts[1] != "revoke":
        return
    try:
        session_id = int(parts[2])
    except ValueError:
        return

    await db.revoke_session(session_id)
    await query.edit_message_text(Messages.SESSION_REVOKED)


async def change_password_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/change_password - show instructions (the hash lives in .env, not
    in the database, so the bot cannot change it live for itself)."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        Messages.CHANGE_PASSWORD_INSTRUCTIONS, parse_mode="HTML"
    )


def register_auth_handlers(application) -> None:
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("sessions", sessions_command))
    application.add_handler(CommandHandler("change_password", change_password_command))
    application.add_handler(CallbackQueryHandler(sessions_callback, pattern="^session:"))
