"""Global password-based authentication gate.

This runs as a group=-1 handler for EVERY update (message or callback)
before any feature handler runs. It is the single point of access control
for the whole bot:

  1. If the account/device already has a valid session -> update last_seen
     and let the update continue to normal handlers.
  2. If the account/device is currently in the middle of a login prompt
     (context.user_data["awaiting_password"]) -> treat the incoming text
     as the password attempt.
  3. Otherwise -> ask for the password and stop the update from reaching
     any other handler.

Locked-out accounts (too many recent failed attempts) are told to wait
and are never shown the password prompt again until the lockout expires.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from bot.config import settings
from bot.constants import Messages
from bot.services.auth_service import AuthService
from bot.middlewares.rate_limit import rate_limiter

auth_service = AuthService()


async def _reply(update: Update, text: str) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.answer(text, show_alert=True)


async def global_auth_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Message-path gate. Registered with group=-1 for filters.ALL."""
    if not update.effective_user:
        raise ApplicationHandlerStop

    if not settings.is_password_configured:
        await _reply(update, Messages.PASSWORD_NOT_CONFIGURED)
        raise ApplicationHandlerStop

    telegram_id = update.effective_user.id
    username = update.effective_user.username

    session = await auth_service.get_valid_session(telegram_id)
    if session:
        await auth_service.touch(session.session_token)
        if not await rate_limiter.check_rate_limit(update, context):
            raise ApplicationHandlerStop
        return  # authenticated - let the update continue to real handlers

    # Not authenticated yet.
    if await auth_service.is_locked_out(telegram_id):
        await _reply(
            update,
            Messages.LOGIN_LOCKED_OUT.format(minutes=settings.login_lockout_minutes),
        )
        raise ApplicationHandlerStop

    awaiting = bool(context.user_data and context.user_data.get("awaiting_password"))
    message = update.effective_message

    if awaiting and message and message.text:
        password = message.text
        # Always try to delete the password message so it doesn't linger in chat history.
        try:
            await message.delete()
        except Exception:
            pass

        ok = await auth_service.attempt_login(telegram_id, username, password)
        if context.user_data is not None:
            context.user_data["awaiting_password"] = False

        if ok:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=Messages.PASSWORD_ACCEPTED, parse_mode="HTML")
            return  # let this same update continue (unlikely to be a real command, but harmless)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=Messages.PASSWORD_REJECTED, parse_mode="HTML")
            raise ApplicationHandlerStop

    # First contact, or a non-text update while unauthenticated: ask for password.
    if context.user_data is not None:
        context.user_data["awaiting_password"] = True
    await _reply(update, Messages.PASSWORD_PROMPT)
    raise ApplicationHandlerStop


async def global_auth_gate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback-query-path gate. Registered with group=-1 for all callback queries."""
    if not update.effective_user:
        raise ApplicationHandlerStop

    telegram_id = update.effective_user.id
    session = await auth_service.get_valid_session(telegram_id)
    if session:
        await auth_service.touch(session.session_token)
        return

    if update.callback_query:
        await update.callback_query.answer(Messages.UNAUTHORIZED, show_alert=True)
    raise ApplicationHandlerStop
