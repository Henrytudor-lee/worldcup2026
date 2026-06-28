# AGENTS.md — 2026 世界杯 48 强预测项目

> **目标读者**：未来接手本项目的 Mavis / 其他 AI agent session
> **最后更新**：2026-06-28（v2.3.4 - 全部 72 场小组赛接入 + 6/28 ESPN summary 兜底抓取）

---

## 0. 项目业务流（用户最早期定下的，必须按顺序）

1. **数据采集**：查询世界杯所有参赛队伍 / 球员 / 教练 / 赛程 → 存为 CSV 表格
2. **数据审核**：核实所有数据准确性（零估算：查不到 = `X待核实`，绝不编造）
3. **后端服务器**：开发本地可启动的后端，跑预测算法
4. **前端页面**：开发 HTML web 前端，调用后端跑预测
5. **预测算法**：基于已有数据，参考所有可能影响比赛的因素——球员身价/赛季数据/年龄/奖项、教练水平/风格/生涯奖项、比赛当天的天气/海拔等
6. **用户交互**：用户通过前端查看预测，并**自由调整影响因子的系数大小**来控制预测结果更新

**关键设计原则**：用户对算法的 23 个系数有**完全控制权**——UI 滑块改完要能立即在客户端/服务端重算并刷新预测。

### 0.1 架构决策（2026-06-11 与用户确认）

- **后端为主**：本地启动的后端进程（Python）跑预测算法，**直接读取 CSV**（不再走 `players_data_v21.json` 中间文件）。
- **接口调用**：前端 HTML 通过 HTTP fetch 调用后端接口 → 后端跑算法 → 返回 JSON 数据 → 前端渲染。
- **实时重算**：方案 A——用户拖系数滑块 → 前端 fetch `/predict?weights=...` → 后端用新系数重算 104 场 → 返回 → 前端刷新。
- **数据时效**：以**用户告知的截止日期**为准（当前为 2026-06-11），后续要更新用户会说。
- **算法因子清单**（用户确认不再扩展）：
  - 球员：身价 / 赛季数据 / 年龄 / 奖项
  - 教练：水平 / 风格 / 生涯奖项
  - 场地：天气 / 海拔

### 0.2 当前架构现状（v4.2 SPA，2026-06-10）

- 前端离线模式：`build_spa.py` 把 4 个 JSON **嵌入** HTML，**浏览器 JS 跑算法**
- 23 系数在前端 JS 中生效，但**不调任何后端**
- 缺失：HTTP 后端 / CSV 实时读取 / 接口契约 / `weights` 入参 → 重算管线

### 0.3 架构升级 v2.1（2026-06-12，后端驱动）

**新架构**：
- 新增 `backend/` 子目录：FastAPI 4 个接口（`/api/ranking` `/api/predictions` `/api/players` `/api/weights/default`）
- 前端 v2.1：`build_spa_v2.py` 不再嵌入 JSON，HTML 启动时 fetch 4 个接口
- weights 入参走 query string，**前端调系数 → 后端真重算 104 场**
- 启动流程：`cd backend && python3 server.py`（8765 端口）→ `cd 4_比赛预测 && python3 -m http.server 8080` → 浏览器开 8080

**踩坑（必看）**：
- **schema 范围 vs preset 数值要同步**：preset 写 `who_bonus_base=10` 但 schema 卡 `[5.0, 8.0]` → 切 preset 就 400。**改 preset 数值前先 grep `weights_schema.py` 的 `RANGES`**；改 RANGES 也要回头检查所有 preset 是不是还在范围内
- **前端 fetch 一定要 try/catch + alert**：weights 非法时 `rData.ranking` 是 undefined → 后续 `RANKING.map` 静默崩。runPrediction 函数已经加防御（response.ok 检查 + 弹窗）
- **FastAPI 默认端口 8000，本项目用 8765**（避免和前端 HTTP 8080 冲突 + 历史约定）
> **项目**：2026 美加墨世界杯 48 队实力排名 + 104 场（72 小组 + 32 淘汰）预测 → 后端驱动 SPA + 23 系数实时可调 + FastAPI 重算管线
> **最后更新**：2026-06-28（v2.3.4 - 全部 72 场小组赛接入 + 6/28 ESPN summary 兜底抓取）

---

## 1. 30 秒上手

