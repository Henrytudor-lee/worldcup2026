#!/usr/bin/env bash
# 一键部署到 Vercel: 复制 SPA → git commit → git push → 等待 Vercel 自动部署
# 用法:
#   ./deploy.sh                              # 仅同步 SPA + vercel.json + deploy.sh
#   ./deploy.sh "更新伊朗比分"                # 自定义 commit msg
#   ./deploy.sh --all                        # git add -A（包含所有其他改动）
#   ./deploy.sh --skip-spa "fix typo"         # 跳过 SPA 复制
#   ./deploy.sh --dry-run                     # 不真 push，只预览
set -e

# ====== 路径配置 ======
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SPA_SRC="$SCRIPT_DIR/4_比赛预测/world_cup_2026_spa.html"
SPA_DST="$SCRIPT_DIR/public/index.html"
REMOTE="origin"
BRANCH="main"

# ====== 颜色 ======
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ====== 参数 ======
SKIP_SPA=0
DRY_RUN=0
ADD_ALL=0
CUSTOM_MSG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-spa)   SKIP_SPA=1; shift ;;
    --all)        ADD_ALL=1; shift ;;
    --dry-run)    DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '2,15p' "$0"
      exit 0
      ;;
    *)
      CUSTOM_MSG="$1"
      shift
      ;;
  esac
done

