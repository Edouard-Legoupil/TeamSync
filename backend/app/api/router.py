"""Aggregate all API routers under a single ``/api`` router."""

from fastapi import APIRouter

from app.api.routes import (
    action_items,
    admin,
    auth,
    export,
    meetings,
    outlook,
    reports,
    search,
    series,
    teams,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(teams.router)
api_router.include_router(meetings.router)
api_router.include_router(action_items.router)
api_router.include_router(export.router)
api_router.include_router(series.router)
api_router.include_router(search.router)
api_router.include_router(reports.router)
api_router.include_router(outlook.router)
api_router.include_router(admin.router)
