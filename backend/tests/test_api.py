from datetime import timedelta

from sqlalchemy import select

from app.db import SessionLocal
from app.models import ActivityEvent, User
from app.payments import record_payment

from .conftest import auth


async def test_unauthorized(client):
    r = await client.get("/api/me", headers={"X-Telegram-Init-Data": "hash=bad"})
    assert r.status_code == 401


async def test_chat_flow_and_feedback(client, fake_llm):
    h = auth(100)
    r = await client.patch("/api/me", json={"level": "A2", "goal": "speaking"}, headers=h)
    assert r.status_code == 200 and r.json()["level"] == "A2"

    r = await client.post("/api/chats", json={"mode": "free"}, headers=h)
    assert r.status_code == 200, r.text
    chat_id = r.json()["id"]
    assert r.json()["reply"]

    r = await client.post(f"/api/chats/{chat_id}/messages", json={"text": "I goed to park"}, headers=h)
    assert r.status_code == 200 and "reply" in r.json()
    # LLM'ga daraja va tarix yuborilganini tekshiramiz
    system = fake_llm.calls[-1][1][0]["content"]
    assert "A2" in system

    r = await client.post(f"/api/chats/{chat_id}/finish", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["overall_band"] == 6.5
    assert r.json()["mistakes"][0]["better"] == "I went"

    r = await client.get("/api/history", headers=h)
    assert r.json()[0]["overall_band"] == 6.5
    me = (await client.get("/api/me", headers=h)).json()
    assert me["streak_days"] == 1


async def test_voice(client, fake_llm):
    h = auth(101)
    chat_id = (await client.post("/api/chats", json={"mode": "free"}, headers=h)).json()["id"]
    r = await client.post(f"/api/chats/{chat_id}/voice", files={"audio": ("a.webm", b"xx")}, headers=h)
    assert r.status_code == 200
    assert r.json()["transcript"] == "I like football"


async def test_free_limit_and_premium(client, fake_llm):
    h = auth(102)
    chat_id = (await client.post("/api/chats", json={"mode": "free"}, headers=h)).json()["id"]
    for _ in range(3):
        assert (await client.post(f"/api/chats/{chat_id}/messages", json={"text": "hi"}, headers=h)).status_code == 200
    r = await client.post(f"/api/chats/{chat_id}/messages", json={"text": "hi"}, headers=h)
    assert r.status_code == 402

    # IELTS rejimi premium talab qiladi
    assert (await client.post("/api/chats", json={"mode": "ielts_p2"}, headers=h)).status_code == 402

    r = await client.post("/api/trial", headers=h)
    assert r.json()["is_premium"] is True
    assert (await client.post("/api/trial", headers=h)).status_code == 409
    assert (await client.post(f"/api/chats/{chat_id}/messages", json={"text": "hi"}, headers=h)).status_code == 200
    assert (await client.post("/api/chats", json={"mode": "ielts_p2"}, headers=h)).status_code == 200


async def test_payment_idempotent():
    async with SessionLocal() as s:
        user = User(telegram_id=555)
        s.add(user)
        await s.commit()
        assert await record_payment(s, user, "stars", "ch_1", 300, "XTR", 30)
        first_until = user.premium_until
        assert not await record_payment(s, user, "stars", "ch_1", 300, "XTR", 30)
        assert user.premium_until == first_until
        assert await record_payment(s, user, "stars", "ch_2", 300, "XTR", 30)  # oylik yangilanish
        assert user.premium_until - first_until == timedelta(days=30)


async def test_plans_only_in_telegram(client):
    plans = (await client.get("/api/payments/plans")).json()
    assert [p["provider"] for p in plans] == ["stars"]
    assert plans[0]["currency"] == "XTR"


async def test_dashboard(client, fake_llm):
    assert (await client.get("/api/admin/dashboard", headers=auth(100))).status_code == 403
    r = await client.get("/api/admin/dashboard", headers=auth(1, "Admin"))
    assert r.status_code == 200
    d = r.json()
    assert len(d["by_hour"]) == 24
    async with SessionLocal() as s:
        n = len((await s.scalars(select(ActivityEvent).where(ActivityEvent.kind.in_(("message", "voice"))))).all())
    assert sum(d["by_hour"]) == n
    a2 = next(x for x in d["levels"] if x["level"] == "A2")
    assert a2["users"] >= 1 and a2["messages"] >= 1
