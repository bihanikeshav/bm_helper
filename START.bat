@echo off
title BM Exam Helper
echo.
echo  ====================================
echo    BM EXAM HELPER
echo    Starting up...
echo  ====================================
echo.

REM Kill any existing server on port 5000
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :5000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

REM Wait for port to release
ping -n 2 127.0.0.1 >nul 2>&1

REM Start Flask server in its OWN hidden window
start "BM_Server" /min python "%~dp0server.py"

REM Wait for server to be ready
ping -n 4 127.0.0.1 >nul 2>&1

REM Open dashboard in default browser
start "" http://localhost:5000

echo  Server running at http://localhost:5000
echo  Dashboard opened in browser.
echo.
echo  ====================================
echo   READY! Paste your exam question
echo   below and press Enter.
echo.
echo   Commands:
echo     "more examples"      - different brands
echo     "different framework" - different angle
echo     Ctrl+C then re-paste - if it hangs
echo  ====================================
echo.

REM Start Claude Code - skip permissions (no prompts during exam)
REM Resume if session exists, otherwise start new
claude --dangerously-skip-permissions --resume 2>nul || claude --dangerously-skip-permissions
