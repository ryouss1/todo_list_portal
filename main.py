import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.config import DEFAULT_LOCALE, SECRET_KEY
from app.core.exception_handlers import app_error_handler
from app.core.exceptions import AppError
from app.core.logging_config import LOGGING_CONFIG
from app.init_db import seed_default_categories, seed_default_presets, seed_default_user
from app.routers import all_routers
from app.services.log_scanner import start_scanner, stop_scanner
from app.services.websocket_manager import alert_ws_manager, log_ws_manager, presence_ws_manager

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    seed_default_user()
    seed_default_presets()
    seed_default_categories()
    await start_scanner(app)
    logger.info("Application startup complete.")
    yield
    await stop_scanner(app)


app = FastAPI(title="Todo List Portal", lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)


@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    """Set locale on request.state from session."""
    locale = request.session.get("locale", DEFAULT_LOCALE)
    request.state.locale = locale
    response = await call_next(request)
    return response


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

for _router in all_routers:
    app.include_router(_router)


def _ws_get_user_id(websocket: WebSocket) -> int:
    """Get user_id from WebSocket session cookie. Returns 0 if not authenticated."""
    try:
        return websocket.session.get("user_id", 0)
    except Exception:
        return 0


async def _ws_handler(websocket: WebSocket, manager, name: str) -> None:
    """Common WebSocket handler: authenticate, receive loop, disconnect."""
    await manager.connect(websocket)
    if not _ws_get_user_id(websocket):
        await websocket.close(code=4401, reason="Not authenticated")
        manager.disconnect(websocket)
        return
    logger.info("%s WebSocket client connected: %s", name, websocket.client)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("%s WebSocket client disconnected: %s", name, websocket.client)


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await _ws_handler(websocket, log_ws_manager, "Logs")


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await _ws_handler(websocket, alert_ws_manager, "Alerts")


@app.websocket("/ws/presence")
async def websocket_presence(websocket: WebSocket):
    await _ws_handler(websocket, presence_ws_manager, "Presence")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
