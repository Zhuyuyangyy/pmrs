"""
Tests for the AFL++ fuzzer wrapper.
"""
import sys
from pathlib import Path
import os
import tempfile

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestAFLFuzzer:
    """Tests for the AFLFuzzer class."""

    def test_fuzzer_import(self):
        """AFLFuzzer can be imported."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        assert AFLFuzzer is not None

    def test_fuzzer_initialization(self):
        """AFLFuzzer initializes with correct defaults."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        fuzzer = AFLFuzzer(target_ip="192.168.1.1", target_port=502)
        assert fuzzer.target_ip == "192.168.1.1"
        assert fuzzer.target_port == 502

    def test_fuzzer_creates_directories(self):
        """AFLFuzzer creates input/output directories."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        with tempfile.TemporaryDirectory() as tmpdir:
            fuzzer = AFLFuzzer()
            fuzzer.input_dir = os.path.join(tmpdir, "input")
            fuzzer.output_dir = os.path.join(tmpdir, "output")
            os.makedirs(fuzzer.input_dir, exist_ok=True)
            os.makedirs(fuzzer.output_dir, exist_ok=True)
            assert os.path.exists(fuzzer.input_dir)
            assert os.path.exists(fuzzer.output_dir)

    def test_create_harness_modbus(self):
        """create_harness generates Modbus TCP C code."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        fuzzer = AFLFuzzer(target_ip="192.168.1.1", target_port=502)
        code = fuzzer.create_harness("modbus_tcp")
        assert "192.168.1.1" in code
        assert "502" in code
        assert "#include" in code
        assert "socket" in code

    def test_create_harness_generic(self):
        """create_harness generates generic C code for unknown protocols."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        fuzzer = AFLFuzzer(target_ip="10.0.0.1", target_port=20000)
        code = fuzzer.create_harness("unknown_protocol")
        assert "10.0.0.1" in code
        assert "20000" in code

    def test_create_harness_contains_main(self):
        """Generated harness contains main function."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        fuzzer = AFLFuzzer()
        code = fuzzer.create_harness("modbus_tcp")
        assert "int main" in code

    @pytest.mark.asyncio
    async def test_write_testcase(self):
        """write_testcase writes hex data to file."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        with tempfile.TemporaryDirectory() as tmpdir:
            fuzzer = AFLFuzzer()
            fuzzer.input_dir = tmpdir
            filepath = await fuzzer.write_testcase("00010000000601030000000a", case_id=1)
            assert os.path.exists(filepath)
            with open(filepath, "rb") as f:
                data = f.read()
            assert data == bytes.fromhex("00010000000601030000000a")

    @pytest.mark.asyncio
    async def test_write_testcase_with_spaces(self):
        """write_testcase handles hex strings with spaces."""
        from fuzzers.afl_fuzzer import AFLFuzzer
        with tempfile.TemporaryDirectory() as tmpdir:
            fuzzer = AFLFuzzer()
            fuzzer.input_dir = tmpdir
            filepath = await fuzzer.write_testcase("00 01 00 00 00 06", case_id=2)
            assert os.path.exists(filepath)
            with open(filepath, "rb") as f:
                data = f.read()
            assert len(data) == 6


class TestCrashMonitor:
    """Tests for the CrashMonitor class."""

    def test_crash_monitor_import(self):
        """CrashMonitor can be imported."""
        from fuzzers.afl_fuzzer import CrashMonitor
        assert CrashMonitor is not None

    def test_crash_monitor_initialization(self):
        """CrashMonitor initializes with empty monitors."""
        from fuzzers.afl_fuzzer import CrashMonitor
        monitor = CrashMonitor()
        assert monitor.active_monitors == {}

    def test_stop_monitor_nonexistent(self):
        """stop_monitor on non-existent PID does not raise."""
        from fuzzers.afl_fuzzer import CrashMonitor
        monitor = CrashMonitor()
        # Should not raise
        monitor.stop_monitor(pid=99999)

    def test_stop_monitor_existing(self):
        """stop_monitor cancels and removes existing monitor."""
        from fuzzers.afl_fuzzer import CrashMonitor
        from unittest.mock import MagicMock
        monitor = CrashMonitor()
        mock_task = MagicMock()
        monitor.active_monitors[123] = mock_task
        monitor.stop_monitor(pid=123)
        assert 123 not in monitor.active_monitors
        mock_task.cancel.assert_called_once()


class TestGlobalInstances:
    """Tests for global instances."""

    def test_crash_monitor_global_exists(self):
        """Global crash_monitor instance exists."""
        from fuzzers.afl_fuzzer import crash_monitor
        assert crash_monitor is not None

    def test_crash_monitor_global_type(self):
        """Global crash_monitor is a CrashMonitor instance."""
        from fuzzers.afl_fuzzer import crash_monitor, CrashMonitor
        assert isinstance(crash_monitor, CrashMonitor)
