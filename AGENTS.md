# AGENTS.md — 2026 世界杯 48 强预测项目

> **目标读者**：未来接手本项目的 Mavis / 其他 AI agent session
> **最后更新**：2026-06-28（v2.3.6 - R16/QF/SF/Final 全链路配对按 FIFA 官方对阵图 + ranking 胜者填充）

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
> **最后更新**：2026-06-28（v2.3.6 - R16/QF/SF/Final 全链路配对按 FIFA 官方对阵图 + ranking 胜者填充）

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


## 10.6 v2.3.7 真实小组赛出线 → R32→Final 全链路真实化 (2026-06-28)

### 核心改动
小组赛已结束 (6/28 全部 72 场已踢), 用真实出线队做 R32→Final 预测, 配对严格按 FIFA 2026 官方对阵表.

### 数据接入
- **CSV 真实赛果覆盖**: `compute_predictions()` 现在读 `1_数据基础/match_results.csv` 自动覆盖 group 阶段 best_score → actual_score, 并按真实赛果算 group_standings → R32 配对
- **top_8_third 排序修正**: 旧版只按 pts 排, 现按 FIFA 规则 (pts → gd → gf → 字母), 否则 top 8 选错 (塞内加尔 I3 P4 GD+2 进 top 8 vs 韩国 A3 P3 GD-1 落选)
- **R32 配对硬编码**: `OFFICIAL_R32_PAIRS` 16 场按 (home_group, home_pos, away_group, away_pos) 严格按 FIFA 官方表 (来源: ESPN API 2026-06-28)
- **R16 配对修正**: 旧 `(0,1)(2,3)...` 错的, 现按 bracket 几何 + FIFA 真实表 (上半 M1-M3/M2-M5/M4-M6/M7-M8, 下半 M11-M12/M9-M10/M14-M16/M13-M15)
- **KO 日期**: 改用 `KO_SCHEDULE[stage][i]` 逐场精确表 (不再用 KO_DATES+KO_WEIGHTS 推算)
- **KO 球场/城市**: `KO_VENUES[stage][i]` 16 R32 + 8 R16 + 4 QF + 2 SF + 1 Final + 1 3RD 全部按 ESPN
- **KO actual_score 留 None**: 旧版把 best_score 当 actual_score → 进度条算 16/16 已完成; 现 KO 全 pending, winner/loser/best_score 保留用于显示预测

### frontend JS 也同步修正
- `simulateKnockout()`: R32 用 OFFICIAL_R32 + R16/QF/SF 用真实配对 (用户切 preset 时不再算错)
- `KO_SCHEDULE_BY_INDEX[12]`: "蒙特雷" → "瓜达卢佩" (Estadio BBVA 实际在 Nuevo León 州 Guadalupe 市, 不是 Monterrey)

### 备份
- `5_算法/all_104_predictions.json.bak_20260628_bracket` (v2.3.6 错配对版)
- `backend/predictor.py.bak_20260628` (v2.3.6 配对计算版)

### 预测结果 (v2.3.7 默认权重)
- **冠军**: 🇩🇪 德国 4-4 葡萄牙 (点球)
- **亚军**: 🇵🇹 葡萄牙
- **季军**: 🇳🇱 荷兰 4-4 阿根廷 (点球)

### KO 时间表 (北京时间)
- R32: 6/28 (1) + 6/29 (2) + 6/30 (3) + 7/1 (3) + 7/2 (3) + 7/3 (3) + 7/4 (1) = 16 场
- R16: 7/4 (2) + 7/5 (2) + 7/6 (2) + 7/7 (2) = 8 场
- QF: 7/9 + 7/10 + 7/11 (2) = 4 场
- SF: 7/14 + 7/15 = 2 场
- 3RD: 7/18, FINAL: 7/19

### 后续工作
- R32 真实赛果接入: 每场踢完跑 `python3 0_scripts/sync_match_results.py` (R32 走的是同样的 group → R32 链路, 改 sync 脚本覆盖 KO)
- 一旦 R32 真实赛果进入, 重算 R16 配对 + 重 build SPA


## 10.7 v2.3.8 KO bracket 全链路顺读 + 日期/城市全量显示 (2026-07-01)

