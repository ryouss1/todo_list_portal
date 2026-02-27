"""Tests for background log scanner."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_source_due():
    """A source whose polling interval has elapsed (should be scanned)."""
    source = MagicMock()
    source.id = 1
    source.name = "Test Source"
    source.polling_interval_sec = 60
    source.last_checked_at = datetime.now(timezone.utc) - timedelta(seconds=120)
    return source


@pytest.fixture
def mock_source_not_due():
    """A source whose polling interval has NOT elapsed (should be skipped)."""
    source = MagicMock()
    source.id = 2
    source.name = "Recent Source"
    source.polling_interval_sec = 60
    source.last_checked_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    return source


@pytest.fixture
def mock_source_never_scanned():
    """A source that has never been scanned (last_checked_at=None)."""
    source = MagicMock()
    source.id = 3
    source.name = "New Source"
    source.polling_interval_sec = 60
    source.last_checked_at = None
    return source


class _FakeState:
    """Simple state object for testing (no auto-creation like MagicMock)."""

    pass


class _FakeApp:
    """Simple app object with a state attribute."""

    def __init__(self):
        self.state = _FakeState()


class TestStartStopScanner:
    """Tests for start_scanner / stop_scanner lifecycle."""

    @pytest.mark.asyncio
    async def test_start_scanner_disabled(self):
        """When LOG_SCANNER_ENABLED=False, no task should be created."""
        app = _FakeApp()
        with patch("app.services.log_scanner.LOG_SCANNER_ENABLED", False):
            from app.services.log_scanner import start_scanner

            await start_scanner(app)
        assert not hasattr(app.state, "log_scanner_task")

    @pytest.mark.asyncio
    async def test_start_scanner_enabled(self):
        """When LOG_SCANNER_ENABLED=True, a task should be created."""
        app = _FakeApp()

        async def _fake_loop():
            await asyncio.sleep(999)

        with (
            patch("app.services.log_scanner.LOG_SCANNER_ENABLED", True),
            patch(
                "app.services.log_scanner._scanner_loop",
                side_effect=_fake_loop,
            ),
        ):
            from app.services.log_scanner import start_scanner, stop_scanner

            await start_scanner(app)
            assert hasattr(app.state, "log_scanner_task")
            assert app.state.log_scanner_task is not None
            # Clean up
            await stop_scanner(app)

    @pytest.mark.asyncio
    async def test_stop_scanner(self):
        """stop_scanner should cancel the running task."""
        app = _FakeApp()

        async def _fake_loop():
            while True:
                await asyncio.sleep(1)

        app.state.log_scanner_task = asyncio.create_task(_fake_loop())
        from app.services.log_scanner import stop_scanner

        await stop_scanner(app)
        assert app.state.log_scanner_task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_scanner_no_task(self):
        """stop_scanner should not raise when no task exists."""
        app = _FakeApp()
        from app.services.log_scanner import stop_scanner

        await stop_scanner(app)  # Should not raise


class TestScanDueSources:
    """Tests for _scan_due_sources logic."""

    @pytest.mark.asyncio
    async def test_no_sources(self):
        """No enabled sources — should complete without error."""
        mock_db = MagicMock()
        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.crud_log_source.get_enabled_log_sources",
                return_value=[],
            ),
        ):
            from app.services.log_scanner import _scan_due_sources

            await _scan_due_sources()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_source_not_due(self, mock_source_not_due):
        """Source whose polling interval hasn't elapsed should be skipped."""
        mock_db = MagicMock()
        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.crud_log_source.get_enabled_log_sources",
                return_value=[mock_source_not_due],
            ),
            patch("app.services.log_scanner.asyncio.to_thread") as mock_to_thread,
        ):
            from app.services.log_scanner import _scan_due_sources

            await _scan_due_sources()
        mock_to_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_source_due(self, mock_source_due):
        """Source whose polling interval has elapsed should be scanned."""
        mock_db = MagicMock()
        scan_result = {
            "file_count": 5,
            "new_count": 1,
            "updated_count": 0,
            "alerts_created": 0,
            "message": "Scan completed: 5 files",
            "changed_paths": [],
            "alert_broadcast": None,
        }
        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.crud_log_source.get_enabled_log_sources",
                return_value=[mock_source_due],
            ),
            patch(
                "app.services.log_scanner.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=scan_result,
            ),
        ):
            from app.services.log_scanner import _scan_due_sources

            await _scan_due_sources()

    @pytest.mark.asyncio
    async def test_source_never_scanned(self, mock_source_never_scanned):
        """Source with last_checked_at=None should be scanned immediately."""
        mock_db = MagicMock()
        scan_result = {
            "file_count": 0,
            "new_count": 0,
            "updated_count": 0,
            "alerts_created": 0,
            "message": "Scan completed",
            "changed_paths": [],
            "alert_broadcast": None,
        }
        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.crud_log_source.get_enabled_log_sources",
                return_value=[mock_source_never_scanned],
            ),
            patch(
                "app.services.log_scanner.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=scan_result,
            ) as mock_to_thread,
        ):
            from app.services.log_scanner import _scan_due_sources

            await _scan_due_sources()
        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_isolation(self, mock_source_due):
        """Error in one source should not prevent scanning others."""
        mock_db = MagicMock()
        source2 = MagicMock()
        source2.id = 99
        source2.name = "Good Source"
        source2.polling_interval_sec = 60
        source2.last_checked_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        call_count = 0

        async def mock_to_thread_fn(fn, source_id):
            nonlocal call_count
            call_count += 1
            if source_id == mock_source_due.id:
                raise ConnectionError("FTP refused")
            return {
                "file_count": 1,
                "new_count": 0,
                "updated_count": 0,
                "alerts_created": 0,
                "message": "ok",
                "changed_paths": [],
                "alert_broadcast": None,
            }

        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.crud_log_source.get_enabled_log_sources",
                return_value=[mock_source_due, source2],
            ),
            patch(
                "app.services.log_scanner.asyncio.to_thread",
                side_effect=mock_to_thread_fn,
            ),
        ):
            from app.services.log_scanner import _scan_due_sources

            await _scan_due_sources()  # Should not raise
        # Both sources attempted
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_broadcasts_alert(self, mock_source_due):
        """When scan creates alert, WebSocket broadcast should be called."""
        mock_db = MagicMock()
        alert_data = {
            "id": 42,
            "title": "File changes detected",
            "message": "1 new file",
            "severity": "warning",
            "source": "log_source:1",
            "rule_id": None,
            "is_active": True,
            "acknowledged": False,
            "created_at": "2026-02-18T10:00:00+00:00",
        }
        scan_result = {
            "file_count": 1,
            "new_count": 1,
            "updated_count": 0,
            "alerts_created": 1,
            "message": "Scan completed",
            "changed_paths": [],
            "alert_broadcast": alert_data,
        }
        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.crud_log_source.get_enabled_log_sources",
                return_value=[mock_source_due],
            ),
            patch(
                "app.services.log_scanner.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=scan_result,
            ),
            patch(
                "app.services.log_scanner.alert_ws_manager.broadcast",
                new_callable=AsyncMock,
            ) as mock_broadcast,
        ):
            from app.services.log_scanner import _scan_due_sources

            await _scan_due_sources()
        mock_broadcast.assert_called_once_with({"type": "new_alert", "alert": alert_data})


