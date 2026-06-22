@echo off
REM Mavis PDP 环境诊断脚本
REM 用法: 双击运行, 把输出截图给我
chcp 65001 >nul
echo.
echo ================================================
echo   Mavis PDP 环境诊断
echo ================================================
echo.

REM 1. Python
echo [1] Python 检查
where python >nul 2>&1
if errorlevel 1 (
    echo     X Python 不在 PATH
    echo     装: https://www.python.org/downloads/
    echo     安装时务必勾: Add Python to PATH
) else (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo     √ %%v
    for /f "tokens=*" %%p in ('where python') do echo     路径: %%p
)
echo.

REM 2. pip
echo [2] pip 检查
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo     X pip 不可用
) else (
    for /f "tokens=*" %%v in ('python -m pip --version 2^>^&1') do echo     √ %%v
)
echo.

REM 3. venv 模块
echo [3] venv 模块
python -c "import venv; print('  √ venv ok')" 2>nul
if errorlevel 1 echo     X venv 模块不可用, 重新装 Python 时勾 "tcl/tk and IDLE"
echo.

REM 4. 项目结构
echo [4] 项目结构
REM check_env.bat 在 0_scripts/ 里, 项目根是上级目录
set "SCRIPT_DIR=%~dp0.."
for %%I in ("%SCRIPT_DIR%") do set "SCRIPT_DIR=%%~fI"
if exist "%SCRIPT_DIR%\backend\server.py" (
    echo     √ backend\server.py
) else (
    echo     X backend\server.py 缺失
)
if exist "%SCRIPT_DIR%\4_比赛预测\world_cup_2026_spa.html" (
    echo     √ 4_比赛预测\world_cup_2026_spa.html
) else (
    echo     X 4_比赛预测\world_cup_2026_spa.html 缺失
)
echo     项目根: %SCRIPT_DIR%
echo.

REM 5. 端口占用
echo [5] 端口占用
netstat -aon | findstr ":8765 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo     8765: 被占用
    netstat -aon | findstr ":8765 " | findstr "LISTENING"
) else (
    echo     √ 8765 空闲
)
netstat -aon | findstr ":8080 " | findstr "LISTENING" >nul
if not errorlevel 1 (
    echo     8080: 被占用
    netstat -aon | findstr ":8080 " | findstr "LISTENING"
) else (
    echo     √ 8080 空闲
)
echo.

REM 6. 后端依赖
echo [6] 后端关键依赖
python -c "import fastapi" >nul 2>&1 && echo     √ fastapi || echo     X fastapi 缺失
python -c "import uvicorn" >nul 2>&1 && echo     √ uvicorn || echo     X uvicorn 缺失
python -c "import skopt" >nul 2>&1 && echo     √ scikit-optimize || echo     X scikit-optimize 缺失
python -c "import pandas" >nul 2>&1 && echo     √ pandas || echo     ! pandas 缺失 (可选)
echo.

REM 7. 防火墙/网络
echo [7] 网络探测
curl -s -o nul -w "    http://localhost:8765/ -> %%{http_code}\n" "http://localhost:8765/" 2>nul
curl -s -o nul -w "    http://localhost:8080/ -> %%{http_code}\n" "http://localhost:8080/" 2>nul
echo.

REM 8. 关键文件编码
echo [8] 中文路径探测
if exist "%SCRIPT_DIR%\4_比赛预测" (
    cd /d "%SCRIPT_DIR%\4_比赛预测"
    dir /b "*.html" >nul 2>&1 && echo     √ 4_比赛预测\ 可访问 (中文路径)
    cd /d "%SCRIPT_DIR%"
) else (
    echo     X 中文目录 4_比赛预测 不可访问
)
echo.

echo ================================================
echo   诊断完成
echo ================================================
echo.
echo 把上面输出截图发给我即可
echo.
pause
