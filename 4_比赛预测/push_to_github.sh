#!/bin/bash
# 推送 World Cup 2026 104 场预测到 GitHub 私密仓库
# 用法: ./push_to_github.sh <repo-name>
# 示例: ./push_to_github.sh world-cup-2026-prediction

set -e

REPO_NAME="${1:-world-cup-2026-prediction}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 准备推送 World Cup 2026 预测到 GitHub 私密仓库: $REPO_NAME"
echo ""

# 检查 gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ 缺少 GitHub CLI (gh)"
    echo ""
    echo "请先安装（一个命令搞定，1 分钟）:"
    echo "  brew install gh"
    echo "  gh auth login  # 弹浏览器 GitHub 授权页面"
    echo ""
    echo "或者用 git + GitHub token 方式:"
    echo "  1. 去 https://github.com/new 手动建一个空仓库 '$REPO_NAME' (Private)"
    echo "  2. 把这个脚本里 'gh repo create' 那行替换为手动 git push:"
    echo "     git remote add origin git@github.com:YOUR_NAME/$REPO_NAME.git"
    echo "     git push -u origin main"
    exit 1
fi

# 检查 git 认证
if ! gh auth status &> /dev/null; then
    echo "❌ GitHub 还没登录，请先: gh auth login"
    exit 1
fi

cd "$SCRIPT_DIR"

# 创建 git 仓库（如果还没有）
if [ ! -d ".git" ]; then
    echo "📦 初始化 git 仓库..."
    git init
    git config user.name "lixiaolong134"
    git config user.email "lixiaolong134@h-partners.com"
fi

# 创建 .gitignore（防止推送整个数据目录）
cat > .gitignore <<'EOF'
# 完整数据目录 (太大了，HTML 已经够)
../1_数据基础/
../2_数据补全/
../3_排名v2.0/
../5_算法/
data/
*.pyc
__pycache__/
.DS_Store
EOF

# 创建 README.md
cat > README.md <<'EOF'
# 🏆 2026 世界杯 104 场全预测 · Mavis PDP

> 默认参数下冠军：**🇵🇹 葡萄牙**（点球 4-3 战胜西班牙）

## 快速查看

双击打开 `world_cup_2026_bracket_v1.html` (844KB)，在浏览器中查看完整 104 场预测。

## 交互功能

- 点 home/away 队名 → 弹出该队小组赛 panel（含 4 维 λ 分解、球员 Top 5、教练对比）
- 点 32 强卡片 → 查看比赛详情
- 点 R16+ 弹框 → 触发 KO 比赛弹窗 + 4 维 λ 实时计算
- 点顶部「调权重」按钮 → 打开权重 UI，16 个算法系数实时调整

## 数据基础

- 48 强球员身价（基于 2026 年 5-6 月最新数据）
- 1248 名球员 + 教练 + FIFA 系数 + 场地 + 状态
- 14 个 X待核实 已全部 web search 真实核实（零估算）

## 算法：4 维加权 λ 模型 (v2.1)

- 位置分桶：FW=3 / MID=3 / DEF=4 / GK=1 (位置内 Top N)
- 球员权重：0.7 (球员) / 0.3 (教练)
- λ 公式：`λ_home = 1.3 + (attack_home - defense_away) × 1.5`
- 平局概率：15%
- 加时 λ：`0.3 × (1 + 实力差 × 0.3)` (强队加时多进)
- 点球大战：按 p_home_win / p_away_win 比例

## 文件清单

- `world_cup_2026_bracket_v1.html` - **核心交付物** (844KB)
- `world_cup_2026_all_104_predictions.csv` - 104 场全预测表 (25KB)
- `push_to_github.sh` - 这个推送脚本

## 隐私

🔒 仓库为 Private，仅授权人可访问。
EOF

# 添加文件
echo "📝 添加文件到 git..."
git add .
git status --short

# 提交
echo ""
echo "💾 提交..."
git commit -m "🏆 2026 世界杯 104 场全预测 v3 (默认参数) - 冠军: 葡萄牙

- 1248 球员数据审核完成 (14个 X待核实 全部 web search 核实)
- 4 维加权 λ 模型 (v2.1) - 位置分桶 + 加时点球
- 比赛预测: 葡萄牙点球 4-3 西班牙夺冠
- 关键路径: 土耳其点球淘汰巴西 / 葡萄牙点球淘汰英格兰 / 摩洛哥进 SF
- HTML 844KB 含 32 强卡片 + 104 modal + 调权重 UI"

# 创建远程仓库
echo ""
echo "🌐 创建 GitHub 私密仓库..."
if gh repo view "$REPO_NAME" &> /dev/null; then
    echo "  仓库已存在，跳过创建"
else
    gh repo create "$REPO_NAME" \
        --private \
        --description "🏆 2026 世界杯 104 场全预测 (Mavis PDP v2.1) - 冠军: 葡萄牙" \
        --source=. \
        --remote=origin \
        --push
    echo "✅ 仓库创建并推送完成"
    exit 0
fi

# 如果仓库已存在,只推送
git remote add origin "https://github.com/$(gh api user --jq .login)/$REPO_NAME.git" 2>/dev/null || true
git branch -M main
git push -u origin main

echo ""
echo "✅ 推送完成!"
echo "🔗 仓库地址: https://github.com/$(gh api user --jq .login)/$REPO_NAME"
