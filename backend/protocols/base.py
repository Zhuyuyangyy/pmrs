"""
工控协议基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import struct
import logging

logger = logging.getLogger(__name__)


class ProtocolBase(ABC):
    """工控协议基类"""

    PROTOCOL_NAME: str = "unknown"
    DEFAULT_PORT: int = 0

    def __init__(self):
        self.state_machine: Dict[str, Any] = {}
        self.parsed_packets: List[Dict] = []

    @abstractmethod
    def parse(self, data: bytes) -> Optional[Dict[str, Any]]:
        """解析协议数据包"""
        pass

    @abstractmethod
    def build(self, fields: Dict[str, Any]) -> bytes:
        """构建协议数据包"""
        pass

    @abstractmethod
    def validate(self, data: bytes) -> bool:
        """验证数据包格式"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """获取当前协议状态"""
        return self.state_machine

    def set_state(self, state: str, context: Optional[Dict] = None):
        """设置协议状态"""
        self.state_machine["current"] = state
        if context:
            self.state_machine["context"] = context

    def get_functions(self) -> List[str]:
        """获取协议支持的功能码"""
        return []

    def identify_vulnerabilities(self) -> List[Dict[str, Any]]:
        """基于协议特征识别潜在漏洞"""
        return []


class ProtocolField:
    """协议字段定义"""
    def __init__(self, name: str, offset: int, length: int, dtype: str = "uint"):
        self.name = name
        self.offset = offset
        self.length = length
        self.dtype = dtype

    def parse_value(self, data: bytes) -> Any:
        """解析字段值"""
        try:
            raw = data[self.offset:self.offset + self.length]
            if self.dtype == "uint":
                return int.from_bytes(raw, 'big')
            elif self.dtype == "int":
                return int.from_bytes(raw, 'big', signed=True)
            elif self.dtype == "bytes":
                return raw
            elif self.dtype == "str":
                return raw.decode('ascii', errors='ignore')
            return raw
        except Exception as e:
            logger.error(f"Failed to parse field {self.name}: {e}")
            return None

    def build_value(self, value: Any) -> bytes:
        """构建字段值"""
        try:
            if self.dtype == "uint":
                return int(value).to_bytes(self.length, 'big')
            elif self.dtype == "int":
                return int(value).to_bytes(self.length, 'big', signed=True)
            elif self.dtype == "bytes":
                return value[:self.length].ljust(self.length, b'\x00')
            elif self.dtype == "str":
                return str(value).encode('ascii')[:self.length].ljust(self.length, b'\x00')
            return bytes(self.length)
        except Exception as e:
            logger.error(f"Failed to build field {self.name}: {e}")
            return bytes(self.length)


class ProtocolRegistry:
    """协议注册表"""
    _protocols: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, protocol_class: type):
        cls._protocols[name] = protocol_class

    @classmethod
    def get(cls, name: str) -> Optional[ProtocolBase]:
        return cls._protocols.get(name)

    @classmethod
    def list_protocols(cls) -> List[str]:
        return list(cls._protocols.keys())
