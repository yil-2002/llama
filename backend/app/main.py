from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .db import init_db
from .queue import queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await queue.close()


app = FastAPI(title="Owly English API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().webapp_url, "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"ok": True}
