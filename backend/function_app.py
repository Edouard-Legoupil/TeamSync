"""Azure Functions v4 entrypoint wrapping the FastAPI app as an ASGI app.

Deploy this directory as a Python Azure Function. The HTTP trigger serves the
whole API (and the static SPA when ``frontend/dist`` is present alongside it).
"""

from __future__ import annotations

import logging

import azure.functions as func

from app.database import init_db
from main import app as fastapi_app

logger = logging.getLogger("teamsync")

# The Azure Functions ASGI worker may not run the FastAPI lifespan, so create
# tables at cold start. Safe to repeat — create_all is idempotent.
try:
    init_db()
except Exception as exc:  # noqa: BLE001 - don't prevent cold start on DB hiccup
    logger.warning("init_db failed at cold start: %s", exc)

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)


# --- Scaling note -----------------------------------------------------------
# FastAPI BackgroundTasks run inside the same worker and are fine for short AI
# calls. For long-running processing, offload to a Storage Queue instead and
# run the heavy work in a dedicated queue-triggered Function. Example pattern:
#
# @app.function_name("process_meeting_queue")
# @app.queue_trigger(arg_name="msg", queue_name="meeting-processing",
#                    connection="AzureWebJobsStorage")
# def process_meeting_queue(msg: func.QueueMessage) -> None:
#     from app.services.processing import process_meeting
#     process_meeting(msg.get_body().decode("utf-8"))
#
# In that mode, POST /api/meetings/upload should enqueue the meeting_id instead
# of scheduling a BackgroundTask.
