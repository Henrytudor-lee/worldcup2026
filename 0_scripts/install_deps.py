#!/usr/bin/env python3
"""
Mavis PDP 依赖安装脚本 (跨平台)
- 自动检测 Python (>= 3.9)
- 创建 venv: backend/.venv
- 安装依赖: fastapi / uvicorn / scikit-optimize
- 默认走清华源 (国内加速)

用法:
  python 0_scripts/install_deps.py            # 用默认清华源
  python 0_scripts/install_deps.py --pypi     # 用官方 PyPI
  python 0_scripts/install_deps.py --tsinghua # 显式指定清华源
  python 0_scripts/install_deps.py --skip-venv # 不创建 venv, 直接装到系统 Python (不推荐)

装完后:
  Windows: backend\\.venv\\Scripts\\python server.py
  Mac/Linux: backend/.venv/bin/python server.py
"""
import argparse
import os
import platform
import subprocess
import sys
import shutil
from pathlib import Path

# ============ 路径 ============
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
VENV_DIR = BACKEND_DIR / ".venv"

# 关键依赖 (从 backend/server.py / predictor.py / dynamic_factors.py / weights_schema.py 提取)
REQUIRED = [
    "fastapi",
    "uvicorn",
    "scikit-optimize",
]

# 镜像源
MIRROR_TSINGHUA = "https://pypi.tuna.tsinghua.edu.cn/simple"
MIRROR_ALIYUN = "https://mirrors.aliyun.com/pypi/simple/"


# ============ 颜色输出 (Windows cmd 也支持) ============
class C:
    """颜色, 自动降级"""
    if sys.platform == "win32":
        try:
            import colorama  # type: ignore
            colorama.init()
        except ImportError:
            pass

    R = "\033[0;31m"
    G = "\033[0;32m"
    Y = "\033[1;33m"
    B = "\033[0;34m"
    N = "\033[0m"


def info(msg: str) -> None:
    print(f"{C.B}>>>{C.N} {msg}")


def ok(msg: str) -> None:
    print(f"{C.G} √ {C.N} {msg}")


def warn(msg: str) -> None:
    print(f"{C.Y} ! {C.N} {msg}")


def err(msg: str) -> None:
    print(f"{C.R} X {C.N} {msg}", file=sys.stderr)


