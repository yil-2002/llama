"""Pytest sozlamalari."""
from __future__ import annotations

import pytest


@pytest.fixture
async def db():
    """Test ma'lumotlar bazasi."""
    from bot.database import Database
    database = Database()
    await database.init()
    yield database
