"""Input validation utilities."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from bot.config import settings


FORBIDDEN_PATHS = {"/etc/shadow", "/proc", "/sys", "/dev"}
FORBIDDEN_PATTERNS = [r"\.\.", r"~\/\.ssh", r"~\/\.gnupg"]


def validate_path(user_path: str, base_dir: Optional[Path] = None) -> Path:
    """Validate and resolve a user-provided path.

    Args:
        user_path: The path string from user input.
        base_dir: Optional base directory to restrict access to.

    Returns:
        Resolved absolute Path.

    Raises:
        ValueError: If path is forbidden or outside allowed scope.
    """
    path = Path(user_path).expanduser().resolve()
    abs_path = str(path)

    for forbidden in FORBIDDEN_PATHS:
        if abs_path.startswith(forbidden):
            raise ValueError(f"Access to {forbidden} is forbidden.")

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, abs_path):
            raise ValueError(f"Path matches forbidden pattern: {pattern}")

    if base_dir:
        base = Path(base_dir).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise ValueError(f"Path must be within {base_dir}")

    return path


def is_command_forbidden(command: str) -> bool:
    """Check if a shell command contains forbidden patterns.

    Args:
        command: The command string to check.

    Returns:
        True if command is forbidden.
    """
    cmd_lower = command.lower().strip()
    for forbidden in settings.forbidden_commands_list:
        if forbidden in cmd_lower:
            return True
    # Block dangerous redirects and pipes that could be exploited
    dangerous = ["> /dev/null", "&>", "2>&1", "| bash", "| sh", "curl", "wget", "rm -rf /"]
    for d in dangerous:
        if d in cmd_lower:
            return True
    return False


def sanitize_command(command: str) -> str:
    """Sanitize a command string for safe execution.

    Args:
        command: Raw command string.

    Returns:
        Sanitized command.

    Raises:
        ValueError: If command contains forbidden patterns.
    """
    if is_command_forbidden(command):
        raise ValueError("Command contains forbidden patterns and cannot be executed.")
    return command.strip()
