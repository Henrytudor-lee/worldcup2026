#!/usr/bin/env bash
# 一键启动 Next.js 16 SPA（球队/赛程/配置/预测 4 路由）
# Usage: ./start.sh [dev|prod|stop]  (默认 dev，端口 3010)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${PORT:-3010}"
MODE="${1:-dev}"

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

start_dev() {
  stop_server
  echo "🚀 启动 dev 模式 (Turbopack HMR) · 端口 $PORT"
  nohup npx next dev --port "$PORT" > "$LOG" 2>&1 &
  echo $! > "$PID_FILE"
}

start_prod() {
  stop_server
  echo "📦 启动 prod 模式 · 端口 $PORT"
  if [ ! -f ".next/BUILD_ID" ]; then
    echo "  ⚙️ 首次运行，先 build (跳过 type-check + eslint 用 next.config.ts)..."
    if ! npx next build 2>&1 | tail -20; then
      echo "❌ build 失败, 自动回退到 dev 模式"
      start_dev
      return
    fi
  fi
  nohup npx next start -p "$PORT" > "$LOG" 2>&1 &
  echo $! > "$PID_FILE"
}

case "$MODE" in
  stop)
    stop_server
    echo "✅ 已停止"
    exit 0
    ;;
  dev)
    start_dev
    ;;
  prod)
    start_prod
    ;;
  *)
    echo "Usage: $0 [dev|prod|stop]"
    exit 1
    ;;
esac

sleep 5
if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" 2>/dev/null | grep -q 200; then
  echo "✅ 服务已就绪 → http://localhost:$PORT"
  echo "   · 球队:   http://localhost:$PORT/"
  echo "   · 赛程:   http://localhost:$PORT/schedule"
  echo "   · 配置:   http://localhost:$PORT/config"
  echo "   · 预测:   http://localhost:$PORT/predict"
  echo "   · PID:    $(cat $PID_FILE)"
  echo "   · 日志:   $LOG"
else
  echo "❌ 启动失败，查看日志: tail -f $LOG"
  tail -20 "$LOG" 2>/dev/null
  exit 1
fi
