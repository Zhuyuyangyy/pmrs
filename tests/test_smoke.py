"""
Smoke tests: verify all core modules can be imported and basic objects created.

Run:
    cd D:/ZYY Project/pmrs
    python -m pytest tests/test_smoke.py -v
"""

import sys
from pathlib import Path

import pytest

# Ensure backend is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def test_import_core_config():
    """Core config module can be imported and Settings instantiated."""
    from core.config import Settings
    s = Settings()
    assert s.PROJECT_NAME is not None
    assert s.VERSION is not None


def test_import_core_response():
    """Response helpers can be imported."""
    from core.response import ApiException
    assert ApiException is not None


def test_import_core_security():
    """Security middleware can be imported."""
    from core.security import SecurityHeadersMiddleware, RateLimitMiddleware
    assert SecurityHeadersMiddleware is not None
    assert RateLimitMiddleware is not None


def test_import_core_metrics():
    """Metrics middleware can be imported."""
    from core.metrics import MetricsMiddleware, metrics
    assert MetricsMiddleware is not None


def test_import_protocols_base():
    """Protocol base classes can be imported."""
    from protocols.base import ProtocolBase, ProtocolField, ProtocolRegistry
    assert ProtocolBase is not None
    assert ProtocolField is not None
    assert ProtocolRegistry is not None


def test_import_protocol_modbus():
    """ModbusTCP protocol can be imported."""
    from protocols.modbus_tcp import ModbusTCP
    assert ModbusTCP is not None


def test_import_protocol_dnp3():
    """DNP3 protocol can be imported (skip if not implemented)."""
    try:
        from protocols.dnp3 import DNP3Protocol
        assert DNP3Protocol is not None
    except (ImportError, AttributeError):
        pytest.skip("DNP3 protocol module not yet implemented")


def test_import_protocol_iec61850():
    """IEC61850 protocol can be imported (skip if not implemented)."""
    try:
        from protocols.iec61850 import IEC61850Protocol
        assert IEC61850Protocol is not None
    except (ImportError, AttributeError):
        pytest.skip("IEC 61850 protocol module not yet implemented")


def test_import_cvss_calculator():
    """CVSS calculator can be imported."""
    from services.cvss import CVSSCalculator, cvss_calculator
    assert CVSSCalculator is not None
    assert cvss_calculator is not None


def test_protocol_registry_populated():
    """ProtocolRegistry should have modbus_tcp registered after import."""
    from protocols.base import ProtocolRegistry
    protocols = ProtocolRegistry.list_protocols()
    assert "modbus_tcp" in protocols


def test_modbus_tcp_instantiation():
    """ModbusTCP can be instantiated and has correct metadata."""
    from protocols.modbus_tcp import ModbusTCP
    modbus = ModbusTCP()
    assert modbus.PROTOCOL_NAME == "modbus_tcp"
    assert modbus.DEFAULT_PORT == 502
    assert len(modbus.FUNCTION_CODES) > 0
