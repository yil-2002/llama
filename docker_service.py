"""Docker management service."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import docker
from docker.errors import DockerException
from loguru import logger

from bot.config import settings
from bot.services.base_service import BaseService
from bot.utils import safe_subprocess


class DockerService(BaseService):
    """Docker SDK wrapper for container and compose management."""

    def __init__(self) -> None:
        super().__init__("Docker")
        self._client: Optional[docker.DockerClient] = None

    def _get_client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    async def check_availability(self) -> bool:
        try:
            client = self._get_client()
            client.ping()
            self._available = True
            return True
        except DockerException as e:
            logger.warning(f"Docker not available: {e}")
            self._available = False
            return False

    async def list_containers(self, all_containers: bool = False) -> list[dict[str, Any]]:
        """List Docker containers."""
        try:
            client = self._get_client()
            containers = client.containers.list(all=all_containers)
            return [
                {
                    "id": c.id[:12],
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                    "status": c.status,
                    "state": c.attrs["State"]["Health"]["Status"] if c.attrs.get("State", {}).get("Health") else c.status,
                    "ports": self._format_ports(c.attrs.get("NetworkSettings", {}).get("Ports", {})),
                    "created": c.attrs["Created"],
                }
                for c in containers
            ]
        except DockerException as e:
            return [self.handle_error("list_containers", e)]

    def _format_ports(self, ports: dict) -> str:
        if not ports:
            return ""
        parts = []
        for container_port, bindings in ports.items():
            if bindings:
                for binding in bindings:
                    host_ip = binding.get("HostIp", "0.0.0.0")
                    host_port = binding.get("HostPort", "")
                    parts.append(f"{host_ip}:{host_port}->{container_port}")
            else:
                parts.append(container_port)
        return ", ".join(parts) if parts else ""

    async def get_container(self, name_or_id: str) -> Optional[dict[str, Any]]:
        """Get single container details."""
        try:
            client = self._get_client()
            c = client.containers.get(name_or_id)
            return {
                "id": c.id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                "status": c.status,
                "logs": c.logs(tail=50).decode("utf-8", errors="replace"),
                "stats": c.stats(stream=False),
            }
        except DockerException as e:
            logger.error(f"Container {name_or_id} not found: {e}")
            return None

    async def start_container(self, name_or_id: str) -> dict[str, Any]:
        try:
            client = self._get_client()
            container = client.containers.get(name_or_id)
            container.start()
            return {"success": True, "message": f"Container {name_or_id} started"}
        except DockerException as e:
            return self.handle_error("start_container", e)

    async def stop_container(self, name_or_id: str) -> dict[str, Any]:
        try:
            client = self._get_client()
            container = client.containers.get(name_or_id)
            container.stop(timeout=30)
            return {"success": True, "message": f"Container {name_or_id} stopped"}
        except DockerException as e:
            return self.handle_error("stop_container", e)

    async def restart_container(self, name_or_id: str) -> dict[str, Any]:
        try:
            client = self._get_client()
            container = client.containers.get(name_or_id)
            container.restart(timeout=30)
            return {"success": True, "message": f"Container {name_or_id} restarted"}
        except DockerException as e:
            return self.handle_error("restart_container", e)

    async def get_container_logs(self, name_or_id: str, tail: int = 50) -> str:
        try:
            client = self._get_client()
            container = client.containers.get(name_or_id)
            logs = container.logs(tail=tail, timestamps=True)
            return logs.decode("utf-8", errors="replace")
        except DockerException as e:
            return f"Error fetching logs: {e}"

    async def get_container_stats(self, name_or_id: str) -> dict[str, Any]:
        try:
            client = self._get_client()
            container = client.containers.get(name_or_id)
            stats = container.stats(stream=False)
            cpu_stats = stats.get("cpu_stats", {})
            memory_stats = stats.get("memory_stats", {})

            cpu_usage = cpu_stats.get("cpu_usage", {})
            total_usage = cpu_usage.get("total_usage", 0)
            system_cpu = cpu_stats.get("system_cpu_usage", 1)
            cpu_percent = 0.0
            if system_cpu > 0:
                cpu_percent = (total_usage / system_cpu) * 100

            mem_usage = memory_stats.get("usage", 0)
            mem_limit = memory_stats.get("limit", 1)
            mem_percent = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0

            return {
                "success": True,
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage": mem_usage,
                "memory_limit": mem_limit,
                "memory_percent": round(mem_percent, 2),
                "network_rx": stats.get("networks", {}).get("eth0", {}).get("rx_bytes", 0),
                "network_tx": stats.get("networks", {}).get("eth0", {}).get("tx_bytes", 0),
            }
        except DockerException as e:
            return self.handle_error("get_container_stats", e)

    async def list_images(self) -> list[dict[str, Any]]:
        try:
            client = self._get_client()
            images = client.images.list()
            return [
                {
                    "id": img.id[:12],
                    "tags": img.tags,
                    "size": img.attrs.get("Size", 0),
                    "created": img.attrs.get("Created", ""),
                }
                for img in images
            ]
        except DockerException as e:
            return [self.handle_error("list_images", e)]

    async def prune_images(self) -> dict[str, Any]:
        try:
            client = self._get_client()
            result = client.images.prune()
            return {
                "success": True,
                "deleted": len(result.get("ImagesDeleted", [])),
                "space_reclaimed": result.get("SpaceReclaimed", 0),
            }
        except DockerException as e:
            return self.handle_error("prune_images", e)

    async def list_compose_projects(self, base_dir: str = "/opt/docker") -> list[dict[str, Any]]:
        """List docker-compose projects."""
        from pathlib import Path
        base = Path(base_dir)
        if not base.exists():
            base = Path.home() / "docker"
        projects = []
        if base.exists():
            for compose_file in base.rglob("docker-compose.yml"):
                projects.append({
                    "name": compose_file.parent.name,
                    "path": str(compose_file.parent),
                    "file": str(compose_file),
                })
        return projects

    async def compose_up(self, project_dir: str) -> dict[str, Any]:
        code, out, err = await safe_subprocess(
            ["docker", "compose", "up", "-d"],
            cwd=project_dir,
            timeout=120,
        )
        return {"success": code == 0, "stdout": out, "stderr": err}

    async def compose_down(self, project_dir: str) -> dict[str, Any]:
        code, out, err = await safe_subprocess(
            ["docker", "compose", "down"],
            cwd=project_dir,
            timeout=120,
        )
        return {"success": code == 0, "stdout": out, "stderr": err}

    async def compose_pull(self, project_dir: str) -> dict[str, Any]:
        code, out, err = await safe_subprocess(
            ["docker", "compose", "pull"],
            cwd=project_dir,
            timeout=300,
        )
        return {"success": code == 0, "stdout": out, "stderr": err}

    async def compose_logs(self, project_dir: str, tail: int = 50) -> str:
        code, out, err = await safe_subprocess(
            ["docker", "compose", "logs", "--tail", str(tail)],
            cwd=project_dir,
            timeout=30,
        )
        return out if code == 0 else err
