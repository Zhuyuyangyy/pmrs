"""
仪表盘API - 漏洞dashboard和可视化
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from core.database import get_db
from models.models import Project, Scan, Vulnerability, Crash, Severity, ScanStatus

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """获取仪表盘统计数据"""
    # 项目总数
    project_count = await db.execute(select(func.count(Project.id)))
    total_projects = project_count.scalar()

    # 扫描总数
    scan_count = await db.execute(select(func.count(Scan.id)))
    total_scans = scan_count.scalar()

    # 漏洞总数
    vuln_count = await db.execute(select(func.count(Vulnerability.id)))
    total_vulnerabilities = vuln_count.scalar()

    # 严重漏洞统计
    critical_count = await db.execute(
        select(func.count(Vulnerability.id))
        .where(Vulnerability.severity == Severity.CRITICAL)
    )
    critical_vulns = critical_count.scalar()

    high_count = await db.execute(
        select(func.count(Vulnerability.id))
        .where(Vulnerability.severity == Severity.HIGH)
    )
    high_vulns = high_count.scalar()

    # 活跃扫描数
    active_count = await db.execute(
        select(func.count(Scan.id))
        .where(Scan.status == ScanStatus.RUNNING)
    )
    active_scans = active_count.scalar()

    # 最近崩溃数
    recent_crashes = await db.execute(
        select(func.count(Crash.id))
        .where(Crash.created_at >= datetime.utcnow() - timedelta(days=7))
    )
    recent = recent_crashes.scalar()

    return {
        "total_projects": total_projects,
        "total_scans": total_scans,
        "total_vulnerabilities": total_vulnerabilities,
        "critical_vulnerabilities": critical_vulns,
        "high_vulnerabilities": high_vulns,
        "active_scans": active_scans,
        "recent_crashes": recent,
    }


@router.get("/vulnerabilities/trend")
async def get_vulnerability_trend(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """获取漏洞趋势（按日期）"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(
            func.date(Vulnerability.created_at).label("date"),
            func.count(Vulnerability.id).label("count"),
        )
        .where(Vulnerability.created_at >= start_date)
        .group_by(func.date(Vulnerability.created_at))
        .order_by(desc("date"))
    )
    
    trends = [
        {
            "date": row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
            "count": row[1],
        }
        for row in result.all()
    ]
    
    return trends


@router.get("/vulnerabilities/distribution/severity")
async def get_severity_distribution(db: AsyncSession = Depends(get_db)):
    """获取漏洞严重性分布"""
    result = await db.execute(
        select(
            Vulnerability.severity,
            func.count(Vulnerability.id).label("count"),
        )
        .group_by(Vulnerability.severity)
    )
    
    distribution = [
        {"severity": row[0].value, "count": row[1]}
        for row in result.all()
    ]
    
    return distribution


@router.get("/vulnerabilities/distribution/protocol")
async def get_protocol_distribution(db: AsyncSession = Depends(get_db)):
    """获取漏洞协议分布"""
    total_result = await db.execute(select(func.count(Vulnerability.id)))
    total = total_result.scalar() or 1

    result = await db.execute(
        select(
            Vulnerability.protocol,
            func.count(Vulnerability.id).label("count"),
        )
        .group_by(Vulnerability.protocol)
    )
    
    distribution = []
    for row in result.all():
        percentage = (row[1] / total) * 100 if total > 0 else 0
        distribution.append({
            "protocol": row[0].value,
            "count": row[1],
            "percentage": round(percentage, 2),
        })
    
    return distribution


@router.get("/vulnerabilities/recent")
async def get_recent_vulnerabilities(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取最近发现的漏洞"""
    result = await db.execute(
        select(Vulnerability)
        .order_by(desc(Vulnerability.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/scans/recent")
async def get_recent_scans(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取最近扫描"""
    result = await db.execute(
        select(Scan)
        .order_by(desc(Scan.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/vulnerabilities/by-project/{project_id}")
async def get_project_vulnerability_summary(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取项目的漏洞汇总"""
    result = await db.execute(
        select(
            Vulnerability.severity,
            func.count(Vulnerability.id).label("count"),
        )
        .where(Vulnerability.project_id == project_id)
        .group_by(Vulnerability.severity)
    )
    
    summary = {row[0].value: row[1] for row in result.all()}
    
    return {
        "project_id": project_id,
        "total": sum(summary.values()),
        "by_severity": summary,
    }
