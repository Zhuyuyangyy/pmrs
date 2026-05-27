"""
IEC 61850 协议实现
IEC 61850 是电力系统自动化通信协议
"""
from typing import Dict, Any, Optional, List
import struct
import logging

from protocols.base import ProtocolBase, ProtocolRegistry

logger = logging.getLogger(__name__)


class IEC61850(ProtocolBase):
    """IEC 61850 协议解析器"""

    PROTOCOL_NAME = "iec61850"
    DEFAULT_PORT = 102

    # IEC 61850 服务类型
    SERVICES = {
        0x00: "GetDataValues",
        0x01: "SetDataValues",
        0x02: "GetDataDirectory",
        0x03: "GetDataDefinition",
        0x04: "GetDataSetDirectory",
        0x05: "DataSetDirectory",
        0x06: "GetDataSetValues",
        0x07: "SetDataSetValues",
        0x08: "CreateDataSet",
        0x09: "DeleteDataSet",
        0x0A: "GetFile",
        0x0B: "SetFile",
        0x0C: "DeleteFile",
        0x0D: "GetFileDirectory",
        0x0E: "GetServerDirectory",
    }

    # MMS协议功能码 (ISO 9506)
    MMS_FUNCTIONS = {
        0x01: "confirmed-RequestPDU",
        0x02: "confirmed-ResponsePDU",
        0x03: "confirmed-ErrorPDU",
        0x04: "unconfirmed-PDU",
        0x05: "reject-PDU",
        0x06: "cancel-PDU",
        0x07: "cancel-ResponsePDU",
        0x08: "initiate-PDU",
        0x09: "initiate-ResponsePDU",
        0x0A: "terminate-PDU",
    }

    def __init__(self):
        super().__init__()
        self.state_machine = {
            "current": "DISCONNECTED",
            "context": {
                "session_id": None,
                "assoc_id": None,
            },
            "states": [
                "DISCONNECTED",
                "CONNECTING",
                "ASSOCIATED",
                "SELECTED",
                "OPERATING",
                "ERROR",
            ],
        }

    def parse(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析IEC 61850/MMS数据包"""
        if len(data) < 8:
            return None

        try:
            # 简单解析 - 实际协议更复杂
            result = {
                "valid": False,
                "protocol": "IEC61850",
                "raw_length": len(data),
                "raw_hex": data.hex(),
            }

            # 检测是否是ISO/COTP/S7或直接MMS
            if data[0] == 0x03 and data[1] == 0x00:  # RFC 1006 header
                result["transport_protocol"] = "RFC 1006 (TCP/IP)"
                # 跳过TPKT (4 bytes) + COTP (varies)
                if len(data) > 8:
                    payload = data[8:]
                    result["payload"] = payload.hex()
                    result["valid"] = True
            elif data[0] >= 0x80:  # MMS priority
                result["transport_protocol"] = "MMS"
                result["valid"] = True

            self.parsed_packets.append(result)
            return result

        except Exception as e:
            logger.error(f"IEC61850: Parse error - {e}")
            return None

    def build(self, service_type: str, data: bytes) -> bytes:
        """构建IEC 61850数据包"""
        # 简化实现
        if service_type == "GetDataValues":
            # MMS GetDataValues request
            return b"\x01" + struct.pack(">H", len(data) + 1) + data
        return data

    def validate(self, data: bytes) -> bool:
        """验证数据包"""
        if len(data) < 4:
            return False
        # 基本验证
        return True

    def get_functions(self) -> List[str]:
        return list(self.SERVICES.values())

    def identify_vulnerabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "protocol": self.PROTOCOL_NAME,
                "type": "state_machine",
                "indicator": "State confusion attack",
                "description": "协议状态转换验证不足",
            },
            {
                "protocol": self.PROTOCOL_NAME,
                "type": "injection",
                "indicator": "MMS service manipulation",
                "description": "MMS服务参数注入",
            },
        ]


class DNP3(ProtocolBase):
    """DNP3 协议解析器 - 电力行业分布式网络协议"""

    PROTOCOL_NAME = "dnp3"
    DEFAULT_PORT = 20000

    # DNP3 功能码
    FUNCTION_CODES = {
        0x00: "Confirm",
        0x01: "Read",
        0x02: "Write",
        0x03: "Select",
        0x04: "Operate",
        0x05: "Direct Operate",
        0x06: "Direct Operate No ACK",
        0x07: "Immedinate Freeze",
        0x08: "Immedinate Freeze No ACK",
        0x09: "Freeze Clear",
        0x0A: "Freeze Clear No ACK",
        0x0B: "Freeze At Time",
        0x0C: "Freeze At Time No ACK",
        0x0D: "Cold Restart",
        0x0E: "Warm Restart",
        0x0F: "Enable Unsolicited",
        0x10: "Disable Unsolicited",
        0x14: "Time Sync",
    }

    # 对象组
    OBJECT_GROUPS = {
        1: "Binary Input",
        2: "Binary Output",
        3: "Binary Counter",
        4: "Analog Input",
        5: "Analog Output",
        10: "Time and Date",
        12: "File Control",
        20: "Internal Indication",
    }

    def __init__(self):
        super().__init__()
        self.state_machine = {
            "current": "IDLE",
            "context": {},
            "states": ["IDLE", "WAITING", "RESPONSE", "ERROR"],
        }

    def parse(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析DNP3数据包"""
        if len(data) < 10:
            return None

        try:
            # DNP3 数据链路层头
            start_bytes = data[0:2]
            if start_bytes != b'\x05\x64':  # DNP3固定起始符
                logger.warning(f"DNP3: Invalid start bytes {start_bytes.hex()}")
                return None

            # 长度
            length = data[2]

            # 控制字节
            control = data[3]
            dir_bit = (control >> 7) & 1  # Direction
            prim_bit = (control >> 6) & 1  # Primary
            fcb_bit = (control >> 5) & 1  # Frame Count Bit
            fcv_bit = (control >> 4) & 1  # Frame Count Valid

            # 目标地址和源地址
            dest_addr = struct.unpack("<H", data[4:6])[0]
            src_addr = struct.unpack("<H", data[6:8])[0]

            # CRC (简化)
            header_crc = data[8:10]

            result = {
                "valid": True,
                "length": length,
                "direction": "primary" if prim_bit else "secondary",
                "dest_address": dest_addr,
                "src_address": src_addr,
                "raw_hex": data.hex(),
            }

            self.parsed_packets.append(result)
            return result

        except Exception as e:
            logger.error(f"DNP3: Parse error - {e}")
            return None

    def build(self, dest: int, src: int, function: int, data: bytes = b"") -> bytes:
        """构建DNP3数据包"""
        length = 10 + len(data)  # Header + data + CRC
        
        pkt = b'\x05\x64'  # Start bytes
        pkt += struct.pack("B", length)
        pkt += struct.pack("B", 0x05)  # Control: primary + dir
        pkt += struct.pack("<H", dest)
        pkt += struct.pack("<H", src)
        # CRC placeholder
        pkt += b'\x00\x00'
        pkt += data
        
        # Calculate CRC (simplified)
        # In real implementation, would use DNP3 CRC table
        
        return pkt

    def validate(self, data: bytes) -> bool:
        """验证DNP3数据包"""
        if len(data) < 10:
            return False
        if data[0:2] != b'\x05\x64':
            return False
        return True

    def get_functions(self) -> List[str]:
        return list(self.FUNCTION_CODES.values())

    def identify_vulnerabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "protocol": self.PROTOCOL_NAME,
                "type": "buffer_overflow",
                "indicator": "Excessive data length",
                "description": "数据长度字段与实际不符",
            },
            {
                "protocol": self.PROTOCOL_NAME,
                "type": "auth_bypass",
                "indicator": "Sequence number attack",
                "description": "帧计数验证绕过",
            },
        ]


# 注册协议
ProtocolRegistry.register("iec61850", IEC61850)
ProtocolRegistry.register("dnp3", DNP3)
