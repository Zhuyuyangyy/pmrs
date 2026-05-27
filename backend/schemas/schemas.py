"""
Pydantic Schemas - Industrial Control Protocol Vulnerability Mining System
Request/Response models for SCADA/ICS protocol fuzzing and vulnerability scanning
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class ProtocolType(str, Enum):
    MODBUS_TCP = "modbus_tcp"
    IEC61850 = "iec61850"
    DNP3 = "dnp3"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VulnerabilityType(str, Enum):
    BUFFER_OVERFLOW = "buffer_overflow"
    INJECTION = "injection"
    AUTH_BYPASS = "auth_bypass"
    DOS = "dos"
    MEMORY_CORRUPTION = "memory_corruption"
    RACE_CONDITION = "race_condition"
    INPUT_VALIDATION = "input_validation"
    STATE_MACHINE = "state_machine"
    UNKNOWN = "unknown"


# ============ Project Schemas ============
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_ip: str = Field(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    target_port: int = Field(..., ge=1, le=65535)
    protocol: ProtocolType
    config: Optional[dict] = {}


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    config: Optional[dict] = None
    status: Optional[ScanStatus] = None


class ProjectResponse(ProjectBase):
    id: int
    status: ScanStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Scan Schemas ============
class ScanBase(BaseModel):
    scan_type: str = Field(default="full", pattern="^(full|incremental|targeted)$")
    llm_model: Optional[str] = None
    fuzz_duration: Optional[int] = Field(default=3600, ge=60)


class ScanCreate(ScanBase):
    project_id: int


class ScanResponse(ScanBase):
    id: int
    project_id: int
    status: ScanStatus
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    progress: float
    total_testcases: int
    executed_testcases: int
    crashes_found: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Vulnerability Schemas ============
class VulnerabilityBase(BaseModel):
    vulnerability_type: VulnerabilityType
    protocol: ProtocolType
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None


class VulnerabilityResponse(VulnerabilityBase):
    id: int
    project_id: int
    scan_id: Optional[int]
    severity: Severity
    location: Optional[str]
    severity_score: Optional[float]
    cvss_base_score: Optional[float]
    poc_available: bool
    is_confirmed: bool
    is_false_positive: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VulnerabilityDetailResponse(VulnerabilityResponse):
    cvss_impact_score: Optional[float]
    cvss_exploitability_score: Optional[float]
    cvss_vector: Optional[str]
    poc_exploit: Optional[str]
    poc_description: Optional[str]
    remediation: Optional[str]


# ============ TestCase Schemas ============
class TestCaseResponse(BaseModel):
    id: int
    scan_id: int
    protocol: ProtocolType
    raw_data: str
    semantic_valid: bool
    function_code: Optional[str]
    state_transition: Optional[str]
    edge_case: bool
    execution_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Crash Schemas ============
class CrashResponse(BaseModel):
    id: int
    scan_id: int
    crash_type: str
    crash_signal: Optional[str]
    input_data: Optional[str]
    severity_estimate: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ CVSS Schemas ============
class CVSSCalculation(BaseModel):
    attack_vector: str = Field(default="N", pattern="^[NAL裴P]$")
    attack_complexity: str = Field(default="L", pattern="^[LH]$")
    privileges_required: str = Field(default="N", pattern="^[NLPH]$")
    user_interaction: str = Field(default="N", pattern="^[NM]$")
    scope: str = Field(default="U", pattern="^[UC]$")
    confidentiality_impact: str = Field(default="H", pattern="^[NLH]$")
    integrity_impact: str = Field(default="H", pattern="^[NLH]$")
    availability_impact: str = Field(default="H", pattern="^[NLH]$")


class CVSSResponse(BaseModel):
    base_score: float
    impact_score: float
    exploitability_score: float
    severity: Severity
    vector: str


# ============ Dashboard Schemas ============
class DashboardStats(BaseModel):
    total_projects: int
    total_scans: int
    total_vulnerabilities: int
    critical_vulnerabilities: int
    high_vulnerabilities: int
    active_scans: int
    recent_crashes: int


class VulnerabilityTrend(BaseModel):
    date: str
    count: int
    critical_count: int
    high_count: int


class ProtocolDistribution(BaseModel):
    protocol: str
    count: int
    percentage: float


class SeverityDistribution(BaseModel):
    severity: Severity
    count: int


# ============ Protocol Analysis Schemas ============
class ProtocolAnalysisRequest(BaseModel):
    protocol: ProtocolType
    code_content: Optional[str] = None
    pcap_file: Optional[str] = None
    specification: Optional[str] = None


class ProtocolAnalysisResponse(BaseModel):
    protocol: ProtocolType
    understood_states: List[str]
    understood_functions: List[str]
    semantic_summary: str
    state_machine: dict
    potential_vulnerabilities: List[str]


# ============ LLMPrompt Schemas ============
class TestGenerationRequest(BaseModel):
    protocol: ProtocolType
    state_context: Optional[str] = None
    target_function: Optional[str] = None
    num_testcases: int = Field(default=10, ge=1, le=100)
    edge_case_ratio: float = Field(default=0.3, ge=0.0, le=1.0)


class TestGenerationResponse(BaseModel):
    testcases: List[dict]
    generated_count: int
    semantic_valid_count: int
    llm_model: str
