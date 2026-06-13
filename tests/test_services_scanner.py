"""
Tests for the Scanner service module.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestVulnerabilityScanner:
    """Tests for the VulnerabilityScanner class."""

    @pytest.fixture
    def scanner(self):
        from services.scanner import VulnerabilityScanner
        return VulnerabilityScanner()

    def test_scanner_initialization(self, scanner):
        """Scanner initializes with empty active scans."""
        assert scanner.active_scans == {}
        assert scanner.db is None

    @pytest.mark.asyncio
    async def test_start_scan(self, scanner):
        """start_scan creates a new scan entry."""
        result = await scanner.start_scan(project_id=1, scan_type="full")
        assert result["project_id"] == 1
        assert result["scan_type"] == "full"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_start_scan_with_duration(self, scanner):
        """start_scan accepts custom fuzz duration."""
        result = await scanner.start_scan(
            project_id=1,
            scan_type="targeted",
            fuzz_duration=1800
        )
        assert result["project_id"] == 1

    @pytest.mark.asyncio
    async def test_cancel_scan(self, scanner):
        """cancel_scan updates scan status."""
        await scanner.start_scan(project_id=1)
        await scanner.cancel_scan(scan_id=1)
        status = await scanner.get_scan_status(scan_id=1)
        assert status["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_get_scan_status_existing(self, scanner):
        """get_scan_status returns scan info for existing scan."""
        await scanner.start_scan(project_id=42)
        status = await scanner.get_scan_status(scan_id=1)
        assert status is not None
        assert status["project_id"] == 42

    @pytest.mark.asyncio
    async def test_get_scan_status_nonexistent(self, scanner):
        """get_scan_status returns None for non-existent scan."""
        status = await scanner.get_scan_status(scan_id=999)
        assert status is None

    @pytest.mark.asyncio
    async def test_list_active_scans_empty(self, scanner):
        """list_active_scans returns empty list initially."""
        scans = await scanner.list_active_scans()
        assert scans == []

    @pytest.mark.asyncio
    async def test_list_active_scans_multiple(self, scanner):
        """list_active_scans returns all active scans."""
        await scanner.start_scan(project_id=1)
        await scanner.start_scan(project_id=2)
        await scanner.start_scan(project_id=3)
        scans = await scanner.list_active_scans()
        assert len(scans) == 3


class TestTargetConnectivity:
    """Tests for target connectivity testing."""

    @pytest.mark.asyncio
    async def test_test_target_connectivity_unreachable(self):
        """test_target_connectivity returns unreachable for invalid host."""
        from services.scanner import test_target_connectivity
        result = await test_target_connectivity(
            target_ip="192.0.2.1",  # RFC 5737 TEST-NET
            target_port=502,
            protocol="modbus_tcp"
        )
        assert result["reachable"] is False
        assert result["target_ip"] == "192.0.2.1"
        assert result["target_port"] == 502

    @pytest.mark.asyncio
    async def test_test_target_connectivity_returns_protocol(self):
        """test_target_connectivity includes protocol in result."""
        from services.scanner import test_target_connectivity
        result = await test_target_connectivity(
            target_ip="127.0.0.1",
            target_port=1,
            protocol="dnp3"
        )
        assert result["protocol"] == "dnp3"


class TestGetScanStatusStandalone:
    """Tests for the standalone get_scan_status function."""

    @pytest.mark.asyncio
    async def test_get_scan_status_returns_dict(self):
        """Standalone get_scan_status returns a dict."""
        from services.scanner import get_scan_status
        result = await get_scan_status(scan_id=1)
        assert isinstance(result, dict)
        assert "scan_id" in result
        assert result["scan_id"] == 1
