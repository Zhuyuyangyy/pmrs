"""
Shared test fixtures for PMRS test suite.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def settings():
    """Import and return Settings instance."""
    from core.config import Settings
    return Settings()


@pytest.fixture
def cvss_calculator():
    """Return a CVSS 3.1 calculator instance."""
    from services.cvss import CVSSCalculator
    return CVSSCalculator(version="3.1")


@pytest.fixture
def modbus_protocol():
    """Return a ModbusTCP protocol instance."""
    from protocols.modbus_tcp import ModbusTCP
    return ModbusTCP()


@pytest.fixture
def iec61850_protocol():
    """Return an IEC61850 protocol instance."""
    from protocols.iec61850 import IEC61850Protocol
    return IEC61850Protocol()


@pytest.fixture
def dnp3_protocol():
    """Return a DNP3 protocol instance."""
    from protocols.dnp3 import DNP3Protocol
    return DNP3Protocol()


@pytest.fixture
def mock_llm_service():
    """Return a mocked LLM service."""
    with patch("services.llm_service.llm_service") as mock:
        mock.understand_protocol = AsyncMock(return_value={
            "states": ["IDLE", "ACTIVE"],
            "critical_functions": ["read_registers"],
            "potential_vulnerabilities": ["buffer_overflow"],
            "semantic_summary": "Test protocol",
        })
        mock.generate_testcases = AsyncMock(return_value=[
            {
                "function_code": "0x03",
                "raw_hex": "00000000000601030000000a",
                "semantic_description": "Read 10 registers",
                "edge_case": False,
            }
        ])
        mock.classify_vulnerability = AsyncMock(return_value={
            "vulnerability_type": "buffer_overflow",
            "severity": "HIGH",
            "cvss_base_score": 8.5,
            "title": "Test vulnerability",
        })
        mock.generate_poc = AsyncMock(return_value="import socket\n# PoC code here")
        yield mock


@pytest.fixture
def mock_db_session():
    """Return a mocked database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    return session
