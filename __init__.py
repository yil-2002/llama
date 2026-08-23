"""Telegram bot handlers."""
from __future__ import annotations

from .start import register_start_handlers
from .auth import register_auth_handlers
from .confirm import register_confirm_handlers
from .alerts import register_alert_handlers
from .ai_coding import register_ai_handlers
from .docker import register_docker_handlers
from .monitoring import register_monitoring_handlers
from .file_manager import register_file_handlers
from .vpn import register_vpn_handlers
from .media_server import register_media_handlers
from .git_server import register_git_handlers
from .backup import register_backup_handlers
from .system import register_system_handlers
from .nginx import register_nginx_handlers
from .database_mgmt import register_db_handlers
from .logs import register_logs_handlers
from .agent import register_agent_handlers

__all__ = [
    "register_start_handlers",
    "register_auth_handlers",
    "register_confirm_handlers",
    "register_alert_handlers",
    "register_ai_handlers",
    "register_docker_handlers",
    "register_monitoring_handlers",
    "register_file_handlers",
    "register_vpn_handlers",
    "register_media_handlers",
    "register_git_handlers",
    "register_backup_handlers",
    "register_system_handlers",
    "register_nginx_handlers",
    "register_db_handlers",
    "register_logs_handlers",
    "register_agent_handlers",
]
