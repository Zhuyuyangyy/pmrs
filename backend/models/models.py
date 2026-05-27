"""
数据库模型 - Industrial Control Protocol Vulnerability Database
SQLAlchemy models for SCADA/ICS protocol vulnerability scanning and crash tracking
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, Enum, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from core.database import Base


class ProtocolType(str, enum.Enum):
    MODBUS_TCP = "modbus_tcp"
    IEC61850 = "iec61850"
    DNP3 = "dnp3"


class Severity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VulnerabilityType(str, enum.Enum):
    BUFFER_OVERFLOW = "buffer_overflow"
    INJECTION = "injection"
    AUTH_BYPASS = "auth_bypass"
    DOS = "dos"
    MEMORY_CORRUPTION = "memory_corruption"
    RACE_CONDITION = "race_condition"
    INPUT_VALIDATION = "input_validation"
    STATE_MACHINE = "state_machine"
    UNKNOWN = "unknown"


class Project(Base):
    """扫描项目"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    target_ip = Column(String(45), nullable=False)
    target_port = Column(Integer, nullable=False)
    protocol = Column(Enum(ProtocolType), nullable=False)
    config = Column(JSON, default={})
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scans = relationship("Scan", back_populates="project", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="project", cascade="all, delete-orphan")


class Scan(Base):
    """扫描任务"""
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    scan_type = Column(String(50), default="full")  # full, incremental, targeted
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    progress = Column(Float, default=0.0)  # 0.0 - 100.0
    total_testcases = Column(Integer, default=0)
    executed_testcases = Column(Integer, default=0)
    crashes_found = Column(Integer, default=0)
    llm_model = Column(String(100))
    fuzz_duration = Column(Integer, default=0)  # seconds
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="scans")
    testcases = relationship("TestCase", back_populates="scan", cascade="all, delete-orphan")
    crashes = relationship("Crash", back_populates="scan", cascade="all, delete-orphan")


class Vulnerability(Base):
    """漏洞记录"""
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    
    vulnerability_type = Column(Enum(VulnerabilityType), nullable=False)
    severity = Column(Enum(Severity), nullable=False, index=True)
    protocol = Column(Enum(ProtocolType), nullable=False)
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    location = Column(String(500))  # 代码位置/函数名
    severity_score = Column(Float)  # CVSS score
    
    # CVSS 评分
    cvss_base_score = Column(Float)
    cvss_impact_score = Column(Float)
    cvss_exploitability_score = Column(Float)
    cvss_vector = Column(String(100))
    
    # PoC信息
    poc_available = Column(Boolean, default=False)
    poc_exploit = Column(Text)
    poc_description = Column(Text)
    
    # 状态
    is_confirmed = Column(Boolean, default=False)
    is_false_positive = Column(Boolean, default=False)
    remediation = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="vulnerabilities")
    crash = relationship("Crash", back_populates="vulnerability", uselist=False)

    __table_args__ = (
        Index("idx_vuln_severity_protocol", "severity", "protocol"),
        Index("idx_vuln_project_created", "project_id", "created_at"),
    )


class TestCase(Base):
    """LLM生成的测试用例"""
    __tablename__ = "testcases"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    
    protocol = Column(Enum(ProtocolType), nullable=False)
    raw_data = Column(Text, nullable=False)  # 原始十六进制数据
    semantic_valid = Column(Boolean, default=True)
    
    # 语义标签
    function_code = Column(String(10))
    state_transition = Column(String(100))
    edge_case = Column(Boolean, default=False)
    
    # 执行结果
    execution_status = Column(String(50))  # pending, success, crash, timeout
    execution_time = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="testcases")


class Crash(Base):
    """崩溃记录"""
    __tablename__ = "crashes"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False)
    vulnerability_id = Column(Integer, ForeignKey("vulnerabilities.id"), unique=True)
    
    crash_type = Column(String(100), nullable=False)  # sigsegv, sigabrt, sigill, etc.
    crash_signal = Column(String(50))
    crash_address = Column(String(100))
    
    # 触发数据
    input_data = Column(Text)  # hex
    input_size = Column(Integer)
    
    # 回溯信息
    backtrace = Column(Text)
    registers = Column(Text)
    
    # AFL信息
    afl_id = Column(String(100))  # AFL crash ID
    afl_output = Column(Text)
    
    severity_estimate = Column(String(20))  # high, medium, low
    
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="crashes")
    vulnerability = relationship("Vulnerability", back_populates="crash", uselist=False)


class ProtocolStateMachine(Base):
    """协议状态机"""
    __tablename__ = "protocol_state_machines"

    id = Column(Integer, primary_key=True, index=True)
    protocol = Column(Enum(ProtocolType), nullable=False, unique=True)
    
    states = Column(JSON, default=[])  # 状态列表
    transitions = Column(JSON, default=[])  # 转换规则
    initial_state = Column(String(100))
    final_states = Column(JSON, default=[])
    
    # LLM分析结果
    semantic_summary = Column(Text)  # LLM生成的语义总结
    critical_paths = Column(JSON, default=[])  # 关键路径
    
    version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
