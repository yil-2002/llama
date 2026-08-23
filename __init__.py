"""Service layer for external integrations."""
from __future__ import annotations

from .docker_service import DockerService
from .system_service import SystemService
from .ollama_service import OllamaService
from .jellyfin_service import JellyfinService
from .gitea_service import GiteaService
from .wireguard_service import WireguardService
from .backup_service import BackupService
from .nginx_service import NginxService
from .auth_service import AuthService

__all__ = [
    "DockerService",
    "SystemService",
    "OllamaService",
    "JellyfinService",
    "GiteaService",
    "WireguardService",
    "BackupService",
    "NginxService",
    "AuthService",
]
