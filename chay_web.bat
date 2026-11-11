@echo off
chcp 65001 >nul
title Nhip Mobile - dang chay (dong cua so nay de tat web)
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
    goto done
)
python --version >nul 2>nul
if %errorlevel%==0 (
    python app.py
    goto done
)

echo.
echo  ============================================================
echo   CHUA TIM THAY PYTHON TREN MAY.
echo   1. Vao python.org/downloads, tai ban cho Windows.
echo   2. Khi cai, TICH VAO O "Add python.exe to PATH".
echo   3. Cai xong, bam dup lai file chay_web.bat nay.
echo  ============================================================
echo.

:done
echo.
pause
