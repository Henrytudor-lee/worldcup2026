#!/usr/bin/env bash
# 停止 Mavis PDP 后端 + 前端 HTTP
# 用法: ./stop.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$SCRIPT_DIR/.run"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ ! -d "$RUN_DIR" ]; then
  echo -e "${YELLOW}⚠️  没找到 $RUN_DIR，似乎没启动过${NC}"
  exit 0
fi

stop_one() {
  local name=$1
  local pid_file="$RUN_DIR/${name}.pid"
  if [ -f "$pid_file" ]; then
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      echo "  停止 $name (PID $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
      echo -e "${GREEN}  ✅ $name 已停止${NC}"
    else
      echo "  $name 进程已不在运行"
    fi
    rm -f "$pid_file"
  fi
}

echo "🛑 停止 Mavis PDP 服务"
echo "================================"
stop_one backend
stop_one frontend
echo ""
echo -e "${GREEN}✅ 全部停止${NC}"
