"""System monitoring and control service."""
from __future__ import annotations

import asyncio
import os
import shutil
from datetime import datetime
from typing import Any, Optional

import psutil
from loguru import logger

from bot.config import settings
from bot.models import SystemStats
from bot.services.base_service import BaseService
from bot.utils import bytes_to_human, safe_subprocess, seconds_to_human


class SystemService(BaseService):
    """System resource monitoring and control."""

    def __init__(self) -> None:
        super().__init__("System")
        self._boot_time: Optional[float] = None

    async def check_availability(self) -> bool:
        try:
            psutil.cpu_percent(interval=0.1)
            self._available = True
            return True
        except Exception as e:
            logger.warning(f"System monitoring not available: {e}")
            self._available = False
            return False

    async def get_stats(self) -> SystemStats:
        """Get current system statistics."""
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net_io = psutil.net_io_counters()
        load_avg = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0

        return SystemStats(
            cpu_percent=cpu_percent,
            ram_percent=memory.percent,
            ram_used_bytes=memory.used,
            ram_total_bytes=memory.total,
            disk_percent=disk.percent,
            disk_used_bytes=disk.used,
            disk_total_bytes=disk.total,
            network_sent_bytes=net_io.bytes_sent,
            network_recv_bytes=net_io.bytes_recv,
            load_avg_1m=load_avg,
            created_at=datetime.now().isoformat(),
        )

    async def get_uptime(self) -> str:
        """Get system uptime as human-readable string."""
        boot_time = psutil.boot_time()
        uptime_seconds = int(datetime.now().timestamp() - boot_time)
        return seconds_to_human(uptime_seconds)

    async def get_top_processes(self, sort_by: str = "cpu", limit: int = 10) -> list[dict[str, Any]]:
        """Get top processes by CPU or memory."""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info"]):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"],
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": info["memory_percent"] or 0.0,
                    "memory_rss": info["memory_info"].rss if info["memory_info"] else 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        reverse = True
        if sort_by == "cpu":
            processes.sort(key=lambda x: x["cpu_percent"], reverse=reverse)
        elif sort_by == "memory":
            processes.sort(key=lambda x: x["memory_percent"], reverse=reverse)

        return processes[:limit]

    async def get_network_info(self) -> dict[str, Any]:
        """Get network interface information."""
        interfaces = {}
        for name, stats in psutil.net_if_addrs().items():
            addresses = []
            for addr in stats:
                if addr.family == 2:  # IPv4
                    addresses.append(addr.address)
            if addresses:
                interfaces[name] = addresses

        net_io = psutil.net_io_counters()
        return {
            "interfaces": interfaces,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
        }

    async def get_public_ip(self) -> str:
        """Get public IP address."""
        try:
            code, out, _ = await safe_subprocess(
                ["curl", "-s", "-m", "5", "https://api.ipify.org"],
                timeout=10,
            )
            if code == 0 and out.strip():
                return out.strip()
        except Exception:
            pass
        return "Unknown"

    async def reboot(self) -> dict[str, Any]:
        """Reboot the system."""
        code, out, err = await safe_subprocess(
            ["sudo", "reboot"],
            timeout=10,
        )
        return {"success": code == 0, "message": "Reboot initiated" if code == 0 else err}

    async def shutdown(self) -> dict[str, Any]:
        """Shutdown the system."""
        code, out, err = await safe_subprocess(
            ["sudo", "shutdown", "-h", "now"],
            timeout=10,
        )
        return {"success": code == 0, "message": "Shutdown initiated" if code == 0 else err}

    async def list_services(self) -> list[dict[str, Any]]:
        """List systemd services."""
        code, out, _ = await safe_subprocess(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend"],
            timeout=30,
        )
        services = []
        if code == 0:
            for line in out.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "load": parts[1],
                        "active": parts[2],
                        "sub": parts[3],
                        "description": " ".join(parts[4:]) if len(parts) > 4 else "",
                    })
        return services

    async def service_action(self, service_name: str, action: str) -> dict[str, Any]:
        """Start, stop, or restart a service."""
        code, out, err = await safe_subprocess(
            ["sudo", "systemctl", action, service_name],
            timeout=30,
        )
        return {"success": code == 0, "stdout": out, "stderr": err}

    async def update_packages(self) -> dict[str, Any]:
        """Run apt update and upgrade."""
        code1, out1, err1 = await safe_subprocess(
            ["sudo", "apt", "update", "-y"],
            timeout=300,
        )
        code2, out2, err2 = await safe_subprocess(
            ["sudo", "apt", "upgrade", "-y"],
            timeout=600,
        )
        return {
            "success": code1 == 0 and code2 == 0,
            "update_output": out1 + "\n" + err1,
            "upgrade_output": out2 + "\n" + err2,
        }

    async def get_ufw_status(self) -> dict[str, Any]:
        """Get UFW firewall status."""
        code, out, err = await safe_subprocess(
            ["sudo", "ufw", "status", "verbose"],
            timeout=10,
        )
        return {"success": code == 0, "output": out, "error": err}

    async def ufw_allow(self, port: int, protocol: str = "tcp") -> dict[str, Any]:
        code, out, err = await safe_subprocess(
            ["sudo", "ufw", "allow", f"{port}/{protocol}"],
            timeout=10,
        )
        return {"success": code == 0, "output": out, "error": err}

    async def ufw_deny(self, port: int, protocol: str = "tcp") -> dict[str, Any]:
        code, out, err = await safe_subprocess(
            ["sudo", "ufw", "deny", f"{port}/{protocol}"],
            timeout=10,
        )
        return {"success": code == 0, "output": out, "error": err}

    async def list_cron_jobs(self) -> list[dict[str, Any]]:
        """List current user's cron jobs."""
        code, out, _ = await safe_subprocess(
            ["crontab", "-l"],
            timeout=10,
        )
        jobs = []
        if code == 0:
            for line in out.strip().split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split(None, 5)
                    if len(parts) >= 6:
                        jobs.append({
                            "schedule": " ".join(parts[:5]),
                            "command": parts[5],
                        })
        return jobs

    async def add_cron_job(self, schedule: str, command: str) -> dict[str, Any]:
        """Add a cron job."""
        # Get existing crontab
        code, out, _ = await safe_subprocess(["crontab", "-l"], timeout=10)
        existing = out if code == 0 else ""
        new_entry = f"{schedule} {command}\n"
        new_crontab = existing + new_entry

        # Write new crontab via stdin
        proc = await asyncio.create_subprocess_exec(
            "crontab", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(new_crontab.encode())
        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
        }
