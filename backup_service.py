"""Zaxira xizmati."""
from __future__ import annotations

import asyncio
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from bot.config import settings
from bot.models import BackupMeta, BackupStatus
from bot.services.base_service import BaseService
from bot.utils import bytes_to_human, safe_subprocess


class BackupService(BaseService):
    """Zaxira yaratish va tiklash."""

    def __init__(self) -> None:
        super().__init__("Backup")
        self.backup_dir = settings.backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(
        self,
        name: str,
        backup_type: str,
        custom_path: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> dict[str, Any]:
        """Zaxira yaratish.

        Args:
            name: Zaxira nomi.
            backup_type: 'full', 'docker', 'db', 'config', 'custom'.
            custom_path: Boshqa yo'l (faqat 'custom' uchun).
            progress_callback: Progressni yangilash funksiyasi.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.tar.gz"
            backup_path = self.backup_dir / filename

            sources = []
            if backup_type == "full":
                sources = [
                    "/opt/docker",
                    "/etc/nginx",
                    "/etc/wireguard",
                    str(settings.bot_data_dir),
                ]
            elif backup_type == "docker":
                sources = ["/opt/docker"]
            elif backup_type == "db":
                # PostgreSQL va MySQL dump
                sources = []
            elif backup_type == "config":
                sources = ["/etc/nginx", "/etc/wireguard"]
            elif backup_type == "custom" and custom_path:
                sources = [custom_path]

            # Create tar.gz
            def _create_tar():
                with tarfile.open(backup_path, "w:gz") as tar:
                    for source in sources:
                        src_path = Path(source)
                        if src_path.exists():
                            tar.add(src_path, arcname=src_path.name)

            await asyncio.to_thread(_create_tar)

            size = backup_path.stat().st_size

            return {
                "success": True,
                "name": filename,
                "path": str(backup_path),
                "size": size,
                "size_human": bytes_to_human(size),
            }
        except Exception as e:
            return self.handle_error("create_backup", e)

    async def list_backups(self) -> list[dict[str, Any]]:
        """Zaxiralar ro'yxati."""
        try:
            backups = []
            for file_path in self.backup_dir.glob("*.tar.gz"):
                stat = file_path.stat()
                backups.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "size_human": bytes_to_human(stat.st_size),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            backups.sort(key=lambda x: x["created"], reverse=True)
            return backups
        except Exception as e:
            logger.error(f"Zaxiralarni olishda xatolik: {e}")
            return []

    async def delete_backup(self, backup_path: str) -> dict[str, Any]:
        """Zaxirani o'chirish."""
        try:
            path = Path(backup_path)
            if not path.exists():
                return {"success": False, "error": "Zaxira topilmadi"}
            path.unlink()
            return {"success": True, "message": "Zaxira o'chirildi"}
        except Exception as e:
            return self.handle_error("delete_backup", e)

    async def restore_backup(self, backup_path: str, target_dir: Optional[str] = None) -> dict[str, Any]:
        """Zaxirani tiklash."""
        try:
            path = Path(backup_path)
            if not path.exists():
                return {"success": False, "error": "Zaxira topilmadi"}

            target = Path(target_dir) if target_dir else Path("/tmp/restore")
            target.mkdir(parents=True, exist_ok=True)

            def _extract():
                with tarfile.open(path, "r:gz") as tar:
                    tar.extractall(path=target)

            await asyncio.to_thread(_extract)
            return {"success": True, "message": f"Zaxira {target} ga tiklandi"}
        except Exception as e:
            return self.handle_error("restore_backup", e)

    async def cleanup_old_backups(self, keep_daily: int = 7, keep_weekly: int = 4) -> dict[str, Any]:
        """Eski zaxiralarni tozalash."""
        try:
            backups = await self.list_backups()
            # Simple rotation: keep last N
            to_delete = backups[keep_daily:]
            deleted = 0
            for backup in to_delete:
                Path(backup["path"]).unlink()
                deleted += 1
            return {"success": True, "deleted": deleted}
        except Exception as e:
            return self.handle_error("cleanup_old_backups", e)
