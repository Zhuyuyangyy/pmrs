"""
IEC 61850 协议实现
IEC 61850 MMS (Manufacturing Message Specification) protocol parser
"""
from typing import Dict, Any, Optional, List
import struct
import logging

from protocols.base import ProtocolBase, ProtocolRegistry, ProtocolField

logger = logging.getLogger(__name__)


class IEC61850Protocol(ProtocolBase):
    """IEC 61850 MMS协议解析器"""

    PROTOCOL_NAME = "iec61850"
    DEFAULT_PORT = 102

    # TPKT header length (RFC 1006)
    TPKT_HEADER_LENGTH = 4
    # COTP header length
    COTP_HEADER_LENGTH = 3

    # MMS PDU types
    MMS_PDU_TYPES = {
        0: "confirmed-Request",
        1: "confirmed-Response",
        2: "confirmed-Error",
        3: "unconfirmed-PDU",
        4: "reject-PDU",
        5: "cancel-Request",
        6: "cancel-Response",
        7: "cancel-Error",
        8: "initiate-Request",
        9: "initiate-Response",
        10: "initiate-Error",
        11: "conclude-Request",
        12: "conclude-Response",
        13: "conclude-Error",
    }

    # MMS services
    MMS_SERVICES = {
        0: "status",
        1: "getNameList",
        2: "identify",
        3: "rename",
        4: "read",
        5: "write",
        6: "getVariableAccessAttributes",
        7: "defineNamedVariable",
        8: "defineScatteredAccess",
        9: "getScatteredAccessAttributes",
        10: "deleteVariableAccess",
        11: "defineNamedVariableList",
        12: "getNamedVariableListAttributes",
        13: "deleteNamedVariableList",
        14: "defineNamedType",
        15: "getNamedTypeAttributes",
        16: "deleteNamedType",
        17: "input",
        18: "output",
        19: "takeControl",
        20: "relinquishControl",
        21: "defineSemaphore",
        22: "deleteSemaphore",
        23: "reportSemaphoreStatus",
        24: "reportPoolSemaphoreStatus",
        25: "reportSemaphoreEntryStatus",
        26: "initiateDownloadSequence",
        27: "downloadSegment",
        28: "terminateDownloadSequence",
        29: "initiateUploadSequence",
        30: "uploadSegment",
        31: "terminateUploadSequence",
        32: "requestDomainDownload",
        33: "requestDomainUpload",
        34: "loadDomainContent",
        35: "storeDomainContent",
        36: "deleteDomain",
        37: "getDomainAttributes",
        38: "createProgramInvocation",
        39: "deleteProgramInvocation",
        40: "start",
        41: "stop",
        42: "resume",
        43: "reset",
        44: "kill",
        100: "eventNotification",
        101: "eventNotification",
        102: "attachToEventCondition",
        103: "attachToSemaphore",
        104: "conclude",
    }

    def __init__(self):
        super().__init__()
        self.state_machine = {
            "current": "IDLE",
            "context": {
                "session_established": False,
                "last_service": None,
            },
            "states": [
                "IDLE",
                "CONNECTING",
                "SESSION_ESTABLISHED",
                "DATA_EXCHANGE",
                "ERROR",
                "DISCONNECTING",
            ],
        }

    def parse(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析IEC 61850 MMS数据包"""
        if len(data) < self.TPKT_HEADER_LENGTH + self.COTP_HEADER_LENGTH:
            logger.warning(f"IEC 61850: Data too short ({len(data)} bytes)")
            return None

        try:
            offset = 0

            # Parse TPKT header
            tpkt_version = data[0]
            tpkt_reserved = data[1]
            tpkt_length = struct.unpack(">H", data[2:4])[0]
            offset += self.TPKT_HEADER_LENGTH

            if tpkt_version != 3:
                logger.warning(f"IEC 61850: Invalid TPKT version {tpkt_version}")

            # Parse COTP header
            cotp_length = data[offset]
            cotp_pdu_type = data[offset + 1]
            cotp_dest_ref = data[offset + 2] if cotp_length > 1 else 0
            offset += cotp_length + 1

            result = {
                "valid": True,
                "tpkt": {
                    "version": tpkt_version,
                    "length": tpkt_length,
                },
                "cotp": {
                    "length": cotp_length,
                    "pdu_type": cotp_pdu_type,
                },
                "mms_pdu_type": None,
                "mms_service": None,
                "mms_data": None,
            }

            # Parse MMS PDU if enough data remains
            if offset < len(data):
                mms_data = data[offset:]
                if len(mms_data) >= 2:
                    # ASN.1 BER tag
                    mms_tag = mms_data[0]
                    mms_length = mms_data[1]

                    if mms_tag < len(self.MMS_PDU_TYPES):
                        result["mms_pdu_type"] = self.MMS_PDU_TYPES.get(mms_tag, f"unknown({mms_tag})")
                    else:
                        result["mms_pdu_type"] = f"unknown({mms_tag})"

                    result["mms_data"] = mms_data.hex()

                    # Update state
                    if cotp_pdu_type == 0xE0:  # Connection Request
                        self.set_state("CONNECTING")
                    elif cotp_pdu_type == 0xD0:  # Connection Confirm
                        self.set_state("SESSION_ESTABLISHED")
                        self.state_machine["context"]["session_established"] = True
                    else:
                        self.set_state("DATA_EXCHANGE")

            self.parsed_packets.append(result)
            return result

        except struct.error as e:
            logger.error(f"IEC 61850: Parse error - {e}")
        except Exception as e:
            logger.error(f"IEC 61850: Unexpected error - {e}")

        return None

    def build(self, fields: Dict[str, Any]) -> bytes:
        """构建IEC 61850 MMS数据包"""
        pdu_type = fields.get("pdu_type", 0)
        service_data = fields.get("service_data", b"")

        # Build MMS PDU
        mms_pdu = struct.pack("BB", pdu_type, len(service_data)) + service_data

        # Build COTP header
        cotp = struct.pack("BBB", 2, 0xF0, 0x80)  # Data PDU

        # Build TPKT header
        total_length = self.TPKT_HEADER_LENGTH + len(cotp) + len(mms_pdu)
        tpkt = struct.pack(">BBH", 3, 0, total_length)

        return tpkt + cotp + mms_pdu

    def validate(self, data: bytes) -> bool:
        """验证IEC 61850数据包格式"""
        if len(data) < self.TPKT_HEADER_LENGTH + self.COTP_HEADER_LENGTH:
            return False

        try:
            # Check TPKT version
            if data[0] != 3:
                return False

            # Check TPKT length
            tpkt_length = struct.unpack(">H", data[2:4])[0]
            if tpkt_length != len(data):
                return False

            return True
        except Exception:
            return False

    def get_functions(self) -> List[str]:
        """获取支持的MMS服务列表"""
        return list(self.MMS_SERVICES.values())

    def identify_vulnerabilities(self) -> List[Dict[str, Any]]:
        """识别潜在漏洞点"""
        vulnerabilities = [
            {
                "type": "buffer_overflow",
                "indicator": "Malformed TPKT/COTP headers",
                "description": "TPKT长度字段与实际数据不匹配可能导致缓冲区溢出",
            },
            {
                "type": "dos",
                "indicator": "Large MMS PDU",
                "description": "超大MMS PDU可能导致内存耗尽",
            },
            {
                "type": "injection",
                "indicator": "Crafted MMS service requests",
                "description": "构造的MMS服务请求可能绕过访问控制",
            },
            {
                "type": "state_machine",
                "indicator": "Invalid state transitions",
                "description": "协议状态机转换异常可能导致未授权访问",
            },
        ]

        for v in vulnerabilities:
            v["protocol"] = self.PROTOCOL_NAME

        return vulnerabilities


# Register protocol
ProtocolRegistry.register("iec61850", IEC61850Protocol)
