"""Password authentication and session helper logic.

The bot has a single owner. Any Telegram account/device can log in from
/start as long as it knows the shared password (hashed and stored in
BOT_PASSWORD_HASH). A successful login creates a session row so the
account/device does not need to re-enter the password until the session
expires or is revoked.
"""
from __future__ import annotations

from typing import Optional

import bcrypt
from loguru import logger

from bot.config import settings
from bot.database import Database
from bot.models import Session


class AuthService:
    """Password + session logic, independent of Telegram update objects."""

    def __init__(self) -> None:
        self.db = Database()

    # --- Password hashing helpers ---

    @staticmethod
    def hash_password(plain: str) -> str:
        """Hash a plaintext password for storage in BOT_PASSWORD_HASH."""
        return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plaintext password against a stored bcrypt hash."""
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError) as e:
            logger.error(f"Password verification error (is BOT_PASSWORD_HASH a valid bcrypt hash?): {e}")
            return False

    # --- Lockout ---

    async def is_locked_out(self, telegram_id: int) -> bool:
        """True if telegram_id has too many recent failed login attempts."""
        if settings.max_login_attempts <= 0:
            return False
        failed = await self.db.count_recent_failed_attempts(
            telegram_id, settings.login_lockout_minutes
        )
        return failed >= settings.max_login_attempts

    # --- Login ---

    async def attempt_login(self, telegram_id: int, username: Optional[str], password: str) -> bool:
        """Check a submitted password. Records the attempt and creates a
        session on success. Returns True iff the password was correct.
        """
        if not settings.is_password_configured:
            logger.warning("Login attempted but BOT_PASSWORD_HASH is not configured.")
            return False

        ok = self.verify_password(password, settings.bot_password_hash)  # type: ignore[arg-type]
        await self.db.log_login_attempt(telegram_id, success=ok)

        if ok:
            await self.db.clear_failed_attempts(telegram_id)
            await self.db.create_session(
                telegram_id=telegram_id,
                username=username,
                ttl_days=settings.session_ttl_days,
            )
        return ok

    # --- Session check ---

    async def get_valid_session(self, telegram_id: int) -> Optional[Session]:
        """Return the active session for telegram_id, if any."""
        return await self.db.get_active_session(telegram_id)

    async def is_authenticated(self, telegram_id: int) -> bool:
        return await self.get_valid_session(telegram_id) is not None

    async def touch(self, session_token: str) -> None:
        await self.db.touch_session(session_token)

    async def logout(self, telegram_id: int) -> None:
        await self.db.revoke_session_by_telegram_id(telegram_id)
