"""Application configuration using Pydantic Settings."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bot configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    # IXTIYORIY: kunlik hisobot/alert xabarlari uchun sobit chat.
    # Bo'sh qoldirsangiz, bu xabarlar barcha FAOL sessiyalarga (hozir
    # tizimga kirgan barcha akkaunt/qurilmalarga) yuboriladi - chunki
    # botda alohida "admin ID" tushunchasi yo'q, faqat umumiy parol bor.
    # Berilsa ham, bu ID botga kirish huquqi bermaydi - kirish faqat
    # BOT_PASSWORD_HASH orqali (pastga qarang).
    telegram_superadmin_id: Optional[int] = Field(default=None, alias="TELEGRAM_SUPERADMIN_ID")

    # Bot Behavior
    bot_language: str = Field(default="en", alias="BOT_LANGUAGE")
    bot_timezone: str = Field(default="UTC", alias="BOT_TIMEZONE")
    command_prefix: str = Field(default="/", alias="COMMAND_PREFIX")
    max_output_length: int = Field(default=4000, alias="MAX_OUTPUT_LENGTH")

    # Password authentication (owner-only bot, any device/account may log in
    # with the correct password; see scripts/gen_password_hash.py)
    bot_password_hash: Optional[str] = Field(default=None, alias="BOT_PASSWORD_HASH")
    session_ttl_days: int = Field(default=30, alias="SESSION_TTL_DAYS")
    max_login_attempts: int = Field(default=5, alias="MAX_LOGIN_ATTEMPTS")
    login_lockout_minutes: int = Field(default=3, alias="LOGIN_LOCKOUT_MINUTES")

    # Paths
    bot_data_dir: Path = Field(default=Path("/app/data"), alias="BOT_DATA_DIR")
    bot_log_dir: Path = Field(default=Path("/app/logs"), alias="BOT_LOG_DIR")
    backup_dir: Path = Field(default=Path("/app/backups"), alias="BACKUP_DIR")

    # Services
    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_default_model: str = Field(default="qwen2.5-coder:1.5b", alias="OLLAMA_DEFAULT_MODEL")

    # Agentic erkin-matn buyruq routeri (phase 4). Har bir oddiy matn xabari
    # Ollama'ga yuborilishini istamasangiz false qiling.
    enable_agent: bool = Field(default=True, alias="ENABLE_AGENT")
    # Bo'sh bo'lsa ollama_default_model ishlatiladi. Tool-routing uchun
    # umumiy instruction-following modeli (masalan llama3.1) coding
    # modeliga qaraganda ko'proq mos kelishi mumkin.
    agent_model: Optional[str] = Field(default=None, alias="AGENT_MODEL")
    jellyfin_url: Optional[str] = Field(default=None, alias="JELLYFIN_URL")
    jellyfin_api_key: Optional[str] = Field(default=None, alias="JELLYFIN_API_KEY")
    gitea_url: Optional[str] = Field(default=None, alias="GITEA_URL")
    gitea_token: Optional[str] = Field(default=None, alias="GITEA_TOKEN")
    wireguard_config_dir: Path = Field(default=Path("/etc/wireguard"), alias="WIREGUARD_CONFIG_DIR")
    postgres_host: Optional[str] = Field(default=None, alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: Optional[str] = Field(default=None, alias="POSTGRES_USER")
    postgres_password: Optional[str] = Field(default=None, alias="POSTGRES_PASSWORD")
    mysql_host: Optional[str] = Field(default=None, alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: Optional[str] = Field(default=None, alias="MYSQL_USER")
    mysql_password: Optional[str] = Field(default=None, alias="MYSQL_PASSWORD")
    redis_host: Optional[str] = Field(default=None, alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")

    # Security
    enable_confirmation: bool = Field(default=True, alias="ENABLE_CONFIRMATION")
    max_shell_timeout: int = Field(default=30, alias="MAX_SHELL_TIMEOUT")
    forbidden_commands: str = Field(
        default="rm -rf,dd if=/dev/zero,mkfs,fdisk",
        alias="FORBIDDEN_COMMANDS",
    )
    enable_rate_limit: bool = Field(default=True, alias="ENABLE_RATE_LIMIT")
    rate_limit_commands_per_minute: int = Field(default=20, alias="RATE_LIMIT_COMMANDS_PER_MINUTE")

    # Notifications
    enable_daily_report: bool = Field(default=False, alias="ENABLE_DAILY_REPORT")
    daily_report_hour: int = Field(default=9, alias="DAILY_REPORT_HOUR")
    enable_alerts: bool = Field(default=True, alias="ENABLE_ALERTS")
    alert_check_interval_seconds: int = Field(default=300, alias="ALERT_CHECK_INTERVAL_SECONDS")

    # Webhook (optional)
    telegram_webhook_url: Optional[str] = Field(default=None, alias="TELEGRAM_WEBHOOK_URL")
    webhook_port: int = Field(default=8080, alias="WEBHOOK_PORT")

    @field_validator("bot_data_dir", "bot_log_dir", "backup_dir", mode="before")
    @classmethod
    def _ensure_path(cls, v: str | Path) -> Path:
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def forbidden_commands_list(self) -> list[str]:
        return [cmd.strip().lower() for cmd in self.forbidden_commands.split(",") if cmd.strip()]

    @property
    def db_path(self) -> Path:
        return self.bot_data_dir / "bot.db"

    @property
    def is_jellyfin_enabled(self) -> bool:
        return bool(self.jellyfin_url and self.jellyfin_api_key)

    @property
    def is_gitea_enabled(self) -> bool:
        return bool(self.gitea_url and self.gitea_token)

    @property
    def is_postgres_enabled(self) -> bool:
        return bool(self.postgres_host and self.postgres_user and self.postgres_password)

    @property
    def is_mysql_enabled(self) -> bool:
        return bool(self.mysql_host and self.mysql_user and self.mysql_password)

    @property
    def is_redis_enabled(self) -> bool:
        return bool(self.redis_host)

    @property
    def is_password_configured(self) -> bool:
        return bool(self.bot_password_hash)


# Global settings instance
settings = Settings()
