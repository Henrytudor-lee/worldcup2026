# 🏆 2026 世界杯 48 强预测 · Mavis PDP v2.1

> **Mavis PDP** = **Mavis Positional Dixon-Coles Poisson**（位置化 Dixon-Coles 泊松模型）
>
> 48 队实力排名 + 104 场（72 小组 + 32 淘汰）全预测 · 后端驱动 + 客户端 SPA + 23 系数实时可调

## ⚡ 快速启动（30 秒）

```bash
# 终端 1：启动后端 (FastAPI, 端口 8765)
cd backend && pip3 install fastapi uvicorn --break-system-packages && python3 server.py

# 终端 2：启动前端 HTTP 服务 (端口 8080)
cd 4_比赛预测 && python3 -m http.server 8080

# 浏览器
open http://localhost:8080/world_cup_2026_spa.html
```

## 🏗️ 架构

```
WorldCup2026/
├── AGENTS.md                   ← 工程记忆（必读）
├── README.md                   ← 本文件
├── .gitignore                  ← 排除 1_数据基础/ 整个目录
│
├── 1_数据基础/                  ⭐ 数据源（4 CSV，仅本地，不进 git）
│   ├── world_cup_2026_complete.csv          1248 球员主表
│   ├── world_cup_2026_coaches.csv           48 教练
│   ├── world_cup_2026_fifa_ranking.csv      FIFA 排名
│   └── world_cup_2026_group_schedule.csv    72 场小组赛
│
├── backend/                    ⭐ FastAPI 后端（v2.1 新增）
│   ├── server.py               4 个接口
│   ├── predictor.py            算法包装层（接受 weights）
│   ├── weights_schema.py       23 系数 schema + 6 preset
│   └── README.md               启动文档
│
├── 4_比赛预测/                 ⭐ 主战场
│   ├── world_cup_2026_spa.html 主交付物（81KB，调后端）
│   ├── build_spa_v2.py         SPA 生成器（v2.1 fetch 版）
│   ├── build_spa.py            SPA 生成器（v2.0 嵌入 JSON 版，已停用）
│   └── push_to_github.sh       推送脚本（兼容）
│
└── 5_算法/                     算法复现工具
    ├── ranking_v2.py           排名 CLI 工具
    ├── ranking_v20.json        最新排名
    ├── all_104_predictions.json 最新 104 场预测
    └── players_data_v22.json   1248 球员数据
```

## 🌐 后端 API（4 接口）

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/api/ranking?weights=...` | 48 队排名 |
| `GET` | `/api/predictions?weights=...` | 104 场预测 + 决赛 + 季军 + 小组排名 |
| `GET` | `/api/players?team=...` | 1248 球员（按国家过滤） |
| `GET` | `/api/weights/default` | 23 系数默认值 |
| `GET` | `/api/weights/presets` | 6 个 preset (default/high_value/high_form/low_value/coach_heavy/balance_343) |

**weights 入参**：JSON 字符串（`encodeURIComponent(JSON.stringify(weights))`）或 preset 名（`coach_heavy`）

## 📊 前端 SPA 6 Tab

1. **⚽ 球队** — 48 队卡片 + 详情 modal
2. **📅 赛程** — 72 场小组赛 + 详情
3. **🎛️ 配置** — 23 系数滑块 + 6 preset + "开始预测"按钮
4. **🏆 预测** — 顺读 5 列 KO bracket + 上下半区小组赛
5. **🆚 对比** — 两队 4 维 λ 横向对比
6. **🔍 搜索** — 全局球员/球队/比赛

## 🧠 算法 (Mavis PDP v2.1)

### 4-3-3 位置分桶
- 锋线 FW Top N / 中场 MID Top N / 后卫 DEF Top N / 门将 GK Top 1
- 避免"混合 Top N"误判（前锋身价高把中场也填成前锋）

### λ 公式（4 维对位）
```
λ_home_attack  = fw × 1.0 + mid × 0.7  (主控球)
λ_home_defense = def × 0.6 + gk × 0.4 (主防守)

λ_home_score = 1.3 + (λ_home_attack - λ_away_defense) × 1.5
λ_away_score = 1.3 + (λ_away_attack - λ_home_defense) × 1.5
```

### 23 系数（6 区块 + 适应度）
- `position_top_n` (4) · `status_weights` (4) · `nat_intl` (2) · `def_gk_weights` (3) · `player_to_total` (2) · `smoothing` (3)
- `venue_weights` (4) —— 海拔阈值/客队高原惩罚/高温阈值/高温双方惩罚
- `venue_adaptation_weight` (1) —— 球员适应度调节强度 (0=关闭, 1=全生效)

### 球员场地适应度
每个联赛标"典型主场位置"（海拔+6月均温），计算球员对比赛场地的适应度 (0~1)：
- `adaptation = 1.0 - 0.5*tanh(海拔差/1500) - 0.4*tanh(温度差/10)`
- 客队 venue_coef 按适应度调节：适应=1.0 → 无惩罚, 适应=0.0 → 原惩罚
- 适应度高的球队（如墨超球员在墨西哥城）几乎不受高原惩罚
- 适应度低的球队（如北欧球员在沙漠）受更重惩罚

## 🏆 KO 淘汰赛时间表（FIFA 2026 官方）

| 阶段 | 日期 | 场次/天 |
|---|---|---|
| 32 强 (R32) | 6/30 - 7/3 | 每天 4 场 (4 天) |
| 16 强 (R16) | 7/6 - 7/7 | 每天 4 场 |
| 8 强 (QF) | 7/10 - 7/11 | 每天 2 场 |
| 半决赛 (SF) | 7/14 - 7/15 | 每天 1 场 |
| 季军赛 | 7/18 | 1 场 |
| 决赛 | 7/19 | 1 场 |

**R32 排序规则**（保证眼睛扫描连贯）：
- 上半 M1-M8：A1, B1, ..., H1 各 1 场，配 (B2/D2/F2/H2) + 4 个最强第 3
- 下半 M9-M16：I1, J1, K1, L1 + 剩余 4 个第 3 + 上半未用第 2 名
- R16 配对严格 R32[i] + R32[i+1] 胜者 → 眼睛扫到 R32 胜者立刻知道会进 R16 哪个位置

## 🔧 数据完整性

- **零估算原则**：查不到 = `X待核实`，绝不编造
- 1248 球员主表全部 2025-26 赛季最新数据
- 截止日期：**2026-06-11**

## 📜 协议

- **Mavis**: MIT
- **数据**: 用户私有（基于公开数据 + 用户审核）
- **GitHub**: Private (Henrytudor-lee/worldcup2026)

## 🔗 相关链接

- 工程记忆：`AGENTS.md`（必读）
- 后端文档：`backend/README.md`
- 前端代码：`4_比赛预测/world_cup_2026_spa.html`（单文件 HTML）
