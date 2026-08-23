"""Helper utilities for subprocess and file operations."""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

from bot.config import settings


async def safe_subprocess(
    command: list[str],
    cwd: Optional[Path] = None,
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
) -> tuple[int, str, str]:
    """Execute a subprocess safely with timeout.

    Args:
        command: Command as list of strings (no shell injection).
        cwd: Working directory.
        timeout: Timeout in seconds (defaults to settings.max_shell_timeout).
        env: Optional environment variables.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    timeout = timeout or settings.max_shell_timeout
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env={**os.environ, **(env or {})},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        logger.warning(f"Subprocess timed out: {' '.join(command)}")
        if proc and proc.returncode is None:
            proc.kill()
        return -1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        logger.error(f"Subprocess error: {e}")
        return -1, "", str(e)


class temp_file_cleanup:
    """Context manager for temporary files that auto-deletes on exit."""

    def __init__(self, suffix: str = "", prefix: str = "vpsbot_") -> None:
        self.suffix = suffix
        self.prefix = prefix
        self.path: Optional[Path] = None

    def __enter__(self) -> Path:
        fd, name = tempfile.mkstemp(suffix=self.suffix, prefix=self.prefix)
        os.close(fd)
        self.path = Path(name)
        return self.path

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.path and self.path.exists():
            try:
                self.path.unlink()
            except OSError as e:
                logger.warning(f"Failed to delete temp file {self.path}: {e}")
