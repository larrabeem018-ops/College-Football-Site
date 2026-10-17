@echo off
setlocal
title CFB Analytics Hub (local)
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Node.js is not installed, or this window can't find it.
  echo  1. Install the LTS version from https://nodejs.org
  echo  2. Close this window and double-click start-site.bat again.
  echo.
  pause
  exit /b 1
)

for /f "tokens=1 delims=v." %%a in ('node -v') do set NODE_MAJOR=%%a
if %NODE_MAJOR% LSS 20 (
  echo.
  echo  Your Node.js is too old. This site needs version 20 or newer.
  node -v
  echo  Install the current LTS from https://nodejs.org, then try again.
  echo.
  pause
  exit /b 1
)

if not exist "public\data\meta.json" (
  echo.
  echo  No site data yet. From the main project folder, run:
  echo      python export_web_data.py
  echo.
  pause
  exit /b 1
)

if not exist "node_modules\next" (
  echo.
  echo  First run: installing the site's packages. This takes a few minutes.
  echo  Tip: pause OneDrive syncing until this finishes.
  echo.
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo.
    echo  npm install failed. See the error above. Common fixes are listed in web\README.md.
    pause
    exit /b 1
  )
)

echo.
echo  Starting the site. It opens in your browser in a few seconds.
echo  Leave this window open while you use the site. Press Ctrl+C here to stop it.
echo.
start "" cmd /c "timeout /t 6 >nul & start http://localhost:3000"
call npm run dev
pause
