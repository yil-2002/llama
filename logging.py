"""Command audit logging middleware."""
from __future__ import annotations

import time
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import Database


class LoggingMiddleware:
    """Har bir buyruqni logga yozish."""

    def __init__(self) -> None:
        self.db = Database()

    async def log_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        handler_name: str,
        start_time: float,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Buyruq bajarilishini logga yozish."""
        if not update.effective_user:
            return

        execution_time = int((time.time() - start_time) * 1000)
        args = " ".join(context.args) if hasattr(context, "args") and context.args else None

        await self.db.log_command(
            user_id=update.effective_user.id,
            command=handler_name,
            args=args,
            success=success,
            error_message=error,
            execution_time_ms=execution_time,
        )