# ============ Python 检查 ============
def check_python() -> None:
    if sys.version_info < (3, 9):
        err(f"需要 Python 3.9+, 当前是 {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        err("装新版: https://www.python.org/downloads/")
        err("安装时务必勾 'Add Python to PATH'")
        sys.exit(1)
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


# ============ venv 处理 ============
def venv_python() -> Path:
    """venv 内的 python.exe / python3"""
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python3"


def venv_pip() -> list[str]:
    """venv 内 pip 调用命令"""
    py = venv_python()
    return [str(py), "-m", "pip"]


def create_venv() -> None:
    if VENV_DIR.exists():
        ok(f"venv 已存在: {VENV_DIR}")
        return

    info(f"创建 venv: {VENV_DIR}")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except subprocess.CalledProcessError as e:
        err(f"创建 venv 失败: {e}")
        err("可能是 Python 缺 venv 模块, 重新装 Python 时勾 'tcl/tk and IDLE'")
        sys.exit(1)
    ok("venv 创建完成")


# ============ 装依赖 ============
def check_venv_healthy() -> bool:
    """检查 venv 内是否所有关键包都能 import"""
    code = "import fastapi, uvicorn; from skopt import gp_minimize"
    try:
        subprocess.check_call(
            venv_pip()[:-1] + ["-c", code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def install_with_pip(extra_index: str | None, label: str) -> None:
    pip = venv_pip()
    cmd = pip + ["install", "--disable-pip-version-check", "--upgrade"]
    if extra_index:
        cmd += ["-i", extra_index]
    cmd += REQUIRED

    info(f"pip install ({label}): {' '.join(REQUIRED)}")
    try:
        subprocess.check_call(cmd, stdout=sys.stdout, stderr=sys.stderr)
        ok("依赖装好")
    except subprocess.CalledProcessError as e:
        err(f"pip install 失败: {e}")
        warn("可换源重试: 加 --tsinghua 或 --pypi")
        sys.exit(1)


def verify_imports() -> None:
    """装完验证 import 不报错"""
    info("验证依赖 import ...")
    code = (
        "import fastapi, uvicorn;"
        "from skopt import gp_minimize;"
        "print('fastapi', fastapi.__version__);"
        "print('uvicorn', uvicorn.__version__);"
        "print('skopt ok')"
    )
    try:
        out = subprocess.check_output(
            venv_pip()[:-1] + ["-c", code],
            stderr=subprocess.STDOUT,
        ).decode()
    except subprocess.CalledProcessError as e:
        err("依赖验证失败 (可能没装上):")
        print(e.output.decode())
        sys.exit(1)
    for line in out.strip().splitlines():
        ok(line)


# ============ Main ============
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mavis PDP 依赖安装脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--tsinghua", action="store_true", help="用清华源 (默认)")
    src.add_argument("--aliyun", action="store_true", help="用阿里云源")
    src.add_argument("--pypi", action="store_true", help="用官方 PyPI")
    parser.add_argument("--skip-venv", action="store_true", help="不创建 venv, 直接装到系统 Python")
    parser.add_argument("--force-install", action="store_true", help="强制重装依赖, 不跳过")
    args = parser.parse_args()

    print()
    print("==========================================")
    print("  Mavis PDP 依赖安装")
    print("==========================================")
    print()

    # 1. Python 检查
    info("检查 Python 版本...")
    check_python()
    print()

    # 2. 源选择
    if args.pypi:
        index_url = None
        label = "PyPI 官方源"
    elif args.aliyun:
        index_url = MIRROR_ALIYUN
        label = "阿里云源"
    else:
        index_url = MIRROR_TSINGHUA
        label = "清华源"
    info(f"使用 {label}")
    print()

    # 3. venv
    if args.skip_venv:
        warn("跳过 venv, 装到系统 Python (不推荐)")
        global venv_pip  # noqa: PLW0603
        venv_pip = lambda: [sys.executable, "-m", "pip"]  # type: ignore
        install_with_pip(index_url, label)
    else:
        info(f"项目根: {PROJECT_ROOT}")
        info(f"后端:   {BACKEND_DIR}")
        create_venv()
        print()
        # idempotency: 关键包都齐就跳过 pip install
        if args.force_install:
            install_with_pip(index_url, label)
            print()
            verify_imports()
        elif check_venv_healthy():
            ok("关键依赖已装, 跳过 pip install (加 --force-install 强制重装)")
        else:
            install_with_pip(index_url, label)
            print()
            verify_imports()

    # 4. 完成 + 启动提示
    print()
    print("==========================================")
    print(f" {C.G}装好了!{C.N}")
    print("==========================================")
    print()
    py = venv_python()
    print(f"  启动后端 (新开一个 cmd 窗口保持):")
    print(f"    cd /d \"{BACKEND_DIR}\"")
    print(f"    \"{py}\" server.py")
    print()
    print(f"  启动前端 (再开一个 cmd 窗口):")
    print(f"    cd /d \"{PROJECT_ROOT / '4_比赛预测'}\"")
    print(f"    \"{py}\" -m http.server 8080")
    print()
    print(f"  浏览器打开:")
    print(f"    http://localhost:8080/world_cup_2026_spa.html")
    print()
    if not args.skip_venv:
        # 跨电脑访问提示
        if sys.platform == "win32":
            print("  跨电脑访问: 双击 start_remote.bat (会自动放行 Windows 防火墙)")
        else:
            print("  跨电脑访问: ./start.sh 自动绑 0.0.0.0")
    print()
    print("  停止服务: 双击 stop.bat / ./stop.sh")
    print("==========================================")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        err("\n用户中断")
        sys.exit(130)
