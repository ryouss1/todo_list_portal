"""PortalApp factory — assembles a FastAPI application with core authentication,
user management, and department management pre-configured.

Usage::

    from portal_core.app_factory import NavItem, PortalApp

    portal = PortalApp(config, title="My App")
    portal.setup_core()
    portal.register_router(my_router)
    portal.register_nav_item(NavItem("Stuff", "/stuff", "bi-box", sort_order=50))
    portal.register_page("/stuff", "stuff.html")
    app = portal.build()
"""

import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from portal_core.config import CoreConfig
from portal_core.core.exception_handlers import app_error_handler
from portal_core.core.exceptions import AppError
from portal_core.core.i18n import get_translator
from portal_core.core.logging_config import LOGGING_CONFIG
from portal_core.init_db import seed_default_user
from portal_core.routers import api_auth, api_departments, api_oauth, api_roles, api_users
from portal_core.services.websocket_manager import WebSocketManager

logger = logging.getLogger("portal_core")


class NavItem:
    """Navigation bar item."""

    def __init__(
        self,
        label: str,
        path: str,
        icon: str = "",
        badge_id: Optional[str] = None,
        hidden: bool = False,
        sort_order: int = 100,
    ):
        self.label = label
        self.path = path
        self.icon = icon
        self.badge_id = badge_id
        self.hidden = hidden
        self.sort_order = sort_order

    # Allow dict-style access from Jinja2 templates that use item.xxx or item['xxx']
    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


