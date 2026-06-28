#!/usr/bin/env bash
# 一键启动 Next.js 16 SPA（球队/赛程/配置/预测 4 路由）
# Usage: ./start.sh [dev|prod|stop]  (默认 prod，端口 3010)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-3010}"
MODE="${1:-prod}"

LOG="/tmp/worldcup-next.log"
PID_FILE="/tmp/worldcup-next.pid"

stop_server() {
  if [ -f "$PID_FILE" ]; then
    local pid
    pid=$(cat "$PID_FILE")
    if ps -p "$pid" > /dev/null 2>&1; then
      echo "🛑 停止旧服务 PID=$pid"
      kill "$pid" 2>/dev/null || true
      sleep 1
    fi
    rm -f "$PID_FILE"
  fi
  pkill -f "next start.*$PORT" 2>/dev/null || true
  pkill -f "next dev.*$PORT" 2>/dev/null || true
  sleep 1
}

case "$MODE" in
  stop)
    stop_server
    echo "✅ 已停止"
    exit 0
    ;;
  dev)
    stop_server
    echo "🚀 启动 dev 模式 (Turbopack) · 端口 $PORT"
    nohup npx next dev --port "$PORT" > "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    ;;
  prod)
    stop_server
    echo "📦 启动 prod 模式 · 端口 $PORT"
    if [ ! -d ".next" ]; then
      echo "  ⚙️ 首次运行，先 build..."
      npm run build
    fi
    nohup npx next start -p "$PORT" > "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    ;;
  *)
    echo "Usage: $0 [dev|prod|stop]"
    exit 1
    ;;
esac

sleep 3
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" | grep -q 200; then
  echo "✅ 服务已就绪 → http://localhost:$PORT"
  echo "   · 球队:   http://localhost:$PORT/"
  echo "   · 赛程:   http://localhost:$PORT/schedule"
  echo "   · 配置:   http://localhost:$PORT/config"
  echo "   · 预测:   http://localhost:$PORT/predict"
  echo "   · PID:    $(cat $PID_FILE)"
  echo "   · 日志:   $LOG"
else
  echo "❌ 启动失败，查看日志: tail -f $LOG"
  tail -20 "$LOG"
  exit 1
fi
