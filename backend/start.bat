@echo off
echo ====================================
echo PMRS Backend Server Starter
echo ====================================

cd /d "%~dp0"

echo.
echo [1/3] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

echo [2/3] Installing dependencies...
if exist requirements.txt (
    pip install -r requirements.txt -q
)

echo.
echo [3/3] Starting FastAPI server on port 8011...
echo.
echo Server will be available at:
echo   - API: http://localhost:8011
echo   - Docs: http://localhost:8011/docs
echo   - Health: http://localhost:8011/health
echo.
echo Press Ctrl+C to stop the server.
echo.

python app.py

pause
