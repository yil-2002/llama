"""Formatlash funksiyalari testlari."""
from __future__ import annotations

import pytest

from bot.utils import bytes_to_human, seconds_to_human


def test_bytes_to_human():
    assert bytes_to_human(0) == "0 B"
    assert bytes_to_human(1024) == "1.00 KB"
    assert bytes_to_human(1024 ** 2) == "1.00 MB"
    assert bytes_to_human(1024 ** 3) == "1.00 GB"


def test_seconds_to_human():
    assert seconds_to_human(30) == "30s"
    assert seconds_to_human(60) == "1m"
    assert seconds_to_human(3661) == "1h 1m 1s"
