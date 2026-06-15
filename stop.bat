@echo off
REM Mavis PDP Windows 停止脚本
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
set "BACKEND_PORT=8765"
set "FRONTEND_PORT=8080"

echo 停止 Mavis PDP 服务...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    if not "%%a"=="0" (
        echo   杀掉后端 PID %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    if not "%%a"=="0" (
        echo   杀掉前端 PID %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)

REM 兜底: 用 taskkill 按窗口名杀
taskkill /F /FI "WINDOWTITLE eq Mavis-Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Mavis-Frontend*" >nul 2>&1

echo √ 已停止
pause
exit /b 0
