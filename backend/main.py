from __future__ import annotations

import logging
import mimetypes
import os
from contextlib import asynccontextmanager
from pathlib import Path

# Fix Windows registry missing MIME types for web assets
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("text/html", ".html")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.services import notebooklm_service
from backend.session.manager import cleanup_expired_sessions
from backend.routers import health, chat, upload, generate

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────
    logger.info("Sintrix KNX Bot starting up…")
    os.makedirs(settings.sessions_dir, exist_ok=True)
    os.makedirs(settings.temp_uploads_dir, exist_ok=True)

    await notebooklm_service.initialize()

    removed = cleanup_expired_sessions()
    if removed:
        logger.info(f"Cleaned up {removed} expired sessions.")

    logger.info("Startup complete.")
    yield

    # ── Shutdown ───────────────────────────────────────────────────
    logger.info("Sintrix KNX Bot shutting down.")


app = FastAPI(
    title="Sintrix KNX Bot",
    description="KNX building automation expert — AI chat assistant",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# API routers
PREFIX = "/api/v1"
app.include_router(health.router,   prefix=PREFIX, tags=["health"])
app.include_router(chat.router,     prefix=PREFIX, tags=["chat"])
app.include_router(upload.router,   prefix=PREFIX, tags=["upload"])
app.include_router(generate.router, prefix=PREFIX, tags=["generate"])


# ── Frontend HTML routes ───────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def home_page():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/knx-bot", include_in_schema=False)
async def knx_bot_page():
    return FileResponse(FRONTEND_DIR / "knx-bot" / "index.html")

@app.get("/knx-bot/", include_in_schema=False)
async def knx_bot_page_slash():
    return FileResponse(FRONTEND_DIR / "knx-bot" / "index.html")

# ── Static asset mounts (specific paths, no ambiguity) ────────────
app.mount("/knx-bot/css", StaticFiles(directory=str(FRONTEND_DIR / "knx-bot" / "css")), name="knx-css")
app.mount("/knx-bot/js",  StaticFiles(directory=str(FRONTEND_DIR / "knx-bot" / "js")),  name="knx-js")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
