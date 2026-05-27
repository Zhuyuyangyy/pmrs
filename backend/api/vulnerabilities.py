"""
漏洞管理API - 工业控制协议漏洞管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from core.database import get_db
from models.models import Vulnerability, Severity, ProtocolType
from schemas.schemas import VulnerabilityResponse, VulnerabilityDetailResponse

router = APIRouter()


@router.get("/", response_model=List[VulnerabilityResponse])
async def list_vulnerabilities(
    project_id: Optional[int] = None,
    scan_id: Optional[int] = None,
    severity: Optional[Severity] = None,
    protocol: Optional[ProtocolType] = None,
    is_false_positive: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取漏洞列表"""
    query = select(Vulnerability)
    
    if project_id:
        query = query.where(Vulnerability.project_id == project_id)
    if scan_id:
        query = query.where(Vulnerability.scan_id == scan_id)
    if severity:
        query = query.where(Vulnerability.severity == severity)
    if protocol:
        query = query.where(Vulnerability.protocol == protocol)
    if is_false_positive is not None:
        query = query.where(Vulnerability.is_false_positive == is_false_positive)
    
    query = query.offset(skip).limit(limit).order_by(Vulnerability.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{vulnerability_id}", response_model=VulnerabilityDetailResponse)
async def get_vulnerability(
    vulnerability_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取漏洞详情"""
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.id == vulnerability_id)
    )
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    return vuln


@router.patch("/{vulnerability_id}/confirm")
async def confirm_vulnerability(
    vulnerability_id: int,
    is_false_positive: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """确认或标记漏洞为误报"""
    result = await db.execute(
        select(Vulnerability).where(Vulnerability.id == vulnerability_id)
    )
    vuln = result.scalar_one_or_none()
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")

    vuln.is_confirmed = True
    vuln.is_false_positive = is_false_positive
    await db.commit()
    
    return {"status": "updated", "is_confirmed": True}


@router.get("/stats/summary")
async def get_vulnerability_stats(
    db: AsyncSession = Depends(get_db),
):
    """获取漏洞统计"""
    # 总数
    total_result = await db.execute(select(func.count(Vulnerability.id)))
    total = total_result.scalar()

    # 按严重性统计
    severity_result = await db.execute(
        select(Vulnerability.severity, func.count(Vulnerability.id))
        .group_by(Vulnerability.severity)
    )
    severity_stats = {row[0].value: row[1] for row in severity_result.all()}

    # 按协议统计
    protocol_result = await db.execute(
        select(Vulnerability.protocol, func.count(Vulnerability.id))
        .group_by(Vulnerability.protocol)
    )
    protocol_stats = {row[0].value: row[1] for row in protocol_result.all()}

    return {
        "total": total,
        "by_severity": severity_stats,
        "by_protocol": protocol_stats,
    }
