@echo off
title BM Exam Helper - First Time Setup
echo.
echo  ====================================
echo    BM EXAM HELPER - SETUP
echo    First-time installation
echo  ====================================
echo.

echo  [1/3] Installing Python dependencies...
pip install flask chromadb playwright
echo.

echo  [2/3] Installing browser for ChatGPT scraper...
playwright install chromium
echo.

echo  [3/3] Building knowledge base index (takes ~2 minutes)...
python "%~dp0build_vector_db.py"
echo.

echo  ====================================
echo    SETUP COMPLETE!
echo    Double-click START.bat to begin.
echo  ====================================
pause
