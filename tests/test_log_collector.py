"""Tests for log collector logic."""

import os
import tempfile

from app.models.log_source import LogSource
from app.services.log_collector import parse_log_line, read_new_lines


class TestParseLogLine:
    def _make_source(self, **kwargs):
        defaults = {
            "id": 1,
            "name": "test",
            "file_path": "/tmp/test.log",
            "system_name": "test-sys",
            "log_type": "app",
            "parser_pattern": None,
            "severity_field": None,
            "default_severity": "INFO",
            "polling_interval_sec": 30,
            "is_enabled": True,
            "last_read_position": 0,
            "last_file_size": 0,
        }
        defaults.update(kwargs)
        source = LogSource()
        for k, v in defaults.items():
            setattr(source, k, v)
        return source

    def test_no_pattern_raw_message(self):
        source = self._make_source()
        result = parse_log_line("Some raw log line", source)
        assert result.message == "Some raw log line"
        assert result.severity == "INFO"
        assert result.system_name == "test-sys"
        assert result.log_type == "app"

    def test_regex_parsing(self):
        source = self._make_source(
            parser_pattern=r"(?P<severity>\w+)\s+(?P<message>.+)",
            severity_field="severity",
        )
        result = parse_log_line("ERROR Something went wrong", source)
        assert result.severity == "ERROR"
        assert result.message == "Something went wrong"

    def test_non_matching_line(self):
        source = self._make_source(
            parser_pattern=r"^\[(?P<severity>\w+)\] (?P<message>.+)$",
            severity_field="severity",
        )
        result = parse_log_line("no brackets here", source)
        assert result.message == "no brackets here"
        assert result.severity == "INFO"


class TestReadNewLines:
    def _make_source(self, file_path, position=0, file_size=0):
        source = LogSource()
        source.file_path = file_path
        source.last_read_position = position
        source.last_file_size = file_size
        return source

    def test_collect_new_lines(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("line1\nline2\nline3\n")
            f.flush()
            path = f.name

        try:
            source = self._make_source(path)
            lines, pos, size = read_new_lines(source)
            assert len(lines) == 3
            assert lines[0].strip() == "line1"
            assert pos > 0
            assert size > 0
        finally:
            os.unlink(path)

    def test_skip_no_new_data(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("line1\n")
            f.flush()
            path = f.name

        try:
            file_size = os.path.getsize(path)
            source = self._make_source(path, position=file_size, file_size=file_size)
            lines, pos, size = read_new_lines(source)
            assert len(lines) == 0
        finally:
            os.unlink(path)

    def test_file_rotation(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("new content\n")
            f.flush()
            path = f.name

        try:
            # Simulate: last_file_size was 1000 but current file is smaller (rotation)
            source = self._make_source(path, position=500, file_size=1000)
            lines, pos, size = read_new_lines(source)
            assert len(lines) == 1
            assert lines[0].strip() == "new content"
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        source = self._make_source("/tmp/nonexistent_log_file_12345.log")
        try:
            read_new_lines(source)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_partial_line_held_back(self):
        """ISSUE-038: Incomplete lines (no trailing newline) should not be consumed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("complete line\nincomplete")
            f.flush()
            path = f.name

        try:
            source = self._make_source(path)
            lines, pos, size = read_new_lines(source)
            # Only the complete line should be returned
            assert len(lines) == 1
            assert lines[0].strip() == "complete line"
            # Position should be after "complete line\n" but before "incomplete"
            assert pos < size
        finally:
            os.unlink(path)

    def test_all_complete_lines_consumed(self):
        """When all lines end with newline, all are consumed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("line1\nline2\n")
            f.flush()
            path = f.name

        try:
            source = self._make_source(path)
            lines, pos, size = read_new_lines(source)
            assert len(lines) == 2
            assert pos == size  # All consumed
        finally:
            os.unlink(path)