```bash
cd /Users/garcia/Desktop/WorldCup2026

# 看工程记忆 (本文件)
cat AGENTS.md

# 跑起来
cd 4_比赛预测 && python3 build_spa.py      # 生成 SPA
python3 -m http.server 8765                 # 浏览器开 http://localhost:8765/world_cup_2026_spa.html

# 推 GitHub
cd 4_比赛预测 && ./push_to_github.sh        # 或手动 git add/commit/push
```

**主交付物**：`4_比赛预测/world_cup_2026_spa.html`（1.05MB 单文件离线可跑，66 场真实赛果 + 38 场待定）
**GitHub**：`git@github.com:Henrytudor-lee/worldcup2026.git`（Private，HEAD = `45e15d2`）

---

## 2. 用户核心偏好（必看，做错了会被打回）

### 2.1 数据态度（**硬性要求**）
- **零估算原则**：查不到 = 标 `X待核实`，**绝不编造**。14 个 X待核实已全部 web search 核实。
- **主表 `国家队进球` 字段不动**（已修复字段错乱，但用户多次强调）
- **修复前先备份** `.csv.bakDATE`，Edit 工具逐个改，不一次大改

### 2.2 视觉态度
- **HTML 优先** PNG/Word（自带交互 + 邮件附件友好）
- **可调权重模式** — 16 个算法系数抽到 `weights_v21.json` + UI 滑块
- **国旗 + 组别排名** 必带（emoji + A1/B2 格式）
- **响应式适配**（≤768px 平板 + ≤480px 手机两个断点）

### 2.3 Bracket 阅读方向（关键）
**默认顺读 5 列**（用户对镜像布局敏感，跳跃 1 次就被指出）：
- R32 16 场按 #1-#16 从上到下顺序（**上面 8 场 + 下面 8 场**）
- 后续 R16/QF/SF 同样按顺序（上半 + 下半）
- **决赛在中央正中间**，**季军赛紧贴决赛下方**
- 眼睛扫描路径 Z 字形（从左上到右下）

用户没主动说"按 FIFA 官方"就用顺读；要镜像等用户主动说。

### 2.4 沟通风格
- 中文为主 / 微信 + Mavis 双通道
- 务实 / 不绕弯 / 喜欢"做"或"停"
- 深度算法思辨：用户从"逻辑漏洞"角度质疑，每质疑推版本升级
- 关键决策用 `ask_user` 弹确认
- 微信 1-2 句简短回复；"提交代码" "继续" 也要直接执行不啰嗦

---

## 3. 项目结构（v2.3.2 后端驱动 + 2026-06-27 清理后）