### 背景
v2.3.7 修完 KO 日期/城市错位后, 全局审查发现两个新问题:
1. **R32 卡片按 match_id 拼音排序** (localeCompare zh-CN) → 南非vs加拿大 显示在最上面, 但 FIFA bracket 应该是 M73 (A2vsB2) 在最上面
2. **R16/QF/SF/Final/3rd 卡片不显示日期和城市** → renderBracket 调用 renderMatchCard 时传 null, 但 KO_SCHEDULE_BY_MATCHID map 已有 R16/QF 数据, 只是没用上

### 修复
**位置:** `4_比赛预测/world_cup_2026_spa.html` `renderBracket()` (lines ~2740-2960)

1. **R32 顺序**: `computeActualR32()` 末尾删掉 `matches.sort((x, y) => x.match_id.localeCompare(y.match_id))`, 保持 R32_BRACKET 定义的 M73-M88 顺序
2. **R16/QF/SF 顺序**: 改成"按上一轮 bracket 几何位置排序" — 对每场比赛取两个参赛队伍在上一轮中的最小 idx, 小的排前. 这样保证上→下、上半→下半的顺读顺序
3. **KO 全链路日期/城市**: R16/QF 卡片从 `KO_SCHEDULE_BY_MATCHID[m.match_id]` 取, SF/Final/3rd 用新增的硬编码 SF_SCHEDULE/FINAL_SCHEDULE/THIRD_SCHEDULE (北京时间 UTC+8)
   - Final 北京时间 7月20日 03:00 (ET 7/19 15:00)
   - 3rd 北京时间 7月19日 09:00 (ET 7/18 21:00)

### 为什么不用 match_id 排序
zh-CN locale 的 `localeCompare` 按拼音排: ā → ào → bā → bā lā → bǐ → dé → ... 完全不是 bracket 几何顺序. 任何 sort by id 的方案都会偏离顺读布局.

### 验证
- 浏览器实测 32 张卡片顺序: R32 M73-M88 ✓, R16 M89-M96 ✓, QF M97-M100 ✓, SF M101-M102 ✓
- 所有 32 张卡片都显示 日期—城市
- console 无 error / warning
- 三档视口 (1280/768/390) 渲染正常, 5 列顺读


## 10.9 v2.4.1 手动对阵页 /bracket (2026-07-01)

### 核心改动
新增 `/bracket` 路由: Next.js 16 客户端组件, 7 列骨架图 (R32 → R16 → QF → SF → Final + 3rd) + 手动标记 + 播放动画.

### 交互
- **左键点击国旗 chip** = 标记该队晋级 (切换 winner, 自动推进到下一轮 home/away)
- **右键点击** = 退回 (清除该场手动标记, 恢复 JSON 默认 winner)
- **🔒 锁定**: `data_status === 'real'` 的场次 (已完赛) → 整张卡 `pointer-events: none` + 🔒 icon + Toast 提示
- **▶ 播放**: 0.5x/1x/2x 速度, 按 R32 → R16 → QF → SF → Final 顺序 reveal, 折线分阶段变橙色 (`is-active`)
- **↺ 重置**: 清空所有手动标记

### 几何布局
- 6 列固定列宽 (R32 200 / R16 200 / QF 200 / SF 200 / Final 220 / 3rd 180) + 5 gap × 20
- 16 row 等高 grid (`grid-template-rows: repeat(16, 1fr)`), `display: contents` 让 col-head + 比赛卡直接参与外层 grid
- 比赛卡 grid-row: R32 = `2+i / span 1`, R16 = `2+2j / span 2`, QF = `2+4k / span 4`, SF = `2+8l / span 8`, Final/3rd = `2 / span 16`
- SVG 折线 (R32→R16→QF→SF→Final + Final→3rd) 按列宽比例定位

### 文件
- `web/app/bracket/page.tsx` (40 行) - server component, 读 JSON
- `web/app/bracket/BracketClient.tsx` (~550 行) - 客户端: state + 派生 + 渲染
- `web/app/components/TabNav.tsx` 加 `🎯 手动对阵` Tab (第 5 个)
- `web/app/globals.css` +260 行 bracket 样式

### 启动
同 `web/`: `cd web && npx next start -p 3010` → http://localhost:3010/bracket

### 后续工作
- R32 真实赛果进入 CSV 后, 锁定逻辑自动生效 (data_status=real)
- 手动标记未持久化 (刷新页面丢失) - 如需持久化可加 localStorage

## 10.10 v2.4.2 /bracket1 视觉调优 — 中央列重排 + 连接线加粗 (2026-07-01)

