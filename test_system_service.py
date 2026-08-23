"""Tizim xizmati testlari."""
from __future__ import annotations

import pytest

from bot.services import SystemService


@pytest.mark.asyncio
async def test_system_stats():
    service = SystemService()
    stats = await service.get_stats()
    assert stats.cpu_percent >= 0
    assert stats.ram_percent >= 0
    assert stats.ram_total_bytes > 0


@pytest.mark.asyncio
async def test_uptime():
    service = SystemService()
    uptime = await service.get_uptime()
    assert isinstance(uptime, str)
    assert len(uptime) > 0
