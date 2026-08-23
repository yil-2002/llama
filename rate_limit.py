"""Rate limiting middleware."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import settings
from bot.constants import Messages


class RateLimitMiddleware:
    """Foydalanuvchi so'rovlarini cheklash."""

    def __init__(self) -> None:
        self._requests: dict[int, list[float]] = defaultdict(list)

    async def check_rate_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Tekshirish: foydalanuvchi limitdan oshmaganmi?"""
        if not settings.enable_rate_limit:
            return True
        if not update.effective_user:
            return True

        user_id = update.effective_user.id
        now = time.time()
        window = 60  # 1 daqiqa

        # Eski so'rovlarni tozalash
        self._requests[user_id] = [t for t in self._requests[user_id] if now - t < window]

        # Limit tekshirish
        if len(self._requests[user_id]) >= settings.rate_limit_commands_per_minute:
            wait_time = int(window - (now - self._requests[user_id][0]))
            if update.effective_message:
                await update.effective_message.reply_text(
                    Messages.RATE_LIMIT.format(seconds=wait_time)
                )
            return False

        # So'rovni qayd etish
        self._requests[user_id].append(now)
        return True


# Singleton instance - must be shared across the whole app, otherwise a
# fresh instance per-call would reset _requests and rate limiting would
# never actually trigger.
rate_limiter = RateLimitMiddleware()
