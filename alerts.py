"""Alert threshold management and manual daily-report trigger."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.constants import Messages
from bot.database import Database
from bot.services.scheduler_service import daily_report_job
from bot.utils import log_execution

db = Database()

VALID_METRICS = {"cpu", "ram", "disk"}


def _format_alert_line(alert: dict) -> str:
    status = "🟢" if alert.get("enabled") else "⚪️"
    return (
        f"{status} <b>{alert['metric']}</b> — {alert['threshold']}% "
        f"({alert['duration_minutes']} daq.) "
        f"— oxirgi trigger: {alert.get('last_triggered_at') or 'hech qachon'}"
    )


@log_execution("alerts")
async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/alerts - show current threshold configuration."""
    if not update.effective_message:
        return
    await db.ensure_default_alerts()
    alerts = await db.get_alerts()
    if not alerts:
        await update.effective_message.reply_text(Messages.NO_ALERTS)
        return
    lines = [_format_alert_line(a) for a in alerts]
    await update.effective_message.reply_text(
        Messages.ALERT_LIST.format(alerts="\n".join(lines)), parse_mode="HTML"
    )


@log_execution("alert_set")
async def alert_set_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/alert_set <metric> <threshold> [duration_minutes] - configure a threshold."""
    if not update.effective_message:
        return

    args = context.args or []
    if len(args) < 2:
        await update.effective_message.reply_text(Messages.ALERT_SET_USAGE, parse_mode="HTML")
        return

    metric = args[0].lower()
    if metric not in VALID_METRICS:
        await update.effective_message.reply_text(Messages.ALERT_SET_USAGE, parse_mode="HTML")
        return

    try:
        threshold = float(args[1])
        duration = int(args[2]) if len(args) > 2 else 5
    except ValueError:
        await update.effective_message.reply_text(Messages.ALERT_SET_USAGE, parse_mode="HTML")
        return

    threshold = max(1.0, min(threshold, 100.0))
    duration = max(1, duration)

    await db.upsert_alert(metric, threshold, duration, enabled=True)
    await update.effective_message.reply_text(
        Messages.ALERT_SET_CONFIRM.format(metric=metric, threshold=threshold, duration=duration),
        parse_mode="HTML",
    )


@log_execution("report_now")
async def report_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/report_now - immediately send the daily report (for testing)."""
    if not update.effective_message:
        return
    await daily_report_job(context)
    await update.effective_message.reply_text(Messages.REPORT_SENT)


def register_alert_handlers(application) -> None:
    application.add_handler(CommandHandler("alerts", alerts_command))
    application.add_handler(CommandHandler("alert_set", alert_set_command))
    application.add_handler(CommandHandler("report_now", report_now_command))
