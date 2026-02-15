"""Tests for WebSocket endpoints."""


def _login(client):
    """Login to get session cookie for WebSocket auth."""
    client.post("/api/auth/login", json={"email": "default_user@example.com", "password": "testpass"})


class TestWebSocket:
    def test_websocket_connect(self, client):
        _login(client)
        with client.websocket_connect("/ws/logs"):
            pass  # Connection success = no exception

    def test_websocket_broadcast_on_log_create(self, client):
        _login(client)
        with client.websocket_connect("/ws/logs") as ws:
            client.post(
                "/api/logs/",
                json={
                    "system_name": "ws-test",
                    "log_type": "app",
                    "severity": "INFO",
                    "message": "Broadcast test",
                },
            )
            data = ws.receive_json()
            assert data["system_name"] == "ws-test"
            assert data["message"] == "Broadcast test"

    def test_websocket_disconnect_cleanup(self, client):
        _login(client)
        from app.services.websocket_manager import log_ws_manager

        initial_count = len(log_ws_manager.active_connections)
        with client.websocket_connect("/ws/logs"):
            assert len(log_ws_manager.active_connections) == initial_count + 1
        assert len(log_ws_manager.active_connections) == initial_count

    def test_websocket_unauthenticated_disconnect(self, raw_client):
        """Unauthenticated WebSocket connections are closed with 4401."""
        import pytest
        from starlette.websockets import WebSocketDisconnect

        with raw_client.websocket_connect("/ws/logs") as ws:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                ws.receive_json()
            assert exc_info.value.code == 4401
