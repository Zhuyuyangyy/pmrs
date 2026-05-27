"""
协议分析API - 工业控制协议解析与模糊测试
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from core.database import get_db
from schemas.schemas import ProtocolAnalysisRequest, ProtocolAnalysisResponse
from services.llm_service import llm_service
from protocols.base import ProtocolRegistry
from protocols.modbus_tcp import ModbusTCP
from protocols.iec61850 import IEC61850, DNP3

router = APIRouter()


@router.get("/")
async def list_supported_protocols():
    """获取支持的协议列表"""
    protocols = ProtocolRegistry.list_protocols()
    return {
        "protocols": protocols,
        "count": len(protocols),
    }


@router.get("/{protocol_name}/info")
async def get_protocol_info(protocol_name: str):
    """获取协议详细信息"""
    protocol_class = ProtocolRegistry.get(protocol_name)
    if not protocol_class:
        raise HTTPException(status_code=404, detail="Protocol not found")

    protocol = protocol_class()
    return {
        "name": protocol.PROTOCOL_NAME,
        "default_port": protocol.DEFAULT_PORT,
        "functions": protocol.get_functions(),
        "state_machine": protocol.state_machine,
        "vulnerability_patterns": protocol.identify_vulnerabilities(),
    }


@router.post("/analyze")
async def analyze_protocol(
    request: ProtocolAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """分析协议实现（LLM双通道理解）"""
    # LLM协议分析
    analysis_result = await llm_service.understand_protocol(
        protocol=request.protocol.value,
        code_content=request.code_content,
        pcap_summary=None,
        specification=request.specification,
    )

    return {
        "protocol": request.protocol.value,
        "analysis": analysis_result,
    }


@router.post("/parse")
async def parse_packet(
    protocol: str,
    data: str,
):
    """解析协议数据包"""
    protocol_class = ProtocolRegistry.get(protocol)
    if not protocol_class:
        raise HTTPException(status_code=404, detail="Protocol not found")

    protocol = protocol_class()
    try:
        parsed = protocol.parse(bytes.fromhex(data.replace(" ", "")))
        return {
            "valid": parsed is not None,
            "result": parsed,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
        }


@router.post("/build")
async def build_packet(
    protocol: str,
    function_code: str,
    params: dict,
):
    """构建协议数据包"""
    protocol_class = ProtocolRegistry.get(protocol)
    if not protocol_class:
        raise HTTPException(status_code=404, detail="Protocol not found")

    protocol = protocol_class()

    try:
        if protocol == ModbusTCP:
            # Modbus TCP 特殊处理
            if function_code == "read_holding_registers":
                raw = ModbusTCP.build_read_request(
                    transaction_id=params.get("transaction_id", 1),
                    unit_id=params.get("unit_id", 1),
                    start_address=params.get("start_address", 0),
                    quantity=params.get("quantity", 10),
                )
            elif function_code == "write_multiple_registers":
                raw = ModbusTCP.build_write_request(
                    transaction_id=params.get("transaction_id", 1),
                    unit_id=params.get("unit_id", 1),
                    start_address=params.get("start_address", 0),
                    values=params.get("values", []),
                )
            else:
                raise ValueError(f"Unknown function code: {function_code}")
            
            return {
                "success": True,
                "raw_hex": raw.hex(),
            }
        else:
            return {
                "success": False,
                "error": "Build not supported for this protocol",
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/generate-tests")
async def generate_testcases(
    protocol: str,
    state_context: Optional[str] = None,
    target_function: Optional[str] = None,
    num_testcases: int = 10,
    edge_case_ratio: float = 0.3,
):
    """生成测试用例"""
    testcases = await llm_service.generate_testcases(
        protocol=protocol,
        state_context=state_context,
        target_function=target_function,
        num_testcases=num_testcases,
        edge_case_ratio=edge_case_ratio,
    )

    return {
        "protocol": protocol,
        "testcases": testcases,
        "generated_count": len(testcases),
    }
