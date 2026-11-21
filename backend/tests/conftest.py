import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.update(
    DATABASE_URL=f"sqlite+aiosqlite:///{_db}",
    QUEUE_MODE="inline",
    BOT_TOKEN="123456:TEST",
    ADMIN_IDS="[1]",
    FREE_DAILY_MESSAGES="3",
)

import json  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import jobs  # noqa: E402
from app.db import init_db  # noqa: E402
from app.queue import queue  # noqa: E402
from app.speech import NoTTS  # noqa: E402
from app.telegram_auth import sign_init_data  # noqa: E402


class FakeLLM:
    def __init__(self):
        self.calls = []

    async def chat(self, model, messages, **kw):
        self.calls.append((model, messages))
        return "That sounds great! What else do you enjoy?"

    async def chat_json(self, model, messages, **kw):
        self.calls.append((model, messages))
        return {
            "overall_band": 6.5,
            "scores": {"fluency": 6.5, "lexical": 6.0, "grammar": 6.0, "pronunciation": 7.0},
            "summary_uz": "Yaxshi!",
            "mistakes": [{"original": "I goed", "better": "I went", "explanation_uz": "go noto'g'ri fe'l"}],
            "estimated_level": "B1",
        }

    async def aclose(self):
        pass


class FakeSTT:
    async def transcribe(self, audio, filename="voice.ogg"):
        return "I like football"


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    await init_db()


@pytest.fixture
def fake_llm():
    llm = FakeLLM()
    queue._ctx = {"llm": llm, "stt": FakeSTT(), "tts": NoTTS()}
    return llm


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def auth(tg_id: int, name: str = "Ali") -> dict:
    import time

    init = sign_init_data(
        {"auth_date": int(time.time()), "user": {"id": tg_id, "first_name": name}, "query_id": "q"}, "123456:TEST"
    )
    return {"X-Telegram-Init-Data": init}
