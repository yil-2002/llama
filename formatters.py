"""Text and data formatting utilities."""
from __future__ import annotations

import html


SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
TIME_UNITS = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]


def bytes_to_human(size_bytes: int, precision: int = 2) -> str:
    """Convert bytes to human-readable string."""
    if size_bytes == 0:
        return "0 B"
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(SIZE_UNITS) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.{precision}f} {SIZE_UNITS[unit_index]}"


def seconds_to_human(total_seconds: int) -> str:
    """Convert seconds to human-readable duration."""
    if total_seconds < 60:
        return f"{total_seconds}s"
    parts = []
    remaining = total_seconds
    for label, seconds in TIME_UNITS:
        if remaining >= seconds:
            count = remaining // seconds
            remaining %= seconds
            parts.append(f"{count}{label}")
    return " ".join(parts)


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML parse mode."""
    if not text:
        return ""
    return html.escape(str(text))


def truncate_text(text: str, max_length: int = 4000, suffix: str = "\n\n... (truncated)") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_status_emoji(value: float, thresholds: tuple[float, float] = (70.0, 90.0)) -> str:
    """Return status emoji based on percentage value."""
    from bot.constants import Emoji
    if value >= thresholds[1]:
        return Emoji.ERROR
    if value >= thresholds[0]:
        return Emoji.WARNING
    return Emoji.ACTIVE
