"""Zaxira handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Emoji, Messages
from bot.database import Database
from bot.keyboards import get_back_keyboard, get_backup_menu_keyboard
from bot.models import BackupMeta, BackupStatus
from bot.services import BackupService
from bot.utils import log_execution, bytes_to_human

backup_service = BackupService()
db = Database()


@log_execution("backup")
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/backup buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "💾 <b>Zaxira Boshqaruvi</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_backup_menu_keyboard(),
        parse_mode="HTML",
    )


@log_execution("backup_schedule")
async def backup_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/backup_schedule buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "📅 <b>Zaxira jadvali</b>\n\nBu funksiya tez orada qo'shiladi.",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML",
    )


async def backup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zaxira callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "type" and len(data) > 2:
        backup_type = data[2]
        loading_msg = await query.edit_message_text(
            Messages.BACKUP_STARTED.format(type=backup_type),
            parse_mode="HTML",
        )

        result = await backup_service.create_backup(
            name=f"backup_{backup_type}",
            backup_type=backup_type,
        )

        if result.get("success"):
            # Save to DB
            backup_meta = BackupMeta(
                name=result["name"],
                path=result["path"],
                size_bytes=result["size"],
                status=BackupStatus.COMPLETED,
                created_by=update.effective_user.id if update.effective_user else None,
            )
            await db.create_backup_record(backup_meta)

            text = Messages.BACKUP_COMPLETED.format(
                name=result["name"],
                size=result["size_human"],
                path=result["path"],
            )
            await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
        else:
            await query.edit_message_text(
                Messages.BACKUP_FAILED.format(error=result.get("error", "Noma'lum")),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )

    elif action == "schedule":
        await query.edit_message_text(
            "📅 <b>Zaxira jadvali</b>\n\nTez orada qo'shiladi.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )


def register_backup_handlers(application) -> None:
    application.add_handler(CommandHandler("backup", backup_command))
    application.add_handler(CommandHandler("backup_schedule", backup_schedule_command))
    application.add_handler(CallbackQueryHandler(backup_callback, pattern="^backup:"))
