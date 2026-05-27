"""
API路由总览 - 工业控制协议漏洞挖掘系统
"""
from fastapi import APIRouter
from api import projects, scans, vulnerabilities, dashboard, protocols

api_router = APIRouter()

api_router.include_router(projects.router, prefix="/projects", tags=["项目管理"])
api_router.include_router(scans.router, prefix="/scans", tags=["扫描任务"])
api_router.include_router(vulnerabilities.router, prefix="/vulnerabilities", tags=["漏洞管理"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(protocols.router, prefix="/protocols", tags=["协议分析"])
