"""Daily report and threshold-alert background jobs.

Registered via PTB's built-in JobQueue in bot/main.py (no extra
dependency like APScheduler needed - python-telegram-bot[job-queue]
already provides this).
"""
from __future__ import annotations

import socket
from datetime import datetime
from typing import Any

from loguru import logger
from telegram.ext import ContextTypes

from bot.config import settings
from bot.constants import Messages
from bot.database import Database
from bot.services import DockerService, SystemService
from bot.utils import bytes_to_human

system_service = SystemService()
docker_service = DockerService()
db = Database()


async def _notify(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Send a message to the notification chat(s).

    If TELEGRAM_SUPERADMIN_ID is configured, notifications go there only.
    Otherwise (the default, since the bot has no fixed "admin" concept -
    only a shared password), the message is broadcast to every currently
    active session (i.e. every account/device that is logged in right
    now).
    """
    if settings.telegram_superadmin_id:
        try:
            await context.bot.send_message(
                chat_id=settings.telegram_superadmin_id, text=text, parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Bildirishnoma yuborib bo'lmadi: {e}")
        return

    sessions = await db.get_all_sessions(active_only=True)
    if not sessions:
        logger.warning("Bildirishnoma yuborilmadi: hech qanday faol sessiya yo'q.")
        return
    for session in sessions:
        try:
            await context.bot.send_message(
                chat_id=session.telegram_id, text=text, parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Bildirishnoma yuborib bo'lmadi ({session.telegram_id}): {e}")


async def daily_report_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a daily summary of system health, docker status and backups."""
    try:
        stats = await system_service.get_stats()
        uptime = await system_service.get_uptime()

        containers = await docker_service.list_containers(all_containers=True)
        containers = [c for c in containers if isinstance(c, dict) and "status" in c]
        running = sum(1 for c in containers if c.get("status") == "running")

        backups = await db.get_backups(limit=1)
        last_backup = (
            f"{backups[0].name} ({backups[0].created_at})" if backups else "hali yo'q"
        )

        text = Messages.DAILY_REPORT.format(
            hostname=socket.gethostname(),
            uptime=uptime,
            cpu=round(stats.cpu_percent, 1),
            ram=round(stats.ram_percent, 1),
            disk=round(stats.disk_percent, 1),
            load=round(stats.load_avg_1m, 2),
            docker_running=running,
            docker_total=len(containers),
            last_backup=last_backup,
        )
        await _notify(context, text)
    except Exception as e:
        logger.error(f"Kunlik hisobotni tayyorlashda xatolik: {e}")


async def _check_metric_alert(context: ContextTypes.DEFAULT_TYPE, metric: str, value: float) -> None:
    """Debounced threshold check for a single percentage metric (cpu/ram/disk).

    An alert only fires once the metric has been continuously above the
    threshold for `duration_minutes` (avoids spamming for brief spikes),
    and won't fire again until the value drops back below the threshold.
    """
    config = await db.get_alert(metric)
    if not config or not config.get("enabled"):
        return

    threshold = float(config["threshold"])
    duration_minutes = int(config.get("duration_minutes") or 5)
    above_since = config.get("above_since")
    now = datetime.utcnow()

    if value < threshold:
        if above_since:
            await db.set_alert_above_since(metric, None)
        return

    if not above_since:
        await db.set_alert_above_since(metric, now.isoformat(sep=" ", timespec="seconds"))
        return

    since_dt = datetime.fromisoformat(above_since)
    elapsed_minutes = (now - since_dt).total_seconds() / 60
    if elapsed_minutes < duration_minutes:
        return  # not sustained long enough yet

    await db.mark_alert_triggered(metric)
    text = Messages.ALERT_TRIGGERED.format(
        metric=metric,
        value=round(value, 1),
        threshold=threshold,
        timestamp=now.isoformat(sep=" ", timespec="seconds"),
    )
    await _notify(context, text)


async def _check_container_alerts(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Alert once when a previously-running container stops (dedup via
    Database settings key so we don't re-alert every interval)."""
    containers = await docker_service.list_containers(all_containers=True)
    containers = [c for c in containers if isinstance(c, dict) and "name" in c]

    import json

    raw = await db.get_setting("alert_container_down_state", "{}")
    try:
        known_down = set(json.loads(raw))
    except Exception:
        known_down = set()

    currently_down = set()
    for c in containers:
        if c.get("status") not in ("running",):
            currently_down.add(c["name"])
            if c["name"] not in known_down:
                text = Messages.CONTAINER_DOWN_ALERT.format(
                    name=c["name"],
                    status=c.get("status", "noma'lum"),
                    timestamp=datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
                )
                await _notify(context, text)

    if currently_down != known_down:
        await db.set_setting("alert_container_down_state", json.dumps(sorted(currently_down)))


async def alert_check_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job: check cpu/ram/disk thresholds and container health."""
    try:
        await db.ensure_default_alerts()
        stats = await system_service.get_stats()
        await _check_metric_alert(context, "cpu", stats.cpu_percent)
        await _check_metric_alert(context, "ram", stats.ram_percent)
        await _check_metric_alert(context, "disk", stats.disk_percent)
        await _check_container_alerts(context)
    except Exception as e:
        logger.error(f"Alert tekshiruvida xatolik: {e}")
