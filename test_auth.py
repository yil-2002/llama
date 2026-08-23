"""Autentifikatsiya testlari (parol/sessiya asosidagi owner-only auth)."""
from __future__ import annotations

import pytest

from bot.services.auth_service import AuthService


def test_password_hash_roundtrip():
    plain = "juda-kuchli-maxfiy-parol"
    hashed = AuthService.hash_password(plain)
    assert hashed != plain
    assert AuthService.verify_password(plain, hashed) is True


def test_password_hash_rejects_wrong_password():
    hashed = AuthService.hash_password("togri-parol")
    assert AuthService.verify_password("notogri-parol", hashed) is False


def test_password_hash_rejects_invalid_hash_format():
    # Not a real bcrypt hash - must fail closed, not raise.
    assert AuthService.verify_password("istalgan-parol", "not-a-bcrypt-hash") is False


@pytest.mark.asyncio
async def test_session_created_on_successful_login(db):
    auth = AuthService()
    auth.db = db

    from bot.config import settings
    settings.bot_password_hash = AuthService.hash_password("test-parol")

    ok = await auth.attempt_login(telegram_id=555, username="tester", password="test-parol")
    assert ok is True

    session = await auth.get_valid_session(555)
    assert session is not None
    assert session.telegram_id == 555


@pytest.mark.asyncio
async def test_lockout_after_repeated_failures(db):
    auth = AuthService()
    auth.db = db

    from bot.config import settings
    settings.bot_password_hash = AuthService.hash_password("togri-parol")
    settings.max_login_attempts = 3
    settings.login_lockout_minutes = 15

    for _ in range(3):
        ok = await auth.attempt_login(telegram_id=777, username="tester", password="notogri")
        assert ok is False

    assert await auth.is_locked_out(777) is True
