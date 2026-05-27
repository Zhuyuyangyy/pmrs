"""
Modbus TCP 协议实现
"""
from typing import Dict, Any, Optional, List
import struct
import logging

from protocols.base import ProtocolBase, ProtocolRegistry, ProtocolField

logger = logging.getLogger(__name__)


class ModbusTCP(ProtocolBase):
    """Modbus TCP协议解析器"""

    PROTOCOL_NAME = "modbus_tcp"
    DEFAULT_PORT = 502

    # Modbus TCP 头部长度
    HEADER_LENGTH = 7
    # MBAP = 事务标识符(2) + 协议标识符(2) + 长度(2) + 单元标识符(1)

    # 功能码定义
    FUNCTION_CODES = {
        0x01: "Read Coils",
        0x02: "Read Discrete Inputs",
        0x03: "Read Holding Registers",
        0x04: "Read Input Registers",
        0x05: "Write Single Coil",
        0x06: "Write Single Register",
        0x0F: "Write Multiple Coils",
        0x10: "Write Multiple Registers",
        0x17: "Read/Write Multiple Registers",
        0x2B: "Read Device Identification",
    }

    # 异常码
    EXCEPTION_CODES = {
        0x01: "Illegal Function",
        0x02: "Illegal Data Address",
        0x03: "Illegal Data Value",
        0x04: "Server Device Failure",
        0x05: "Acknowledge",
        0x06: "Server Device Busy",
        0x08: "Memory Parity Error",
        0x0A: "Gateway Path Unavailable",
        0x0B: "Gateway Target Device Failed to Respond",
    }

    def __init__(self):
        super().__init__()
        self.state_machine = {
            "current": "IDLE",
            "context": {
                "transaction_id": 0,
                "last_function": None,
            },
            "states": ["IDLE", "WAITING_RESPONSE", "RESPONSE_RECEIVED", "ERROR"],
        }

    def parse(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析Modbus TCP数据包"""
        if len(data) < self.HEADER_LENGTH:
            logger.warning(f"Modbus TCP: Data too short ({len(data)} bytes)")
            return None

        try:
            # 解析MBAP头
            transaction_id = struct.unpack(">H", data[0:2])[0]
            protocol_id = struct.unpack(">H", data[2:4])[0]
            length = struct.unpack(">H", data[4:6])[0]
            unit_id = data[6]

            # 基本验证
            if protocol_id != 0:
                logger.warning(f"Modbus TCP: Invalid protocol ID {protocol_id}")
            
            if len(data) < self.HEADER_LENGTH + length - 1:
                logger.warning(f"Modbus TCP: Incomplete PDU")
                return None

            # 解析PDU
            pdu_start = self.HEADER_LENGTH
            if len(data) > pdu_start:
                pdu = data[pdu_start:]
                function_code = pdu[0]

                result = {
                    "valid": True,
                    "mbap": {
                        "transaction_id": transaction_id,
                        "protocol_id": protocol_id,
                        "length": length,
                        "unit_id": unit_id,
                    },
                    "function_code": function_code,
                    "function_name": self.FUNCTION_CODES.get(function_code, "Unknown"),
                    "pdu_data": pdu[1:].hex(),
                }

                # 处理异常响应
                if function_code & 0x80:
                    exception_code = pdu[1] if len(pdu) > 1 else 0
                    result["is_exception"] = True
                    result["exception_code"] = exception_code
                    result["exception_name"] = self.EXCEPTION_CODES.get(exception_code, "Unknown")
                    self.set_state("ERROR", {"exception": exception_code})
                else:
                    result["is_exception"] = False
                    self.set_state("RESPONSE_RECEIVED", {"function": function_code})

                self.parsed_packets.append(result)
                return result

        except struct.error as e:
            logger.error(f"Modbus TCP: Parse error - {e}")
        except Exception as e:
            logger.error(f"Modbus TCP: Unexpected error - {e}")

        return None

    def build(
        self,
        transaction_id: int,
        unit_id: int,
        function_code: int,
        data: bytes = b"",
    ) -> bytes:
        """构建Modbus TCP数据包"""
        # MBAP头
        mbap = struct.pack(">HHH", transaction_id, 0, len(data) + 1)
        mbap += struct.pack("B", unit_id)

        # PDU
        pdu = struct.pack("B", function_code) + data

        return mbap + pdu

    def validate(self, data: bytes) -> bool:
        """验证Modbus TCP数据包格式"""
        if len(data) < self.HEADER_LENGTH:
            return False

        try:
            protocol_id = struct.unpack(">H", data[2:4])[0]
            if protocol_id != 0:
                return False

            length = struct.unpack(">H", data[4:6])[0]
            if len(data) < self.HEADER_LENGTH + length - 1:
                return False

            return True
        except:
            return False

    def get_functions(self) -> List[str]:
        """获取支持的功能码列表"""
        return list(self.FUNCTION_CODES.values())

    def identify_vulnerabilities(self) -> List[Dict[str, Any]]:
        """识别潜在漏洞点"""
        vulnerabilities = []

        # 基于协议特征的漏洞检测
        vuln_patterns = [
            {
                "type": "buffer_overflow",
                "indicator": "Read with excessive length",
                "description": "读取请求中长度字段过大可能导致缓冲区溢出",
            },
            {
                "type": "input_validation",
                "indicator": "Invalid address range",
                "description": "寄存器地址超出有效范围",
            },
            {
                "type": "state_machine",
                "indicator": "Unexpected state transition",
                "description": "协议状态机转换异常",
            },
            {
                "type": "dos",
                "indicator": "Flooding attack",
                "description": "大量请求可能导致拒绝服务",
            },
        ]

        for pattern in vuln_patterns:
            vulnerabilities.append({
                "protocol": self.PROTOCOL_NAME,
                **pattern,
            })

        return vulnerabilities

    @staticmethod
    def build_read_request(
        transaction_id: int,
        unit_id: int,
        start_address: int,
        quantity: int,
    ) -> bytes:
        """构建读取保持寄存器请求"""
        data = struct.pack(">HH", start_address, quantity)
        return ModbusTCP().build(transaction_id, unit_id, 0x03, data)

    @staticmethod
    def build_write_request(
        transaction_id: int,
        unit_id: int,
        start_address: int,
        values: List[int],
    ) -> bytes:
        """构建写多个寄存器请求"""
        byte_count = len(values) * 2
        data = struct.pack(">HHB", start_address, len(values), byte_count)
        for v in values:
            data += struct.pack(">H", v)
        return ModbusTCP().build(transaction_id, unit_id, 0x10, data)

    @staticmethod
    def build_raw_hex(hex_string: str) -> bytes:
        """从十六进制字符串构建原始数据包"""
        return bytes.fromhex(hex_string.replace(" ", ""))


# 注册协议
ProtocolRegistry.register("modbus_tcp", ModbusTCP)
