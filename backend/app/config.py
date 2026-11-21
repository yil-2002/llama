"""Barcha sozlamalar .env orqali beriladi (qarang: .env.example)."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Telegram
    bot_token: str = "000000:test"
    webapp_url: str = "https://example.com"
    admin_ids: list[int] = Field(default_factory=list)

    # Ma'lumotlar bazasi va navbat
    database_url: str = "postgresql+asyncpg://bot:bot@localhost:5432/englishbot"
    redis_url: str = "redis://localhost:6379/0"

    # LLM (OpenAI-mos API). Model nomini shu yerda yoki bot ichida /setmodel bilan almashtirish mumkin.
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4.1-flash"
    llm_timeout: float = 60.0

    # Nutq: "openai" (OpenAI-mos /audio API) yoki "none"
    stt_provider: str = "none"
    stt_base_url: str = "https://api.openai.com/v1"
    stt_api_key: str = ""
    stt_model: str = "whisper-1"
    tts_provider: str = "none"
    tts_base_url: str = "https://api.openai.com/v1"
    tts_api_key: str = ""
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"

    # Limitlar va obuna
    free_daily_messages: int = 15
    trial_days: int = 3
    premium_stars_price: int = 300  # 30 kunlik obuna narxi, Stars
    premium_period_days: int = 30

    # To'lov provayderlari: vergul bilan, masalan "stars" yoki "stars,click,payme"
    payment_providers: str = "stars"
    click_service_id: str = ""
    click_merchant_id: str = ""
    click_secret_key: str = ""
    payme_merchant_id: str = ""
    payme_secret_key: str = ""
    premium_uzs_price: int = 49000
    external_pay_url: str = ""  # Click/Payme uchun tashqi sayt manzili

    # Dashboard vaqt zonasi (Toshkent: UTC+5, yozgi vaqt yo'q)
    tz_offset_hours: int = 5

    @property
    def enabled_payment_providers(self) -> list[str]:
        return [p.strip() for p in self.payment_providers.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
