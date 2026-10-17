@echo off
cd /d "%~dp0.."
echo === Updating 2026 data from CollegeFootballData (scores, lines, QB and team stats) ===
python update_data.py --seasons 2026
if errorlevel 1 goto fail
echo.
echo === Rebuilding website data ===
python export_web_data.py
if errorlevel 1 goto fail
echo.
echo Done. You can close this window.
pause
exit /b 0
:fail
echo.
echo Something failed - see the error above.
pause
exit /b 1