```
WorldCup2026/
├── AGENTS.md                                 ← 本文件（工程记忆）
├── README.md                                 ← 项目入口
├── README_WINDOWS.md                         ← Windows 启动指南
├── CLAUDE.md                                 ← Claude 会话说明
├── start.sh / stop.sh                        ← Mac 启动/停止
├── start.bat / stop.bat / start_remote.bat   ← Windows 启动/停止
│
├── 1_数据基础/                               ← 数据源（11 CSV，git 跟踪）
│   ├── world_cup_2026_complete.csv              ⭐ 球员主表 1248 行 × 17 列
│   ├── world_cup_2026_coaches.csv               教练 48 行
│   ├── world_cup_2026_fifa_ranking.csv          FIFA 排名 48 行
│   ├── world_cup_2026_group_schedule.csv        赛程 72 场
│   ├── match_results.csv                         真实比赛结果（v2.3 接入）
│   ├── match_team_stats.csv                      赛事队伍统计
│   ├── match_player_stats.csv                    赛事球员统计
│   ├── match_events.csv                          赛事事件（进球/红黄牌）
│   ├── player_availability.csv                   球员可用性
│   ├── player_index.csv                          球员索引（build_player_index 产物）
│   ├── player_match_master.csv                   球员-比赛主表
│   └── lottery_odds_live.json                    实时赔率（odds_fetcher 用）
│
├── 4_比赛预测/                               ← 主战场
│   ├── world_cup_2026_spa.html                  ⭐⭐ 主交付物（1.4MB SPA v2.3）
│   ├── world_cup_2026_all_104_predictions.csv   104 场预测 CSV
│   └── README.md                                本目录说明
│
├── 5_算法/                                   ← 算法数据（6 JSON，git 跟踪）
│   ├── ranking_v20.json                         排名 JSON（嵌入 SPA）
│   ├── all_104_predictions.json                 104 场 JSON（嵌入 SPA）
│   ├── players_data_v22.json                    1248 球员 JSON（嵌入 SPA）
│   ├── weights_v21.json                         23 系数 v21（build_spa.py 用）
│   ├── weights_v22.json                         23 系数 v22（backend server.py 用）
│   └── situational_lambda_v1.json                场地 λ 因子
│
├── backend/                                  ← FastAPI 后端（v2.1 升级）
│   ├── server.py                                ⭐ 主入口（端口 8765，13 个 API）
│   ├── predictor.py                             ⭐ 算法包装层（接受 weights）
│   ├── weights_schema.py                        ⭐ 23 系数 schema + 6 preset
│   ├── dynamic_factors.py                       ⭐ 30+ 动态因子（教练/球员 bio + 阵型）
│   ├── round2_predictor.py                      淘汰赛二轮预测
│   ├── betting_strategy.py                      价值投注策略
│   ├── odds_fetcher.py                          实时赔率抓取
│   ├── scrape_lottery_odds.js                   赔率抓取脚本（被 odds_fetcher 调用）
│   └── README.md                                后端启动文档
│
├── 0_scripts/                                ← 数据抓取/校核/报告工具
│   ├── build_spa.py                             ⭐ SPA 生成器（从 5_算法/ 嵌入数据）
│   ├── ranking_v2.py                            ⭐ 排名生成器（CLI）
│   ├── scrape_fbref.py                          fbref 数据抓取
│   ├── scrape_fbref_playwright.py               fbref Playwright 抓取
│   ├── batch_worker6_build.py                   数据批处理
│   ├── run_md2_preds.py / gen_md2_html.py       MD 预测工具
│   ├── verify_croatia.py / verify_croatia_batch2/3.py  克罗地亚数据校核
│   ├── fbref_match_urls.json                    fbref URL 列表
│   ├── check_env.bat / install_deps.py          跨平台环境工具
│   └── push_to_github.sh                        Git 推送脚本
│
├── 6_审核报告/                                ← 审核产物
│   ├── group_standings.html                     小组赛排行榜
│   ├── round2_predictions.html                  淘汰赛二轮预测
│   ├── fbref_validation_2026-06-26.md           fbref 验证
│   └── field_audit/                             字段审计
│
├── 审核日志/                                   ← 审核批次记录
└── _to_delete_2026_06_27/                     ← ⚠️ 待清理暂存（55MB）
    ├── 根目录_PNG/                            48 个 Playwright 截图
    ├── 0_中间产物/                             早期预测中间产物
    ├── 0_scripts/                              28 个死代码脚本
    ├── 0_scripts_fbref_raw/                    fbref 抓取 raw JSON
    ├── 1_数据基础/                              age 补全脚本 + audit + ranking csv
    ├── 1_数据基础_0_scripts/                    1_数据基础/0_scripts 子目录
    ├── 1_数据基础_bak_files/                    *.bak* 备份 12 个
    ├── 1_数据基础_espn_match_data/              ESPN 抓取 29MB
    ├── 4_比赛预测/                              30+ 老 reports/HTML/JSON
    ├── 5_算法/                                  calibration_*.json
    ├── backend/                                 （空）
    ├── node_modules_etc/                        （空）
    └── 4_比赛预测_bak_etc/                      （空）
```

**文件数对比**：
- 清理前：~150 个文件，~80MB
- 清理后：~80 个核心文件，~25MB（项目目录）
- 备份暂存：55MB（`_to_delete_2026_06_27/`）

**清理原则（2026-06-27 适用）**：
- ✅ 删：无任何引用的死代码、未跟踪的中间产物、过时的 backup/report
- ✅ 删：被 `.gitignore` exclude 的临时文件
- ⏸️ 暂留：被 git tracked 但已无引用的 backend/ 模块（git history 可恢复，不贸然删）
- ⏸️ 暂留：`_to_delete_2026_06_27/` 暂存备份 → 用户确认无价值后再 `rm -rf`

**已确认活跃模块（清点时引用追踪）**：
- `0_scripts/build_spa.py` ← 4_比赛预测/world_cup_2026_spa.html 主生成器
- `0_scripts/ranking_v2.py` ← 排名 CLI（被 build_spa 调用）
- `backend/server.py` ← 7 个活跃 backend 模块主入口
- `backend/{predictor,dynamic_factors,weights_schema,round2_predictor,betting_strategy,odds_fetcher}.py`
- `backend/scrape_lottery_odds.js` ← odds_fetcher 调用

