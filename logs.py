"""Loglar handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Messages
from bot.database import Database
from bot.keyboards import get_back_keyboard, get_logs_menu_keyboard
from bot.services import DockerService, SystemService
from bot.utils import log_execution, escape_html, truncate_text

db = Database()
system = SystemService()
docker = DockerService()


@log_execution("logs")
async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/logs buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        Messages.LOGS_HEADER,
        reply_markup=get_logs_menu_keyboard(),
        parse_mode="HTML",
    )


@log_execution("logs_search")
async def logs_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/logs_search <naqsh> buyrug'i."""
    if not update.effective_message:
        return
    if not context.args:
        await update.effective_message.reply_text("🔍 <b>Loglarni qidirish</b>\n\nNaqshni kiriting: <code>/logs_search error</code>", parse_mode="HTML")
        return

    pattern = context.args[0]
    logs = await db.get_command_logs(limit=100)
    matches = [log for log in logs if pattern.lower() in str(log.get("command", "")).lower()]

    if not matches:
        await update.effective_message.reply_text("📭 Hech narsa topilmadi.")
        return

    lines = []
    for log in matches[:20]:
        lines.append(
            f"📋 {log.get('created_at', '')} | "
            f"User: {log.get('user_id', '')} | "
            f"Cmd: {log.get('command', '')}"
        )

    text = f"🔍 <b>Qidirish natijalari ({len(matches)} ta)</b>\n\n" + "\n".join(lines)
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def logs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loglar callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    source = data[1] if len(data) > 1 else ""

    if source == "bot":
        logs = await db.get_command_logs(limit=50)
        if not logs:
            await query.edit_message_text(Messages.LOGS_NOT_FOUND, reply_markup=get_back_keyboard())
            return
        lines = []
        for log in logs[:20]:
            status = "✅" if log.get("success") else "❌"
            lines.append(f"{status} {log.get('created_at', '')[:16]} | {log.get('command', '')}")
        text = Messages.LOGS_CONTENT.format(source="Bot", lines=len(lines), content="\n".join(lines))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif source == "system":
        from bot.utils import safe_subprocess
        code, out, _ = await safe_subprocess(["journalctl", "-n", "50", "--no-pager"], timeout=10)
        content = out if code == 0 else "Loglarni olishda xatolik"
        text = Messages.LOGS_CONTENT.format(source="Tizim", lines=50, content=escape_html(content[:3000]))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif source == "service":
        await query.edit_message_text(
            "⚙️ <b>Xizmat loglari</b>\n\nBu funksiya tez orada qo'shiladi.",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )

    elif source == "nginx":
        from bot.utils import safe_subprocess
        code, out, _ = await safe_subprocess(["sudo", "tail", "-n", "50", "/var/log/nginx/error.log"], timeout=10)
        content = out if code == 0 else "Loglarni olishda xatolik"
        text = Messages.LOGS_CONTENT.format(source="Nginx", lines=50, content=escape_html(content[:3000]))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif source == "docker":
        containers = await docker.list_containers(all_containers=False)
        if not containers:
            await query.edit_message_text("📭 Ishlayotgan konteynerlar yo'q.", reply_markup=get_back_keyboard())
            return
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        for c in containers[:10]:
            keyboard.append([InlineKeyboardButton(f"📋 {c['name']}", callback_data=f"logs:docker_logs:{c['name']}")])
        keyboard.append([InlineKeyboardButton(ButtonText.BACK, callback_data="logs:back")])
        await query.edit_message_text("🐳 <b>Konteiner loglari</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif source == "docker_logs" and len(data) > 2:
        container_name = data[2]
        logs = await docker.get_container_logs(container_name, tail=50)
        text = Messages.LOGS_CONTENT.format(source=f"Docker: {container_name}", lines=50, content=escape_html(logs[:3000]))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


from bot.constants import ButtonText

def register_logs_handlers(application) -> None:
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("logs_search", logs_search_command))
    application.add_handler(CallbackQueryHandler(logs_callback, pattern="^logs:"))
