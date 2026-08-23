"""System statistics model."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SystemStats(BaseModel):
    """System resource usage snapshot."""

    cpu_percent: float = Field(default=0.0, description="CPU usage percentage")
    ram_percent: float = Field(default=0.0, description="RAM usage percentage")
    ram_used_bytes: int = Field(default=0, description="RAM used in bytes")
    ram_total_bytes: int = Field(default=0, description="RAM total in bytes")
    disk_percent: float = Field(default=0.0, description="Disk usage percentage")
    disk_used_bytes: int = Field(default=0, description="Disk used in bytes")
    disk_total_bytes: int = Field(default=0, description="Disk total in bytes")
    network_sent_bytes: int = Field(default=0, description="Network bytes sent")
    network_recv_bytes: int = Field(default=0, description="Network bytes received")
    load_avg_1m: float = Field(default=0.0, description="1-minute load average")
    created_at: Optional[str] = Field(default=None, description="Timestamp")
