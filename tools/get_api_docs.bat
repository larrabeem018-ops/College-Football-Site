@echo off
cd /d "%~dp0"
python get_api_docs.py
if errorlevel 1 py get_api_docs.py
timeout /t 5
