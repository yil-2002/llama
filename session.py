"""Session model for password-based owner authentication."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Session(BaseModel):
    """A logged-in Telegram account/device session."""

    id: Optional[int] = Field(default=None, description="Session row ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(default=None, description="Telegram username")
    session_token: str = Field(..., description="Opaque session token")
    created_at: Optional[str] = Field(default=None, description="Login timestamp")
    expires_at: Optional[str] = Field(default=None, description="Expiry timestamp, null = never")
    last_seen: Optional[str] = Field(default=None, description="Last activity timestamp")
    is_revoked: bool = Field(default=False, description="Whether session has been revoked")

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return str(self.telegram_id)
