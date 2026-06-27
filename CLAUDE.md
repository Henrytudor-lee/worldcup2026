# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目

**2026 世界杯 48 强预测** — 本地单 HTML SPA，48 队实力排名 + 104 场（72 小组 + 32 淘汰）全预测。
- 算法：**Mavis PDP v2.1**（Mavis Positional Dixon-Coles Poisson，4 维 λ 对位泊松）
- 用户可调 **23 个权重系数**（6 preset + UI 滑块），改完立即重算 104 场
- 数据源：`1_数据基础/` 4 个 CSV（球员 / 教练 / FIFA 排名 / 赛程），截止 2026-06-11

> **工程记忆**：[`AGENTS.md`](AGENTS.md) — 业务流、算法公式、踩坑清单、修改 checklist。**进任何工作前先读**。

## 快速启动

```bash
./start.sh        # Mac / Linux — 一键起后端 8765 + 前端 8080
./stop.sh

start.bat         # Windows — 本机
start_remote.bat  # Windows — 跨电脑（自动放行防火墙）
```

启动后浏览器打开（**必须 `http://`，`file://` 会被 fetch 拒绝 → 空白**）：
```
http://localhost:8080/world_cup_2026_spa.html
```

`start.sh` 首次运行会自动建 `backend/.venv` 并装 `fastapi uvicorn scikit-optimize`。手动启动：

```bash
cd backend && .venv/bin/python3 server.py
cd 4_比赛预测 && python3 -m http.server 8080
```

Swagger 文档：http://localhost:8765/docs

## 架构

```
浏览器 (SPA 4_比赛预测/world_cup_2026_spa.html)
    │ fetch http://localhost:8765/api/...
    ↓
FastAPI (backend/server.py, 端口 8765)
    │ predictor.compute_predictions(weights)
    ↓
1_数据基础/*.csv          ← 单一数据真相源
```

| 层 | 路径 | 角色 |
|---|---|---|
| 数据 | `1_数据基础/` | 4 个 CSV（git 内，clone 即跑） |
| 后端算法 | `backend/predictor.py` | Dixon-Coles 泊松 + 4 维 λ |
| 权重定义 | `backend/weights_schema.py` | 23 系数 schema + 范围校验 + 6 preset |
| 后端入口 | `backend/server.py` | FastAPI 4 个接口 |
| 前端交付物 | `4_比赛预测/world_cup_2026_spa.html` | 6 Tab + 顺读 5 列 KO bracket |
| SPA 生成器 | `0_scripts/build_spa.py` | 离线模式（嵌入 4 JSON，浏览器跑算法） |
| SPA 生成器 v2 | `0_scripts/build_spa_v2.py` | fetch 模式（实验性，server.py 已支持） |
| 派生 JSON | `5_算法/*.json` | `ranking_v20` / `all_104_predictions` / `players_data_v22` / `weights_v21` |
| 审核 | `审核日志/` + `6_审核报告/` | 球员数据人工核对 + 现场审计报告 |

**前端两种构建模式**：
- `build_spa.py`（**当前主用**）— 把 `5_算法/*.json` 嵌入 HTML，纯前端 JS 跑算法，零后端依赖
- `build_spa_v2.py`（实验性）— HTML 启动时 fetch 4 个后端接口，权重滑块 → 后端真重算

## 后端接口（8765）

| 方法 | 路径 | 用途 | 耗时 |
|---|---|---|---|
| GET | `/api/ranking?weights=...` | 48 队排名 | ~50ms |
| GET | `/api/predictions?weights=...` | 104 场 + 决赛 + 季军 + 小组排名 | ~50ms |
| GET | `/api/players?team=...` | 1248 球员（按国家过滤） | ~30ms |
| GET | `/api/weights/default` | 23 系数默认值 | <1ms |
| GET | `/api/weights/presets` | 6 preset 元数据 | <1ms |

`weights` 入参：JSON 字符串（`encodeURIComponent(JSON.stringify(w))`）或 preset 名（`default` / `high_value` / `high_form` / `low_value` / `coach_heavy` / `balance_343`）。

## 修改流水线

**改数据**（加国家 / 改球员字段）：
1. 编辑前先 `cp 1_数据基础/world_cup_2026_complete.csv .bakDATE`（AGENTS.md §2.1）
2. 跑 `python3 0_scripts/ranking_v2.py` 重生成 4 个 JSON 到 `5_算法/`
3. 跑 `python3 0_scripts/build_spa.py` 重生成 `4_比赛预测/world_cup_2026_spa.html`

**改权重默认值**：
- `5_算法/weights_v21.json` 改值 → `build_spa.py` 重生成
- **改 preset 数值前**先 grep `backend/weights_schema.py` 的 `RANGES`，确认在范围内
- **改 `RANGES` 也要回头**检查所有 preset 是不是还在范围内

**改 KO bracket 几何 / 响应式断点 / SPA 视觉**：
- 都在 `0_scripts/build_spa.py`（`renderBracket()` 函数 + 末尾 CSS @media）
- 三档断点：`vw≤480` / `≤768` / `>768`

**改后端接口**：
- `backend/server.py`（FastAPI 路由，447 行）
- `backend/predictor.py`（算法包装，1176 行）
- `backend/weights_schema.py`（schema + preset，222 行）

## 测试与验证

**无单元测试**。验证走 Playwright 截图三视口（桌面 1280 / 平板 768 / 手机 390）：
- `.playwright-mcp/` 缓存最近截图
- `package.json` 只有 `playwright` devDep，目前通过 MCP 工具手动跑

**未配置 linter**（Python / JS 都没有）。

## 硬性约束（违反就会被用户打回）

1. **零估算**：查不到的数据 = `X待核实`，**绝不编造**。AGENTS.md §2.1。
2. **必须用 `http://` 打开 SPA**：`file://` 浏览器禁止 fetch → 空白页。
3. **CSV 是单一真相源**（v2.1 之后）：算法直接读 `1_数据基础/*.csv`，不再走中间 JSON 文件（生成器产物除外）。
4. **schema 范围 vs preset 数值同步**：见上方「改权重默认值」。
5. **顺读 5 列 KO bracket**：用户对镜像布局敏感——第 1 次做镜像就被打回。决赛在中央正中间，季军赛紧贴下方。AGENTS.md §2.3 + §5.2。
6. **前端 fetch 必 try/catch + alert**：weights 非法时 `rData.ranking` undefined → 后续 `.map` 静默崩。

## 目录约定

`N_xxx/` 编号反映 AGENTS.md §0 业务流顺序：
- `1_数据基础` = 数据采集
- `4_比赛预测` = 前端主战场
- `5_算法` = 算法复现 + 派生 JSON
- `6_审核报告` = 数据审核
- `0_scripts` = 跨流程的脚本（构建 / 推送 / 诊断）
- `0_中间产物` / `审核日志` = 临时产物
- `2_数据补全` / `3_排名v2.0` 已精简删除（历史背景）
