"""Backup metadata model."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BackupStatus(str, Enum):
    """Backup lifecycle states."""
    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"


class BackupMeta(BaseModel):
    """Backup record metadata."""

    id: Optional[int] = Field(default=None, description="Database ID")
    name: str = Field(..., description="Backup name")
    path: str = Field(..., description="File system path")
    size_bytes: int = Field(default=0, description="Size in bytes")
    status: BackupStatus = Field(default=BackupStatus.CREATING, description="Current status")
    created_by: Optional[int] = Field(default=None, description="Telegram ID of creator")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
