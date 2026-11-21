from datetime import timedelta

from app.db import SessionLocal
from app.models import ActivityEvent, User, utcnow
from app.services.dashboard import build_dashboard, format_dashboard_text


async def test_hours_use_tashkent_time():
    async with SessionLocal() as s:
        u = User(telegram_id=9001, level="C1")
        s.add(u)
        await s.flush()
        before = (await build_dashboard(s))["by_hour"][0]
        # 19:00 UTC = 00:00 Toshkent
        now = (utcnow() - timedelta(days=1)).replace(hour=19, minute=30)
        s.add(ActivityEvent(user_id=u.id, kind="message", level="C1", created_at=now))
        await s.commit()
        d = await build_dashboard(s)
        assert d["by_hour"][0] == before + 1
        assert "C1" in format_dashboard_text(d)
