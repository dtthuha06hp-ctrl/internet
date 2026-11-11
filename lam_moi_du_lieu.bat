@echo off
chcp 65001 >nul
title Nhip Mobile - lam moi du lieu
cd /d "%~dp0"
echo.
echo  Thao tac nay XOA toan bo don hang, tai khoan, san pham da sua...
echo  va nap lai DU LIEU MAU ban dau. Hay tat cua so web truoc khi lam.
echo.
set /p ok=" Go chu C roi Enter de tiep tuc (Enter de huy): "
if /i not "%ok%"=="C" goto end

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py --reset
    goto end
)
python app.py --reset

:end
echo.
pause
