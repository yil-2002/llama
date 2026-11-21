"""Admin dashboard: faollik soat va daraja bo'yicha."""
from datetime import timedelta

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import LEVELS, ActivityEvent, Payment, User, utcnow

ACTIVE_KINDS = ("message", "voice")


async def build_dashboard(session: AsyncSession, days: int = 7) -> dict:
    now = utcnow()
    since = now - timedelta(days=days)
    off = get_settings().tz_offset_hours

    # 1) Soat bo'yicha faollik (Toshkent vaqti), oxirgi N kun
    hour_col = extract("hour", ActivityEvent.created_at)
    rows = await session.execute(
        select(hour_col, func.count())
        .where(ActivityEvent.created_at >= since, ActivityEvent.kind.in_(ACTIVE_KINDS))
        .group_by(hour_col)
    )
    by_hour = [0] * 24
    for hour, count in rows.all():
        by_hour[(int(hour) + off) % 24] += count

    # 2) Daraja bo'yicha: foydalanuvchilar soni va oxirgi N kundagi xabarlar
    users_rows = await session.execute(select(User.level, func.count()).group_by(User.level))
    users_by_level = {lvl or "unknown": c for lvl, c in users_rows.all()}
    act_rows = await session.execute(
        select(ActivityEvent.level, func.count())
        .where(ActivityEvent.created_at >= since, ActivityEvent.kind.in_(ACTIVE_KINDS))
        .group_by(ActivityEvent.level)
    )
    activity_by_level = {lvl or "unknown": c for lvl, c in act_rows.all()}
    levels = [*LEVELS, "unknown"]

    # 3) Umumiy ko'rsatkichlar
    total_users = await session.scalar(select(func.count(User.id))) or 0
    premium_users = await session.scalar(select(func.count(User.id)).where(User.premium_until > now)) or 0
    active_users = (
        await session.scalar(
            select(func.count(func.distinct(ActivityEvent.user_id))).where(
                ActivityEvent.created_at >= since, ActivityEvent.kind.in_(ACTIVE_KINDS)
            )
        )
        or 0
    )
    new_users = await session.scalar(select(func.count(User.id)).where(User.created_at >= since)) or 0
    stars_revenue = (
        await session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.created_at >= since, Payment.currency == "XTR"
            )
        )
        or 0
    )

    peak_hour = max(range(24), key=lambda h: by_hour[h]) if any(by_hour) else None
    return {
        "days": days,
        "totals": {
            "users": total_users,
            "premium": premium_users,
            "active": active_users,
            "new": new_users,
            "stars_revenue": stars_revenue,
        },
        "by_hour": by_hour,
        "peak_hour": peak_hour,
        "levels": [
            {"level": lvl, "users": users_by_level.get(lvl, 0), "messages": activity_by_level.get(lvl, 0)}
            for lvl in levels
        ],
    }


def _bar(value: int, max_value: int, width: int = 12) -> str:
    if max_value <= 0:
        return ""
    return "█" * max(1 if value else 0, round(width * value / max_value))


def format_dashboard_text(d: dict) -> str:
    """Bot ichidagi /stats uchun matnli dashboard."""
    t = d["totals"]
    lines = [
        f"📊 <b>Dashboard — oxirgi {d['days']} kun</b>",
        f"👥 Jami: {t['users']} · yangi: {t['new']} · faol: {t['active']}",
        f"⭐ Premium: {t['premium']} · tushum: {t['stars_revenue']} Stars",
        "",
        "<b>Soat bo'yicha faollik</b> (Toshkent vaqti)",
    ]
    hours = d["by_hour"]
    # 3 soatlik bloklar — Telegram xabarida ixcham ko'rinadi
    blocks = [(h, sum(hours[h : h + 3])) for h in range(0, 24, 3)]
    mx = max(v for _, v in blocks)
    for h, v in blocks:
        lines.append(f"<code>{h:02d}-{h + 3:02d}</code> {_bar(v, mx)} {v}")
    if d["peak_hour"] is not None:
        lines.append(f"Eng faol soat: {d['peak_hour']:02d}:00")
    lines += ["", "<b>Daraja bo'yicha</b> (foydalanuvchi / xabar)"]
    mx = max((row["messages"] for row in d["levels"]), default=0)
    for row in d["levels"]:
        if row["users"] or row["messages"]:
            name = "?" if row["level"] == "unknown" else row["level"]
            lines.append(f"<code>{name:>2}</code> {_bar(row['messages'], mx)} {row['users']} / {row['messages']}")
    return "\n".join(lines)
