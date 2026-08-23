"""Start va yordam handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.constants import Messages
from bot.keyboards import get_main_menu_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'i.

    Authentication (password prompt / session check) already happened in
    bot.middlewares.auth.global_auth_gate before this handler is ever
    reached, so by the time we get here the account/device is a
    logged-in owner session.
    """
    if not update.effective_message:
        return

    await update.effective_message.reply_text(
        Messages.START,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(Messages.HELP, parse_mode="HTML")


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Asosiy menyu callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    if query.data == "menu:main":
        await query.edit_message_text(
            Messages.MAIN_MENU_TEXT,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML",
        )


async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Orqaga callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        Messages.MAIN_MENU_TEXT,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )


def register_start_handlers(application) -> None:
    """Start handlerlarini ro'yxatdan o'tkazish."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu:main$"))
    application.add_handler(CallbackQueryHandler(back_callback, pattern="^.*:back$"))