# ====== 工具函数 ======
step()  { echo -e "\n${BLUE}▶ $1${NC}"; }
ok()    { echo -e "${GREEN}✓ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
err()   { echo -e "${RED}✗ $1${NC}"; exit 1; }
info()  { echo -e "${CYAN}  $1${NC}"; }

# ====== 1. 同步 SPA ======
if [[ $SKIP_SPA -eq 0 ]]; then
  step "1/5 同步 SPA → public/index.html"
  if [[ ! -f "$SPA_SRC" ]]; then
    err "找不到 $SPA_SRC\n  → 先跑 python3 0_scripts/build_spa.py 生成 SPA"
  fi
  SIZE_SRC=$(wc -c < "$SPA_SRC" | tr -d ' ')
  SIZE_DST=$(wc -c < "$SPA_DST" 2>/dev/null | tr -d ' ' || echo 0)
  if [[ "$SIZE_SRC" == "$SIZE_DST" ]]; then
    info "SPA 大小未变 (${SIZE_SRC} bytes)，跳过复制"
  else
    cp "$SPA_SRC" "$SPA_DST"
    ok "已复制 ${SIZE_SRC} bytes (旧 ${SIZE_DST} bytes)"
  fi
else
  step "1/5 跳过 SPA 复制 (--skip-spa)"
fi

# ====== 2. Git 状态检查 ======
step "2/5 检查 git 状态"
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  err "当前目录不是 git 仓库"
fi

# 决定要 stage 哪些文件
if [[ $ADD_ALL -eq 1 ]]; then
  STAGE_CMD="git add -A"
  STAGE_DESC="所有变更 (--all)"
else
  # 默认只 stage 部署相关文件
  STAGE_CMD="git add public/index.html vercel.json deploy.sh"
  STAGE_DESC="仅部署相关文件 (public/index.html + vercel.json + deploy.sh)"
fi

# 先看其他文件状态（不 stage）
OTHER_MODIFIED=$(git diff --name-only)
OTHER_UNTRACKED=$(git ls-files --others --exclude-standard | grep -vE "(public/index\.html|vercel\.json|deploy\.sh)$" || true)

# ====== 3. 预览 ======
echo -e "  ${CYAN}本次提交策略: ${STAGE_DESC}${NC}"
echo ""
echo -e "  ${CYAN}将 stage:${NC}"
echo -e "    + public/index.html"

# Dry-run 时把改动列完整
if [[ $DRY_RUN -eq 1 ]]; then
  eval "$STAGE_CMD" > /dev/null 2>&1 || true
  STAGED=$(git diff --cached --name-only)
  if [[ -n "$STAGED" ]]; then
    echo "$STAGED" | sed 's/^/    + /'
  fi
  if [[ -n "$OTHER_MODIFIED" ]] && [[ $ADD_ALL -eq 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}未 stage 的已修改文件 (用 --all 包含):${NC}"
    echo "$OTHER_MODIFIED" | sed 's/^/    M /'
  fi
  if [[ -n "$OTHER_UNTRACKED" ]] && [[ $ADD_ALL -eq 0 ]]; then
    echo ""
    echo -e "  ${YELLOW}未 stage 的未跟踪文件 (用 --all 包含):${NC}"
    echo "$OTHER_UNTRACKED" | sed 's/^/    ? /'
  fi
  warn "DRY RUN 模式：不提交、不 push"
  exit 0
fi

# 询问是否真提交
if [[ -n "$OTHER_MODIFIED" ]] || [[ -n "$OTHER_UNTRACKED" ]]; then
  COUNT_M=$(echo "$OTHER_MODIFIED" | grep -c . || true)
  COUNT_U=$(echo "$OTHER_UNTRACKED" | grep -c . || true)
  warn "工作区还有 ${COUNT_M} 个修改 + ${COUNT_U} 个未跟踪文件未包含"
  info "用 ./deploy.sh --all 一次性包含；或先 git commit 那些再 ./deploy.sh"
  echo ""
fi

read -r -p "$(echo -e ${YELLOW}"按 Enter 继续提交，其他键取消: "${NC})" CONT
if [[ -n "$CONT" ]]; then
  err "用户取消"
fi

# ====== 4. Stage + commit ======
step "3/5 git commit"
eval "$STAGE_CMD"
STAGED=$(git diff --cached --name-only)
if [[ -z "$STAGED" ]]; then
  warn "没有可提交的内容（部署文件无变化）"
  info "强制空 commit 触发 Vercel 重部署吗？Ctrl+C 取消"
  read -r _
  CUSTOM_MSG="${CUSTOM_MSG:-chore: 触发 Vercel 重新部署}"
  git commit --allow-empty -m "$CUSTOM_MSG"
  ok "已创建空 commit"
else
  ok "已 stage $(echo "$STAGED" | wc -l | tr -d ' ') 个文件"
  if [[ -z "$CUSTOM_MSG" ]]; then
    CUSTOM_MSG="📦 build: 重生成 SPA 部署到 Vercel ($(date +%Y-%m-%d))"
  fi
  git commit -m "$CUSTOM_MSG"
  ok "已 commit: $CUSTOM_MSG"
fi

# ====== 5. Push ======
step "4/5 git push $REMOTE $BRANCH"
git push "$REMOTE" "$BRANCH"
ok "推送完成"

# ====== 6. 等待 Vercel 部署 ======
step "5/5 Vercel 自动部署"
info "等待 8 秒让 Vercel webhook 触发 + 构建..."
sleep 8

DEPLOY=$(vercel ls world-cup-2026 2>/dev/null | grep -oE "dpl_[A-Za-z0-9]+" | head -1 || echo "")
if [[ -n "$DEPLOY" ]]; then
  STATE=$(vercel inspect "$DEPLOY" 2>/dev/null | grep "status" | head -1 | grep -oE "Ready|Building|Error|Queued" || echo "Unknown")
  URL=$(vercel inspect "$DEPLOY" 2>/dev/null | grep -E "^\s+url" | awk '{print $2}' | head -1)
  case "$STATE" in
    Ready)    ok "部署完成 ✅" ;;
    Building) warn "构建中（去 dashboard 查看: https://vercel.com/garcialees-projects/world-cup-2026）" ;;
    Error)    err "部署失败，看 dashboard 日志" ;;
    *)        warn "状态: $STATE" ;;
  esac
  [[ -n "$URL" ]] && info "最新 deployment: $URL"
else
  warn "未获取到 deployment，去 dashboard 查看"
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 部署完成${NC}"
echo -e "${GREEN}   https://worldcup-2026v.vercel.app${NC}"
echo -e "${GREEN}══════════════════════════════════════${NC}"
