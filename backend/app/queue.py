"""Navbat abstraksiyasi.

QUEUE_MODE=arq (standart) — Redis navbati, ishni worker bajaradi.
QUEUE_MODE=inline — lokal ishlab chiqish va testlar uchun, ish shu jarayonda bajariladi.
"""
import os

from arq import create_pool
from arq.connections import RedisSettings

from . import jobs
from .config import get_settings

JOB_TIMEOUT = 90


class Queue:
    def __init__(self) -> None:
        self.mode = os.getenv("QUEUE_MODE", "arq")
        self._pool = None
        self._ctx: dict | None = None

    async def run(self, name: str, **kwargs):
        if self.mode == "inline":
            if self._ctx is None:
                self._ctx = jobs.build_ctx()
            fn = {f.__name__: f for f in jobs.FUNCTIONS}[name]
            return await fn(self._ctx, **kwargs)

        if self._pool is None:
            self._pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
        job = await self._pool.enqueue_job(name, **kwargs)
        return await job.result(timeout=JOB_TIMEOUT)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()


queue = Queue()
