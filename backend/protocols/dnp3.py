"""
DNP3 协议实现
DNP3 (Distributed Network Protocol 3) parser for SCADA/ICS systems
"""
from typing import Dict, Any, Optional, List
import struct
import logging

from protocols.base import ProtocolBase, ProtocolRegistry, ProtocolField

logger = logging.getLogger(__name__)


class DNP3Protocol(ProtocolBase):
    """DNP3协议解析器"""

    PROTOCOL_NAME = "dnp3"
    DEFAULT_PORT = 20000

    # DNP3 data link layer constants
    START_BYTES = 0x0564
    HEADER_LENGTH = 10  # Data link header

    # DNP3 function codes (application layer)
    FUNCTION_CODES = {
        0x00: "Confirm",
        0x01: "Read",
        0x02: "Write",
        0x03: "Select",
        0x04: "Operate",
        0x05: "Direct Operate",
        0x06: "Direct Operate No Ack",
        0x07: "Freeze",
        0x08: "Freeze No Ack",
        0x09: "Freeze Clear",
        0x0A: "Freeze Clear No Ack",
        0x0B: "Freeze At Time",
        0x0C: "Freeze At Time No Ack",
        0x0D: "Cold Restart",
        0x0E: "Warm Restart",
        0x0F: "Initialize Data",
        0x10: "Initialize Application",
        0x11: "Start Application",
        0x12: "Stop Application",
        0x13: "Save Configuration",
        0x14: "Enable Unsolicited",
        0x15: "Disable Unsolicited",
        0x16: "Assign Class",
        0x17: "Delay Measure",
        0x18: "Record Current Time",
        0x19: "Open File",
        0x1A: "Close File",
        0x1B: "Delete File",
        0x1C: "Get File Info",
        0x1D: "Authenticate File",
        0x1E: "Abort File",
        0x1F: "Reconfigure Master Station",
        0x81: "Response",
        0x82: "Unsolicited Response",
    }

    # Object types
    OBJECT_TYPES = {
        0x00: "Device Attributes",
        0x01: "Binary Input",
        0x02: "Binary Input Event",
        0x03: "Double-bit Binary Input",
        0x04: "Double-bit Binary Input Event",
        0x05: "Binary Output",
        0x06: "Binary Output Event",
        0x07: "Binary Output Command",
        0x08: "Counter",
        0x09: "Frozen Counter",
        0x0A: "Counter Event",
        0x0B: "Frozen Counter Event",
        0x0C: "Analog Input",
        0x0D: "Frozen Analog Input",
        0x0E: "Analog Input Event",
        0x0F: "Analog Output Status",
        0x10: "Analog Output",
        0x14: "Analog Output Command",
        0x1E: "Authentication",
        0x28: "Security Statistics",
        0x3C: "Class Data",
        0x3D: "File Control",
        0x46: "Internal Indications",
        0x50: "Time and Date",
        0x51: "Time Delay",
    }

    def __init__(self):
        super().__init__()
        self.state_machine = {
            "current": "IDLE",
            "context": {
                "last_sequence": 0,
                "last_function": None,
                "session_active": False,
            },
            "states": [
                "IDLE",
                "LINK_RESET",
                "USER_DATA",
                "CONFIRMATION",
                "ERROR",
            ],
        }

    def parse(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析DNP3数据包"""
        if len(data) < self.HEADER_LENGTH:
            logger.warning(f"DNP3: Data too short ({len(data)} bytes)")
            return None

        try:
            offset = 0

            # Parse data link header
            start = struct.unpack(">H", data[0:2])[0]
            if start != self.START_BYTES:
                logger.warning(f"DNP3: Invalid start bytes 0x{start:04X}")
                return None

            length = data[2]
            control = data[3]
            destination = struct.unpack(">H", data[4:6])[0]
            source = struct.unpack(">H", data[6:8])[0]
            crc = struct.unpack(">H", data[8:10])[0]

            # Parse control byte
            direction = (control >> 6) & 0x01
            primary = (control >> 5) & 0x01
            frame_type = (control >> 4) & 0x01
            function_code = control & 0x0F

            # Data link function codes
            dl_function_names = {
                0x00: "Reset Link",
                0x01: "Reset of User Process",
                0x02: "Test Function for Link",
                0x03: "User Data",
                0x04: "Unconfirmed User Data",
                0x09: "Request Link Status",
                0x0B: "Link Status",
                0x0F: "Not Supported",
            }

            result = {
                "valid": True,
                "data_link": {
                    "start": hex(start),
                    "length": length,
                    "control": control,
                    "direction": direction,
                    "primary": primary,
                    "frame_type": frame_type,
                    "function_code": function_code,
                    "function_name": dl_function_names.get(function_code, "Unknown"),
                    "destination": destination,
                    "source": source,
                    "crc": hex(crc),
                },
                "transport": None,
                "application": None,
            }

            offset = self.HEADER_LENGTH

            # Parse transport header if present
            if offset < len(data):
                transport_control = data[offset]
                sequence = transport_control & 0x3F
                fir = (transport_control >> 7) & 0x01
                fin = (transport_control >> 6) & 0x01
                result["transport"] = {
                    "sequence": sequence,
                    "fir": fir,  # First fragment
                    "fin": fin,  # Final fragment
                }
                offset += 1

            # Parse application layer if present
            if offset < len(data):
                app_control = data[offset]
                app_sequence = app_control & 0x3F
                unsolicited = (app_control >> 6) & 0x01
                iin = (app_control >> 7) & 0x01

                result["application"] = {
                    "control": app_control,
                    "sequence": app_sequence,
                    "unsolicited": unsolicited,
                }

                if offset + 1 < len(data):
                    func_code = data[offset + 1]
                    result["application"]["function_code"] = func_code
                    result["application"]["function_name"] = self.FUNCTION_CODES.get(
                        func_code, f"Unknown(0x{func_code:02X})"
                    )

                    # Update state based on function
                    if func_code == 0x00:  # Confirm
                        self.set_state("CONFIRMATION")
                    elif func_code in (0x81, 0x82):  # Response
                        self.set_state("USER_DATA")
                    else:
                        self.set_state("USER_DATA")

                    self.state_machine["context"]["last_function"] = func_code

            self.parsed_packets.append(result)
            return result

        except struct.error as e:
            logger.error(f"DNP3: Parse error - {e}")
        except Exception as e:
            logger.error(f"DNP3: Unexpected error - {e}")

        return None

    def build(self, fields: Dict[str, Any]) -> bytes:
        """构建DNP3数据包"""
        destination = fields.get("destination", 0)
        source = fields.get("source", 0)
        function_code = fields.get("function_code", 0x03)  # User Data
        app_function = fields.get("app_function", 0x01)  # Read
        app_data = fields.get("app_data", b"")

        # Build control byte
        direction = fields.get("direction", 1)  # Master -> Outstation
        primary = fields.get("primary", 1)
        control = ((direction & 1) << 6) | ((primary & 1) << 5) | (0 << 4) | (function_code & 0x0F)

        # Application layer
        app_layer = struct.pack("BB", 0xC0, app_function) + app_data

        # Transport header
        transport = struct.pack("B", 0xC0)  # FIR=1, FIN=1, SEQ=0

        # Data length (transport + application)
        data_length = len(transport) + len(app_layer)

        # Data link header
        dl_header = struct.pack(">HBBHH", self.START_BYTES, data_length, control, destination, source)

        # Calculate CRC for data link header
        dl_crc = self._calculate_crc(dl_header)

        # Calculate CRC for data
        data_with_crc = transport + app_layer
        data_crc = self._calculate_crc(data_with_crc)

        return dl_header + dl_crc + data_with_crc + data_crc

    def validate(self, data: bytes) -> bool:
        """验证DNP3数据包格式"""
        if len(data) < self.HEADER_LENGTH:
            return False

        try:
            start = struct.unpack(">H", data[0:2])[0]
            if start != self.START_BYTES:
                return False

            length = data[2]
            if length > 292:  # DNP3 max frame size
                return False

            return True
        except Exception:
            return False

    def get_functions(self) -> List[str]:
        """获取支持的功能码列表"""
        return list(self.FUNCTION_CODES.values())

    def identify_vulnerabilities(self) -> List[Dict[str, Any]]:
        """识别潜在漏洞点"""
        vulnerabilities = [
            {
                "type": "buffer_overflow",
                "indicator": "Oversized data link length field",
                "description": "数据链路层长度字段过大可能导致缓冲区溢出",
            },
            {
                "type": "injection",
                "indicator": "Crafted application layer objects",
                "description": "构造的应用层对象可能绕过访问控制",
            },
            {
                "type": "dos",
                "indicator": "Fragment flood attack",
                "description": "大量未完成的分片可能导致拒绝服务",
            },
            {
                "type": "state_machine",
                "indicator": "Invalid transport sequence",
                "description": "传输层序列号异常可能导致状态机混乱",
            },
            {
                "type": "auth_bypass",
                "indicator": "Authentication object manipulation",
                "description": "认证对象篡改可能绕过安全机制",
            },
        ]

        for v in vulnerabilities:
            v["protocol"] = self.PROTOCOL_NAME

        return vulnerabilities

    @staticmethod
    def _calculate_crc(data: bytes) -> bytes:
        """计算DNP3 CRC-16 (CRC-DNP)"""
        crc = 0x0000
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return struct.pack("<H", crc)


# Register protocol
ProtocolRegistry.register("dnp3", DNP3Protocol)
