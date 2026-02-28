"""Re-export WebSocketManager from portal_core.

Singleton instances remain here (app-specific).
"""

from portal_core.services.websocket_manager import WebSocketManager  # noqa: F401

log_ws_manager = WebSocketManager()
presence_ws_manager = WebSocketManager()
alert_ws_manager = WebSocketManager()
calendar_ws_manager = WebSocketManager()
site_ws_manager = WebSocketManager()
