# 球员评分大工程 - 新 Session Handoff

## 状态
- ✅ **MVP 验证完成** (2026-07-10): 法国 4-1 挪威 27 球员真实评分
- ⏳ **批量抓 103 场未开始** (2026-07-12 用户选 A 方案, 退出本 session, 新 session 加载 playwright)

## MVP 文件
- `4_比赛预测/player_ratings/france_norway.json` (5944B raw data)
- `4_比赛预测/player_ratings/france_norway_ratings.csv` (5453B, 27 行)
- `4_比赛预测/player_ratings/france_norway_ratings.html` (16KB 演示页面)

## 抓取方法 (MVP 已验证)
1. `browser_navigate` 到 `https://www.flashscoreusa.com/match/{game_id}/`
2. `browser_evaluate` 执行 JS:
   ```js
   const data = [...document.querySelectorAll('.participant__participantName')]
     .map(el => {
       const row = el.closest('[class*="row"]');
       const ratingEl = row?.querySelector('[class*="playerRating"]');
       const statsEls = row?.querySelectorAll('[class*="stat"]') || [];
       return {
         name: el.textContent.trim(),
         rating: ratingEl ? parseFloat(ratingEl.textContent) : null,
         pos: row?.querySelector('[class*="position"]')?.textContent.trim() || '',
         stats: [...statsEls].map(s => s.textContent.trim())
       };
     });
   return JSON.stringify({count: data.length, players: data});
   ```
3. 写入 `4_比赛预测/player_ratings/{date}_{home}_vs_{away}.json`
4. CSV 累计到 `1_数据基础/world_cup_player_ratings.csv`

## 关键文件参考
- `4_比赛预测/ko_tracker.html` v6 - FIFA 官方 16 强配对 (game_id 映射起点)
- `4_比赛预测/ko_tracker_data.json` - 24 场 KO 真实数据
- `1_数据基础/world_cup_2026_complete.csv` - 1248 球员主表 (join 锚点)

## 批次计划
1. **第一批**: 72 场小组赛 (3 组 / 6 场 / 6 天 = 36 轮 估 1.5h)
2. **第二批**: 16 场 R32 (估 20min)
3. **第三批**: 8 场 R16 + 4 场 QF + 2 场 SF + 1 场 Final (估 20min)
4. **排行榜**: 30min

## 排行榜页面规范
- 路径: `4_比赛预测/player_ratings_leaderboard.html`
- 默认过滤: 至少踢 3 场
- 排序: 平均评分降序
- 列: 排名 | 球员 | 国家队 | 位置 | 比赛数 | 平均分 | 最高分 | 最低分 | 关键表现
- 头部: 比赛阶段切换 tab (全部 / 小组赛 / R32 / R16 / QF / SF / Final)
- 国家过滤: 下拉框
- 整合 v23 算法预测 vs 真实表现

## 已建/已有
- ✅ 数据 schema: match_id, date, stage, team, player_en, pos_en, rating, stats_json, captured_at
- ✅ MVP HTML 单文件 (16KB) 演示
- ⏳ 待做: 批次抓取脚本, 排行榜生成器, 与 1_数据基础/world_cup_2026_complete.csv join
