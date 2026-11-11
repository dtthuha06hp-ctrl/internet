@echo off
chcp 65001 >nul
title Nhip Mobile - kiem thu tu dong
cd /d "%~dp0"
echo.
echo  Dang chay toan bo kiem thu tu dong, vui long doi khoang 30 giay...
echo.
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 xuat_bao_cao_kiem_thu.py
) else (
    python xuat_bao_cao_kiem_thu.py
)
echo.
echo  Dong "OK" o tren = tat ca kiem thu deu DAT.
echo  Bang ket qua da mo trong trinh duyet: tai-lieu\ket-qua-kiem-thu.html
pause
