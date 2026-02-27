"""Tests for WebSocket infrastructure (portal_core)."""

import asyncio
import inspect


def _login(client):
    """Login to get session cookie for WebSocket auth."""
    client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})


class TestWebSocket:
    def test_websocket_connect(self, client):
        """Authenticated WebSocket connection succeeds."""
        _login(client)
        with client.websocket_connect("/ws/test"):
            pass  # Connection success = no exception

    def test_websocket_broadcast(self, client, core_app):
        """WebSocketManager.broadcast sends data to connected clients."""
        import asyncio

        _login(client)
        ws_manager = core_app.state.test_ws_manager
        with client.websocket_connect("/ws/test") as ws:
            # Broadcast a message via the manager (broadcast expects a dict)
            asyncio.get_event_loop().run_until_complete(ws_manager.broadcast({"msg": "hello"}))
            data = ws.receive_json()
            assert data["msg"] == "hello"

    def test_websocket_disconnect_cleanup(self, client, core_app):
        """Disconnected clients are removed from active connections."""
        _login(client)
        ws_manager = core_app.state.test_ws_manager
        initial_count = len(ws_manager.active_connections)
        with client.websocket_connect("/ws/test"):
            assert len(ws_manager.active_connections) == initial_count + 1
        assert len(ws_manager.active_connections) == initial_count

    def test_websocket_unauthenticated_disconnect(self, raw_client):
        """Unauthenticated WebSocket connections are closed with 4401."""
        import pytest
        from starlette.websockets import WebSocketDisconnect

        with raw_client.websocket_connect("/ws/test") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_json()
            assert exc_info.value.code == 4401


class TestWebSocketAsync:
    def test_websocket_disconnect_is_async(self):
        """disconnect() must be a coroutine so asyncio.Lock can be acquired."""
        from portal_core.services.websocket_manager import WebSocketManager

        assert inspect.iscoroutinefunction(WebSocketManager.disconnect)

    def test_websocket_concurrent_broadcast_and_disconnect(self):
        """Concurrent broadcast + disconnect must not raise RuntimeError or lose connections."""
        from portal_core.services.websocket_manager import WebSocketManager

        async def _run():
            manager = WebSocketManager()

            class FakeWS:
                async def accept(self):
                    pass

                async def send_json(self, data):
                    pass

            ws1, ws2 = FakeWS(), FakeWS()
            await manager.connect(ws1)
            await manager.connect(ws2)
            assert len(manager.active_connections) == 2

            # Concurrent broadcast and disconnect — must not raise
            await asyncio.gather(
                manager.broadcast({"msg": "hi"}),
                manager.disconnect(ws1),
            )

            assert len(manager.active_connections) == 1
            assert ws2 in manager.active_connections

        asyncio.run(_run())
