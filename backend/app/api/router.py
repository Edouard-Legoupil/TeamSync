"""Aggregate all API routers under a single ``/api`` router."""

from fastapi import APIRouter

from app.api.routes import (
    action_items,
    admin,
    analytics,
    auth,
    export,
    meetings,
    notifications,
    outlook,
    reports,
    search,
    series,
    tags,
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
api_router.include_router(tags.router)
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
