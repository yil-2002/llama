"""Single global handler for all destructive-action confirmations.

Every @confirm_destructive(...) decorated command shows a Ha/Yo'q keyboard
with callback_data "confirm:go:<action>" / "confirm:cancel:<action>".
This is the ONE place that keyboard is ever handled - previously the bot
had two incompatible callback_data formats and neither was wired to a
handler, so pressing "Ha" silently did nothing.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.constants import Messages
from bot.utils.decorators import CONFIRM_REGISTRY


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) < 3:
        return
    _, verdict, action_name = parts

    if verdict == "cancel":
        await query.edit_message_text(Messages.OPERATION_CANCELLED)
        return

    handler = CONFIRM_REGISTRY.get(action_name)
    if handler is None:
        await query.edit_message_text(
            Messages.ERROR_OCCURRED.format(error="Amal topilmadi yoki muddati o'tgan.")
        )
        return

    await query.edit_message_text(Messages.PROCESSING)

    from bot.database import Database  # local import: avoid import cycles at module load

    db = Database()
    user_id = update.effective_user.id if update.effective_user else 0
    success = True
    error_message = None
    try:
        await handler(update, context)
    except Exception as e:  # noqa: BLE001 - re-raise after logging
        success = False
        error_message = str(e)
        raise
    finally:
        try:
            await db.log_command(
                user_id=user_id,
                command=f"confirm:{action_name}",
                success=success,
                error_message=error_message,
            )
        except Exception:
            pass


def register_confirm_handlers(application) -> None:
    application.add_handler(CallbackQueryHandler(confirm_callback, pattern="^confirm:"))
