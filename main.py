import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.config import SECRET_KEY
from app.core.exception_handlers import app_error_handler
from app.core.exceptions import AppError
from app.core.logging_config import LOGGING_CONFIG
from app.init_db import seed_default_categories, seed_default_presets, seed_default_user
from app.routers import (
    api_alert_rules,
    api_alerts,
    api_attendance_presets,
    api_attendances,
    api_auth,
    api_calendar,
    api_groups,
    api_log_sources,
    api_logs,
    api_oauth,
    api_presence,
    api_reports,
    api_summary,
    api_task_categories,
    api_task_list,
    api_tasks,
    api_todos,
    api_users,
    pages,
)
from app.services.log_collector import start_collector, stop_collector
from app.services.websocket_manager import alert_ws_manager, log_ws_manager, presence_ws_manager

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    seed_default_user()
    seed_default_presets()
    seed_default_categories()
    await start_collector(app)
    logger.info("Application startup complete.")
    yield
    await stop_collector(app)


app = FastAPI(title="Todo List Portal", lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    """Check Origin header for state-changing requests to prevent CSRF."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        host = request.headers.get("host", "")
        # Allow requests with no Origin (non-browser clients, e.g. curl/API tools)
        if origin:
            from urllib.parse import urlparse

            origin_host = urlparse(origin).netloc
            if origin_host != host:
                from starlette.responses import JSONResponse

                return JSONResponse({"detail": "CSRF check failed: origin mismatch"}, status_code=403)
        elif referer:
            from urllib.parse import urlparse

            referer_host = urlparse(referer).netloc
            if referer_host != host:
                from starlette.responses import JSONResponse

                return JSONResponse({"detail": "CSRF check failed: referer mismatch"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    public_prefixes = ("/login", "/forgot-password", "/reset-password", "/static/", "/api/auth/", "/api/logs/", "/ws/")
    if any(path.startswith(p) for p in public_prefixes):
        return await call_next(request)
    if not request.session.get("user_id"):
        if not path.startswith("/api/"):
            return RedirectResponse(url="/login", status_code=302)
    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(api_todos.router)
app.include_router(api_attendances.router)
app.include_router(api_attendance_presets.router)
app.include_router(api_tasks.router)
app.include_router(api_logs.router)
app.include_router(api_users.router)
app.include_router(api_presence.router)
app.include_router(api_reports.router)
app.include_router(api_summary.router)
app.include_router(api_auth.router)
app.include_router(api_log_sources.router)
app.include_router(api_alerts.router)
app.include_router(api_task_categories.router)
app.include_router(api_alert_rules.router)
app.include_router(api_task_list.router)
app.include_router(api_calendar.router)
app.include_router(api_groups.router)
app.include_router(api_oauth.router)
app.include_router(api_oauth.admin_router)


def _ws_get_user_id(websocket: WebSocket) -> int:
    """Get user_id from WebSocket session cookie. Returns 0 if not authenticated."""
    try:
        return websocket.session.get("user_id", 0)
    except Exception:
        return 0


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await log_ws_manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        log_ws_manager.disconnect(websocket)
        return
    logger.info("WebSocket client connected: %s", websocket.client)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected: %s", websocket.client)


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await alert_ws_manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        alert_ws_manager.disconnect(websocket)
        return
    logger.info("Alerts WebSocket client connected: %s", websocket.client)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        alert_ws_manager.disconnect(websocket)
        logger.info("Alerts WebSocket client disconnected: %s", websocket.client)


@app.websocket("/ws/presence")
async def websocket_presence(websocket: WebSocket):
    await presence_ws_manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        presence_ws_manager.disconnect(websocket)
        return
    logger.info("Presence WebSocket client connected: %s", websocket.client)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        presence_ws_manager.disconnect(websocket)
        logger.info("Presence WebSocket client disconnected: %s", websocket.client)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
