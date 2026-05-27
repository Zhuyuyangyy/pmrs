"""
扫描任务API - 工业控制协议漏洞扫描任务
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from core.database import get_db
from models.models import Scan, Project, ScanStatus
from schemas.schemas import ScanCreate, ScanResponse
from services.scanner import VulnerabilityScanner, get_scan_status

router = APIRouter()


@router.post("/", response_model=ScanResponse, status_code=201)
async def create_scan(
    scan: ScanCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建并启动扫描"""
    # 检查项目存在
    result = await db.execute(
        select(Project).where(Project.id == scan.project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scanner = VulnerabilityScanner(db)
    new_scan = await scanner.start_scan(
        project_id=scan.project_id,
        scan_type=scan.scan_type,
        llm_model=scan.llm_model,
        fuzz_duration=scan.fuzz_duration,
    )
    return new_scan


@router.get("/", response_model=List[ScanResponse])
async def list_scans(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取扫描列表"""
    query = select(Scan)
    if project_id:
        query = query.where(Scan.project_id == project_id)
    if status:
        query = query.where(Scan.status == status)
    
    query = query.offset(skip).limit(limit).order_by(Scan.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{scan_id}", response_model=dict)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取扫描详情和状态"""
    status = await get_scan_status(scan_id, db)
    if not status:
        raise HTTPException(status_code=404, detail="Scan not found")
    return status


@router.post("/{scan_id}/cancel", status_code=204)
async def cancel_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
):
    """取消扫描"""
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    scanner = VulnerabilityScanner(db)
    await scanner.cancel_scan(scan_id)
