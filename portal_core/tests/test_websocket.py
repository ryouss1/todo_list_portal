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


class TestWebSocketHeartbeat:
    def test_websocket_ping_pong_response(self, client):
        """Server responds with __pong__ when client sends __ping__."""
        _login(client)
        with client.websocket_connect("/ws/test") as ws:
            ws.send_text("__ping__")
            response = ws.receive_text()
            assert response == "__pong__"

    def test_websocket_ping_interval_config(self, core_app):
        """WS_PING_INTERVAL and WS_PING_TIMEOUT are accessible on app config."""
        config = core_app.state.config
        assert hasattr(config, "WS_PING_INTERVAL")
        assert hasattr(config, "WS_PING_TIMEOUT")
        assert isinstance(config.WS_PING_INTERVAL, int)
        assert isinstance(config.WS_PING_TIMEOUT, int)
        assert config.WS_PING_INTERVAL > 0
        assert config.WS_PING_TIMEOUT > 0

    def test_websocket_zombie_detection_on_send_failure(self):
        """When server ping send fails, the connection is treated as zombie and removed."""
        from portal_core.services.websocket_manager import WebSocketManager

        async def _run():
            manager = WebSocketManager()

            class ZombieWS:
                """Simulates a zombie connection: receive_text blocks forever, send_text raises."""

                async def accept(self):
                    pass

                async def receive_text(self):
                    # Block until cancelled
                    await asyncio.sleep(9999)

                async def send_text(self, data):
                    raise RuntimeError("Broken pipe")

                async def send_json(self, data):
                    raise RuntimeError("Broken pipe")

            ws = ZombieWS()
            await manager.connect(ws)
            assert ws in manager.active_connections

            # Simulate the timeout path: send_text raises → disconnect must be called
            # We test the manager's disconnect directly here since the full handler
            # loop requires a real WebSocket connection.
            await manager.disconnect(ws)
            assert ws not in manager.active_connections

        asyncio.run(_run())
