"""Tizim boshqaruv handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.constants import Emoji, Messages
from bot.keyboards import get_back_keyboard, get_system_menu_keyboard
from bot.services import SystemService
from bot.utils import log_execution, build_confirm_keyboard, confirm_destructive

system = SystemService()


async def system_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tizim menyusi."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "⚙️ <b>Tizim Boshqaruvi</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_system_menu_keyboard(),
        parse_mode="HTML",
    )


@confirm_destructive("serverni qayta yuklash")
async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/reboot buyrug'i."""
    if not update.effective_message:
        return
    result = await system.reboot()
    if result.get("success"):
        await update.effective_message.reply_text(Messages.REBOOT_INITIATED)
    else:
        await update.effective_message.reply_text(
            Messages.ERROR_OCCURRED.format(error=result.get("error", "Noma'lum")),
            parse_mode="HTML",
        )


@confirm_destructive("serverni o'chirish")
async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/shutdown buyrug'i."""
    if not update.effective_message:
        return
    result = await system.shutdown()
    if result.get("success"):
        await update.effective_message.reply_text(Messages.SHUTDOWN_INITIATED)
    else:
        await update.effective_message.reply_text(
            Messages.ERROR_OCCURRED.format(error=result.get("error", "Noma'lum")),
            parse_mode="HTML",
        )


@log_execution("services")
async def services_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/services buyrug'i."""
    if not update.effective_message:
        return

    services_list = await system.list_services()
    if not services_list:
        await update.effective_message.reply_text("📭 Xizmatlar topilmadi.")
        return

    lines = []
    for svc in services_list[:15]:
        status = Emoji.ACTIVE if svc.get("active") == "active" else Emoji.ERROR
        lines.append(f"{status} <b>{svc['name']}</b> - {svc.get('description', '')}")

    text = Messages.SERVICE_STATUS.format(services="\n".join(lines))
    await update.effective_message.reply_text(text, parse_mode="HTML")


@log_execution("update")
async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/update buyrug'i."""
    if not update.effective_message:
        return

    loading_msg = await update.effective_message.reply_text(
        Messages.SYSTEM_UPDATE.format(output="Boshlanmoqda..."),
        parse_mode="HTML",
    )

    result = await system.update_packages()

    if loading_msg:
        try:
            await loading_msg.delete()
        except Exception:
            pass

    if result.get("success"):
        await update.effective_message.reply_text(Messages.SYSTEM_UPDATE_DONE)
    else:
        await update.effective_message.reply_text(
            Messages.ERROR_OCCURRED.format(error=result.get("upgrade_output", "Noma'lum")),
            parse_mode="HTML",
        )


@log_execution("ufw")
async def ufw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ufw buyrug'i."""
    if not update.effective_message:
        return

    status = await system.get_ufw_status()
    text = Messages.UFW_STATUS.format(status=status.get("output", "Noma'lum"))
    await update.effective_message.reply_text(text, parse_mode="HTML")


@log_execution("cron")
async def cron_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cron buyrug'i."""
    if not update.effective_message:
        return

    jobs = await system.list_cron_jobs()
    if not jobs:
        await update.effective_message.reply_text("📭 Cron vazifalari yo'q.", reply_markup=get_back_keyboard())
        return

    lines = [f"⏰ <code>{j['schedule']}</code> {j['command']}" for j in jobs]
    text = Messages.CRON_LIST.format(jobs="\n".join(lines))
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def system_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tizim callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "services":
        services_list = await system.list_services()
        if not services_list:
            await query.edit_message_text("📭 Xizmatlar topilmadi.", reply_markup=get_back_keyboard())
            return
        lines = [f"{'🟢' if s.get('active') == 'active' else '🔴'} <b>{s['name']}</b>" for s in services_list[:15]]
        text = Messages.SERVICE_STATUS.format(services="\n".join(lines))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "update":
        await query.edit_message_text("🔄 Yangilanmoqda...", reply_markup=get_back_keyboard())
        result = await system.update_packages()
        if result.get("success"):
            await query.edit_message_text(Messages.SYSTEM_UPDATE_DONE, reply_markup=get_back_keyboard())
        else:
            await query.edit_message_text(
                Messages.ERROR_OCCURRED.format(error="Yangilashda xatolik"),
                reply_markup=get_back_keyboard(),
                parse_mode="HTML",
            )

    elif action == "ufw":
        status = await system.get_ufw_status()
        text = Messages.UFW_STATUS.format(status=status.get("output", "Noma'lum"))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "cron":
        jobs = await system.list_cron_jobs()
        if not jobs:
            await query.edit_message_text("📭 Cron vazifalari yo'q.", reply_markup=get_back_keyboard())
            return
        lines = [f"⏰ <code>{j['schedule']}</code> {j['command']}" for j in jobs]
        text = Messages.CRON_LIST.format(jobs="\n".join(lines))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "reboot":
        await query.edit_message_text(
            Messages.REBOOT_CONFIRM,
            reply_markup=build_confirm_keyboard("serverni qayta yuklash"),
            parse_mode="HTML",
        )


def register_system_handlers(application) -> None:
    application.add_handler(CommandHandler("reboot", reboot_command))
    application.add_handler(CommandHandler("shutdown", shutdown_command))
    application.add_handler(CommandHandler("services", services_command))
    application.add_handler(CommandHandler("update", update_command))
    application.add_handler(CommandHandler("ufw", ufw_command))
    application.add_handler(CommandHandler("cron", cron_command))
    application.add_handler(CallbackQueryHandler(system_callback, pattern="^system:"))
