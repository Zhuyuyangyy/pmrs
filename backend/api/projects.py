"""
项目管理API - 工业控制协议漏洞挖掘项目
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from core.database import get_db
from models.models import Project, ScanStatus
from schemas.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from services.scanner import VulnerabilityScanner, test_target_connectivity

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建新项目"""
    scanner = VulnerabilityScanner(db)
    new_project = await scanner.create_project(
        name=project.name,
        target_ip=project.target_ip,
        target_port=project.target_port,
        protocol=project.protocol.value,
        description=project.description,
    )
    return new_project


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取项目列表"""
    result = await db.execute(
        select(Project).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取项目详情"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新项目"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if update.name is not None:
        project.name = update.name
    if update.description is not None:
        project.description = update.description
    if update.config is not None:
        project.config = update.config
    if update.status is not None:
        project.status = update.status

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除项目"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.execute(delete(Project).where(Project.id == project_id))
    await db.commit()


@router.get("/{project_id}/connectivity")
async def check_connectivity(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """检查目标连接性"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_reachable = await test_target_connectivity(
        project.target_ip,
        project.target_port,
    )

    return {
        "project_id": project_id,
        "target_ip": project.target_ip,
        "target_port": project.target_port,
        "reachable": is_reachable,
    }
