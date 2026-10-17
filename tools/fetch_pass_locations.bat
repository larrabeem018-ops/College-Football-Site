@echo off
cd /d "%~dp0.."
echo Pulling QB pass-location splits from CollegeFootballData...
python update_data.py --only-pass-locations
if errorlevel 9009 py update_data.py --only-pass-locations
echo.
pause