---

## 4. 核心算法 Mavis PDP v2.1

### 4.1 命名
**Mavis PDP** = **Mavis Positional Dixon-Coles Poisson**（位置化 Dixon-Coles 泊松模型）

### 4.2 4-3-3 位置分桶（v8 终版）
每队按位置取 Top N 球员（**避免混合 Top N 误判**）：
- 锋线 FW Top 5 / 中场 MID Top 5 / 后卫 DEF Top 6 / 门将 GK Top 1 = 17 人

### 4.3 评分公式（球员维度）
```
player_score =
  base_factor × (FW 1.0 / MID 0.85 / DEF 0.7 / GK 0.5)
  + g_per_goal × 赛季进球
  + a_per_assist × 赛季助攻
  + who_bonus_base / (max_who - 球员who)  (WhoScored 评分)
  + intl_g_per_goal × 国家队进球
  + intl_a_per_assist × 国家队助攻
  + honors × 冠军
  + jersey_bonus × 主力号码加权
```

### 4.4 教练评分
- 5 届+ 世界杯/欧洲杯 = +50
- 世界杯冠军 +50 / 亚军 +30 / 4 强 +15
- 欧洲杯冠军 +40 / 欧国联冠军 +25 / 欧冠冠军 +30
- 欧青赛冠军 +10/项 / 奥运金牌 +15

### 4.5 4 维 λ（关键升级）
```
λ_home_attack  = fw × 1.0 + mid × 0.7  (主控球)
λ_home_defense = def × 0.6 + gk × 0.4 (主防守)

λ_home_score = 1.4 + (λ_home_attack - λ_away_defense) × 1.5
λ_away_score = 1.4 + (λ_away_attack - λ_home_defense) × 1.5
```

**关键**：λ 必须是 4 维对位（不是总分差），否则评分大幅领先却打点球爆冷。

### 4.6 23 系数（weights_v21.json）
6 分类：`position_top_n` / `status_weights` / `nat_intl` / `def_gk_weights` / `player_to_total` / `smoothing`

### 4.7 6 个预设 (PRESETS)
| key | 名称 | 特点 |
|---|---|---|
| `default` | 默认（均衡） | 4-3-3 标准 |
| `high_value` | 身价优先 💰 | Top N 加权 + 状态权重下调 |
| `high_form` | 状态优先 🔥 | 进球/助攻权重高 + 防守加权 |
| `low_value` | 低身价 📉 | 反身价，鼓励黑马 |
| `coach_heavy` | 教练为王 👔 | player 0.30 / coach 0.70 |
| `balance_343` | 3-4-3 阵型 ⚔️ | FW 5 / MID 3 / DEF 3 |

---

## 5. SPA v4.2 架构

```
world_cup_2026_spa.html (564KB)
├── 6 Tab
│   ├── ⚽ 球队 (48 队卡片 grid)
│   ├── 📅 赛程 (72 场小组赛详情)
│   ├── 🎛️ 配置 (23 系数滑块 + 6 预设 + 重排按钮)
│   ├── 🏆 预测 (KO bracket + 上下半区小组赛)
│   ├── 🆚 对比 (两队 4 维 λ 横向)
│   └── 🔍 搜索 (全局球员/球队/比赛)
├── CSS @media（≤768 平板 + ≤480 手机）
│   ├── 平板：3 列 Tab / Stat 卡 3 列
│   └── 手机：2 列 Tab / Stat 卡 2 列 / KO 卡片 95px
└── JS（无依赖，纯 vanilla）
    ├── PREDICTIONS / RANKING / PLAYERS / WEIGHTS（嵌入 JSON）
    ├── renderBracket()  ← 顺读 5 列 + 上下半区居中
    ├── renderUpperGroups() / renderLowerGroups()
    ├── playMatch(h, a)  ← 蒙特卡洛模拟
    ├── openTeamDetail() / openMatchDetail()  ← 弹窗
    └── 全局搜索 + 暗色/亮色主题切换
```