### 背景
用户反馈: "你自己看看丑不丑，线对上了吗，左边半区跟右边半区为什么是错开的?"
3 个具体问题:
1. 奖杯 SVG 夹在 Final 和 3rd place 中间（语义错位 — 奖杯应该归属冠军 / 在底部装饰）
2. "26 FIFA WORLD CUP 2026" 文字标签卡在 Final 和 3rd 中间
3. SVG 连接线 stroke-width 仅 0.18 (非缩放) → 几乎不可见

### 修复

#### 中央列 6 个元素全部重排 (`web/app/globals.css` lines 1179-1184)
| 元素 | 旧 top | 新 top | 说明 |
|---|---|---|---|
| `.fiba-champion-title-wrap` | 2% | 3% | 略下移避 Header |
| `.fiba-final-wrap` | 22% | **14%** | 决赛靠近顶端 |
| `.fiba-bronze-label` | 68% | **27%** | 紧跟 Final 下方 |
| `.fiba-center-3rd` | 71% | **33%** | 紧跟 BRONZE FINAL 下方 |
| `.fiba-trophy-wrap` | 42% | **62%** | **下移到 3rd place 下方** |
| `.fiba-wc26-wrap` | 60% | **88%** | 沉底 |

视觉效果: Title → Final → BRONZE FINAL → 3rd → Trophy → Branding (自上而下读起来自然)

#### 连接线加粗 (`web/app/globals.css` lines 1129-1142)
- 默认态: `stroke-width: 0.18` → **1.2** (约 5x), `stroke` 透明度 0.5 → 0.75
- 激活态 (动画中): 1.6 → **2.4**, 加 drop-shadow (5px 橙色光晕)
- `vector-effect: non-scaling-stroke` 保留 → 拉伸到任意尺寸线宽都一致

#### SVG 折线坐标同步更新 (`web/app/bracket1/BracketClient.tsx` lines 732-733)
```
finalY: 22 → 14
thirdY: 71 → 33
```
跟 `.fiba-final-wrap` / `.fiba-center-3rd` 新位置对齐

### 验证
- 截图 `bracket1-final.png` (1400×1300 视口) 显示 6 个元素按预期顺序排列
- SVG `<polyline>` 默认态可见, is-active 动画态高亮橙色 + 发光
- Final → SF lower 长折线从 y=14 → y=76 (62% 垂直跨度), 不会被任何中央列卡片遮挡 (`x=midX(5)=64.5` 已在中央列右边界外)

### 为什么不重排 R32 几何
R32_UPPER_Y / R32_LOWER_Y 的 4 pair 等距分布 + 中间 SF gap 10% 已经是 FIFA 官方对阵图标准布局. 用户说的 "错开" 经实际计算 (R32_UPPER_Y=[0,6,14,20,28,34,42,48] centers=[3,17,31,45] 间隔 14; R32_LOWER_Y mirrors) 是镜像对称的, 视觉错位感源于线宽太细看不清 — 加粗后缓解.

## 10.8 v2.3.9 /bracket 手动对阵交互页 (2026-07-01)

### 背景
用户希望在 Next.js SPA 里加一个**手动对阵预测**页面（参考 FIFA 官方 9 列对阵图），左键点旗标晋级、右键退回、播放按钮动画。已存在 `web/app/bracket/BracketClient.tsx` 实现, 但有 2 个 bug 要修:

1. **Hydration mismatch**: `rawByStage` 对 R16/QF/SF/FINAL/3RD 走 `match_id.localeCompare(b)` 不带 locale — Node 默认 en_US 和浏览器 zh-CN 排序不同 → 服务器/客户端产出的 m.home/m.away 不同 → 旗子渲染顺序不同 → React hydration 报错 + 整页重渲染
2. **R32 → R16 顺序错位**: 即使顺序修了, 浏览器先按 en_US 排序再按 zh-CN 排还是会和 R32_BRACKET 几何位置对不齐

### 修复
**位置:** `web/app/bracket/BracketClient.tsx` lines 168-175

**改动**: `rawByStage` 不再对 R16/QF/SF/FINAL/3RD 排序, **直接保留 JSON 数组顺序** (`backend/predictor.py` 写入时已经按 FIFA R16-1..R16-8 / QF-1..QF-4 / SF-1..SF-2 顺序).

