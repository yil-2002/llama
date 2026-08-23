"""Monitoring handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Emoji, Messages
from bot.database import Database
from bot.keyboards import get_back_keyboard, get_monitoring_menu_keyboard
from bot.models import SystemStats
from bot.services import SystemService
from bot.utils import log_execution, bytes_to_human, escape_html, format_status_emoji, seconds_to_human

system = SystemService()
db = Database()


@log_execution("status")
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status buyrug'i."""
    if not update.effective_message:
        return

    stats = await system.get_stats()
    uptime = await system.get_uptime()
    cpu_emoji = format_status_emoji(stats.cpu_percent)
    ram_emoji = format_status_emoji(stats.ram_percent)
    disk_emoji = format_status_emoji(stats.disk_percent)

    text = Messages.STATUS_OVERVIEW.format(
        status_emoji=Emoji.ACTIVE,
        uptime=uptime,
        cpu=round(stats.cpu_percent, 1),
        cores=4,  # TODO: get actual core count
        ram_used=bytes_to_human(stats.ram_used_bytes),
        ram_total=bytes_to_human(stats.ram_total_bytes),
        ram_percent=round(stats.ram_percent, 1),
        disk_used=bytes_to_human(stats.disk_used_bytes),
        disk_total=bytes_to_human(stats.disk_total_bytes),
        disk_percent=round(stats.disk_percent, 1),
        net_recv=bytes_to_human(stats.network_recv_bytes),
        net_sent=bytes_to_human(stats.network_sent_bytes),
        load=round(stats.load_avg_1m, 2),
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")

    # Save stats to DB
    await db.insert_stats(stats)


@log_execution("top")
async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/top buyrug'i."""
    if not update.effective_message:
        return

    processes = await system.get_top_processes(sort_by="cpu", limit=10)
    lines = []
    for i, p in enumerate(processes, 1):
        lines.append(
            f"{i}. <b>{escape_html(p['name'])}</b> (PID: {p['pid']})\n"
            f"   🧠 CPU: {p['cpu_percent']}% | 💾 RAM: {bytes_to_human(p['memory_rss'])}"
        )

    text = Messages.TOP_PROCESSES.format(sort_by="CPU", processes="\n\n".join(lines))
    await update.effective_message.reply_text(text, parse_mode="HTML")


@log_execution("net")
async def net_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/net buyrug'i."""
    if not update.effective_message:
        return

    net_info = await system.get_network_info()
    public_ip = await system.get_public_ip()

    interfaces = "\n".join(
        f"   • {name}: {', '.join(ips)}"
        for name, ips in net_info["interfaces"].items()
    )

    text = Messages.NETWORK_INFO.format(
        public_ip=public_ip,
        interfaces=interfaces,
        sent=bytes_to_human(net_info["bytes_sent"]),
        recv=bytes_to_human(net_info["bytes_recv"]),
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")


@log_execution("history")
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/history buyrug'i."""
    if not update.effective_message:
        return

    stats_history = await db.get_stats_history(hours=24)
    if not stats_history:
        await update.effective_message.reply_text(Messages.NO_DATA)
        return

    lines = []
    for stat in stats_history[:10]:
        lines.append(
            f"{stat.created_at[:16]} | "
            f"CPU: {round(stat.cpu_percent, 1)}% | "
            f"RAM: {round(stat.ram_percent, 1)}% | "
            f"Disk: {round(stat.disk_percent, 1)}%"
        )

    text = "📈 <b>So'nggi 24 soat statistikasi</b>\n\n" + "\n".join(lines)
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def monitoring_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monitoring callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "status":
        await status_command(update, context)
    elif action == "top":
        await top_command(update, context)
    elif action == "net":
        await net_command(update, context)
    elif action == "history":
        await history_command(update, context)


def register_monitoring_handlers(application) -> None:
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("top", top_command))
    application.add_handler(CommandHandler("net", net_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CallbackQueryHandler(monitoring_callback, pattern="^monitor:"))
