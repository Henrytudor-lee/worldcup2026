# FBref 数据验证报告日期: 2026-06-27## 1. 完整性
- 比赛数: 60 (期望 60)
- 球队/场: {2: 60} (期望全是 2)
- 球员/场: {31: 12, 32: 39, 30: 7, 29: 1, 33: 1}
- GK/场: {2: 57, 3: 3}

## 2. 字段密度 (FBref player stats)
- 总行: 2015
| 字段 | 填充率 |
|------|--------|
| age | 100.0% |
| ast | 93.9% |
| crdr | 93.9% |
| crdy | 93.9% |
| crs | 93.9% |
| date | 100.0% |
| fld | 93.9% |
| fls | 93.9% |
| ga | 6.1% |
| gls | 93.9% |
| home_away | 100.0% |
| int | 93.9% |
| is_gk | 100.0% |
| jersey | 93.9% |
| match_id | 100.0% |
| min | 100.0% |
| off | 93.9% |
| og | 93.9% |
| pk | 93.9% |
| pkatt | 93.9% |
| player_en | 100.0% |
| pos | 93.9% |
| save_pct | 5.7% |
| saves | 6.1% |
| sh | 93.9% |
| sot | 93.9% |
| sota | 6.1% |
| source | 100.0% |
| team_cn | 100.0% |
| tklw | 93.9% |

## 3. 跨源得分一致性 (FBref 球员 gls + og 总和 vs ESPN team score)
- 直接一致 (gls 之和): 49/60 (81.7%)
- OG 计入后一致: 11
- 完全不一致 (非 OG 原因): 0

## 4. 抽样对账 — Turkey 3-2 USA
FBref 球员 gls > 0 的:

- home Barış Alper Yılmaz: gls=1 min=89
- home Kaan Ayhan: gls=1 min=3
- home Arda Güler: gls=1 min=90
- away Sebastian Berhalter: gls=1 min=90
- away Auston Trusty: gls=1 min=90

- 比分预期: 3-2 (用户修正)
- FBref 球员 gls 总和: Turkey 3 + USA 2 = 5 ✓

## 5. 输出文件清单

- ✓ `fbref_player_stats.csv` (262.8KB) — FBref 球员-赛事原始 (60 场 × ~33 行)
- ✓ `fbref_squad_advanced.csv` (10.7KB) — FBref 队级进阶统计 (48 队 × 108 字段)
- ✓ `player_match_master.csv` (1012.0KB) — 跨源合并主表 (2015 行 × 211 字段)
- ✓ `player_index.csv` (70.6KB) — 球员主索引 (1428 unique)

---

生成时间: 2026-06-27
