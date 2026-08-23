"""Fayl menejeri handlerlari."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from bot.config import settings
from bot.constants import Emoji, Messages
from bot.keyboards import get_back_keyboard
from bot.utils import log_execution, escape_html, validate_path


def _safe_filename(raw_name: Optional[str]) -> str:
    """Reduce an attacker-controlled Telegram file_name to a bare, safe
    filename with no directory components, so it can never be used to
    write outside settings.bot_data_dir (e.g. via "../../etc/cron.d/x").
    """
    name = Path(raw_name or "").name  # strips any "/", drive letters, etc.
    if not name or name in (".", ".."):
        name = f"upload_{int(time.time())}"
    return name


@log_execution("files")
async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/files buyrug'i."""
    if not update.effective_message:
        return

    base_dir = settings.bot_data_dir
    await _show_directory(update, context, base_dir)


async def _show_directory(update: Update, context: ContextTypes.DEFAULT_TYPE, path: Path) -> None:
    """Katalogni ko'rsatish."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        if update.effective_message:
            await update.effective_message.reply_text("❌ Ruxsat yo'q.")
        return

    keyboard = []
    lines = [f"📁 <b>{escape_html(str(path))}</b>\n"]

    for item in items[:20]:
        if item.is_dir():
            icon = Emoji.FOLDER
            callback = f"file:dir:{item}"
        else:
            icon = Emoji.FILE
            callback = f"file:file:{item}"
        keyboard.append([InlineKeyboardButton(f"{icon} {item.name}", callback_data=callback)])

    if str(path) != str(settings.bot_data_dir):
        keyboard.append([InlineKeyboardButton(Emoji.BACK + " Yuqoriga", callback_data=f"file:dir:{path.parent}")])
    keyboard.append([InlineKeyboardButton(Emoji.HOME + " Asosiy menyu", callback_data="menu:main")])

    text = Messages.FILE_MANAGER_HEADER.format(path=escape_html(str(path)))
    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fayl callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":", 2)
    if len(data) < 3:
        return

    action = data[1]
    try:
        path = validate_path(data[2], base_dir=settings.bot_data_dir)
    except ValueError:
        await query.edit_message_text(
            Messages.FILE_NOT_FOUND.format(path=escape_html(data[2])),
            reply_markup=get_back_keyboard(),
        )
        return

    if action == "dir":
        await _show_directory(update, context, path)
    elif action == "file":
        try:
            if not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:  # 20MB
                await query.edit_message_text(Messages.FILE_TOO_LARGE, reply_markup=get_back_keyboard())
                return
            # Send file
            await query.message.reply_document(document=open(path, "rb"), filename=path.name)
        except Exception as e:
            await query.edit_message_text(Messages.ERROR_OCCURRED.format(error=str(e)), reply_markup=get_back_keyboard())


@log_execution("find")
async def find_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/find <naqsh> buyrug'i."""
    if not update.effective_message:
        return
    if not context.args:
        await update.effective_message.reply_text("🔍 <b>Qidirish</b>\n\nNaqshni kiriting: <code>/find *.py</code>", parse_mode="HTML")
        return

    pattern = context.args[0]
    base_dir = settings.bot_data_dir

    try:
        matches = list(base_dir.rglob(pattern))
        if not matches:
            await update.effective_message.reply_text("📭 Hech narsa topilmadi.")
            return

        lines = [f"{'📁' if m.is_dir() else '📄'} {m.relative_to(base_dir)}" for m in matches[:20]]
        text = f"🔍 <b>Qidirish natijalari ({len(matches)} ta)</b>\n\n" + "\n".join(lines)
        await update.effective_message.reply_text(text, parse_mode="HTML")
    except Exception as e:
        await update.effective_message.reply_text(Messages.ERROR_OCCURRED.format(error=str(e)), parse_mode="HTML")


async def file_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fayl yuklash handler."""
    if not update.effective_message or not update.effective_message.document:
        return

    doc = update.effective_message.document
    if doc.file_size and doc.file_size > 50 * 1024 * 1024:
        await update.effective_message.reply_text(Messages.FILE_TOO_LARGE)
        return

    try:
        file = await doc.get_file()
        safe_name = _safe_filename(doc.file_name)
        dest_path = validate_path(str(settings.bot_data_dir / safe_name), base_dir=settings.bot_data_dir)
        await file.download_to_drive(dest_path)
        await update.effective_message.reply_text(
            Messages.FILE_UPLOADED.format(path=escape_html(str(dest_path))),
            parse_mode="HTML",
        )
    except Exception as e:
        await update.effective_message.reply_text(Messages.ERROR_OCCURRED.format(error=str(e)), parse_mode="HTML")


def register_file_handlers(application) -> None:
    application.add_handler(CommandHandler("files", files_command))
    application.add_handler(CommandHandler("find", find_command))
    application.add_handler(CallbackQueryHandler(file_callback, pattern="^file:"))
    application.add_handler(MessageHandler(filters.Document.ALL, file_upload_handler))
