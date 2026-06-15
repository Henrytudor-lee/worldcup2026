@echo off
REM Mavis PDP Windows 一键启动脚本
REM 用法: 双击运行, 或 cmd 里输 start.bat
REM 停止: stop.bat

chcp 65001 >nul
setlocal enabledelayedexpansion

REM ====== 路径配置 ======
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
echo   Mavis PDP Windows 一键启动
echo ================================================
echo.

REM ====== 装依赖 ======
if not exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    echo [装依赖] 创建 venv...
    cd /d "%BACKEND_DIR%"
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建 venv 失败, 请确认 Python 已装
        pause
        exit /b 1
    )
    cd /d "%SCRIPT_DIR%"
)

call "%BACKEND_DIR%\.venv\Scripts\activate.bat"
echo [装依赖] pip install fastapi uvicorn scikit-optimize...
pip install fastapi uvicorn scikit-optimize >nul 2>&1
if errorlevel 1 (
    echo [警告] pip install 失败, 试着继续启动 (依赖可能已存在)
)
call deactivate

REM ====== 检查端口 + 自动强杀 ======
call :check_port %BACKEND_PORT%
call :check_port %FRONTEND_PORT%

REM ====== 启动后端 ======
echo.
echo [后端] 启动 FastAPI 端口 %BACKEND_PORT%...
cd /d "%BACKEND_DIR%"
start /b "Mavis-Backend" cmd /c ".venv\Scripts\python.exe server.py > "%LOG_DIR%\backend.log" 2>&1"
set "BACKEND_PID=!errorlevel!"
echo %BACKEND_PID% > "%RUN_DIR%\backend.pid"
cd /d "%SCRIPT_DIR%"

REM 等 3 秒验证
timeout /t 3 /nobreak >nul
curl -s -o nul -w "%%{http_code}" "http://localhost:%BACKEND_PORT%/" > "%RUN_DIR%\backend_check.txt" 2>&1
set /p BACKEND_CODE=<"%RUN_DIR%\backend_check.txt"
del "%RUN_DIR%\backend_check.txt" 2>nul
if "%BACKEND_CODE%"=="200" (
    echo   √ 后端就绪 http://localhost:%BACKEND_PORT%
) else (
    echo   × 后端启动失败, 看日志 %LOG_DIR%\backend.log
    type "%LOG_DIR%\backend.log" 2>nul | findstr /n "^" | findstr "^1: ^2: ^3: ^4: ^5: ^6: ^7: ^8: ^9: ^10:" >nul
    if exist "%LOG_DIR%\backend.log" (
        echo   --- 日志尾部 ---
        powershell -command "Get-Content '%LOG_DIR%\backend.log' -Tail 20"
    )
)

REM ====== 启动前端 ======
echo.
echo [前端] 启动 HTTP 端口 %FRONTEND_PORT%...
cd /d "%FRONTEND_DIR%"
start /b "Mavis-Frontend" cmd /c "python -m http.server %FRONTEND_PORT% > "%LOG_DIR%\frontend.log" 2>&1"
set "FRONTEND_PID=!errorlevel!"
echo %FRONTEND_PID% > "%RUN_DIR%\frontend.pid"
cd /d "%SCRIPT_DIR%"

timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" "http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html" > "%RUN_DIR%\frontend_check.txt" 2>&1
set /p FRONTEND_CODE=<"%RUN_DIR%\frontend_check.txt"
del "%RUN_DIR%\frontend_check.txt" 2>nul
if "%FRONTEND_CODE%"=="200" (
    echo   √ 前端就绪 http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html
)

echo.
echo ================================================
echo   √ 启动完成!
echo.
echo   浏览器打开: http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html
echo.
echo   ! 重要: 必须用 http:// 打开, 不能直接双击 HTML !
echo   ! 双击 HTML 走 file://, 浏览器禁止 fetch 8765 后端 = 没数据
echo ================================================
echo.
echo   停止: stop.bat
echo   日志: %LOG_DIR%\backend.log
echo ================================================
echo.
pause
exit /b 0

REM ====== 检查端口 + 强杀 ======
:check_port
set "PORT=%~1"
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
    if not "%%a"=="0" (
        echo [端口] %PORT% 被 PID %%a 占用, 自动杀掉...
        taskkill /F /PID %%a >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
)
exit /b 0
