#!/usr/bin/env bash
# 一键启动 Mavis PDP 后端 + 前端 HTTP
# 用法: ./start.sh
# 停止: ./stop.sh
set -e

# ====== 路径配置 ======
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/4_比赛预测"
RUN_DIR="$SCRIPT_DIR/.run"

BACKEND_PORT=8765
FRONTEND_PORT=8080
LOG_DIR="$RUN_DIR/logs"

mkdir -p "$RUN_DIR" "$LOG_DIR"

# ====== 颜色 ======
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ====== 检查端口 ======
check_port() {
  local port=$1
  if lsof -ti:"$port" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  端口 $port 已被占用${NC}"
    lsof -ti:"$port" | head -3 | while read pid; do
      echo "    PID $pid: $(ps -p "$pid" -o command= 2>/dev/null | head -c 80)"
    done
    echo ""
    read -p "  杀掉这些进程? [y/N] " yn
    case "$yn" in
      [Yy]*)
        lsof -ti:"$port" | xargs kill -9 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}  ✅ 端口 $port 已释放${NC}"
        ;;
      *)
        echo -e "${RED}  ❌ 启动中止，请手动清理端口 $port${NC}"
        exit 1
        ;;
    esac
  fi
}

# ====== 装依赖 ======
install_deps() {
  # v2.2.2 改: 用 venv 装依赖 (避免 PEP 668 + 装 skopt)
  if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo -e "${YELLOW}📦 创建 venv...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv .venv
    cd "$SCRIPT_DIR"
  fi
  source "$BACKEND_DIR/.venv/bin/activate"
  pip install fastapi uvicorn scikit-optimize 2>&1 | tail -3
  deactivate
}

# ====== 启动后端 ======
start_backend() {
  echo -e "${BLUE}🔧 启动后端 (FastAPI 端口 $BACKEND_PORT)...${NC}"
  cd "$BACKEND_DIR"
  # v2.2.2 改: 用 venv python (含 skopt)
  nohup .venv/bin/python3 server.py > "$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$RUN_DIR/backend.pid"
  cd "$SCRIPT_DIR"
  sleep 2
  if ! kill -0 "$(cat "$RUN_DIR/backend.pid")" 2>/dev/null; then
    echo -e "${RED}❌ 后端启动失败，看日志: $LOG_DIR/backend.log${NC}"
    tail -20 "$LOG_DIR/backend.log"
    exit 1
  fi
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$BACKEND_PORT/" 2>/dev/null | grep -q 200; then
    echo -e "${GREEN}  ✅ 后端就绪 http://localhost:$BACKEND_PORT${NC}"
  else
    echo -e "${YELLOW}  ⏳ 后端启动中... 看日志: tail -f $LOG_DIR/backend.log${NC}"
  fi
}

# ====== 启动前端 ======
start_frontend() {
  echo -e "${BLUE}🌐 启动前端 HTTP (端口 $FRONTEND_PORT)...${NC}"
  cd "$FRONTEND_DIR"
  nohup python3 -m http.server "$FRONTEND_PORT" > "$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$RUN_DIR/frontend.pid"
  cd "$SCRIPT_DIR"
  sleep 1
  if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$FRONTEND_PORT/world_cup_2026_spa.html" 2>/dev/null | grep -q 200; then
    echo -e "${GREEN}  ✅ 前端就绪 http://localhost:$FRONTEND_PORT/world_cup_2026_spa.html${NC}"
  fi
}

# ====== 主流程 ======
echo ""
echo "🚀 Mavis PDP 一键启动"
echo "================================"

# 装依赖
install_deps

# 检查端口
echo ""
echo "🔍 检查端口..."
check_port "$BACKEND_PORT"
check_port "$FRONTEND_PORT"

# 启动
echo ""
start_backend
echo ""
start_frontend

# 输出最终状态
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🎉 启动完成!${NC}"
echo ""
echo "  前端 (浏览器打开): http://localhost:$FRONTEND_PORT/world_cup_2026_spa.html"
echo "  后端 API:          http://localhost:$BACKEND_PORT/docs"
echo ""
echo "  PID 文件:   $RUN_DIR/*.pid"
echo "  日志:       $LOG_DIR/{backend,frontend}.log"
echo ""
echo "  停止服务:   ./stop.sh"
echo "  查看日志:   tail -f $LOG_DIR/backend.log"
echo "================================"
