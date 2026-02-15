import logging
from typing import List

from fastapi import WebSocket

logger = logging.getLogger("app.services.websocket")


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connected. Total connections: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total connections: %d", len(self.active_connections))

    async def broadcast(self, data: dict):
        disconnected = []
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)
            logger.warning("Removed dead WebSocket connection. Total: %d", len(self.active_connections))


log_ws_manager = WebSocketManager()
presence_ws_manager = WebSocketManager()
alert_ws_manager = WebSocketManager()
calendar_ws_manager = WebSocketManager()