### 为什么这样 OK
JSON 数组顺序已经是 FIFA 官方对阵图顺序:
- R16[0..7] = 加拿大_vs_德国, 巴西_vs_挪威, 荷兰_vs_法国, ..., 瑞士_vs_阿根廷 (FIFA R16-1..R16-8)
- QF[0..3] = 德国_vs_巴西, 荷兰_vs_英格兰, 葡萄牙_vs_塞内加尔, 哥伦比亚_vs_阿根廷
- SF[0..1] = 德国_vs_荷兰, 葡萄牙_vs_阿根廷

cascade 配对索引 R16_PAIRING/QF_PAIRING/SF_PAIRING 已经写死邻接几何 (R16[i]=R32[2i]+R32[2i+1]), 所以保持 JSON 顺序 = 保持 bracket 几何顺序.

### 验证
- 浏览器实测 32 张旗子 (R32) + 16 张 (R16) + 8 张 (QF) + 4 张 (SF) + 2 张 (Final+3rd) = 64 旗子 ✓
- console 0 errors (hydration mismatch 修复)
- 左键点旗晋级 ✓, 右键 pair 退回 ✓, 播放按钮 0.5x/1x/2x 速度 ✓, 重置 ✓
- 已完赛锁定 (data_status='real' → 🔒, R32 现在全 pending 所以 0 锁定)


## 10.9 v2.4.0 Next.js 16 App Router 架构切换 (2026-06-28)

### 核心改动
单文件 HTML SPA (`world_cup_2026_spa_v237.html`) → Next.js 16 App Router 4 路由 SPA (`web/`)。

### 路由设计
- `/` ⚽ 球队 — 48 队 grid (锋/中/后/门/总评/综合 + 主帅)
- `/schedule` 📅 赛程 — 12 小组 A-L (绿底晋级 / 橙底第3 候选 + 全部 72 场)
- `/config` 🎛️ 配置 — 23 系数滑块 + 6 preset
- `/predict` 🏆 预测 — 完整 104 场 (R32→Final) + 进度条 + 决赛横幅

### 数据流
- **Server Component** 直读 `5_算法/*.json` (fs.readFile, 不依赖 FastAPI)
- **Client Component** 调 FastAPI (8766) + 静态 JSON fallback
- 两套数据源: `app/lib/data.ts` (server) + `app/lib/api.ts` (client)
- `.env.local` 切换: `NEXT_PUBLIC_DATA_SOURCE=static` / `BACKEND_URL=...`

### 启动
```bash
cd web
./start.sh prod      # 端口 3010 (8765/3000 被 video-prompt-builder 占)
./start.sh dev       # Turbopack dev 模式
./start.sh stop      # 停服务
```

### 技术栈
- Next.js 16.2.9 (Turbopack) + React 19.2.4
- TypeScript 严格模式 + ESLint
- 纯 vanilla CSS (globals.css) + 暗色主题 + 响应式 ≤768/≤480 断点
- 无 UI 库依赖, 无 Tailwind, 无 styled-components

### 文件结构
```
web/
├── app/
│   ├── layout.tsx        (Header + TabNav)
│   ├── page.tsx          (球队 /)
│   ├── schedule/page.tsx (赛程)
│   ├── config/{page,ConfigClient}.tsx (配置 server+client)
│   ├── predict/page.tsx  (预测)
│   ├── components/{Header,TabNav}.tsx
│   ├── lib/{api,data,flag,types}.ts
│   └── globals.css       (375 行, 含响应式)
├── public/static-data/   (client fallback JSON)
├── start.sh              (一键启动/停止)
├── next.config.ts        (outputFileTracingRoot 修 lockfile 警告)
├── package.json
└── .env.local
```

### 验证
- ✅ `npm run build` 5 路由全编译 (3.3s)
- ✅ 4 路由 HTTP 200 + Playwright 截图视觉验证
- ✅ 配置页 23 滑块 + 6 preset 渲染正常
- ✅ 预测页 32 场 KO 卡片 + 进度条 + 决赛金边全到位

### 部署
- 数据源切换: 改 `.env.local` 的 `NEXT_PUBLIC_BACKEND_URL` 即对接 FastAPI
- Vercel 部署: `web/` 作为 root, build cmd 留空 (Next 自动检测)

### 后续工作
- 搜索/对比/复盘 4 个 Tab (用户暂时没要, 等指示)
- 深色/亮色主题切换 (Header 加 toggle)
- PWA manifest (添加桌面图标)

## 11. 已知 TODO（未来 session 可推进）

