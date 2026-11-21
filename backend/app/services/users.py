from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import ActivityEvent, User, utcnow


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, first_name: str = "", username: str | None = None
) -> User:
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, first_name=first_name or "", username=username)
        session.add(user)
        await session.flush()
    else:
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if username != user.username:
            user.username = username
    return user


def local_today(now: datetime | None = None):
    return ((now or utcnow()) + timedelta(hours=get_settings().tz_offset_hours)).date()


def touch_streak(user: User, now: datetime | None = None) -> None:
    today = local_today(now)
    if user.last_active_date == today:
        return
    if user.last_active_date == today - timedelta(days=1):
        user.streak_days += 1
    else:
        user.streak_days = 1
    user.last_active_date = today


def log_event(session: AsyncSession, user: User, kind: str) -> None:
    session.add(ActivityEvent(user_id=user.id, kind=kind, level=user.level))


def _local_day_start_utc(now: datetime) -> datetime:
    off = timedelta(hours=get_settings().tz_offset_hours)
    local = now + off
    return local.replace(hour=0, minute=0, second=0, microsecond=0) - off


async def messages_used_today(session: AsyncSession, user: User, now: datetime | None = None) -> int:
    now = now or utcnow()
    return await session.scalar(
        select(func.count(ActivityEvent.id)).where(
            ActivityEvent.user_id == user.id,
            ActivityEvent.kind.in_(("message", "voice")),
            ActivityEvent.created_at >= _local_day_start_utc(now),
        )
    ) or 0


async def remaining_free_messages(session: AsyncSession, user: User) -> int | None:
    """Premium foydalanuvchi uchun None (cheksiz)."""
    if user.is_premium():
        return None
    return max(0, get_settings().free_daily_messages - await messages_used_today(session, user))


def grant_premium(user: User, days: int, now: datetime | None = None) -> None:
    now = now or utcnow()
    start = user.premium_until if user.premium_until and user.premium_until > now else now
    user.premium_until = start + timedelta(days=days)