### 5.1 KO 卡片视觉（v4.2 终版）
- **左色条**：胜者 3px 绿 / 败者 3px 灰 / 决赛金 / 季军铜
- **胜者态**：绿色加粗 + 比分绿底绿字 + 排名绿底 chip
- **败者态**：灰色 + 删除线 + opacity 0.65
- **点球徽章**：金色 chip + "点" 字
- **决赛卡**：金色立体边框 + 🏆 emoji 置顶 + F I N A L letter-spacing 3px
- **季军赛**：铜色边框 + 🥉 奖牌 + B R O N Z E 标签

### 5.2 KO 几何（顺读 5 列）
```
y[0..7]   = 上半 R32 8 场（密铺）
y[8..11]  = 上半 R16 4 场（每对 R32 中点）
y[12..13] = 上半 QF 2 场
y[14]     = 上半 SF 1 场
y[15..22] = 下半 R32 8 场（密铺）
y[23..26] = 下半 R16 4 场
y[27..28] = 下半 QF 2 场
y[29]     = 下半 SF 1 场
决赛 y = (y[14] + y[29]) / 2  ← 中央居中
```

---

## 6. 当前预测（v2.1 默认权重）

| 排名 | 球队 | 评分 |
|---|---|---|
| 1 | 英格兰 | 98.86 |
| 2 | 西班牙 | 98.84 |
| 3 | 法国 | 98.71 |
| 4 | 葡萄牙 | 98.48 |
| 5 | 阿根廷 | 98.44 |
| 6 | 巴西 | 98.42 |
| 7 | 挪威 | 98.33 |
| 8 | 德国 | 98.04 |

**冠军**：🇵🇹 葡萄牙 4-3 🇪🇸 西班牙（点球大战）  
**季军**：🇳🇴 挪威 3-2 🇲🇦 摩洛哥

**关键事实**：
- 凯恩 51 场 61 球超贝利 78 球 → 英格兰超西班牙第 1
- 姆巴佩 31 场 25 球西甲金靴 + 11 场 15 球欧冠
- C 罗 18 球 5 助但教练分低 → 葡萄牙仍可夺冠（4-3-3 阵型打法 + 高身价深度）

---

## 7. 数据完整性

| 字段 | 完整度 | 来源 |
|---|---|---|
| 球员身价/位置/俱乐部 | 100% | 德转 Transfermarkt |
| 国家队 G/A | 100% | 德转 |
| 2025-26 出场 | 52% | 17 个并行 web_search |
| 2025-26 进球 | 49% | OneFootball/Sofascore/ESPN |
| 2025-26 助攻 | 38% | 同上 |
| WhoScored 评分 | 27% | Top 8 队 + 关键球员精确 |

**重要**：查不到的字段全部标 `X待核实`，零估算。

---

## 8. 已踩过的坑（避免重蹈覆辙）

1. **关键词 substring 匹配**：bio 写"U-20 世青赛冠军"会被 `if "世界杯冠军" in text` 误触发 → 用 regex word-boundary 或改写 bio
2. **批量填充隐藏坑**：同队球员共享同一号码 + 替补 0/0 占位会覆盖真实数据 → 没有依据就留空 + X待核实
3. **4 维分桶但 λ 只看总分**：评分分维度但 λ 用总分差，会出现评分大幅领先却打点球爆冷 → λ 必须 4 维对位
4. **bracket 镜像布局**：用户连续 3 次强调顺读，**第 1 次做镜像就被打回**
5. **重复 const 声明**：JS 重构时 svgDefs 声明两次导致 ReferenceError，console 才能看到
6. **教练 substring 误伤**："塔"匹配成"塔利亚菲科"等 → 改用 word-boundary 或在 bio 改写
7. **教练字段漏写**（西班牙漏"欧洲杯冠军 2024"导致 0 分）→ 加多项兜底（欧国联/欧青赛/奥运）

---

## 9. 修改 checklist（每次改前过一遍）

1. ✅ **数据**：只读 CSV，编辑前 `cp .csv .csv.bakDATE`
2. ✅ **算法**：改 `5_算法/ranking_v2.py` → 跑 → 重生成 4 个 JSON
3. ✅ **生成**：跑 `python3 build_spa.py` 重新生成 HTML
4. ✅ **验证**：`python3 -m http.server 8765` + Playwright 截图 3 视口（桌面 1280/平板 768/手机 390）
5. ✅ **提交**：`git add . && git commit -m "..." && git push origin main`
6. ✅ **记录**：本文件 `AGENTS.md` 跟着更新

