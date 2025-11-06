@echo off
echo ============================================
echo   DocuMind LM - Starting Server
echo ============================================
echo.
echo Server will start at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================

cd /d "%~dp0"
uvicorn logmain:app --reload --host 0.0.0.0 --port 8000

pause
