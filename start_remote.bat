@echo off
REM Mavis PDP Windows 一键启动 (跨电脑访问版 v1)
REM 用法: 双击运行, 自动检测本机 IP + 放行 Windows 防火墙
REM 适用: 在 A 电脑启动, B 电脑访问 A 的 IP
chcp 65001 >nul

setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%4_比赛预测"
set "RUN_DIR=%SCRIPT_DIR%.run"
set "BACKEND_PORT=8765"
set "FRONTEND_PORT=8080"
set "LOG_DIR=%RUN_DIR%\logs"

if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo ================================================
echo   Mavis PDP Windows 一键启动 (远程访问版)
echo ================================================
echo.

REM ====== 0. 检测本机 LAN IP ======
echo [0/5] 检测本机 IP...
set "LOCAL_IP=未知"
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=*" %%i in ("%%a") do (
        if not "%%i"=="" set "LOCAL_IP=%%i"
    )
)
if "%LOCAL_IP%"=="未知" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IP Address"') do (
        for /f "tokens=*" %%i in ("%%a") do (
            if not "%%i"=="" set "LOCAL_IP=%%i"
        )
    )
)
echo   本机 IP: %LOCAL_IP%
echo.

REM ====== 1. Windows 防火墙放行 8765 + 8080 ======
echo [1/5] Windows 防火墙放行端口...
netsh advfirewall firewall show rule name="Mavis-PDP-Backend" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="Mavis-PDP-Backend" dir=in action=allow protocol=TCP localport=%BACKEND_PORT% >nul 2>&1
    echo   √ 已添加 Backend 入站规则 (TCP/%BACKEND_PORT%)
) else (
    echo   √ Backend 入站规则已存在
)
netsh advfirewall firewall show rule name="Mavis-PDP-Frontend" >nul 2>&1
if errorlevel 1 (
    netsh advfirewall firewall add rule name="Mavis-PDP-Frontend" dir=in action=allow protocol=TCP localport=%FRONTEND_PORT% >nul 2>&1
    echo   √ 已添加 Frontend 入站规则 (TCP/%FRONTEND_PORT%)
) else (
    echo   √ Frontend 入站规则已存在
)
echo.

REM ====== 2. 装依赖 (venv) ======
echo [2/5] 检查 venv 和依赖...
set "VENV_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo   venv 不存在, 创建中...
    python -m venv "%BACKEND_DIR%\.venv"
    if errorlevel 1 (
        echo.
        echo   X 创建 venv 失败!
        echo   请确认 Python 已装, 且 python -m venv 能跑
        echo.
        pause
        exit /b 1
    )
    echo   venv 创建完成
)

echo   pip install fastapi uvicorn scikit-optimize...
"%VENV_PY%" -m pip install fastapi uvicorn scikit-optimize --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo   ! pip install 出错, 但继续
) else (
    echo   √ 依赖就绪
)
echo.

REM ====== 3. 检查端口 + 强杀旧进程 ======
echo [3/5] 检查端口 (%BACKEND_PORT% / %FRONTEND_PORT%)...
for %%P in (%BACKEND_PORT% %FRONTEND_PORT%) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%%P " ^| findstr /I "LISTENING"') do (
        if not "%%a"=="0" (
            echo   端口 %%P 被 PID %%a 占用, 杀掉
            taskkill /F /PID %%a >nul 2>&1
        )
    )
)
timeout /t 1 /nobreak >nul
echo   √ 端口已就绪
echo.

REM ====== 4. 启动后端 ======
echo [4/5] 启动后端 (FastAPI :%BACKEND_PORT%)...
set "BACKEND_LOG=%LOG_DIR%\backend.log"
start "Mavis-Backend" /D "%BACKEND_DIR%" /B cmd /c ""%VENV_PY%" server.py > "%BACKEND_LOG%" 2>&1"
timeout /t 3 /nobreak >nul
curl -s -o nul -w "  本机状态码: %%{http_code}\n" "http://localhost:%BACKEND_PORT%/" 2>nul
curl -s -o nul -w "  远程状态码: %%{http_code}\n" "http://%LOCAL_IP%:%BACKEND_PORT%/" 2>nul
echo   √ 后端日志: %BACKEND_LOG%
echo.

REM ====== 5. 启动前端 ======
echo [5/5] 启动前端 (HTTP :%FRONTEND_PORT%)...
set "FRONTEND_LOG=%LOG_DIR%\frontend.log"
start "Mavis-Frontend" /D "%FRONTEND_DIR%" /B cmd /c "python -m http.server %FRONTEND_PORT% --bind 0.0.0.0 > ""%FRONTEND_LOG%"" 2>&1"
timeout /t 2 /nobreak >nul
curl -s -o nul -w "  本机状态码: %%{http_code}\n" "http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html" 2>nul
curl -s -o nul -w "  远程状态码: %%{http_code}\n" "http://%LOCAL_IP%:%FRONTEND_PORT%/world_cup_2026_spa.html" 2>nul
echo   √ 前端日志: %FRONTEND_LOG%
echo.

echo ================================================
echo   √ 启动完成!
echo.
echo   ┌────────────────────────────────────────────┐
echo   │  本机访问 (A 电脑浏览器):                    │
echo   │    http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html │
echo   └────────────────────────────────────────────┘
echo.
echo   ┌────────────────────────────────────────────┐
echo   │  远程访问 (B 电脑浏览器):                    │
echo   │    http://%LOCAL_IP%:%FRONTEND_PORT%/world_cup_2026_spa.html │
echo   └────────────────────────────────────────────┘
echo.
echo   ! 如果 B 电脑访问不到, 检查:
echo     1. A 和 B 在同一局域网 (同一 WiFi/网段)
echo     2. A 电脑 Windows Defender 允许 Python (设置 - 应用 - 已安装应用 - Python - 允许)
echo     3. 路由器没有隔离 AP (家庭路由一般没问题)
echo     4. 试 cmd ping %LOCAL_IP% 看通不通
echo.
echo   ! 注意: 双击 HTML 文件走 file://, 浏览器禁止 fetch 后端 → 没数据
echo     必须把上面 URL 粘到浏览器地址栏 (注意是 http, 不是 file)
echo.
echo   停止服务: 双击 stop.bat
echo   排查环境: 双击 check_env.bat
echo ================================================
echo.
pause
exit /b 0
