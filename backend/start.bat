@echo off
REM =============================================================================
REM PMRS Windows 启动脚本
REM 工业控制协议漏洞挖掘系统
REM =============================================================================
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM 环境配置
set ENVIRONMENT=production
set LOG_LEVEL=info
set GUNICORN_WORKERS=4

REM 颜色支持 (Windows 10+)
reg query "HKCU\Console" /v VirtualTerminalLevel 2>nul >nul
if %errorlevel% neq 0 (
    set "VT="
) else (
    set "VT=1"
)

set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set NC=[0m

echo ==============================================================================
echo   PMRS - 工业控制协议漏洞挖掘系统
echo ==============================================================================
echo.

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [PMRS] 错误: Python 未安装或未在 PATH 中
    exit /b 1
)

REM 检查虚拟环境
set VENV_DIR=%SCRIPT_DIR%.venv
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [PMRS] 创建虚拟环境...
    python -m venv "%VENV_DIR%"
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -q gunicorn uvicorn
) else (
    call "%VENV_DIR%\Scripts\activate.bat"
)

REM 设置环境变量
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/pmrs
set REDIS_URL=redis://localhost:6379/0
set PYTHONPATH=%SCRIPT_DIR%

REM PID 和日志
set PID_FILE=%SCRIPT_DIR%pmrs.pid
set LOG_DIR=%SCRIPT_DIR%logs
set ERROR_LOG=%LOG_DIR%\error.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM =============================================================================
REM 辅助函数
REM =============================================================================

:get_pid
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    exit /b 0
)
set PID=
exit /b 1

:is_running
call :get_pid
if defined PID (
    tasklist /fi "PID eq %PID%" 2>nul | find /i "%PID%" >nul
    if !errorlevel! equ 0 exit /b 0
)
exit /b 1

REM =============================================================================
REM 命令处理
REM =============================================================================

if "%~1"=="" goto usage
if "%~1"=="start" goto start
if "%~1"=="stop" goto stop
if "%~1"=="restart" goto restart
if "%~1"=="status" goto status
goto usage

:start
call :is_running
if !errorlevel! equ 0 (
    echo [PMRS] PMRS 服务已在运行 (PID: !PID!)
    exit /b 1
)

echo [PMRS] 启动 PMRS 后端服务...
echo [PMRS] 工作目录: %SCRIPT_DIR%
echo [PMRS] Workers: %GUNICORN_WORKERS%

REM 检查 gunicorn
python -c "import gunicorn" 2>nul
if !errorlevel! neq 0 (
    echo [PMRS] 安装 gunicorn...
    pip install gunicorn
)

REM 启动 gunicorn
start /b cmd /c "cd /d %SCRIPT_DIR% && ^
gunicorn --config gunicorn_conf.py --pid %PID_FILE% --error-logfile %ERROR_LOG% --daemon main:app"

timeout /t 2 /nobreak >nul

call :is_running
if !errorlevel! equ 0 (
    echo [PMRS] PMRS 服务启动成功 (PID: !PID!)
    echo [PMRS] 健康检查: http://localhost:8000/health
    echo [PMRS] API文档:   http://localhost:8000/docs
) else (
    echo [PMRS] 错误: PMRS 服务启动失败，请检查日志: %ERROR_LOG%
    exit /b 1
)
exit /b 0

:stop
call :is_running
if !errorlevel! neq 0 (
    echo [PMRS] PMRS 服务未运行
    exit /b 1
)

echo [PMRS] 停止 PMRS 服务 (PID: !PID!)...
taskkill /f /pid !PID! >nul 2>&1

REM 等待进程结束
set /a count=0
:wait_loop
timeout /t 1 /nobreak >nul
tasklist /fi "PID eq !PID!" 2>nul | find /i "!PID!" >nul
if !errorlevel! equ 0 (
    set /a count+=1
    if !count! lss 30 goto wait_loop
    echo.
    echo [PMRS] 强制终止...
    taskkill /f /pid !PID! >nul 2>&1
)

REM 清理 PID 文件
if exist "%PID_FILE%" del /f "%PID_FILE%"

echo [PMRS] PMRS 服务已停止
exit /b 0

:restart
echo [PMRS] 重启 PMRS 服务...
call :stop
timeout /t 2 /nobreak >nul
call :start
exit /b 0

:status
call :is_running
if !errorlevel! equ 0 (
    echo [PMRS] PMRS 服务运行中 (PID: !PID!)
    where curl >nul 2>&1
    if !errorlevel! equ 0 (
        curl -s http://localhost:8000/health 2>nul || echo 无法连接
    )
) else (
    echo [PMRS] PMRS 服务未运行
)
exit /b 0

:usage
echo PMRS 后端服务管理脚本
echo.
echo 用法: %~nx0 {start^|stop^|restart^|status}
echo.
echo 命令:
echo   start   启动服务
echo   stop    停止服务
echo   restart 重启服务
echo   status  查看状态
echo.
exit /b 1
