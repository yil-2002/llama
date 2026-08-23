"""Base service class with common error handling."""
from __future__ import annotations

from abc import ABC
from typing import Any

from loguru import logger


class BaseService(ABC):
    """Abstract base for all services."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._available: bool | None = None

    async def check_availability(self) -> bool:
        """Check if the service is available. Override in subclasses."""
        return True

    @property
    def is_available(self) -> bool:
        """Return cached availability status."""
        if self._available is None:
            return True  # Assume available until checked
        return self._available

    def handle_error(self, operation: str, error: Exception) -> dict[str, Any]:
        """Standardized error response."""
        logger.error(f"[{self.name}] {operation} failed: {error}")
        return {
            "success": False,
            "error": str(error),
            "service": self.name,
        }
