"""Decorators for confirmation flows and command logging.

Access control (owner-only password auth) is handled globally by
bot.middlewares.auth.global_auth_gate / global_auth_gate_callback, which
run before any handler in this file is ever reached. Nothing in this
module needs to check identity or role again.
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, Coroutine, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.constants import ButtonText, Messages

Handler = Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[Any, Any, None]]

# Registry mapping action_name -> the *undecorated* handler function.
# Populated automatically whenever @confirm_destructive(...) is applied.
# The generic confirm_callback (registered once in main.py) uses this to
# invoke the right function after the user taps "Ha".
CONFIRM_REGISTRY: Dict[str, Handler] = {}


def build_confirm_keyboard(action_name: str) -> InlineKeyboardMarkup:
    """Build the Ha/Yo'q keyboard for a registered destructive action.

    Shared by the @confirm_destructive decorator and by any menu callback
    that wants to trigger the same confirmation flow (e.g. system.py's
    inline "reboot" button), so there is exactly one callback_data format
    ("confirm:go:<action>" / "confirm:cancel:<action>") in the whole bot.
    """
    keyboard = [
        [
            InlineKeyboardButton(ButtonText.CONFIRM_GO, callback_data=f"confirm:go:{action_name}"),
            InlineKeyboardButton(ButtonText.CONFIRM_CANCEL, callback_data=f"confirm:cancel:{action_name}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_destructive(action_name: str) -> Callable[[Handler], Handler]:
    """Decorator that requires inline confirmation before a destructive
    action runs. Registers the wrapped (inner) handler under action_name
    so the shared confirm_callback (see bot/handlers/confirm.py) can find
    and invoke it once the user taps "Ha".

    Usage:
        @confirm_destructive("serverni qayta yuklash")
        async def reboot_command(update, context):
            ...
    """
    def decorator(handler: Handler) -> Handler:
        if action_name in CONFIRM_REGISTRY and CONFIRM_REGISTRY[action_name] is not handler:
            raise ValueError(
                f"confirm_destructive action name '{action_name}' is already registered "
                f"to a different handler - action names must be unique."
            )
        CONFIRM_REGISTRY[action_name] = handler

        @functools.wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if not update.effective_message:
                return
            await update.effective_message.reply_text(
                Messages.CONFIRMATION.format(action=action_name),
                reply_markup=build_confirm_keyboard(action_name),
                parse_mode="HTML",
            )
        return wrapper
    return decorator


def log_execution(command_name: str) -> Callable[[Handler], Handler]:
    """Decorator that records every command invocation to commands_log via
    Database.log_command, so /logs and future auditing have real data
    (previously this table was always empty because nothing called it).
    """
    def decorator(handler: Handler) -> Handler:
        @functools.wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            from bot.database import Database  # local import: avoid import cycles at module load

            db = Database()
            user_id = update.effective_user.id if update.effective_user else 0
            args = " ".join(context.args) if getattr(context, "args", None) else None
            start = time.monotonic()
            success = True
            error_message = None
            try:
                return await handler(update, context)
            except Exception as e:  # noqa: BLE001 - we re-raise after logging
                success = False
                error_message = str(e)
                raise
            finally:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                try:
                    await db.log_command(
                        user_id=user_id,
                        command=command_name,
                        args=args,
                        success=success,
                        error_message=error_message,
                        execution_time_ms=elapsed_ms,
                    )
                except Exception:
                    pass  # logging must never break the actual command
        return wrapper
    return decorator
