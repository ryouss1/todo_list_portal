"""Tests for background reminder checker."""

import asyncio
from unittest.mock import patch

import pytest


class _FakeApp:
    """Minimal app object with a .state attribute."""

    class _State:
        pass

    def __init__(self):
        self.state = self._State()


class TestReminderCheckerStartStop:
    @pytest.mark.asyncio
    async def test_start_disabled(self):
        """When CALENDAR_REMINDER_ENABLED=False, task should not be created."""
        app = _FakeApp()

        with patch("app.services.reminder_checker.CALENDAR_REMINDER_ENABLED", False):
            from app.services.reminder_checker import start_reminder_checker

            await start_reminder_checker(app)

        assert not hasattr(app.state, "reminder_task")

    @pytest.mark.asyncio
    async def test_start_enabled_creates_tasks(self):
        """When enabled, both main task and watchdog should be created."""
        app = _FakeApp()

        async def _fake_reminder_loop():
            await asyncio.sleep(999)

        async def _fake_watchdog_loop(_app):
            await asyncio.sleep(999)

        with (
            patch("app.services.reminder_checker.CALENDAR_REMINDER_ENABLED", True),
            patch("app.services.reminder_checker._reminder_loop", side_effect=_fake_reminder_loop),
            patch("app.services.reminder_checker._watchdog_loop", side_effect=_fake_watchdog_loop),
        ):
            from app.services.reminder_checker import start_reminder_checker, stop_reminder_checker

            await start_reminder_checker(app)

            assert hasattr(app.state, "reminder_task")
            assert app.state.reminder_task is not None
            assert hasattr(app.state, "reminder_watchdog")
            assert app.state.reminder_watchdog is not None

            # Clean up
            await stop_reminder_checker(app)

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self):
        """stop_reminder_checker should cancel both task and watchdog."""
        app = _FakeApp()

        async def _fake_loop():
            while True:
                await asyncio.sleep(1)

        app.state.reminder_task = asyncio.create_task(_fake_loop())
        app.state.reminder_watchdog = asyncio.create_task(_fake_loop())

        from app.services.reminder_checker import stop_reminder_checker

        await stop_reminder_checker(app)

        assert app.state.reminder_task.cancelled()
        assert app.state.reminder_watchdog.cancelled()

    @pytest.mark.asyncio
    async def test_stop_no_task(self):
        """stop_reminder_checker should not raise when no tasks exist."""
        app = _FakeApp()

        from app.services.reminder_checker import stop_reminder_checker

        await stop_reminder_checker(app)  # Should not raise


def test_watchdog_step_exists():
    """Watchdog step function must exist (TD-03 requirement)."""
    from app.services import reminder_checker

    assert hasattr(reminder_checker, "_watchdog_step")
    assert hasattr(reminder_checker, "_watchdog_loop")
