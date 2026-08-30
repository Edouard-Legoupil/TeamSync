"""TeamSync FastAPI application entrypoint.

Run locally with:  uvicorn main:app --reload
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.database import init_db

STATIC_DIR = Path(settings.STATIC_DIR).resolve()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Convenience for local dev. Use migrations (Alembic) for production.
    init_db()
    yield


app = FastAPI(
    title="TeamSync",
    description="Meeting Intelligence Hub — turn transcripts into structured, portable data.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("teamsync")


@app.middleware("http")
async def request_context(request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "%s %s %d %.0fms rid=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        request_id,
    )
    return response


@app.get("/api/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


def _mount_spa() -> None:
    """Serve the built React SPA with a client-side routing fallback."""
    index = STATIC_DIR / "index.html"
    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    if index.is_file():

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            candidate = (STATIC_DIR / full_path).resolve()
            if full_path and candidate.is_file() and STATIC_DIR in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(index)

    else:

        @app.get("/{full_path:path}", include_in_schema=False)
        def no_frontend(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            return JSONResponse(
                {
                    "detail": "TeamSync API is running. "
                    "Build the frontend first: `npm run build` in frontend/."
                },
                status_code=404,
            )


_mount_spa()