class PortalApp:
    """Factory that assembles a FastAPI application with portal_core built in.

    Typical lifecycle::

        portal = PortalApp(config, title="My App")
        portal.setup_core()          # middleware, core routers, core nav
        portal.register_router(...)   # app-specific API routers
        portal.register_nav_item(...) # app-specific nav items
        portal.register_page(...)     # app-specific HTML pages
        portal.register_websocket(...)
        app = portal.build()          # finalize and return FastAPI instance
    """

    def __init__(self, config: CoreConfig, title: str = "Portal"):
        self.config = config
        self.title = title

        # Registration lists
        self._nav_items: List[NavItem] = []
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._ws_handlers: Dict[str, WebSocketManager] = {}
        self._page_routes: List[Dict[str, Any]] = []
        self._extra_template_dirs: List[str] = []
        self._extra_static_mounts: List[Dict[str, str]] = []
        self._seed_hooks: List[Callable] = []
        self._public_prefixes: List[str] = []
        self._csrf_exempt_prefixes: List[str] = []
        self._extra_routers: List[Dict[str, Any]] = []
        self._extra_head_scripts: List[str] = []

        self.app: Optional[FastAPI] = None
        self._jinja_env: Optional[Environment] = None

    # =================================================================
    # Setup
    # =================================================================

    def setup_core(self):
        """Set up the core infrastructure: logging, FastAPI, middleware,
        exception handlers, core API routers, and core nav items."""
        logging.config.dictConfig(LOGGING_CONFIG)

        # Configure fastapi-csrf-protect with the application secret key
        _secret = str(self.config.SECRET_KEY)

        @CsrfProtect.load_config
        def _csrf_settings():
            return [("secret_key", _secret)]

        portal = self  # capture for lifespan closure

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            logger.info("Application starting up...")
            seed_default_user()
            for hook in portal._seed_hooks:
                hook()
            for hook in portal._startup_hooks:
                await hook(app)
            logger.info("Application startup complete.")
            yield
            for hook in portal._shutdown_hooks:
                await hook(app)

        self.app = FastAPI(title=self.title, lifespan=lifespan)
        self.app.add_exception_handler(AppError, app_error_handler)

        self._setup_middleware()
        self._register_core_routers()

        # Core nav items
        self._nav_items.append(NavItem("Dashboard", "/", "bi-speedometer2", sort_order=0))
        self._nav_items.append(NavItem("Users", "/users", "bi-people-fill", sort_order=900))

    def _setup_middleware(self):
        """Register session, auth, CSRF, and locale middleware."""

        config = self.config
        portal = self

        @self.app.middleware("http")
        async def locale_middleware(request: Request, call_next):
            locale = request.session.get("locale", config.DEFAULT_LOCALE)
            request.state.locale = locale
            response = await call_next(request)
            return response

        @self.app.middleware("http")
        async def csrf_middleware(request: Request, call_next):
            if request.method in ("POST", "PUT", "PATCH", "DELETE"):
                # Auth endpoints and external log ingestion are exempt from CSRF
                csrf_exempt = ["/api/auth/", "/api/logs/"] + portal._csrf_exempt_prefixes
                if not any(request.url.path.startswith(p) for p in csrf_exempt):
                    try:
                        await CsrfProtect().validate_csrf(request)
                    except CsrfProtectError:
                        return JSONResponse(
                            {"detail": "CSRF check failed"},
                            status_code=403,
                        )
            return await call_next(request)

        @self.app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            path = request.url.path
            public = [
                "/login",
                "/forgot-password",
                "/reset-password",
                "/static/",
                "/api/auth/",
                "/ws/",
            ]
            public.extend(portal._public_prefixes)
            if any(path.startswith(p) for p in public):
                return await call_next(request)
            if not request.session.get("user_id"):
                if not path.startswith("/api/"):
                    return RedirectResponse(url="/login", status_code=302)
            return await call_next(request)

        self.app.add_middleware(SessionMiddleware, secret_key=config.SECRET_KEY)

    def _register_core_routers(self):
        """Register auth, user, department, OAuth, and roles API routers."""
        self.app.include_router(api_auth.router)
        self.app.include_router(api_users.router)
        self.app.include_router(api_departments.router)
        self.app.include_router(api_oauth.router)
        self.app.include_router(api_oauth.admin_router)
        self.app.include_router(api_roles.router)

    # =================================================================
    # Registration methods (called by app before build())
    # =================================================================

    def register_router(self, router, prefix: str = "", tags: Optional[List[str]] = None):
        """Register an API router to be included at build time."""
        self._extra_routers.append({"router": router, "prefix": prefix, "tags": tags or []})

    def register_nav_item(self, item: NavItem):
        """Add a navigation bar item."""
        self._nav_items.append(item)

    def register_page(self, path: str, template: str, **extra_context):
        """Register an HTML page route."""
        self._page_routes.append(
            {
                "path": path,
                "template": template,
                "extra_context": extra_context,
            }
        )

    def register_websocket(self, path: str, manager: WebSocketManager):
        """Register a WebSocket endpoint."""
        self._ws_handlers[path] = manager

    def register_template_dir(self, directory: str):
        """Add a template search directory (searched before core templates)."""
        self._extra_template_dirs.append(directory)

    def register_static_dir(self, directory: str, path: str = "/static"):
        """Add a static file mount."""
        self._extra_static_mounts.append({"directory": directory, "path": path})

    def register_startup_hook(self, func: Callable):
        """Register an async function to run at startup."""
        self._startup_hooks.append(func)

    def register_shutdown_hook(self, func: Callable):
        """Register an async function to run at shutdown."""
        self._shutdown_hooks.append(func)

    def register_seed_hook(self, func: Callable):
        """Register a sync function to seed database at startup."""
        self._seed_hooks.append(func)

    def register_public_prefix(self, prefix: str):
        """Add a URL prefix that bypasses authentication."""
        self._public_prefixes.append(prefix)

    def register_csrf_exempt(self, prefix: str):
        """Add a URL prefix that bypasses CSRF validation (use for external API endpoints)."""
        self._csrf_exempt_prefixes.append(prefix)

    def register_head_script(self, path: str):
        """Register a script to be loaded in <head> after core scripts on every page."""
        self._extra_head_scripts.append(path)

    # =================================================================
    # Build
    # =================================================================

    def build(self) -> FastAPI:
        """Finalize and return the FastAPI application."""
        # Register extra API routers
        for r in self._extra_routers:
            self.app.include_router(r["router"], prefix=r["prefix"], tags=r["tags"])

        # Build Jinja2 environment (app templates first, then core templates)
        core_templates = str(Path(__file__).parent / "templates")
        template_dirs = self._extra_template_dirs + [core_templates]
        self._jinja_env = Environment(
            loader=FileSystemLoader(template_dirs),
            autoescape=select_autoescape(["html"]),
            extensions=["jinja2.ext.i18n"],
        )
        self._jinja_env.install_gettext_translations(get_translator())

        # Mount static files: core first, then app-specific
        core_static = str(Path(__file__).parent / "static")
        self.app.mount(
            "/static/core",
            StaticFiles(directory=core_static),
            name="core_static",
        )
        for mount in self._extra_static_mounts:
            self.app.mount(
                mount["path"],
                StaticFiles(directory=mount["directory"]),
                name=f"static_{mount['path'].strip('/').replace('/', '_')}",
            )

        # Sort nav items
        self._nav_items.sort(key=lambda x: x.sort_order)

        # Store render function on app.state for pages.py to access
        self.app.state.render = self._render
        self.app.state.nav_items = self._nav_items
        self.app.state.config = self.config

        # Register core page routes
        self._register_core_pages()

        # Register app-specific page routes
        self._register_app_pages()

        # Register WebSocket endpoints
        self._register_websocket_endpoints()

        return self.app

    # =================================================================
    # Rendering
    # =================================================================

    def _render(self, template_name: str, request: Request, **context) -> HTMLResponse:
        """Render a Jinja2 template with locale-aware translations and nav items."""
        locale = getattr(request.state, "locale", "ja")
        self._jinja_env.install_gettext_translations(get_translator(locale))
        template = self._jinja_env.get_template(template_name)
        context.setdefault("nav_items", self._nav_items)
        context.setdefault("config", self.config)
        context.setdefault("app_title", self.title)
        context.setdefault("extra_head_scripts", self._extra_head_scripts)

        # Generate CSRF token for Double Submit Cookie pattern
        csrf_protect = CsrfProtect()
        csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
        context.setdefault("csrf_token", csrf_token)

        html = template.render(request=request, **context)
        response = HTMLResponse(html)
        csrf_protect.set_csrf_cookie(signed_token, response)
        return response

    # =================================================================
    # Core pages
    # =================================================================

    def _register_core_pages(self):
        """Register core page routes: login, password reset, users, dashboard."""
        config = self.config

        @self.app.get("/login")
        def login_page(request: Request):
            return self._render(
                "login.html",
                request,
                bootstrap_css_url=config.BOOTSTRAP_CSS_URL,
                bootstrap_icons_url=config.BOOTSTRAP_ICONS_URL,
            )

        @self.app.get("/forgot-password")
        def forgot_password_page(request: Request):
            return self._render(
                "forgot_password.html",
                request,
                bootstrap_css_url=config.BOOTSTRAP_CSS_URL,
                bootstrap_icons_url=config.BOOTSTRAP_ICONS_URL,
            )

        @self.app.get("/reset-password")
        def reset_password_page(request: Request):
            return self._render(
                "reset_password.html",
                request,
                bootstrap_css_url=config.BOOTSTRAP_CSS_URL,
                bootstrap_icons_url=config.BOOTSTRAP_ICONS_URL,
            )

        @self.app.get("/users")
        def users_page(request: Request):
            return self._render("users.html", request)

        @self.app.get("/")
        def dashboard(request: Request):
            try:
                return self._render("index.html", request)
            except TemplateNotFound:
                return self._render("_dashboard_base.html", request)

    # =================================================================
    # App-specific pages
    # =================================================================

    def _register_app_pages(self):
        """Register app-specific page routes from register_page() calls."""
        for route in self._page_routes:
            path = route["path"]
            template = route["template"]
            extra = route["extra_context"]

            def make_handler(_template, _extra):
                def handler(request: Request):
                    return self._render(_template, request, **_extra)

                return handler

            self.app.get(path)(make_handler(template, extra))

    # =================================================================
    # WebSocket
    # =================================================================

    def _register_websocket_endpoints(self):
        """Register WebSocket endpoints from register_websocket() calls."""
        for path, manager in self._ws_handlers.items():

            def make_ws_handler(_manager, _path, _portal):
                async def ws_handler(websocket: WebSocket):
                    await _manager.connect(websocket)
                    try:
                        user_id = websocket.session.get("user_id", 0)
                    except Exception:
                        user_id = 0
                    if not user_id:
                        await websocket.close(code=4401, reason="Not authenticated")
                        await _manager.disconnect(websocket)
                        return
                    logger.info("%s WebSocket client connected: %s", _path, websocket.client)
                    ping_interval = _portal.config.WS_PING_INTERVAL
                    ping_timeout = _portal.config.WS_PING_TIMEOUT
                    try:
                        while True:
                            try:
                                msg = await asyncio.wait_for(
                                    websocket.receive_text(),
                                    timeout=ping_interval,
                                )
                                # Respond to client-initiated pings
                                if msg == "__ping__":
                                    await websocket.send_text("__pong__")
                            except asyncio.TimeoutError:
                                # Idle timeout: send a ping and wait for any response
                                try:
                                    await asyncio.wait_for(
                                        websocket.send_text("__ping__"),
                                        timeout=ping_timeout,
                                    )
                                except Exception:
                                    # Send failed = zombie connection
                                    logger.warning(
                                        "%s WebSocket ping failed, disconnecting: %s",
                                        _path,
                                        websocket.client,
                                    )
                                    break
                    except WebSocketDisconnect:
                        pass
                    finally:
                        await _manager.disconnect(websocket)
                        logger.info(
                            "%s WebSocket client disconnected: %s",
                            _path,
                            websocket.client,
                        )

                return ws_handler

            self.app.websocket(path)(make_ws_handler(manager, path, self))
