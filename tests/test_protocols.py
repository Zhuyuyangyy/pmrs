"""
Unit tests for ICS protocol implementations: ModbusTCP, ProtocolField, ProtocolRegistry.

Run:
    cd D:/ZYY Project/pmrs
    python -m pytest tests/test_protocols.py -v
"""

import sys
import struct
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ---------------------------------------------------------------------------
# ProtocolField Tests
# ---------------------------------------------------------------------------
class TestProtocolField:
    """Tests for the ProtocolField class."""

    def test_parse_uint(self):
        """Parse unsigned integer from bytes."""
        from protocols.base import ProtocolField
        field = ProtocolField("test", offset=0, length=2, dtype="uint")
        data = struct.pack(">H", 256)  # 0x0100
        assert field.parse_value(data) == 256

    def test_parse_int(self):
        """Parse signed integer from bytes."""
        from protocols.base import ProtocolField
        field = ProtocolField("test", offset=0, length=2, dtype="int")
        data = struct.pack(">h", -1)
        assert field.parse_value(data) == -1

    def test_parse_bytes(self):
        """Parse raw bytes."""
        from protocols.base import ProtocolField
        field = ProtocolField("test", offset=0, length=4, dtype="bytes")
        data = b'\x01\x02\x03\x04'
        assert field.parse_value(data) == b'\x01\x02\x03\x04'

    def test_parse_str(self):
        """Parse ASCII string."""
        from protocols.base import ProtocolField
        field = ProtocolField("test", offset=0, length=5, dtype="str")
        data = b'hello'
        assert field.parse_value(data) == "hello"

    def test_build_uint(self):
        """Build unsigned integer bytes."""
        from protocols.base import ProtocolField
        field = ProtocolField("test", offset=0, length=2, dtype="uint")
        result = field.build_value(256)
        assert result == struct.pack(">H", 256)

    def test_build_str(self):
        """Build ASCII string bytes with padding."""
        from protocols.base import ProtocolField
        field = ProtocolField("test", offset=0, length=8, dtype="str")
        result = field.build_value("hi")
        assert len(result) == 8
        assert result[:2] == b'hi'


# ---------------------------------------------------------------------------
# ProtocolRegistry Tests
# ---------------------------------------------------------------------------
class TestProtocolRegistry:
    """Tests for the ProtocolRegistry."""

    def test_register_and_get(self):
        """Register and retrieve a protocol class."""
        from protocols.base import ProtocolRegistry, ProtocolBase

        class DummyProtocol(ProtocolBase):
            PROTOCOL_NAME = "dummy"
            DEFAULT_PORT = 9999
            def parse(self, data): return None
            def build(self, fields): return b""
            def validate(self, data): return True

        ProtocolRegistry.register("dummy_test", DummyProtocol)
        result = ProtocolRegistry.get("dummy_test")
        assert result is DummyProtocol

    def test_list_protocols(self):
        """list_protocols returns a list of registered names."""
        from protocols.base import ProtocolRegistry
        protocols = ProtocolRegistry.list_protocols()
        assert isinstance(protocols, list)
        assert "modbus_tcp" in protocols

    def test_get_unknown_returns_none(self):
        """Getting an unregistered protocol returns None."""
        from protocols.base import ProtocolRegistry
        assert ProtocolRegistry.get("nonexistent_protocol_xyz") is None


