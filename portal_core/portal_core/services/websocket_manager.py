import asyncio
import logging
from typing import List

from fastapi import WebSocket

logger = logging.getLogger("portal_core.services.websocket")


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket connected. Total connections: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket disconnected. Total connections: %d", len(self.active_connections))

    async def broadcast(self, data: dict):
        async with self._lock:
            connections = self.active_connections[:]
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.append(connection)
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
                        logger.warning(
                            "Removed dead WebSocket connection. Total: %d",
                            len(self.active_connections),
                        )
