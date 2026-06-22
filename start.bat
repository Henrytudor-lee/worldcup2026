@echo off
REM Mavis PDP Windows 一键启动 (v2 - 简化版, 避免 cmd 引号嵌套坑)
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
echo   Mavis PDP Windows 一键启动
echo ================================================
echo.

REM ====== 1. 装依赖 (venv) ======
echo [1/4] 检查 venv 和依赖...
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

REM 用 venv 装依赖 (静默, 失败也不阻塞 - 可能已经装过了)
echo   pip install fastapi uvicorn scikit-optimize...
"%VENV_PY%" -m pip install fastapi uvicorn scikit-optimize --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo   ! pip install 出错, 但继续 (可能依赖已存在)
) else (
    echo   √ 依赖就绪
)

REM ====== 2. 检查端口 + 强杀旧进程 ======
echo.
echo [2/4] 检查端口 (8765 / 8080)...
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

REM ====== 3. 启动后端 ======
echo.
echo [3/4] 启动后端 (FastAPI :%BACKEND_PORT%)...
set "BACKEND_LOG=%LOG_DIR%\backend.log"
REM 用 start /B + 转义, 避免引号嵌套
start "Mavis-Backend" /D "%BACKEND_DIR%" /B cmd /c ""%VENV_PY%" server.py > "%BACKEND_LOG%" 2>&1"
timeout /t 3 /nobreak >nul

REM 验证后端
curl -s -o nul -w "  状态码: %%{http_code}\n" "http://localhost:%BACKEND_PORT%/" 2>nul
echo   √ 后端日志: %BACKEND_LOG%

REM ====== 4. 启动前端 ======
echo.
echo [4/4] 启动前端 (HTTP :%FRONTEND_PORT%)...
set "FRONTEND_LOG=%LOG_DIR%\frontend.log"
start "Mavis-Frontend" /D "%FRONTEND_DIR%" /B cmd /c "python -m http.server %FRONTEND_PORT% > ""%FRONTEND_LOG%"" 2>&1"
timeout /t 2 /nobreak >nul

curl -s -o nul -w "  状态码: %%{http_code}\n" "http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html" 2>nul
echo   √ 前端日志: %FRONTEND_LOG%

echo.
echo ================================================
echo   √ 启动完成!
echo.
echo   浏览器打开这个 URL (注意是 http, 不是 file):
echo.
echo       http://localhost:%FRONTEND_PORT%/world_cup_2026_spa.html
echo.
echo   ! 双击 HTML 文件走 file://, 浏览器禁止 fetch 8765 后端
echo   ! 必须把上面 URL 粘到浏览器地址栏
echo.
echo   停止服务: 双击 stop.bat
echo   排查环境: 双击 check_env.bat
echo ================================================
echo.
pause
exit /b 0