# ---------------------------------------------------------------------------
# ModbusTCP Tests
# ---------------------------------------------------------------------------
class TestModbusTCP:
    """Tests for ModbusTCP protocol implementation."""

    @pytest.fixture
    def modbus(self):
        from protocols.modbus_tcp import ModbusTCP
        return ModbusTCP()

    def test_protocol_metadata(self, modbus):
        """ModbusTCP has correct name and port."""
        assert modbus.PROTOCOL_NAME == "modbus_tcp"
        assert modbus.DEFAULT_PORT == 502
        assert modbus.HEADER_LENGTH == 7

    def test_initial_state(self, modbus):
        """Initial state machine is IDLE."""
        state = modbus.get_state()
        assert state["current"] == "IDLE"

    def test_build_read_request(self, modbus):
        """Build a valid Modbus read holding registers request."""
        pkt = modbus.build(
            transaction_id=1,
            unit_id=1,
            function_code=0x03,
            data=struct.pack(">HH", 0, 10),  # start=0, quantity=10
        )
        assert len(pkt) >= 12  # 7 header + 1 fc + 4 data
        assert isinstance(pkt, bytes)

    def test_parse_valid_packet(self, modbus):
        """Parse a well-formed Modbus TCP packet."""
        # Build a read response: transaction=1, protocol=0, length=5, unit=1, fc=3, bytecount=2, value=100
        pkt = struct.pack(">HHHB", 1, 0, 5, 1) + struct.pack(">BBH", 0x03, 2, 100)
        result = modbus.parse(pkt)
        assert result is not None
        assert result["valid"] is True
        assert result["function_code"] == 0x03
        assert result["function_name"] == "Read Holding Registers"
        assert result["mbap"]["transaction_id"] == 1
        assert result["mbap"]["unit_id"] == 1
        assert result["is_exception"] is False

    def test_parse_too_short(self, modbus):
        """Parsing data shorter than header returns None."""
        result = modbus.parse(b'\x00\x01')
        assert result is None

    def test_parse_exception_response(self, modbus):
        """Parse an exception response (function code with high bit set)."""
        # Exception response: fc=0x83 (0x03 | 0x80), exception code=0x02 (Illegal Data Address)
        pkt = struct.pack(">HHHB", 1, 0, 3, 1) + struct.pack(">BB", 0x83, 0x02)
        result = modbus.parse(pkt)
        assert result is not None
        assert result["is_exception"] is True
        assert result["exception_code"] == 0x02
        assert result["exception_name"] == "Illegal Data Address"

    def test_validate_valid_packet(self, modbus):
        """Validate a correct Modbus TCP packet."""
        pkt = struct.pack(">HHHB", 1, 0, 5, 1) + struct.pack(">BBH", 0x03, 2, 100)
        assert modbus.validate(pkt) is True

    def test_validate_too_short(self, modbus):
        """Validation fails for data shorter than header."""
        assert modbus.validate(b'\x00\x01') is False

    def test_validate_wrong_protocol_id(self, modbus):
        """Validation fails if protocol ID is not 0."""
        pkt = struct.pack(">HHHB", 1, 1, 5, 1) + struct.pack(">BBH", 0x03, 2, 100)
        assert modbus.validate(pkt) is False

    def test_function_codes_list(self, modbus):
        """get_functions returns a non-empty list of function names."""
        functions = modbus.get_functions()
        assert len(functions) > 0
        assert "Read Holding Registers" in functions

    def test_identify_vulnerabilities(self, modbus):
        """identify_vulnerabilities returns a list of vulnerability patterns."""
        vulns = modbus.identify_vulnerabilities()
        assert len(vulns) > 0
        for v in vulns:
            assert "protocol" in v
            assert "type" in v
            assert v["protocol"] == "modbus_tcp"

    def test_state_transitions(self, modbus):
        """State machine transitions correctly on parse."""
        pkt = struct.pack(">HHHB", 1, 0, 5, 1) + struct.pack(">BBH", 0x03, 2, 100)
        modbus.parse(pkt)
        state = modbus.get_state()
        assert state["current"] == "RESPONSE_RECEIVED"

    def test_build_read_request_static(self):
        """Static build_read_request helper builds correct packet."""
        from protocols.modbus_tcp import ModbusTCP
        pkt = ModbusTCP.build_read_request(
            transaction_id=1, unit_id=1, start_address=0, quantity=10
        )
        assert isinstance(pkt, bytes)
        assert len(pkt) >= 12

    def test_build_write_request_static(self):
        """Static build_write_request helper builds correct packet."""
        from protocols.modbus_tcp import ModbusTCP
        pkt = ModbusTCP.build_write_request(
            transaction_id=1, unit_id=1, start_address=0, values=[100, 200, 300]
        )
        assert isinstance(pkt, bytes)
        assert len(pkt) >= 19  # 7 header + 1 fc + 5 data + 6 values

    def test_build_raw_hex(self):
        """Build raw packet from hex string."""
        from protocols.modbus_tcp import ModbusTCP
        pkt = ModbusTCP.build_raw_hex("0001 0000 0006 01 03 0000 000a")
        assert isinstance(pkt, bytes)
        assert len(pkt) == 12

    def test_parsed_packets_accumulate(self, modbus):
        """Parsed packets are stored in the instance."""
        pkt = struct.pack(">HHHB", 1, 0, 5, 1) + struct.pack(">BBH", 0x03, 2, 100)
        modbus.parse(pkt)
        modbus.parse(pkt)
        assert len(modbus.parsed_packets) == 2


# ---------------------------------------------------------------------------
# DNP3 and IEC61850 Smoke Tests (skip if modules are empty/placeholder)
# ---------------------------------------------------------------------------
class TestDNP3Protocol:
    """Basic tests for DNP3 protocol."""

    def test_import_or_skip(self):
        """Import DNP3Protocol if available, otherwise skip."""
        try:
            from protocols.dnp3 import DNP3Protocol
            dnp3 = DNP3Protocol()
            assert dnp3.PROTOCOL_NAME is not None
        except (ImportError, AttributeError):
            pytest.skip("DNP3 protocol module not yet implemented")


class TestIEC61850Protocol:
    """Basic tests for IEC 61850 protocol."""

    def test_import_or_skip(self):
        """Import IEC61850Protocol if available, otherwise skip."""
        try:
            from protocols.iec61850 import IEC61850Protocol
            iec = IEC61850Protocol()
            assert iec.PROTOCOL_NAME is not None
        except (ImportError, AttributeError):
            pytest.skip("IEC 61850 protocol module not yet implemented")
