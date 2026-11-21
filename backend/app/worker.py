"""arq worker: `arq app.worker.WorkerSettings`"""
from arq.connections import RedisSettings

from . import jobs
from .config import get_settings
from .db import init_db


async def startup(ctx: dict) -> None:
    await init_db()
    ctx.update(jobs.build_ctx())


async def shutdown(ctx: dict) -> None:
    await ctx["llm"].aclose()


class WorkerSettings:
    functions = jobs.FUNCTIONS
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 50  # bitta worker bir vaqtda bajaradigan ishlar (LLM kutish I/O bo'lgani uchun ko'p bo'lishi mumkin)
    job_timeout = 120
    keep_result = 300