class TestScanInThread:
    """Tests for _scan_in_thread."""

    def test_scan_in_thread_uses_own_session(self):
        """_scan_in_thread should create and close its own DB session."""
        mock_db = MagicMock()
        scan_result = {"file_count": 0, "message": "ok"}
        with (
            patch("app.services.log_scanner.SessionLocal", return_value=mock_db),
            patch(
                "app.services.log_scanner.log_source_service.scan_source",
                return_value=scan_result,
            ) as mock_scan,
        ):
            from app.services.log_scanner import _scan_in_thread

            result = _scan_in_thread(5)
        mock_scan.assert_called_once_with(mock_db, 5)
        mock_db.close.assert_called_once()
        assert result == scan_result


# ---------------------------------------------------------------------------
# Watchdog tests
# ---------------------------------------------------------------------------


def test_watchdog_step_exists():
    """_watchdog_step must be importable from log_scanner."""
    from app.services import log_scanner

    assert hasattr(log_scanner, "_watchdog_step"), "_watchdog_step not found in log_scanner"
    assert asyncio.iscoroutinefunction(log_scanner._watchdog_step)


@pytest.mark.asyncio
async def test_watchdog_restarts_completed_scanner_task():
    """Watchdog must restart the scanner if the background task has completed."""
    from app.services import log_scanner

    class MockApp:
        class state:
            log_scanner_task = None
            log_scanner_watchdog = None

    app = MockApp()

    # Simulate a completed (crashed) task
    app.state.log_scanner_task = asyncio.create_task(asyncio.sleep(0))
    await asyncio.sleep(0.05)  # Let it complete
    assert app.state.log_scanner_task.done()

    # Run one watchdog step — should restart
    await log_scanner._watchdog_step(app)

    assert app.state.log_scanner_task is not None
    assert not app.state.log_scanner_task.done(), "Task should be running after watchdog restart"

    # Cleanup
    app.state.log_scanner_task.cancel()
    try:
        await app.state.log_scanner_task
    except asyncio.CancelledError:
        pass


def test_scanner_stale_config_exists():
    """LOG_SCANNER_STALE_MINUTES must be defined in config."""
    from app import config

    assert hasattr(config, "LOG_SCANNER_STALE_MINUTES")
    assert isinstance(config.LOG_SCANNER_STALE_MINUTES, int)
    assert config.LOG_SCANNER_STALE_MINUTES > 0