- 8 个非种子队（苏格兰/威尔士/乌克兰等）FIFA 排名需补全
- 真实赛事数据接入（现在都是预测）
- KO 卡片悬停 tooltip（已有 modal，可加 hover）
- PWA manifest（添加桌面图标）
- 加时/点球分配按 4 维 λ 差（强队加时占优）

---

## 12. v23 算法 - 轮次桶 + sit_lambda（2026-07-06 完成）

**背景**: v11 (whw2.5) 在 31 场 audit 24/31 (77.4%) 是 overfit, 真实 52 场只有 33/52 (63.5%)。v23 解决第 2 轮"生死战"被错误推平的问题, 引入末轮"形势系数"。

**核心架构**:
- 轮次桶: 第 1 轮 (试探, db=3.0) / 第 2 轮 (生死战, db=1.0) / 第 3 轮 (末轮 + sit_lambda, db=1.5)
- sit_lambda: 5 桶末轮形势系数
  - `safe` ≥6p → λ × 0.88 (主力轮休)
  - `hot` 3-5p gd≥0 → λ × 1.12 (争 TOP 2)
  - `edge` 3-5p gd<0 → λ × 1.18 (拼净胜球)
  - `alive` 1-2p gd≥-2 → λ × 1.08 (还有第 3 名机会)
  - `dead` → λ × 0.92 (大势已去)
- 末轮 tag 用**本场日期前**积分 (避免含本场完赛积分)

**最终成绩 (小组赛 72 场, 2026-07-06 全部完赛)**:

| 轮次 | 正确 | 正确率 |
|---|---|---|
| 第 1 轮 (24 场) | 18 | 75% |
| 第 2 轮 (24 场) | 18 | 75% |
| 末轮 (24 场) | 12 | 50% |
| **总计 72 场** | **48** | **66.7%** |
| vs v11 baseline 33/52 | - | **+3.2%** |

**末轮 12 场错分归因**:
- **末轮平局漏判** 5 场 (42%): 巴拉圭 0-0 澳大利亚, 日本 1-1 瑞典, 阿尔及利亚 3-3 奥地利, 哥伦比亚 0-0 葡萄牙, 埃及 1-1 伊朗
- **alive 主场爆冷** 4 场 (33%): 南非 1-0 韩国, 厄瓜多尔 2-1 德国, 捷克 0-3 墨西哥, 克罗地亚 2-1 加纳
- **强主轻敌** 2 场 (17%): 挪威 1-4 法国, 苏格兰 0-3 巴西
- **其他** 1 场 (8%)

**末轮 75% 错分是"末轮平局" + "alive 主场爆冷"** — 完美符合用户洞察"48 强扩容后第 3 名也晋级, 弱队不绝望, 强队轻敌". 这两类算法难以完全预测.

**v24 设计方向** (待实现):
- `weak_home_bonus`: alive 主队末轮 +5% (针对 33% alive 主场爆冷错分)
- `dead_team_relax`: dead 队再 -10% (针对 17% 强主轻敌错分)
- KO 阶段适配: draw_boost × 0.5 (KO 加时+点球大部分会分胜负)

**关键脚本**:
- `0_scripts/v23_round_buckets.py` (外挂, 117 行)
- `4_比赛预测/predictions_v23_full72.csv` (72 场预测)
- `4_比赛预测/v23_final_audit.html` (最终 audit 报告)
- `5_算法/situational_lambda_v1.json` (形势系数)

**Bug 修复历史**:
- ET/BJT 时区错位: collector 抓 ET 6/24 比赛但存为 6/24, 实际是 BJT 6/25 末轮 → 备份 `.bak_et_fix_20260625`, 修 6 场日期
- 末轮 tag 算错: 之前用"全部已完赛"积分 (含本场), 改为"本场前"积分
- match_results 重复: collector overwrite=True 覆盖修复版, 清理 + dedup

---

## 13. 联系上下文

- **用户邮箱**：`tlee4014@gmail.com`（GitHub 已配全局）
- **GitHub 账号**：`Henrytudor-lee`（SSH 协议）
- **GitHub 仓库**：`git@github.com:Henrytudor-lee/worldcup2026.git`（Private）
- **agent memory**：`/Users/garcia/.mavis/agents/mavis/memory/MEMORY.md`（跨项目经验）
- **user profile**：`/Users/garcia/.mavis/memory/user.md`（用户偏好）
