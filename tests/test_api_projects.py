"""
Tests for the Projects API endpoints.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class TestProjectAPI:
    """Tests for project management API endpoints."""

    def test_project_create_schema(self):
        """ProjectCreate schema validates correctly."""
        from schemas.schemas import ProjectCreate
        project = ProjectCreate(
            name="Test Project",
            target_ip="192.168.1.1",
            target_port=502,
            protocol="modbus_tcp",
        )
        assert project.name == "Test Project"
        assert project.target_port == 502
        assert project.protocol.value == "modbus_tcp"

    def test_project_create_schema_validation_port_range(self):
        """ProjectCreate rejects invalid port numbers."""
        from schemas.schemas import ProjectCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProjectCreate(
                name="Test",
                target_ip="192.168.1.1",
                target_port=99999,
                protocol="modbus_tcp",
            )

    def test_project_update_schema_partial(self):
        """ProjectUpdate allows partial updates."""
        from schemas.schemas import ProjectUpdate
        update = ProjectUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.config is None

    def test_project_response_schema(self):
        """ProjectResponse schema works with from_attributes."""
        from schemas.schemas import ProjectResponse
        from datetime import datetime
        data = {
            "id": 1,
            "name": "Test",
            "target_ip": "192.168.1.1",
            "target_port": 502,
            "protocol": "modbus_tcp",
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        resp = ProjectResponse(**data)
        assert resp.id == 1
        assert resp.status.value == "pending"

    def test_scan_create_schema(self):
        """ScanCreate schema validates correctly."""
        from schemas.schemas import ScanCreate
        scan = ScanCreate(project_id=1, scan_type="full")
        assert scan.project_id == 1
        assert scan.scan_type == "full"

    def test_scan_create_invalid_type(self):
        """ScanCreate rejects invalid scan types."""
        from schemas.schemas import ScanCreate
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ScanCreate(project_id=1, scan_type="invalid_type")

    def test_vulnerability_response_schema(self):
        """VulnerabilityResponse schema works correctly."""
        from schemas.schemas import VulnerabilityResponse
        from datetime import datetime
        data = {
            "id": 1,
            "project_id": 1,
            "vulnerability_type": "buffer_overflow",
            "protocol": "modbus_tcp",
            "title": "Test Vuln",
            "severity": "high",
            "created_at": datetime.now(),
        }
        resp = VulnerabilityResponse(**data)
        assert resp.id == 1
        assert resp.severity.value == "high"

    def test_cvss_calculation_schema(self):
        """CVSSCalculation schema validates correctly."""
        from schemas.schemas import CVSSCalculation
        calc = CVSSCalculation()
        assert calc.attack_vector == "N"
        assert calc.attack_complexity == "L"
        assert calc.scope == "U"

    def test_dashboard_stats_schema(self):
        """DashboardStats schema works correctly."""
        from schemas.schemas import DashboardStats
        stats = DashboardStats(
            total_projects=10,
            total_scans=50,
            total_vulnerabilities=100,
            critical_vulnerabilities=5,
            high_vulnerabilities=20,
            active_scans=3,
            recent_crashes=2,
        )
        assert stats.total_projects == 10
        assert stats.critical_vulnerabilities == 5

    def test_test_generation_request_schema(self):
        """TestGenerationRequest schema validates correctly."""
        from schemas.schemas import TestGenerationRequest
        req = TestGenerationRequest(
            protocol="modbus_tcp",
            num_testcases=20,
            edge_case_ratio=0.5,
        )
        assert req.num_testcases == 20
        assert req.edge_case_ratio == 0.5

    def test_test_generation_request_max_testcases(self):
        """TestGenerationRequest enforces max testcases limit."""
        from schemas.schemas import TestGenerationRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            TestGenerationRequest(protocol="modbus_tcp", num_testcases=200)
