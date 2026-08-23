"""Database layer using aiosqlite."""
from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite
from loguru import logger

from bot.config import settings
from bot.models import BackupMeta, BackupStatus, Session, SystemStats


class Database:
    """Async SQLite database manager."""

    _instance: Optional["Database"] = None
    _initialized = False

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if Database._initialized:
            return
        self.db_path: Path = settings.db_path
        Database._initialized = True

    async def _connect(self) -> aiosqlite.Connection:
        """Create database connection."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    async def init(self) -> None:
        """Initialize database schema with migrations."""
        async with await self._connect() as conn:
            await conn.executescript(self._get_schema())
            await conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    def _get_schema(self) -> str:
        """Return full database schema."""
        return """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_revoked BOOLEAN DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            success BOOLEAN NOT NULL,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT UNIQUE NOT NULL,
            threshold REAL NOT NULL,
            duration_minutes INTEGER DEFAULT 5,
            enabled BOOLEAN DEFAULT 1,
            last_triggered_at TIMESTAMP,
            above_since TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS commands_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            command TEXT NOT NULL,
            args TEXT,
            success BOOLEAN,
            error_message TEXT,
            execution_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS system_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpu_percent REAL,
            ram_percent REAL,
            ram_used_bytes INTEGER,
            ram_total_bytes INTEGER,
            disk_percent REAL,
            disk_used_bytes INTEGER,
            disk_total_bytes INTEGER,
            network_sent_bytes INTEGER,
            network_recv_bytes INTEGER,
            load_avg_1m REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER,
            status TEXT CHECK(status IN ('creating', 'completed', 'failed', 'restoring')) DEFAULT 'creating',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT CHECK(metric IN ('cpu', 'ram', 'disk', 'load')),
            threshold_percent INTEGER,
            duration_minutes INTEGER DEFAULT 5,
            is_active BOOLEAN DEFAULT 1,
            last_triggered TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_commands_user ON commands_log(user_id);
        CREATE INDEX IF NOT EXISTS idx_stats_time ON system_stats(created_at);
        CREATE INDEX IF NOT EXISTS idx_backups_status ON backups(status);
        CREATE INDEX IF NOT EXISTS idx_sessions_telegram ON sessions(telegram_id);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
        CREATE INDEX IF NOT EXISTS idx_login_attempts_telegram_time ON login_attempts(telegram_id, attempted_at);
        """

    # --- Session Operations (password-based, owner-only auth) ---

    async def create_session(
        self,
        telegram_id: int,
        username: Optional[str],
        ttl_days: int = 30,
    ) -> Session:
        """Create a new session after successful password login.

        ttl_days=0 means the session never expires.
        """
        token = secrets.token_urlsafe(32)
        expires_at = None
        if ttl_days and ttl_days > 0:
            expires_at = (datetime.utcnow() + timedelta(days=ttl_days)).isoformat(sep=" ", timespec="seconds")

        async with await self._connect() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO sessions (telegram_id, username, session_token, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (telegram_id, username, token, expires_at),
            )
            await conn.commit()
            row_id = cursor.lastrowid

        return await self.get_session_by_id(row_id)  # type: ignore[return-value]

    async def get_active_session(self, telegram_id: int) -> Optional[Session]:
        """Return the most recent non-revoked, non-expired session for a telegram_id, if any."""
        async with await self._connect() as conn:
            async with conn.execute(
                """
                SELECT * FROM sessions
                WHERE telegram_id = ?
                  AND is_revoked = 0
                  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_session(row) if row else None

    async def get_session_by_id(self, session_id: int) -> Optional[Session]:
        """Get a session by its row ID."""
        async with await self._connect() as conn:
            async with conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_session(row) if row else None

    async def get_all_sessions(self, active_only: bool = True) -> list[Session]:
        """List sessions, most recently active first."""
        async with await self._connect() as conn:
            query = "SELECT * FROM sessions"
            if active_only:
                query += " WHERE is_revoked = 0 AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)"
            query += " ORDER BY last_seen DESC"
            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_session(row) for row in rows]

    async def touch_session(self, session_token: str) -> None:
        """Update last_seen for a session."""
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE sessions SET last_seen = CURRENT_TIMESTAMP WHERE session_token = ?",
                (session_token,),
            )
            await conn.commit()

    async def revoke_session(self, session_id: int) -> bool:
        """Revoke a single session by ID."""
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE sessions SET is_revoked = 1 WHERE id = ?", (session_id,)
            )
            await conn.commit()
            return True

    async def revoke_session_by_telegram_id(self, telegram_id: int) -> bool:
        """Revoke all sessions belonging to a telegram_id (used for /logout)."""
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE sessions SET is_revoked = 1 WHERE telegram_id = ?", (telegram_id,)
            )
            await conn.commit()
            return True

    async def revoke_all_sessions(self) -> bool:
        """Revoke every session (used after a password change)."""
        async with await self._connect() as conn:
            await conn.execute("UPDATE sessions SET is_revoked = 1")
            await conn.commit()
            return True

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            session_token=row["session_token"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            last_seen=row["last_seen"],
            is_revoked=bool(row["is_revoked"]),
        )

    # --- Login Attempts (brute-force lockout) ---

    async def log_login_attempt(self, telegram_id: int, success: bool) -> None:
        """Record a login attempt (success or failure)."""
        async with await self._connect() as conn:
            await conn.execute(
                "INSERT INTO login_attempts (telegram_id, success) VALUES (?, ?)",
                (telegram_id, success),
            )
            await conn.commit()

    async def count_recent_failed_attempts(self, telegram_id: int, minutes: int) -> int:
        """Count failed login attempts for telegram_id within the last N minutes."""
        async with await self._connect() as conn:
            async with conn.execute(
                """
                SELECT COUNT(*) as cnt FROM login_attempts
                WHERE telegram_id = ?
                  AND success = 0
                  AND attempted_at >= datetime('now', '-' || ? || ' minutes')
                """,
                (telegram_id, minutes),
            ) as cursor:
                row = await cursor.fetchone()
                return int(row["cnt"]) if row else 0

    async def clear_failed_attempts(self, telegram_id: int) -> None:
        """Clear failed attempt history after a successful login."""
        async with await self._connect() as conn:
            await conn.execute(
                "DELETE FROM login_attempts WHERE telegram_id = ? AND success = 0",
                (telegram_id,),
            )
            await conn.commit()

    # --- Command Log ---

    async def log_command(
        self,
        user_id: int,
        command: str,
        args: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: int = 0,
    ) -> None:
        """Log a command execution."""
        async with await self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO commands_log (user_id, command, args, success, error_message, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, command, args, success, error_message, execution_time_ms),
            )
            await conn.commit()

    async def get_command_logs(self, user_id: Optional[int] = None, limit: int = 50) -> list[dict]:
        """Get command logs."""
        async with await self._connect() as conn:
            if user_id:
                async with conn.execute(
                    "SELECT * FROM commands_log WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with conn.execute(
                    "SELECT * FROM commands_log ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ) as cursor:
                    rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- System Stats ---

    async def insert_stats(self, stats: SystemStats) -> None:
        """Insert system statistics."""
        async with await self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO system_stats
                (cpu_percent, ram_percent, ram_used_bytes, ram_total_bytes,
                 disk_percent, disk_used_bytes, disk_total_bytes,
                 network_sent_bytes, network_recv_bytes, load_avg_1m)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stats.cpu_percent,
                    stats.ram_percent,
                    stats.ram_used_bytes,
                    stats.ram_total_bytes,
                    stats.disk_percent,
                    stats.disk_used_bytes,
                    stats.disk_total_bytes,
                    stats.network_sent_bytes,
                    stats.network_recv_bytes,
                    stats.load_avg_1m,
                ),
            )
            await conn.commit()

    async def get_stats_history(self, hours: int = 24) -> list[SystemStats]:
        """Get stats for last N hours."""
        async with await self._connect() as conn:
            async with conn.execute(
                """
                SELECT * FROM system_stats
                WHERE created_at >= datetime('now', '-' || ? || ' hours')
                ORDER BY created_at DESC
                """,
                (hours,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    SystemStats(
                        cpu_percent=row["cpu_percent"],
                        ram_percent=row["ram_percent"],
                        ram_used_bytes=row["ram_used_bytes"],
                        ram_total_bytes=row["ram_total_bytes"],
                        disk_percent=row["disk_percent"],
                        disk_used_bytes=row["disk_used_bytes"],
                        disk_total_bytes=row["disk_total_bytes"],
                        network_sent_bytes=row["network_sent_bytes"],
                        network_recv_bytes=row["network_recv_bytes"],
                        load_avg_1m=row["load_avg_1m"],
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]

    # --- Backups ---

    async def create_backup_record(self, backup: BackupMeta) -> BackupMeta:
        """Create backup record."""
        async with await self._connect() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO backups (name, path, size_bytes, status, created_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (backup.name, backup.path, backup.size_bytes, backup.status.value, backup.created_by),
            )
            await conn.commit()
            backup.id = cursor.lastrowid
            return backup

    async def update_backup_status(self, backup_id: int, status: BackupStatus) -> None:
        """Update backup status."""
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE backups SET status = ? WHERE id = ?",
                (status.value, backup_id),
            )
            await conn.commit()

    async def get_backups(self, limit: int = 50) -> list[BackupMeta]:
        """Get all backups."""
        async with await self._connect() as conn:
            async with conn.execute(
                "SELECT * FROM backups ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    BackupMeta(
                        id=row["id"],
                        name=row["name"],
                        path=row["path"],
                        size_bytes=row["size_bytes"],
                        status=BackupStatus(row["status"]),
                        created_by=row["created_by"],
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]

    async def get_backup_by_id(self, backup_id: int) -> Optional[BackupMeta]:
        """Get backup by ID."""
        async with await self._connect() as conn:
            async with conn.execute(
                "SELECT * FROM backups WHERE id = ?", (backup_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return BackupMeta(
                        id=row["id"],
                        name=row["name"],
                        path=row["path"],
                        size_bytes=row["size_bytes"],
                        status=BackupStatus(row["status"]),
                        created_by=row["created_by"],
                        created_at=row["created_at"],
                    )
                return None

    async def delete_backup_record(self, backup_id: int) -> None:
        """Delete backup record."""
        async with await self._connect() as conn:
            await conn.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
            await conn.commit()

    # --- Alert Operations (threshold-based monitoring, phase 3) ---

    DEFAULT_ALERT_METRICS = {
        "cpu": 90.0,
        "ram": 90.0,
        "disk": 90.0,
    }

    async def get_alerts(self) -> list[dict]:
        """List all alert threshold configs."""
        async with await self._connect() as conn:
            async with conn.execute("SELECT * FROM alerts ORDER BY metric") as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_alert(self, metric: str) -> Optional[dict]:
        async with await self._connect() as conn:
            async with conn.execute(
                "SELECT * FROM alerts WHERE metric = ?", (metric,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def upsert_alert(
        self,
        metric: str,
        threshold: float,
        duration_minutes: int = 5,
        enabled: bool = True,
    ) -> None:
        """Create or update an alert threshold config."""
        async with await self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO alerts (metric, threshold, duration_minutes, enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(metric) DO UPDATE SET
                    threshold=excluded.threshold,
                    duration_minutes=excluded.duration_minutes,
                    enabled=excluded.enabled
                """,
                (metric, threshold, duration_minutes, enabled),
            )
            await conn.commit()

    async def ensure_default_alerts(self) -> None:
        """Seed default cpu/ram/disk alert thresholds if none configured yet."""
        existing = {row["metric"] for row in await self.get_alerts()}
        for metric, threshold in self.DEFAULT_ALERT_METRICS.items():
            if metric not in existing:
                await self.upsert_alert(metric, threshold)

    async def set_alert_above_since(self, metric: str, timestamp: Optional[str]) -> None:
        """Track when a metric first crossed its threshold (for duration_minutes debounce)."""
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE alerts SET above_since = ? WHERE metric = ?", (timestamp, metric)
            )
            await conn.commit()

    async def mark_alert_triggered(self, metric: str) -> None:
        async with await self._connect() as conn:
            await conn.execute(
                "UPDATE alerts SET last_triggered_at = CURRENT_TIMESTAMP, above_since = NULL WHERE metric = ?",
                (metric,),
            )
            await conn.commit()

    async def set_alert_enabled(self, metric: str, enabled: bool) -> bool:
        async with await self._connect() as conn:
            cursor = await conn.execute(
                "UPDATE alerts SET enabled = ? WHERE metric = ?", (enabled, metric)
            )
            await conn.commit()
            return cursor.rowcount > 0

    # --- Settings ---

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get setting value."""
        async with await self._connect() as conn:
            async with conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        """Set setting value."""
        async with await self._connect() as conn:
            await conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            await conn.commit()