---

## 10. 常见任务速查

### 加 1 个国家数据
1. `1_数据基础/world_cup_2026_complete.csv` 加 26 行（按现有格式）
2. `1_数据基础/world_cup_2026_fifa_ranking.csv` 加 1 行
3. 跑 `5_算法/ranking_v2.py` 重新生成排名
4. 跑 `python3 build_spa.py` 重生成 HTML

### 改 1 个权重系数
1. 改 `5_算法/weights_v21.json`
2. 跑 `python3 build_spa.py`
3. UI 滑块会自动跟着变（运行时 JS 加载）

### 调 KO 卡片宽度
- 改 `4_比赛预测/build_spa.py` 中 `renderBracket()` 函数开头的 vw 断点
- 三档：vw≤480 / ≤768 / >768

### 改响应式断点
- CSS @media 在 `build_spa.py` 末尾（搜索 `📱 移动端响应式`）
- 同步改 `build_spa.py` 中 `renderBracket` 的 vw 判断

---

## 10.5 v2.3.3 真实赛果接入（2026-06-28）

### 数据真实化
- **新增** `0_scripts/sync_match_results.py`：把 `match_results.csv` 真实赛果覆盖到 `5_算法/all_104_predictions.json`
  - 72 场小组赛（66 场已踢 + 6 场 J/K/L 6/28 未踢）：data_status = `real` / `pending`
  - R32/R16/QF/SF/Final 32 场：actual_score + winner/loser 全部清空，标 `pending`
- **修复** build_spa.py 误覆盖 bug：原来用 `home_away` key 覆盖会误伤 R32 同名配对 → 改为只在 `stage === 'group'` 时覆盖
- **数据快照**（2026-06-28 16:00）：
  - 66 场真实赛果 / 38 场待定
  - 8 个最佳第 3 名（FIFA 规则 pts→gd→gf）：韩国 3(-1) / 苏格兰 3(-3) / 巴拉圭 4(-2) / 厄瓜多尔 4(0) / 瑞典 4(0) / 伊朗 3(0) / 塞内加尔 3(+2) / 阿尔及利亚 3(-2)
  - **伊朗真实：3 战 3 平 0 失球 3 分 0 净胜，意外地挤进最佳第 3 第 6 位** ✅

### KO 卡片显示升级
- **新增** KO 阶段进度条（6 个：小组赛 / R32 / R16 / QF / SF / 决赛）
  - 当前 66/72 小组赛（绿），0/16 R32（橙），0/8 R16（紫），0/4 QF（蓝），0/2 SF（粉），0/1 决赛（金）
- **新增** 状态徽章：✅ real（真实赛果，绿底白字）/ 🕐 pending（待定，灰底虚线）
- **CSS 新增类**：`.ko-progress` `.ko-progress-item` `.status-badge` `.status-pending` `.status-real`
- **响应式**：移动端进度条每行 100% 宽度（≤600px 断点）

### 备份
- `5_算法/all_104_predictions.json.bak_20260628`（sync 前 76KB → sync 后 80KB）
- `0_scripts/build_spa.py.bak_20260628`（含 build_spa 修复前版本）

### 后续工作
- R32 真实数据接入：每场比赛结束后手动跑 `python3 sync_match_results.py`（已写好脚本可重复跑）
- 一旦 R32/R16 真实赛果进入 CSV，sync 脚本会自动识别并更新进度条 + 状态徽章

## 11. 已知 TODO（未来 session 可推进）

- 8 个非种子队（苏格兰/威尔士/乌克兰等）FIFA 排名需补全
- 真实赛事数据接入（现在都是预测）
- KO 卡片悬停 tooltip（已有 modal，可加 hover）
- PWA manifest（添加桌面图标）
- 加时/点球分配按 4 维 λ 差（强队加时占优）

---

## 12. 联系上下文

- **用户邮箱**：`tlee4014@gmail.com`（GitHub 已配全局）
- **GitHub 账号**：`Henrytudor-lee`（SSH 协议）
- **GitHub 仓库**：`git@github.com:Henrytudor-lee/worldcup2026.git`（Private）
- **agent memory**：`/Users/garcia/.mavis/agents/mavis/memory/MEMORY.md`（跨项目经验）
- **user profile**：`/Users/garcia/.mavis/memory/user.md`（用户偏好）
