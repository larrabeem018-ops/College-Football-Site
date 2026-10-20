@echo off
cd /d "%~dp0.."
python tools\start_week.py %*
echo.
pause
