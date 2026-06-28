#!/usr/bin/env python3
"""
build_spa.py - 把所有数据和模板合成一个 SPA HTML
读取:
  - /backend/weights_schema.py (v2.2.4 source of truth) → DEFAULT + 6 PRESETS
  - /5_算法/ranking_v20.json
  - /5_算法/all_104_predictions.json
  - /5_算法/players_data_v22.json
输出:
  - /4_比赛预测/world_cup_2026_spa.html (单文件, 离线可跑)
v2.3.2 改: 权重从 weights_schema.py 读, 与后端同步 (修复 #2 #5)
"""

import json
import os
import sys

ROOT = "/Users/garcia/Desktop/WorldCup2026"
ALGO_DIR = f"{ROOT}/5_算法"
OUT_DIR = f"{ROOT}/4_比赛预测"
OUT_FILE = f"{OUT_DIR}/world_cup_2026_spa.html"

# v2.3.2: 从 weights_schema.py 读 (与后端 server.py 同源)
sys.path.insert(0, f"{ROOT}/backend")
from weights_schema import DEFAULT as WEIGHTS_DEFAULT, PRESETS as WEIGHTS_PRESETS

# ---------- 加载数据 ----------
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# v2.3.2: 改用 weights_schema.DEFAULT (与后端同步)
weights = WEIGHTS_DEFAULT
ranking = load_json(f"{ALGO_DIR}/ranking_v20.json")
predictions = load_json(f"{ALGO_DIR}/all_104_predictions.json")
players_data = load_json(f"{ALGO_DIR}/players_data_v22.json")["players"]

# v2.3.2: 把 PRESETS 也嵌入 (前端 6 个 preset 按钮)
weights_presets = {k: v["weights"] for k, v in WEIGHTS_PRESETS.items()}
weights_presets_meta = {k: v.get("label", k) for k, v in WEIGHTS_PRESETS.items()}

# ---------- 合并真实比赛结果 (从 match_results.csv) ----------
# v2.2.3+: predictor 把 best_score 当 actual_score, 必须用真实比分覆盖
# 未踢的比赛: actual_score = None, 标记 played = false
import csv
actual_results = {}
_match_csv = f"{ROOT}/1_数据基础/match_results.csv"
if os.path.exists(_match_csv):
    with open(_match_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = f"{row['home']}_vs_{row['away']}"
            actual_results[key] = {
                'date': row['date'],
                'home_score': int(row['home_score']),
                'away_score': int(row['away_score']),
            }

# ---------- 已完赛详情: team_stats / player_stats / events ----------
# 按 short match_id (home_vs_away) 索引, 给弹窗用
def _read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def _to_num(v):
    try: return float(v) if v not in (None, '', '—') else None
    except: return None

def _short_key(mid):
    """2026-06-11_墨西哥_vs_南非 → 墨西哥_vs_南非"""
    parts = mid.split('_vs_')
    if len(parts) == 2:
        home = parts[0].split('_', 1)[1] if '_' in parts[0] else parts[0]
        return f"{home}_vs_{parts[1]}"
    return mid

# team_stats: keyed by short match_id
team_stats_data = {}
for r in _read_csv(f"{ROOT}/1_数据基础/match_team_stats.csv"):
    k = _short_key(r['match_id'])
    # 只保留前端要的字段, 减小体积
    team_stats_data[k] = {
        'mid': k,
        'date': r['date'],
        'venue': r.get('venue', ''),
        'home': r['home_team_cn'],
        'away': r['away_team_cn'],
        'hs': int(r['home_score']) if r.get('home_score') else 0,
        'as': int(r['away_score']) if r.get('away_score') else 0,
        # 主队
        'h_poss': _to_num(r.get('home_possession_pct')),
        'h_shots': int(r.get('home_total_shots', 0) or 0),
        'h_sot': int(r.get('home_shots_on_target', 0) or 0),
        'h_corners': int(r.get('home_corners', 0) or 0),
        'h_fouls': int(r.get('home_fouls', 0) or 0),
        'h_yc': int(r.get('home_yellow_cards', 0) or 0),
        'h_rc': int(r.get('home_red_cards', 0) or 0),
        'h_off': int(r.get('home_offsides', 0) or 0),
        'h_saves': int(r.get('home_saves', 0) or 0),
        'h_pass': int(r.get('home_passes_total', 0) or 0),
        'h_pass_acc': int(r.get('home_passes_accurate', 0) or 0),
        'h_pass_pct': _to_num(r.get('home_pass_pct')),
        # 客队
        'a_poss': _to_num(r.get('away_possession_pct')),
        'a_shots': int(r.get('away_total_shots', 0) or 0),
        'a_sot': int(r.get('away_shots_on_target', 0) or 0),
        'a_corners': int(r.get('away_corners', 0) or 0),
        'a_fouls': int(r.get('away_fouls', 0) or 0),
        'a_yc': int(r.get('away_yellow_cards', 0) or 0),
        'a_rc': int(r.get('away_red_cards', 0) or 0),
        'a_off': int(r.get('away_offsides', 0) or 0),
        'a_saves': int(r.get('away_saves', 0) or 0),
        'a_pass': int(r.get('away_passes_total', 0) or 0),
        'a_pass_acc': int(r.get('away_passes_accurate', 0) or 0),
        'a_pass_pct': _to_num(r.get('away_pass_pct')),
    }

# player_stats: keyed by short match_id, {home: [...], away: [...]}
match_players_data = {}
for r in _read_csv(f"{ROOT}/1_数据基础/match_player_stats.csv"):
    k = _short_key(r['match_id'])
    if k not in match_players_data:
        match_players_data[k] = {'home': [], 'away': []}
    # 只保留要的字段
    pl = {
        'n': r.get('player_cn') or r.get('player_en', ''),
        'j': r.get('jersey', ''),
        'pos': r.get('position', ''),
        'starter': r.get('starter') == 'True',
        'sub_in': r.get('subbed_in') == 'True',
        'sub_out': r.get('subbed_out') == 'True',
        'min': int(r.get('minutes', 0) or 0),
        'g': int(r.get('goals', 0) or 0),
        'a': int(r.get('assists', 0) or 0),
        'shots': int(r.get('shots', 0) or 0),
        'sot': int(r.get('shots_on_target', 0) or 0),
        'yc': int(r.get('yellow_cards', 0) or 0),
        'rc': int(r.get('red_cards', 0) or 0),
        'og': int(r.get('own_goals', 0) or 0),
        'gc': int(r.get('goals_conceded', 0) or 0),
        'sv': int(r.get('saves', 0) or 0),
    }
    side = 'home' if r.get('home_away') == 'home' else 'away'
    match_players_data[k][side].append(pl)

# events: keyed by short match_id, sorted by clock
match_events_data = {}
for r in _read_csv(f"{ROOT}/1_数据基础/match_events.csv"):
    k = _short_key(r['match_id'])
    if k not in match_events_data:
        match_events_data[k] = []
    match_events_data[k].append({
        'clock': r.get('clock', ''),
        'type': r.get('event_type', ''),
        'team': r.get('team_cn', ''),
        'player': r.get('player_en', ''),
        'desc': r.get('description', ''),
    })
# 按时钟排序 (9', 17', 23', 49' ...)
def _clock_key(s):
    return int(s.split("'")[0]) if "'" in s else 0
for k in match_events_data:
    match_events_data[k].sort(key=lambda e: _clock_key(e['clock']))

print(f"赛事详情: {len(team_stats_data)} 场 team_stats / {len(match_players_data)} 场 player_stats / {len(match_events_data)} 场 events")

for p in predictions:
    # 只在小组赛阶段用 CSV 真实赛果覆盖 (避免 R32/R16/QF 等同名 key 误覆盖)
    if p.get('stage') != 'group':
        p['played'] = False  # R32 之后默认未踢
        continue
    key = f"{p['home']}_vs_{p['away']}"
    if key in actual_results:
        ar = actual_results[key]
        p['actual_score'] = f"{ar['home_score']}-{ar['away_score']}"
        p['home_pts'] = 3 if ar['home_score'] > ar['away_score'] else (1 if ar['home_score'] == ar['away_score'] else 0)
        p['away_pts'] = 3 if ar['away_score'] > ar['home_score'] else (1 if ar['home_score'] == ar['away_score'] else 0)
        p['played'] = True
    else:
        p['actual_score'] = None
        p['home_pts'] = None
        p['away_pts'] = None
        p['played'] = False

played_cnt = sum(1 for p in predictions if p['played'])
print(f"比赛结果合并: {played_cnt}/104 已踢 ({len(actual_results)} 条 CSV 记录)")

# ---------- 输出 ----------
os.makedirs(OUT_DIR, exist_ok=True)

# 把 4 个数据序列化进 HTML
# 注意: 玩家数据可能很大, 但 348KB 还是可以接受
weights_json = json.dumps(weights, ensure_ascii=False)
weights_presets_json = json.dumps(weights_presets, ensure_ascii=False)
weights_presets_meta_json = json.dumps(weights_presets_meta, ensure_ascii=False)
ranking_json = json.dumps(ranking, ensure_ascii=False)
predictions_json = json.dumps(predictions, ensure_ascii=False)
players_json = json.dumps(players_data, ensure_ascii=False)
team_stats_json = json.dumps(team_stats_data, ensure_ascii=False)
match_players_json = json.dumps(match_players_data, ensure_ascii=False)
match_events_json = json.dumps(match_events_data, ensure_ascii=False)

print(f"数据大小:")
print(f"  weights: {len(weights_json)/1024:.1f}KB")
print(f"  weights_presets: {len(weights_presets_json)/1024:.1f}KB ({len(weights_presets)} 个)")
print(f"  ranking: {len(ranking_json)/1024:.1f}KB")
print(f"  predictions: {len(predictions_json)/1024:.1f}KB (104 场)")
print(f"  players: {len(players_json)/1024:.1f}KB (48 队 1248 球员)")
print(f"  team_stats: {len(team_stats_json)/1024:.1f}KB ({len(team_stats_data)} 场)")
print(f"  match_players: {len(match_players_json)/1024:.1f}KB ({len(match_players_data)} 场)")
print(f"  match_events: {len(match_events_json)/1024:.1f}KB ({len(match_events_data)} 场)")

# ---------- HTML 模板 ----------
HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏆 2026 世界杯预测 · Mavis PDP v2.1</title>
<style>
:root {
  --bg: #0d1117;
  --bg-2: #161b22;
  --bg-3: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --text-2: #adbac7;
  --text-3: #7d8590;
  --accent: #f0883e;
  --accent-2: #58a6ff;
  --green: #3fb950;
  --red: #f85149;
  --gold: #ffd700;
  --silver: #c0c0c0;
  --bronze: #cd7f32;
}
[data-theme="light"] {
  --bg: #ffffff;
  --bg-2: #f6f8fa;
  --bg-3: #eaeef2;
  --border: #d0d7de;
  --text: #1f2328;
  --text-2: #59636e;
  --text-3: #818b98;
  --accent: #cf222e;
  --accent-2: #0969da;
  --green: #1a7f37;
  --red: #cf222e;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "Helvetica Neue", "PingFang SC", sans-serif; background: var(--bg); color: var(--text); padding: 0; transition: background 0.3s, color 0.3s; }
.app { max-width: 1700px; margin: 0 auto; padding: 20px; }
.top-bar { background: linear-gradient(90deg, #1f6feb 0%, #8957e5 100%); padding: 24px 32px; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }
.top-bar h1 { color: #fff; font-size: 24px; }
.top-bar .stats { display: flex; gap: 12px; flex-wrap: wrap; }
.stat { background: rgba(0,0,0,0.3); padding: 8px 14px; border-radius: 6px; }
.stat .label { font-size: 11px; color: #adbac7; }
.stat .value { font-size: 16px; font-weight: bold; color: #fff; margin-top: 2px; }
.stat.gold .value { color: var(--gold); }
.stat.silver .value { color: var(--silver); }
.stat.bronze .value { color: var(--bronze); }
.top-bar-actions { display: flex; gap: 8px; }
.top-bar-actions button { background: rgba(0,0,0,0.3); color: #fff; border: 1px solid rgba(255,255,255,0.2); padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.top-bar-actions button:hover { background: rgba(0,0,0,0.5); }
.tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 20px; overflow-x: auto; }
.tab { background: none; border: none; color: var(--text-2); padding: 12px 20px; cursor: pointer; font-size: 14px; font-weight: 500; border-bottom: 2px solid transparent; transition: all 0.2s; white-space: nowrap; }
.tab:hover { color: var(--text); background: var(--bg-2); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-content { display: none; }
.tab-content.active { display: block; }
.section-title { font-size: 18px; font-weight: bold; margin: 24px 0 12px; padding-bottom: 8px; border-bottom: 2px solid var(--accent); color: var(--accent); }
.muted { color: var(--text-3); font-size: 12px; }

/* ⚽ 球队 */
.teams-groups { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.group-card { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.group-header { background: linear-gradient(90deg, #1f6feb, #8957e5); color: #fff; padding: 6px 12px; border-radius: 4px; font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 14px; }
.team-card { display: flex; align-items: center; padding: 8px; border-radius: 4px; cursor: pointer; transition: background 0.2s; gap: 10px; }
.team-card:hover { background: var(--bg-3); }
.team-rank { color: var(--accent); font-weight: bold; min-width: 24px; }
.team-flag { font-size: 18px; }
.team-name { flex: 1; font-size: 14px; }
.team-rating { font-size: 12px; color: var(--text-3); }

/* 球队详情 Modal */
.modal-overlay { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); overflow: auto; }
.modal-overlay.open { display: flex; align-items: center; justify-content: center; }
.modal { background: var(--bg-2); border-radius: 12px; max-width: 1100px; width: 95%; max-height: 90vh; overflow: auto; padding: 24px; border: 1px solid var(--border); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.modal-close { background: none; border: none; color: var(--text-3); font-size: 24px; cursor: pointer; }
.modal-close:hover { color: var(--red); }
.tabs-mini { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--border); }
.tab-mini { background: none; border: none; color: var(--text-2); padding: 8px 14px; cursor: pointer; font-size: 13px; border-bottom: 2px solid transparent; }
.tab-mini.active { color: var(--accent); border-bottom-color: var(--accent); }

/* 📅 赛程 */
.schedule-tabs { display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }
.schedule-tab { background: var(--bg-2); border: 1px solid var(--border); color: var(--text); padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.schedule-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.schedule-list { display: grid; gap: 8px; }
.match-row { background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; display: grid; grid-template-columns: 100px 1fr 200px; gap: 12px; align-items: center; cursor: pointer; }
.match-row:hover { border-color: var(--accent-2); }
.match-row.unplayed { border: 2px dashed #58a6ff; background: linear-gradient(135deg, rgba(88,166,255,0.05), var(--bg-2)); }
.match-row.upcoming-soon { border: 2px solid #ff5722; background: linear-gradient(135deg, rgba(255,87,34,0.15), var(--bg-2)); animation: pulse-soon 2s ease-in-out infinite; }
@keyframes pulse-soon { 0%,100% { box-shadow: 0 0 0 0 rgba(255,87,34,0.4); } 50% { box-shadow: 0 0 0 6px rgba(255,87,34,0); } }
.match-row.upcoming-soon .match-date::after { content: ' ⏰'; color: #ff5722; font-weight: bold; }
.match-row.upcoming-tomorrow { border: 2px solid #ff9800; background: linear-gradient(135deg, rgba(255,152,0,0.12), var(--bg-2)); }
.match-row.upcoming-tomorrow .match-date::after { content: ' 📅'; color: #ff9800; font-weight: bold; }
.match-date { font-size: 12px; color: var(--text-3); }
.match-teams { font-size: 14px; display: flex; align-items: center; gap: 6px; }
.match-vs { color: var(--text-3); font-size: 11px; }
.match-meta { font-size: 12px; color: var(--text-2); text-align: right; }
.match-mini.unplayed { border-left: 3px solid #58a6ff; padding-left: 5px; }
.match-mini.upcoming-soon { border-left: 3px solid #ff5722; padding-left: 5px; background: linear-gradient(90deg, rgba(255,87,34,0.15), transparent); }
.match-mini.upcoming-tomorrow { border-left: 3px solid #ff9800; padding-left: 5px; background: linear-gradient(90deg, rgba(255,152,0,0.10), transparent); }

/* 🎛️ 配置 */
.config-layout { display: grid; grid-template-columns: 320px 1fr; gap: 20px; }
.config-panel { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.preset-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.preset-btn { background: var(--bg-3); border: 1px solid var(--border); color: var(--text); padding: 10px; border-radius: 6px; cursor: pointer; text-align: left; font-size: 13px; }
.preset-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }
.preset-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.slider-group { margin-bottom: 12px; }
.slider-group label { display: block; font-size: 12px; color: var(--text-2); margin-bottom: 4px; }
.slider-group .value { color: var(--accent); font-weight: bold; }
.slider-group input[type=range] { width: 100%; }
.config-action { display: flex; gap: 8px; margin-top: 16px; }
.btn { background: var(--accent); color: #fff; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; }
.btn:hover { filter: brightness(1.1); }
.btn-secondary { background: var(--bg-3); color: var(--text); }
.btn-secondary:hover { background: var(--accent); color: #fff; }

.preview-area { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 16px; min-height: 400px; }
.preview-rank-changed { background: rgba(248, 81, 73, 0.1); }
.preview-rank-up { color: var(--green); }
.preview-rank-down { color: var(--red); }

/* 🏆 预测 */
.bracket-container { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 16px; overflow-x: auto; }
.bracket-flow { display: flex; gap: 0; min-width: max-content; position: relative; }
.bracket-stage { min-width: 200px; position: relative; }
.bracket-stage h3 { font-size: 14px; color: var(--accent); margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border); text-align: center; }
.bracket-stage .stage-matches { display: flex; flex-direction: column; gap: 10px; }
/* ===================================================== */
/* 🏆 KO 淘汰赛 - 进度条 + 状态徽章 */
/* ===================================================== */
.ko-progress {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  padding: 12px 14px;
  margin: 10px 0 14px;
  background: var(--bg-2);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.ko-progress-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 140px;
  min-width: 140px;
}
.ko-progress-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  white-space: nowrap;
}
.ko-progress-bar {
  flex: 1;
  height: 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  min-width: 60px;
}
.ko-progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 3px;
}
.ko-progress-text {
  font-size: 12px;
  font-weight: 700;
  min-width: 38px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* 卡片状态徽章 */
.bracket-match .status-badge {
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 8px;
  line-height: 1.3;
  pointer-events: none;
  z-index: 2;
}
.bracket-match .status-badge.real {
  background: #3fb950;
  color: #fff;
}
.bracket-match .status-badge.pending {
  background: rgba(110, 118, 129, 0.25);
  color: var(--text-muted);
  border: 1px dashed var(--border);
}
.bracket-match .status-badge.predicted {
  background: rgba(240, 136, 62, 0.2);
  color: #f0883e;
  border: 1px solid #f0883e;
}
.bracket-match {
  position: relative;
}
.bracket-match.status-pending {
  opacity: 0.7;
  border-left-color: var(--border) !important;
}
.bracket-match.status-pending .team {
  color: var(--text-muted);
}
.bracket-match.status-real.has-winner {
  border-left-color: #3fb950;
  box-shadow: 0 1px 6px rgba(63, 185, 80, 0.25);
}

/* 移动端进度条 */
@media (max-width: 600px) {
  .ko-progress-item {
    flex: 1 1 100%;
  }
  .ko-progress {
    padding: 8px 10px;
    gap: 6px;
  }
}

/* 🏆 KO 淘汰赛 - 卡片视觉系统 */
/* ===================================================== */
.bracket-match {
  background: linear-gradient(180deg, var(--bg-2), var(--bg));
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);  /* 左侧色条 (胜者绿/败者灰) */
  border-radius: 6px;
  padding: 3px 6px 3px 8px;
  font-size: 12px;
  cursor: pointer;
  min-width: 0;
  overflow: hidden;
  transition: all 0.18s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  box-sizing: border-box;
}

/* R32 三段卡片: 队1 顶 / 日期-城市 中 / 队2 底 (3 段撑开) */
.bracket-match.has-sched {
  justify-content: space-between;
}
.bracket-match:hover { border-color: var(--accent); border-left-color: var(--accent); transform: translateX(2px); box-shadow: 0 2px 8px rgba(240,136,62,0.15); }
.bracket-match.has-winner { border-left: 3px solid var(--green); }
.bracket-match.unplayed { border: 1px dashed #58a6ff; border-left: 3px solid #58a6ff; background: linear-gradient(135deg, rgba(88,166,255,0.05), var(--bg-2)); }
.bracket-match.upcoming-soon { border: 1px solid #ff5722; border-left: 3px solid #ff5722; background: linear-gradient(135deg, rgba(255,87,34,0.15), var(--bg-2)); animation: pulse-soon 2s ease-in-out infinite; }
.bracket-match.upcoming-tomorrow { border: 1px solid #ff9800; border-left: 3px solid #ff9800; background: linear-gradient(135deg, rgba(255,152,0,0.12), var(--bg-2)); }

/* Wiki 风格: 顶部日期+城市 (蓝色 wiki 链接样式) */
.bracket-match .match-date-city {
  font-size: 10px;
  color: #58a6ff;
  font-weight: 500;
  margin-bottom: 1px;
  padding-bottom: 1px;
  border-bottom: 1px dotted rgba(88,166,255,0.25);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.0;
  flex-shrink: 0;
}
.bracket-match .match-date-city .sep { color: var(--text-3); margin: 0 1px; }

/* Wiki 风格: 底部赛事编号+胜方 (灰色一行) */
.bracket-match .match-winner-line {
  font-size: 10px;
  color: var(--text-3);
  margin-top: 1px;
  padding-top: 1px;
  border-top: 1px dotted rgba(125,133,144,0.25);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.1;
  flex-shrink: 0;
}

.bracket-match .team {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1px 0;
  min-width: 0;
  position: relative;
  line-height: 1.15;
  flex-shrink: 0;
}
.bracket-match .team + .team {
  border-top: 1px dashed rgba(125,133,144,0.2);
  margin-top: 2px;
  padding-top: 4px;
}
.bracket-match .team > span:first-child {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  gap: 4px;
}
.bracket-match .winner {
  color: var(--green);
  font-weight: 600;
}
.bracket-match .loser {
  color: var(--text-3);
  opacity: 0.65;
  text-decoration: line-through;
  text-decoration-color: rgba(125,133,144,0.4);
}
.bracket-match .score {
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
  margin-left: 4px;
  min-width: 18px;
  text-align: center;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--bg-3);
  color: var(--text);
}
.bracket-match .winner .score {
  background: rgba(63, 185, 80, 0.18);
  color: var(--green);
}
.bracket-match .loser .score {
  background: transparent;
  color: var(--text-3);
}
.bracket-match .team-rank {
  display: inline-block;
  font-size: 9px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  margin-left: 4px;
  flex-shrink: 0;
  background: rgba(125,133,144,0.15);
  color: var(--text-3);
  letter-spacing: 0.3px;
}
.bracket-match .winner .team-rank {
  background: rgba(63, 185, 80, 0.2);
  color: var(--green);
}
.bracket-match .flag {
  flex-shrink: 0;
  font-size: 13px;
  line-height: 1;
}
.bracket-match .pen {
  color: var(--gold);
  font-size: 9px;
  font-weight: bold;
  margin-left: 2px;
  background: rgba(255, 215, 0, 0.12);
  padding: 1px 3px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}

/* 🏆 决赛卡: 金色立体感 */
.bracket-match.final {
  background: linear-gradient(135deg, rgba(255,215,0,0.18), rgba(255,165,0,0.05), var(--bg-2));
  border: 2px solid var(--gold);
  border-left: 3px solid var(--gold);
  box-shadow: 0 0 24px rgba(255,215,0,0.25), inset 0 1px 0 rgba(255,255,255,0.08);
  padding: 3px 6px 3px 8px;
  position: relative;
  overflow: hidden;
}
.bracket-match.final::before {
  content: '';
  display: none;  /* emoji 改在 F I N A L 标签里, 不再叠加 */
}
.bracket-match.final .team { padding: 2px 0; }
.bracket-match.final .score { font-size: 17px; padding: 2px 9px; }
.bracket-match.final .flag { font-size: 16px; }
.bracket-match.final .winner .score {
  background: rgba(255, 215, 0, 0.25);
  color: var(--gold);
  text-shadow: 0 0 8px rgba(255,215,0,0.4);
}
.bracket-match.final .winner { color: var(--gold); }
.bracket-match.final .winner .team-rank { background: rgba(255,215,0,0.2); color: var(--gold); }

/* 🥉 季军赛: 铜色 */
.bracket-match.third {
  background: linear-gradient(135deg, rgba(205,127,50,0.18), rgba(180,90,40,0.05), var(--bg-2));
  border: 2px solid var(--bronze);
  border-left: 3px solid var(--bronze);
  box-shadow: 0 0 18px rgba(205,127,50,0.2), inset 0 1px 0 rgba(255,255,255,0.05);
  position: relative;
  overflow: visible;
}
.bracket-match.third::before {
  content: '🥉';
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 16px;
  z-index: 2;
}

/* 折线: 胜者路径更粗, 失败路径细灰色 */
.bracket-connector path {
  fill: none;
}
.bracket-connector path.winner-path {
  filter: drop-shadow(0 0 3px rgba(63, 185, 80, 0.4));
}
.bracket-connector { position: absolute; pointer-events: none; }
.bracket-connector line { stroke: var(--border); stroke-width: 1.5; fill: none; }
.bracket-connector line.winner-line { stroke: var(--green); stroke-width: 2; opacity: 0.6; }

/* 小组赛 */
.group-stage { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-bottom: 24px; }
.group-block { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.group-block-header { background: linear-gradient(90deg, #1f6feb, #8957e5); color: #fff; padding: 6px 12px; border-radius: 4px; font-weight: bold; text-align: center; margin-bottom: 10px; font-size: 13px; }
.standings-mini { font-size: 11px; margin-bottom: 8px; border-collapse: collapse; width: 100%; }
.standings-mini th, .standings-mini td { padding: 3px 6px; text-align: left; }
.standings-mini th { color: var(--text-3); font-weight: normal; font-size: 10px; border-bottom: 1px solid var(--border); }
.standings-mini .pos-1 { background: rgba(63, 185, 80, 0.15); }
.standings-mini .pos-2 { background: rgba(63, 185, 80, 0.05); }
.standings-mini .pos-3 { background: rgba(248, 81, 73, 0.1); }
.standings-mini .rank-cell { color: var(--accent); font-weight: bold; width: 20px; }
.matches-mini { display: flex; flex-direction: column; gap: 4px; }
.match-mini { background: var(--bg-3); padding: 5px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; display: flex; justify-content: space-between; }
.match-mini:hover { background: var(--accent-2); color: #fff; }
.match-mini .winner { color: var(--green); font-weight: bold; }
.match-mini .loser { color: var(--text-3); }
.match-mini .score { color: var(--text-2); margin-left: 8px; }

.predict-section { margin-top: 24px; }
.predict-section-title { font-size: 16px; font-weight: bold; color: var(--accent); margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
.predict-section-title .count { color: var(--text-3); font-weight: normal; font-size: 13px; }

/* 🆚 对比 */
.compare-grid { display: grid; grid-template-columns: 1fr 60px 1fr; gap: 12px; }
.compare-side { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.compare-side h3 { color: var(--accent); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.compare-vs { display: flex; align-items: center; justify-content: center; font-size: 24px; color: var(--text-3); }
.compare-row { display: grid; grid-template-columns: 1fr auto 1fr; padding: 6px 0; border-bottom: 1px solid var(--border); align-items: center; }
.compare-row .left, .compare-row .right { font-size: 13px; }
.compare-row .diff { background: var(--accent); color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; }

/* 详情弹窗 */
.detail-section { margin-bottom: 20px; }
.detail-section h4 { color: var(--accent); font-size: 14px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
.player-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
.player-item { background: var(--bg-3); padding: 8px 10px; border-radius: 4px; font-size: 12px; }
.player-item .pname { font-weight: bold; }
.player-item .pmeta { color: var(--text-3); font-size: 11px; margin-top: 2px; }

/* 球员按位置分块 */
.player-by-pos { display: flex; flex-direction: column; gap: 14px; }
.pos-block { background: var(--bg-3); border-radius: 6px; padding: 8px 12px; }
.pos-header { font-size: 13px; font-weight: bold; color: var(--accent); margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 8px; }
.pos-count { color: var(--text-3); font-size: 11px; font-weight: normal; }
.pos-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 6px; }
.player-item-click {
  display: flex; align-items: center; gap: 8px;
  background: var(--bg-2); padding: 6px 10px; border-radius: 4px;
  font-size: 12px; cursor: pointer; transition: all 0.15s;
  border: 1px solid transparent;
}
.player-item-click:hover { background: var(--bg); border-color: var(--accent); transform: translateX(2px); }
.player-item-click .p-jersey { color: var(--accent); font-weight: bold; min-width: 28px; }
.player-item-click .p-name { flex: 1; font-weight: 500; }
.player-item-click .p-club { color: var(--text-3); font-size: 11px; }
.player-item-click .p-val { color: var(--text-2); font-size: 11px; }

/* 教练详情块 */
.coach-block { display: flex; flex-direction: column; gap: 6px; }
.coach-name { font-size: 16px; font-weight: bold; color: var(--accent); }
.coach-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.coach-tag { background: var(--bg-3); padding: 3px 8px; border-radius: 4px; font-size: 11px; color: var(--text-2); }
.coach-tag strong { color: var(--accent); }
.coach-row { font-size: 12px; color: var(--text-2); line-height: 1.6; }
.coach-row b { color: var(--text); }

/* 球员详情 */
.player-detail { display: flex; flex-direction: column; gap: 18px; }
.pd-header { display: flex; align-items: center; gap: 16px; padding: 12px; background: var(--bg-3); border-radius: 8px; }
.pd-jersey { font-size: 32px; font-weight: bold; color: var(--accent); min-width: 60px; text-align: center; }
.pd-info { display: flex; flex-direction: column; gap: 4px; }
.pd-pos { font-size: 14px; color: var(--accent); font-weight: bold; }
.pd-club { font-size: 13px; color: var(--text-2); }
.pd-val { font-size: 16px; font-weight: bold; color: var(--gold); }
.pd-section h4 { color: var(--accent); font-size: 13px; margin-bottom: 8px; }
.pd-section p { font-size: 13px; line-height: 1.7; color: var(--text-2); }
.pd-stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 8px; }
.pd-stat { background: var(--bg-3); padding: 10px; border-radius: 6px; text-align: center; }
.pd-stat-v { font-size: 18px; font-weight: bold; color: var(--accent); }
.pd-stat-l { font-size: 11px; color: var(--text-3); margin-top: 2px; }
.lambda-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 12px 0; }
.lambda-card { background: var(--bg-3); padding: 10px; border-radius: 6px; }
.lambda-card h5 { color: var(--accent); font-size: 12px; margin-bottom: 4px; }
.lambda-card .lam-val { font-size: 20px; font-weight: bold; color: var(--accent); }
.lambda-card .lam-detail { font-size: 11px; color: var(--text-2); margin-top: 4px; }

/* ============== 比赛详情抽屉 (左右滑出) ============== */
.match-drawer { position: fixed; inset: 0; z-index: 1000; pointer-events: none; }
.match-drawer.open { pointer-events: auto; }
.drawer-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.55); opacity: 0; transition: opacity 0.3s; }
.match-drawer.open .drawer-overlay { opacity: 1; }
.drawer-side { position: absolute; top: 0; bottom: 0; width: 23%; background: var(--bg-1); border: 1px solid var(--border); overflow-y: auto; transition: transform 0.35s cubic-bezier(0.4,0,0.2,1); box-shadow: 0 0 30px rgba(0,0,0,0.5); }
.drawer-side.left { left: 0; transform: translateX(-105%); border-right: 2px solid var(--accent); }
.drawer-side.right { right: 0; transform: translateX(105%); border-left: 2px solid var(--accent-2); }
.match-drawer.open .drawer-side.left { transform: translateX(0); }
.match-drawer.open .drawer-side.right { transform: translateX(0); }
.drawer-center { position: absolute; top: 0; bottom: 0; left: 23%; right: 23%; background: var(--bg-1); border-left: 1px solid var(--border); border-right: 1px solid var(--border); display: flex; flex-direction: column; align-items: stretch; padding: 20px; transform: translateY(-100%); transition: transform 0.35s 0.1s cubic-bezier(0.4,0,0.2,1); overflow-y: auto; }
.drawer-center::-webkit-scrollbar { width: 8px; }
.drawer-center::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
.match-drawer.open .drawer-center { transform: translateY(0); }
.drawer-close { position: absolute; top: 10px; right: 10px; background: var(--bg-3); color: var(--text); border: 1px solid var(--border); width: 32px; height: 32px; border-radius: 50%; font-size: 20px; cursor: pointer; z-index: 10; }
.drawer-close:hover { background: var(--accent); color: #fff; }

/* center 内容 (现在 54% 宽, 放完整比赛详情) */
.center-mini { width: 100%; max-width: 720px; margin: 0 auto; text-align: center; }
.center-mini .cm-title { font-size: 22px; font-weight: bold; margin-bottom: 14px; display: flex; align-items: center; justify-content: center; gap: 12px; }
.center-mini .cm-title .cm-flag { font-size: 32px; }
.center-mini .cm-title .cm-vs-tag { color: var(--text-3); font-size: 16px; font-weight: normal; }
.center-mini .cm-meta { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--text-2); margin-bottom: 14px; }
.center-mini .cm-meta span { background: var(--bg-2); padding: 4px 10px; border-radius: 4px; border: 1px solid var(--border); }
.center-mini .cm-lam { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 0; }
.center-mini .cm-lam > div { background: var(--bg-2); padding: 12px; border-radius: 6px; border: 1px solid var(--border); }
.center-mini .cm-lam .cm-team-name { font-size: 14px; color: var(--accent); margin-bottom: 4px; font-weight: bold; }
.center-mini .cm-lam b { color: var(--text); font-size: 22px; }
.center-mini .cm-prob { display: flex; height: 32px; border-radius: 6px; overflow: hidden; margin: 14px 0 6px; font-size: 12px; box-shadow: 0 0 0 1px var(--border); }
.center-mini .cm-prob > div { display: flex; align-items: center; justify-content: center; color: #fff; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.4); }
.center-mini .cm-prob .h { background: linear-gradient(90deg, #2ea043, #3fb950); }
.center-mini .cm-prob .d { background: linear-gradient(90deg, #6e7681, #8b949e); }
.center-mini .cm-prob .a { background: linear-gradient(90deg, #c93c20, #f85149); }
.center-mini .cm-prob-labels { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-3); margin-bottom: 14px; }
.center-mini .cm-prob-labels span:nth-child(2) { text-align: center; }
.center-mini .cm-prob-labels span:last-child { text-align: right; }
.center-mini .cm-section { text-align: left; margin: 16px 0; padding: 12px; background: var(--bg-2); border-radius: 6px; border: 1px solid var(--border); }
.center-mini .cm-section h4 { color: var(--accent); font-size: 13px; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
.center-mini .cm-result { font-size: 14px; margin: 8px 0; }
.center-mini .cm-result strong { font-size: 18px; color: var(--accent); }
.center-mini .cm-info { font-size: 11px; color: var(--text-3); line-height: 1.6; margin-top: 8px; }
.center-mini .cm-tips { font-size: 11px; color: var(--accent); margin-top: 14px; padding: 10px; border: 1px dashed var(--accent); border-radius: 4px; line-height: 1.6; }
.center-mini .cm-scores { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 6px; }
.center-mini .cm-scores td { padding: 4px 8px; border-bottom: 1px solid var(--border); }
.center-mini .cm-scores td:first-child { font-weight: bold; color: var(--text); }
.center-mini .cm-scores td:nth-child(3) { text-align: right; color: var(--accent); font-weight: bold; }
.center-mini .cm-scores .sc-bar-track { background: var(--bg-3); height: 6px; border-radius: 3px; overflow: hidden; }
.center-mini .cm-scores .sc-bar-fill { background: linear-gradient(90deg, #58a6ff, #79c0ff); height: 100%; border-radius: 3px; }
.center-mini .cm-env { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 6px; }
.center-mini .cm-env > div { background: var(--bg-3); padding: 8px; border-radius: 4px; text-align: center; }
.center-mini .cm-env .ce-label { font-size: 10px; color: var(--text-3); margin-bottom: 2px; }
.center-mini .cm-env .ce-val { font-size: 13px; font-weight: bold; color: var(--accent); }

/* team panel (drawer 内) */
.side-inner { padding: 14px 12px; }
.team-hdr { text-align: center; padding: 10px 8px; background: linear-gradient(135deg, var(--bg-2), var(--bg-3)); border-radius: 6px; margin-bottom: 12px; }
.team-hdr .th-flag { font-size: 28px; }
.team-hdr .th-name { font-size: 15px; font-weight: bold; margin: 4px 0 4px; }
.team-hdr .th-ranks { display: flex; justify-content: center; gap: 4px; flex-wrap: wrap; font-size: 10px; color: var(--text-2); margin-bottom: 6px; }
.team-hdr .th-ranks .rk-chip { background: var(--bg-1); padding: 2px 6px; border-radius: 3px; border: 1px solid var(--border); }
.team-hdr .th-4d { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px; font-size: 9px; }
.team-hdr .th-4d > div { background: var(--bg-1); padding: 3px 2px; border-radius: 3px; text-align: center; }
.team-hdr .th-4d b { color: var(--accent); font-size: 11px; display: block; }

.side-section { margin-bottom: 14px; }
.side-section h3 { color: var(--accent); font-size: 12px; margin-bottom: 6px; padding-bottom: 3px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 6px; }
.side-section h3 .ss-count { color: var(--text-3); font-weight: normal; font-size: 10px; margin-left: auto; }

/* coach card */
.coach-card { background: var(--bg-2); padding: 8px 10px; border-radius: 5px; border-left: 3px solid var(--accent); }
.coach-card .c-name { font-weight: bold; font-size: 12px; margin-bottom: 3px; line-height: 1.3; }
.coach-card .c-meta { font-size: 10px; color: var(--text-2); margin-bottom: 4px; }
.coach-card .c-row { font-size: 10px; margin-top: 3px; line-height: 1.5; }
.coach-card .c-row .c-label { color: var(--text-3); margin-right: 4px; }
.coach-card .c-honors { margin-top: 4px; display: flex; flex-wrap: wrap; gap: 3px; }
.coach-card .c-honors span { background: var(--bg-3); padding: 1px 5px; border-radius: 3px; font-size: 9px; color: var(--accent); }

/* player by position group */
.pos-block { background: var(--bg-2); border-radius: 5px; margin-bottom: 6px; overflow: hidden; }
.pos-header { font-size: 11px; font-weight: bold; padding: 6px 8px; background: var(--bg-3); display: flex; align-items: center; gap: 5px; cursor: pointer; }
.pos-header .pos-icon { font-size: 12px; }
.pos-header .pos-count { color: var(--text-3); font-weight: normal; font-size: 10px; margin-left: auto; }
.pos-body { padding: 4px; }
.pos-body.collapsed { display: none; }

/* player row (compact) */
.player-row { padding: 4px 6px; border-radius: 3px; font-size: 10px; cursor: pointer; display: grid; grid-template-columns: 18px 1fr 38px 40px; gap: 4px; align-items: center; }
.player-row:hover { background: var(--bg-3); }
.player-row .pr-jersey { font-weight: bold; color: var(--accent); text-align: center; font-size: 9px; }
.player-row .pr-name { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.player-row .pr-value { text-align: right; color: var(--accent); font-variant-numeric: tabular-nums; font-size: 10px; }

/* player detail (expanded) */
.player-detail { background: var(--bg-1); margin: 2px 4px 4px; padding: 6px 8px; border-radius: 3px; font-size: 10px; border-left: 2px solid var(--accent); }
.player-detail .pd-row { display: flex; justify-content: space-between; padding: 1px 0; line-height: 1.5; gap: 4px; }
.player-detail .pd-row .pd-label { color: var(--text-3); flex-shrink: 0; }
.player-detail .pd-row .pd-val { color: var(--text); text-align: right; word-break: break-word; }
.player-detail .pd-season { color: var(--text-2); font-size: 9px; margin-top: 3px; line-height: 1.4; padding-top: 3px; border-top: 1px dashed var(--border); }

/* full roster (compact 26) */
.roster-mini { background: var(--bg-2); border-radius: 5px; padding: 3px; max-height: 220px; overflow-y: auto; }
.roster-row { display: grid; grid-template-columns: 18px 1fr 36px 50px; gap: 4px; padding: 3px 5px; font-size: 10px; border-bottom: 1px solid var(--border); align-items: center; }
.roster-row:last-child { border-bottom: none; }
.roster-row .rr-jersey { font-weight: bold; color: var(--accent); text-align: center; font-size: 9px; }
.roster-row .rr-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.roster-row .rr-pos { color: var(--text-3); font-size: 9px; text-align: center; }
.roster-row .rr-value { text-align: right; color: var(--text-2); font-variant-numeric: tabular-nums; font-size: 9px; }

/* team schedule */
.sched-row { padding: 6px 8px; border-radius: 4px; font-size: 10px; margin-bottom: 3px; background: var(--bg-2); display: grid; grid-template-columns: 1fr auto; gap: 6px; align-items: center; cursor: pointer; }
.sched-row:hover { background: var(--bg-3); }
.sched-row .sr-left { line-height: 1.4; min-width: 0; }
.sched-row .sr-date { color: var(--text-3); font-size: 9px; }
.sched-row .sr-opp { font-weight: 500; margin-top: 1px; font-size: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sched-row .sr-opp .sr-home { color: var(--text-3); font-size: 9px; margin-right: 3px; }
.sched-row .sr-score { font-weight: bold; font-variant-numeric: tabular-nums; text-align: right; font-size: 11px; }
.sched-row.played { border-left: 3px solid var(--green); }
.sched-row.played.win { border-left-color: var(--green); }
.sched-row.played.lose { border-left-color: var(--red); }
.sched-row.played.draw { border-left-color: var(--text-3); }
.sched-row.future { border-left: 3px solid #58a6ff; }
.sched-row.tomorrow { border-left: 3px solid #ff9800; background: linear-gradient(90deg, rgba(255,152,0,0.08), var(--bg-2)); }
.sched-row.soon { border-left: 3px solid #ff5722; background: linear-gradient(90deg, rgba(255,87,34,0.08), var(--bg-2)); }
.sched-row .sr-score.win { color: var(--green); }
.sched-row .sr-score.lose { color: var(--red); }
.sched-row .sr-score.draw { color: var(--text-2); }
.sched-row .sr-score.future { color: var(--accent); }
.sched-row .sr-meta { color: var(--text-3); font-size: 9px; }

/* 晋级分析页面 */
.qualify-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; margin-bottom: 18px; }
.qualify-group-card { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; }
.qualify-group-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
.qualify-group-title { font-weight: bold; color: var(--accent); font-size: 14px; }
.qualify-group-progress { color: var(--text-3); font-size: 11px; }
.qualify-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.qualify-table th { color: var(--text-3); font-weight: normal; font-size: 10px; padding: 3px 4px; text-align: left; border-bottom: 1px solid var(--border); }
.qualify-table td { padding: 5px 4px; border-bottom: 1px solid var(--bg-2); }
.qualify-table tr.row-q { background: rgba(63, 185, 80, 0.12); }
.qualify-table tr.row-q2 { background: rgba(63, 185, 80, 0.05); }
.qualify-table tr.row-battle { background: rgba(248, 81, 73, 0.06); }
.qualify-table tr.row-out { background: var(--bg-3); opacity: 0.55; }
.qualify-table .rank-cell { width: 22px; font-weight: bold; color: var(--accent); text-align: center; }
.qualify-table .team-cell { font-weight: 500; }
.qualify-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.qualify-table .pos-label { font-size: 9px; color: var(--text-3); }
.qbadge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; }
.qbadge-locked-q { background: rgba(63, 185, 80, 0.25); color: var(--green); }
.qbadge-locked-q2 { background: rgba(63, 185, 80, 0.12); color: var(--green); }
.qbadge-battle-q { background: rgba(248, 81, 73, 0.18); color: var(--red); }
.qbadge-battle-out { background: rgba(248, 81, 73, 0.08); color: var(--text-3); }
.qbadge-out { background: var(--bg-3); color: var(--text-3); }
.qbadge-third { background: rgba(31, 111, 235, 0.15); color: var(--accent-2); }
.qremaining { margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--border); }
.qremaining-title { font-size: 10px; color: var(--text-3); margin-bottom: 4px; }
.qremaining-match { display: flex; justify-content: space-between; font-size: 11px; padding: 2px 0; color: var(--text-2); }
.qremaining-match .date { color: var(--text-3); font-size: 10px; }
.qthird-table { width: 100%; border-collapse: collapse; font-size: 12px; background: var(--bg-1); border-radius: 8px; overflow: hidden; }
.qthird-table th { background: var(--bg-3); padding: 8px 6px; text-align: left; font-size: 11px; color: var(--text-3); font-weight: 600; border-bottom: 1px solid var(--border); }
.qthird-table td { padding: 8px 6px; border-bottom: 1px solid var(--bg-2); }
.qthird-table tr.qualify { background: rgba(63, 185, 80, 0.1); }
.qthird-table tr.qualify td:first-child { border-left: 3px solid var(--green); }
.qthird-table tr.eliminated td:first-child { border-left: 3px solid var(--red); }
.qthird-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.qthird-table .cutoff-row td { background: var(--bg-3); color: var(--text-3); font-size: 10px; padding: 4px 6px; text-align: center; font-style: italic; }
.q-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin: 12px 0 18px; }
.q-stat-card { background: var(--bg-1); border: 1px solid var(--border); border-radius: 6px; padding: 10px; text-align: center; }
.q-stat-num { font-size: 22px; font-weight: bold; font-variant-numeric: tabular-nums; }
.q-stat-lbl { font-size: 10px; color: var(--text-3); margin-top: 2px; }
.q-stat-card.locked-q .q-stat-num { color: var(--green); }
.q-stat-card.battle-q .q-stat-num { color: var(--accent-2); }
.q-stat-card.battle-out .q-stat-num { color: var(--red); }
.q-stat-card.eliminated .q-stat-num { color: var(--text-3); }

/* R32 淘汰赛对阵 */
.qr32-half { margin-bottom: 18px; padding: 12px; background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; }
.qr32-half-upper { border-left: 4px solid var(--accent-2); }
.qr32-half-lower { border-left: 4px solid var(--green); }
.qr32-half-title { font-size: 13px; font-weight: bold; color: var(--text-1); margin-bottom: 4px; }
.qr32-half-sub { font-size: 10px; color: var(--text-3); margin-bottom: 10px; }
.qr32-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 8px; }
.qr32-match { background: var(--bg-1); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; }
.qr32-match-num { font-size: 9px; color: var(--text-3); font-weight: bold; letter-spacing: 1px; }
.qr32-match-date { font-size: 9px; color: var(--text-3); float: right; }
.qr32-team { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 12px; }
.qr32-team.qualified { color: var(--text-1); }
.qr32-team.uncertain { color: var(--text-3); font-style: italic; }
.qr32-team .rank-tag { font-size: 9px; color: var(--text-3); background: var(--bg-3); padding: 1px 4px; border-radius: 3px; margin-left: 4px; }
.qr32-team.uncertain .rank-tag { background: var(--bg-2); }
.qr32-vs { text-align: center; color: var(--text-3); font-size: 10px; margin: 2px 0; }
.qr32-match.tbd { border-style: dashed; opacity: 0.7; }
.qr32-legend { font-size: 10px; color: var(--text-3); margin-bottom: 10px; padding: 8px 12px; background: var(--bg-1); border-radius: 4px; }
.qr32-legend code { background: var(--bg-3); padding: 1px 4px; border-radius: 3px; }
@media (max-width: 900px) {
  .qualify-grid { grid-template-columns: 1fr; }
  .q-summary { grid-template-columns: repeat(2, 1fr); }
  .qr32-grid { grid-template-columns: 1fr; }
  .qr32-half { padding: 8px; }
}

/* responsive: smaller screens → center collapses */
@media (max-width: 1400px) {
  .drawer-side { width: 25%; }
  .drawer-center { left: 25%; right: 25%; }
}
@media (max-width: 1100px) {
  .drawer-side { width: 28%; }
  .drawer-center { left: 28%; right: 28%; padding: 10px 6px; }
  .center-mini { max-width: 100%; }
}
@media (max-width: 768px) {
  .drawer-side { width: 50%; }
  .drawer-side.left { transform: translateX(0); border-right-width: 1px; }
  .drawer-side.right { transform: translateX(0); border-left-width: 1px; }
  .drawer-center { display: none; }
}

/* 已完赛比赛详情弹窗 (区别于预测抽屉) */
.pp-modal { background: var(--bg-2); border-radius: 12px; width: min(1200px, 96vw); max-height: 92vh; overflow-y: auto; border: 1px solid var(--border); box-shadow: 0 8px 40px rgba(0,0,0,0.5); position: relative; }
.pp-body-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 12px 20px 16px; align-items: start; }
.pp-body-grid > .pp-section { margin-bottom: 0; }
.pp-body-grid > .pp-section.col-l { grid-column: 1; }
.pp-body-grid > .pp-section.col-r { grid-column: 2; }
.pp-body-grid > .pp-section.full { grid-column: 1 / -1; }
.pp-header { padding: 12px 24px 10px; background: linear-gradient(135deg, var(--bg-3), var(--bg-2)); border-bottom: 1px solid var(--border); border-radius: 12px 12px 0 0; }
.pp-header .modal-close { position: absolute; top: 10px; right: 12px; }
.pp-stage { text-align: center; color: var(--text-3); font-size: 11px; margin-bottom: 8px; letter-spacing: 1px; }
.pp-title { display: grid; grid-template-columns: 1fr auto 1fr; gap: 16px; align-items: center; }
.pp-team { text-align: center; padding: 8px; border-radius: 8px; transition: background 0.3s; }
.pp-team.winner { background: rgba(46,160,67,0.12); box-shadow: 0 0 0 1px rgba(46,160,67,0.4); }
.pp-team .pp-flag { font-size: 36px; line-height: 1; margin-bottom: 6px; }
.pp-team .pp-name { font-size: 14px; font-weight: 600; line-height: 1.3; }
.pp-team .pp-rk { color: var(--text-3); font-weight: normal; font-size: 11px; margin-left: 3px; }
.pp-team.home { text-align: right; }
.pp-team.away { text-align: left; }
.pp-score { text-align: center; min-width: 120px; }
.pp-score-num { font-size: 36px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1; }
.pp-score-sep { color: var(--text-3); margin: 0 6px; font-weight: 400; }
.pp-score-lbl { color: var(--text-3); font-size: 10px; margin-top: 4px; letter-spacing: 1px; }
.pp-result { text-align: center; margin-top: 8px; padding: 6px 12px; background: var(--bg-1); border-radius: 6px; font-size: 12px; }
.pp-result.home-win { color: var(--green); border-left: 3px solid var(--green); }
.pp-result.away-win { color: var(--green); border-left: 3px solid var(--green); }
.pp-result.draw { color: var(--text-2); border-left: 3px solid var(--text-3); }
.pp-body { padding: 16px 24px 24px; }
.pp-section { background: var(--bg-1); border-radius: 8px; padding: 8px 10px; margin-bottom: 12px; }
.pp-section:last-child { margin-bottom: 0; }
.pp-section h4 { color: var(--accent); font-size: 11px; margin-bottom: 6px; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
.pp-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 16px; font-size: 12px; }
.pp-grid > div { display: flex; justify-content: space-between; gap: 8px; padding: 4px 8px; background: var(--bg-2); border-radius: 4px; }
.pp-lbl { color: var(--text-3); flex-shrink: 0; }
.pp-val { text-align: right; font-weight: 500; word-break: break-word; }
.pp-info { margin-top: 8px; font-size: 11px; color: var(--text-2); line-height: 1.5; padding: 6px 10px; background: var(--bg-2); border-radius: 4px; }
.pp-info-full { grid-column: 1 / -1; margin-top: 4px; font-size: 11px; color: var(--text-2); line-height: 1.5; padding: 6px 10px; background: var(--bg-2); border-radius: 4px; }
.pp-pred-compare { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.pp-pc-cell { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 8px 6px; background: var(--bg-2); border-radius: 6px; font-size: 12px; }
.pp-pc-cell b { font-size: 14px; font-variant-numeric: tabular-nums; }
.pp-missing { padding: 20px; text-align: center; color: var(--text-3); background: var(--bg-2); border-radius: 6px; border: 1px dashed var(--border); }
.pp-missing-sub { font-size: 11px; display: block; margin-top: 6px; color: var(--text-3); }

/* 控球率条 */
.pp-possession { display: grid; grid-template-columns: 80px 1fr 80px; gap: 8px; align-items: center; margin: 6px 0 8px; }
.pp-poss-label { font-size: 13px; text-align: center; }
.pp-poss-label:first-child { text-align: right; }
.pp-poss-label:last-child { text-align: left; }
.pp-poss-track { display: flex; height: 18px; border-radius: 9px; overflow: hidden; background: var(--bg-3); box-shadow: inset 0 1px 2px rgba(0,0,0,0.3); }
.pp-poss-fill.home { background: linear-gradient(90deg, var(--accent), #ffa657); }
.pp-poss-fill.away { background: linear-gradient(90deg, #58a6ff, #79c0ff); }

/* 8 项技术统计 */
.pp-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 8px; margin-top: 4px; }
.pp-stat-row { display: grid; grid-template-columns: 1fr 60px 1fr; gap: 6px; padding: 3px 8px; background: var(--bg-2); border-radius: 4px; align-items: center; font-size: 11px; }
.pp-stat-row.warn { background: rgba(248, 81, 73, 0.06); }
.pp-stat-h { text-align: right; font-variant-numeric: tabular-nums; font-weight: 500; }
.pp-stat-lbl { text-align: center; color: var(--text-3); font-size: 11px; }
.pp-stat-a { text-align: left; font-variant-numeric: tabular-nums; font-weight: 500; }
.pp-stat-h.lead, .pp-stat-a.lead { color: var(--green); font-weight: 700; font-size: 14px; }
.pp-stats-extra { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; padding: 6px 10px; background: var(--bg-1); border-radius: 4px; font-size: 12px; }

/* 比赛事件时间轴 */
.pp-events { display: flex; flex-direction: column; gap: 2px; max-height: 230px; overflow-y: auto; }
.pp-event { display: grid; grid-template-columns: 50px 26px 1fr; gap: 8px; padding: 3px 8px; background: var(--bg-2); border-radius: 4px; align-items: center; font-size: 11px; border-left: 3px solid var(--border); }
.pp-event.home { border-left-color: var(--accent); }
.pp-event.away { border-left-color: var(--accent-2); }
.pp-event-clock { color: var(--text-3); font-weight: bold; font-variant-numeric: tabular-nums; font-size: 11px; }
.pp-event-icon { font-size: 16px; text-align: center; }
.pp-event-info { font-size: 12px; }
.pp-event-info b { color: var(--text); }

/* 球员亮点 */
.pp-player-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; align-items: start; }
.pp-player-section { background: var(--bg-2); padding: 6px 8px; border-radius: 6px; }
.pp-player-section h5 { color: var(--accent); font-size: 11px; margin-bottom: 4px; padding-bottom: 3px; border-bottom: 1px solid var(--border); }
.pp-player-list { display: flex; flex-direction: column; gap: 3px; }
.pp-player-row { display: grid; grid-template-columns: 22px 1fr auto; gap: 6px; padding: 3px 6px; background: var(--bg-1); border-radius: 3px; font-size: 11px; align-items: center; }
.pp-pr-flag { font-size: 14px; }
.pp-pr-name { font-weight: 500; }
.pp-pr-meta { color: var(--text-3); font-size: 10px; }
.pp-pr-stats { font-variant-numeric: tabular-nums; font-size: 11px; }
@media (max-width: 1100px) {
  .pp-body-grid { grid-template-columns: 1fr; }
  .pp-body-grid > .pp-section.col-l,
  .pp-body-grid > .pp-section.col-r { grid-column: 1; }
}
@media (max-width: 600px) {
  .pp-possession { grid-template-columns: 60px 1fr 60px; }
  .pp-player-grid { grid-template-columns: 1fr; }
  .pp-modal { width: 100vw; max-height: 100vh; border-radius: 0; }
}
@media (max-width: 600px) {
  .pp-title { grid-template-columns: 1fr; gap: 12px; }
  .pp-team.home, .pp-team.away { text-align: center; }
  .pp-grid { grid-template-columns: 1fr; }
  .pp-team .pp-flag { font-size: 28px; }
  .pp-score-num { font-size: 32px; }
}

/* 抽屉内 schedule row 修复: 让 sr-meta 不换行错乱 */
.sched-row .sr-score { white-space: nowrap; line-height: 1.2; }
.sched-row .sr-score.future { white-space: normal; }

/* played popup z-index 高于 drawer (避免遮挡) */
#playedPopup { z-index: 1100; }

/* modal: vs-tag / match-meta-line */
.modal-header h2 .vs-tag { color: var(--text-3); font-weight: normal; font-size: 16px; margin: 0 8px; }
.match-meta-line { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: var(--text-2); }
.match-meta-line span { background: var(--bg-3); padding: 4px 10px; border-radius: 4px; }

/* modal: 胜负概率条 */
.prob-bar { display: flex; height: 28px; border-radius: 6px; overflow: hidden; background: var(--bg-3); margin: 10px 0 4px; }
.prob-seg { display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; color: #fff; min-width: 0; overflow: hidden; white-space: nowrap; transition: width 0.3s; }
.prob-seg.home { background: linear-gradient(90deg, #2ea043, #3fb950); }
.prob-seg.draw { background: linear-gradient(90deg, #6e7681, #8b949e); }
.prob-seg.away { background: linear-gradient(90deg, #c93c20, #f85149); }
.prob-seg span { padding: 0 4px; text-shadow: 0 1px 2px rgba(0,0,0,0.4); }
.prob-bar-labels { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-3); }

/* modal: 比分概率表 */
.score-prob-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.score-prob-table th { text-align: left; color: var(--text-3); font-weight: normal; padding: 4px 8px; border-bottom: 1px solid var(--border); }
.score-prob-table td { padding: 5px 8px; border-bottom: 1px solid var(--border); }
.score-prob-table td.num { text-align: right; font-variant-numeric: tabular-nums; color: var(--accent); font-weight: bold; }
.score-bar-track { background: var(--bg-3); height: 8px; border-radius: 4px; overflow: hidden; }
.score-bar-fill { background: linear-gradient(90deg, #58a6ff, #79c0ff); height: 100%; border-radius: 4px; transition: width 0.3s; }

/* modal: 场地环境 */
.env-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 8px; margin-top: 4px; }
.env-card { background: var(--bg-3); padding: 10px; border-radius: 6px; text-align: center; }
.env-label { font-size: 11px; color: var(--text-3); margin-bottom: 4px; }
.env-val { font-size: 16px; font-weight: bold; color: var(--accent); }

/* 搜索 */
.search-box { width: 100%; padding: 10px 14px; background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px; margin-bottom: 16px; }
.search-results { display: grid; gap: 8px; }
.search-result { background: var(--bg-2); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; cursor: pointer; }
.search-result:hover { border-color: var(--accent-2); }
.search-result .sr-type { font-size: 10px; color: var(--accent); display: inline-block; padding: 2px 6px; border-radius: 3px; background: rgba(240,136,62,0.1); margin-right: 8px; }
.search-result .sr-name { font-weight: bold; }

/* ============== 复盘分析页 ============== */
.review-subtitle { color: var(--text-3); font-size: 12px; margin-bottom: 16px; padding: 6px 12px; background: var(--bg-2); border-radius: 6px; }
.review-subtitle span { color: var(--accent); font-weight: bold; }
.rv-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-bottom: 20px; }
.rv-card { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }
.rv-card-num { font-size: 22px; font-weight: bold; color: var(--accent); line-height: 1.2; }
.rv-card-lbl { font-size: 11px; color: var(--text-3); margin-top: 4px; }
.rv-card-sub { font-size: 10px; color: var(--text-2); margin-top: 4px; }
.rv-section { background: var(--bg-2); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 14px; }
.rv-section h3 { color: var(--accent); font-size: 14px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
.rv-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.rv-table th { text-align: left; color: var(--text-3); font-weight: normal; padding: 6px 10px; border-bottom: 1px solid var(--border); background: var(--bg-3); }
.rv-table td { padding: 6px 10px; border-bottom: 1px solid var(--border); }
.rv-table tr:last-child td { border-bottom: none; }
.rv-table tr:hover td { background: var(--bg-3); }
.rv-table .rv-correct { color: var(--green); font-weight: bold; }
.rv-table .rv-pred { color: var(--text-3); }
.rv-info { font-size: 11px; color: var(--text-3); margin-top: 10px; padding: 8px 12px; background: var(--bg-1); border-radius: 4px; border-left: 3px solid var(--accent); }
.rv-bar-track { background: var(--bg-3); height: 18px; border-radius: 3px; overflow: hidden; min-width: 80px; }
.rv-bar-fill { height: 100%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #fff; padding: 0 4px; transition: width 0.5s; }
@media (max-width: 768px) {
  .rv-grid { grid-template-columns: repeat(2, 1fr); }
  .rv-table { font-size: 10px; }
  .rv-table th, .rv-table td { padding: 4px 6px; }
}

/* footer */
.footer { margin-top: 40px; padding: 20px; text-align: center; color: var(--text-3); font-size: 12px; border-top: 1px solid var(--border); }

/* ========================================================== */
/* 📱 移动端响应式 (≤ 768px 平板 + ≤ 480px 手机) */
/* ========================================================== */

/* 平板: ≤ 768px */
@media (max-width: 768px) {
  body { padding: 10px; font-size: 14px; }
  .app { padding: 10px; }
  .top-bar { padding: 16px 18px; flex-direction: column; align-items: flex-start; gap: 12px; }
  .top-bar h1 { font-size: 18px; }
  .top-bar .stats { width: 100%; gap: 6px; }
  .stat { flex: 1 1 calc(33.333% - 4px); min-width: 0; padding: 6px 8px; }
  .stat .value { font-size: 13px; }
  .top-bar-actions { width: 100%; justify-content: flex-end; }
  .top-bar-actions button { padding: 6px 10px; font-size: 12px; }

  /* Tab 改成 3 列 grid */
  .tabs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; border-bottom: none; }
  .tab { padding: 10px 4px; font-size: 12px; text-align: center; border-radius: 6px 6px 0 0; }

  /* 球队 tab */
  .team-card-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
  .team-card { padding: 10px; }

  /* 小组赛 grid: 2 列 */
  .group-stage { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
  .group-block { padding: 8px; }
  .group-block-header { font-size: 12px; padding: 4px 8px; }
  .standings-mini { font-size: 11px; }
  .standings-mini th, .standings-mini td { padding: 3px 4px; }

  /* 权重 6 分类 → 单列 */
  .weights-grid { grid-template-columns: 1fr; }

  /* Modal 全屏化 */
  .modal { width: 100%; max-width: 100%; max-height: 100vh; height: 100vh; border-radius: 0; padding: 16px; }
  .modal-overlay.open { align-items: flex-start; }

  /* 比赛预测折线: 容器宽度跟随卡片 */
  .bracket-container { padding: 8px; }

  /* 对比 grid: 左右两列纵向堆叠, vs 缩小 */
  .compare-grid { grid-template-columns: 1fr; gap: 8px; }
  .compare-vs { font-size: 18px; padding: 4px; }

  /* 预测 section 标题缩小 */
  .predict-section-title { font-size: 14px; }
}

/* 手机: ≤ 480px */
@media (max-width: 480px) {
  body { padding: 6px; font-size: 13px; }
  .app { padding: 6px; }
  .top-bar { padding: 12px 14px; }
  .top-bar h1 { font-size: 16px; }

  /* Tab 改成 2 列 grid (6 个 tab 排 3 行) */
  .tabs { grid-template-columns: repeat(2, 1fr); }

  /* Stat 卡 6 个变 3×2 grid */
  .stat { flex: 1 1 calc(50% - 3px); min-width: 0; padding: 4px 6px; }
  .stat .label { font-size: 10px; }
  .stat .value { font-size: 12px; }

  /* 球队 tab 卡片最小 130px */
  .team-card-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 6px; }

  /* 小组赛 grid: 1 列 */
  .group-stage { grid-template-columns: 1fr; }

  /* 比赛预测 tab 标题 + 描述更小 */
  .section-title { font-size: 16px; }
  .muted { font-size: 12px; }

  /* Modal 边距 */
  .modal { padding: 12px; }
  .modal-header { margin-bottom: 12px; padding-bottom: 8px; }
  .modal-header h2 { font-size: 16px; }

  /* 滑块标签 */
  .weight-row { padding: 6px 8px; }
  .weight-row label { font-size: 11px; }
  .weight-row input[type=range] { width: 100px; }
  .weight-row .weight-value { font-size: 11px; min-width: 30px; }

  /* search input */
  .search-box { font-size: 13px; padding: 8px 12px; }

  /* footer */
  .footer { font-size: 10px; padding: 12px; }

  /* 触摸优化: 卡片可点 */
  .tab, .btn, .team-card, .group-block { -webkit-tap-highlight-color: rgba(240,136,62,0.3); }

  /* 弹窗里 4 维 λ 改成单列 */
  .lambda-grid { grid-template-columns: 1fr; }
  .lambda-cell { padding: 8px; }

  /* 球员卡片 grid 单列 */
  .player-card-grid { grid-template-columns: 1fr; }
}

/* 触摸设备: 鼠标 hover 效果去除 */
@media (hover: none) {
  .team-card:hover, .search-result:hover, .bracket-match:hover { transform: none; box-shadow: none; }
}
</style>
</head>
<body>
<div class="app">
  <!-- 顶栏 -->
  <div class="top-bar">
    <div>
      <h1>🏆 2026 世界杯预测 · Mavis PDP v2.1</h1>
      <div class="stats" id="topStats">
        <div class="stat"><div class="label">球队</div><div class="value" id="statTeams">48</div></div>
        <div class="stat"><div class="label">比赛</div><div class="value" id="statMatches">104</div></div>
        <div class="stat gold"><div class="label">🏆 冠军</div><div class="value" id="statChampion">-</div></div>
        <div class="stat silver"><div class="label">🥈 亚军</div><div class="value" id="statRunnerUp">-</div></div>
        <div class="stat bronze"><div class="label">🥉 季军</div><div class="value" id="statThird">-</div></div>
      </div>
    </div>
    <div class="top-bar-actions">
      <button onclick="toggleTheme()" id="themeBtn">🌙 暗色</button>
      <button onclick="exportConfig()">📤 导出配置</button>
      <button onclick="window.print()">🖨️ 打印</button>
    </div>
  </div>

  <!-- Tab 导航 -->
  <div class="tabs">
    <button class="tab active" data-tab="teams">⚽ 球队</button>
    <button class="tab" data-tab="schedule">📅 赛程</button>
    <button class="tab" data-tab="config">🎛️ 配置</button>
    <button class="tab" data-tab="predict">🏆 预测</button>
    <button class="tab" data-tab="compare">🆚 对比</button>
    <button class="tab" data-tab="review">📊 复盘</button>
    <button class="tab" data-tab="search">🔍 搜索</button>
    <button class="tab" data-tab="qualify">🏅 晋级</button>
  </div>

  <!-- ⚽ 球队 -->
  <div class="tab-content active" id="tab-teams">
    <div class="section-title">分组与排名</div>
    <p class="muted" style="margin-bottom:16px">点击任意球队查看详情（球员/教练/4 维 λ 分解）</p>
    <div class="teams-groups" id="teamsContainer"></div>
  </div>

  <!-- 📅 赛程 -->
  <div class="tab-content" id="tab-schedule">
    <div class="section-title">赛程时间线</div>
    <div class="schedule-tabs" id="scheduleStageTabs">
      <button class="schedule-tab active" data-stage="all">全部</button>
      <button class="schedule-tab" data-stage="group">小组赛</button>
      <button class="schedule-tab" data-stage="R32">32 强</button>
      <button class="schedule-tab" data-stage="R16">16 强</button>
      <button class="schedule-tab" data-stage="QF">8 强</button>
      <button class="schedule-tab" data-stage="SF">半决赛</button>
      <button class="schedule-tab" data-stage="FINAL">决赛</button>
    </div>
    <div class="schedule-list" id="scheduleList"></div>
  </div>

  <!-- 🎛️ 配置 -->
  <div class="tab-content" id="tab-config">
    <div class="section-title">算法参数配置</div>
    <p class="muted" style="margin-bottom:16px">调整 16 个算法系数 → 点击「开始预测」→ 浏览器 1 秒内刷新 32 强</p>
    <div class="config-layout">
      <div class="config-panel">
        <h3 style="margin-bottom:12px">📋 预设</h3>
        <div class="preset-list" id="presetList"></div>
        <div class="config-action">
          <button class="btn" onclick="runPrediction()">🚀 开始预测（离线）</button>
          <button class="btn" onclick="runPredictionLive()" id="btnLiveRecalc" title="需后端: cd backend && python3 server.py">🔄 实时刷新（需后端）</button>
          <button class="btn btn-secondary" onclick="resetConfig()">重置</button>
        </div>
        <div class="config-action">
          <button class="btn btn-secondary" onclick="saveAsPreset()">💾 存为新预设</button>
        </div>
        <p class="muted" style="font-size:11px;margin-top:6px">实时刷新: 调 http://localhost:8765/api/predictions?weights=... 用后端 4 维 λ 算法重算 104 场</p>
      </div>
      <div class="config-panel">
        <div id="slidersContainer"></div>
      </div>
    </div>
    <div class="section-title">📊 32 强排名（实时）</div>
    <div class="preview-area" id="previewArea"></div>
  </div>

  <!-- 🏆 预测 -->
  <div class="tab-content" id="tab-predict">
    <div class="section-title">完整 104 场预测</div>
    <p class="muted" style="margin-bottom:16px">FIFA 2026 官方 bracket 风格：上半区小组赛 (A-F, 6 组) → 淘汰赛 → 下半区小组赛 (G-L, 6 组)</p>
    
    <div class="predict-section">
      <div class="predict-section-title">📋 上半区小组赛 (A-F, 6 组 · 24 场) <span class="count" id="upperGroupCount"></span></div>
      <div class="group-stage" id="upperGroupContainer"></div>
    </div>
    
    <div class="predict-section">
      <div class="predict-section-title">🏆 淘汰赛 (32 场 · 左半区 + 右半区 + 居中决赛 + 季军赛) <span class="count" id="koMatchCount"></span></div>
      <div class="ko-progress" id="koProgress">
        <div class="ko-progress-item">
          <span class="ko-progress-label">小组赛</span>
          <div class="ko-progress-bar"><div class="ko-progress-fill" id="groupProgressFill" style="width:100%; background:linear-gradient(90deg, #3fb950, #2ea043);"></div></div>
          <span class="ko-progress-text" id="groupProgressText" style="color:#3fb950;">72/72</span>
        </div>
        <div class="ko-progress-item">
          <span class="ko-progress-label">R32 32强</span>
          <div class="ko-progress-bar"><div class="ko-progress-fill" id="r32ProgressFill" style="width:0%; background:linear-gradient(90deg, #f0883e, #db6d28);"></div></div>
          <span class="ko-progress-text" id="r32ProgressText" style="color:#f0883e;">0/16</span>
        </div>
        <div class="ko-progress-item">
          <span class="ko-progress-label">R16 16强</span>
          <div class="ko-progress-bar"><div class="ko-progress-fill" id="r16ProgressFill" style="width:0%; background:linear-gradient(90deg, #a371f7, #8957e5);"></div></div>
          <span class="ko-progress-text" id="r16ProgressText" style="color:#a371f7;">0/8</span>
        </div>
        <div class="ko-progress-item">
          <span class="ko-progress-label">QF 8强</span>
          <div class="ko-progress-bar"><div class="ko-progress-fill" id="qfProgressFill" style="width:0%; background:linear-gradient(90deg, #58a6ff, #1f6feb);"></div></div>
          <span class="ko-progress-text" id="qfProgressText" style="color:#58a6ff;">0/4</span>
        </div>
        <div class="ko-progress-item">
          <span class="ko-progress-label">SF 半决赛</span>
          <div class="ko-progress-bar"><div class="ko-progress-fill" id="sfProgressFill" style="width:0%; background:linear-gradient(90deg, #f778ba, #db61a2);"></div></div>
          <span class="ko-progress-text" id="sfProgressText" style="color:#f778ba;">0/2</span>
        </div>
        <div class="ko-progress-item">
          <span class="ko-progress-label">决赛</span>
          <div class="ko-progress-bar"><div class="ko-progress-fill" id="finalProgressFill" style="width:0%; background:linear-gradient(90deg, #ffd700, #ffaa00);"></div></div>
          <span class="ko-progress-text" id="finalProgressText" style="color:#ffd700;">0/1</span>
        </div>
      </div>
      <div class="bracket-container">
        <div class="bracket-flow" id="bracketFlow"></div>
      </div>
    </div>
    
    <div class="predict-section">
      <div class="predict-section-title">📋 下半区小组赛 (G-L, 6 组 · 24 场) <span class="count" id="lowerGroupCount"></span></div>
      <div class="group-stage" id="lowerGroupContainer"></div>
    </div>
  </div>

  <!-- 🆚 对比 -->
  <div class="tab-content" id="tab-compare">
    <div class="section-title">预设对比</div>
    <p class="muted" style="margin-bottom:16px">选两套预设，横向对比 32 强排序</p>
    <div style="display:flex;gap:12px;margin-bottom:16px">
      <div style="flex:1">
        <label>左: 预设 A</label>
        <select id="cmpLeft" class="search-box" style="margin-top:4px"></select>
      </div>
      <div style="flex:1">
        <label>右: 预设 B</label>
        <select id="cmpRight" class="search-box" style="margin-top:4px"></select>
      </div>
    </div>
    <div class="compare-grid">
      <div class="compare-side" id="cmpLeftOut"></div>
      <div class="compare-vs">vs</div>
      <div class="compare-side" id="cmpRightOut"></div>
    </div>
  </div>

  <!-- 🔍 搜索 -->
  <div class="tab-content" id="tab-search">
    <div class="section-title">全局搜索</div>
    <input class="search-box" id="searchInput" placeholder="搜球员姓名 / 球队 / 比赛 / 城市..." oninput="doSearch(this.value)">
    <div class="search-results" id="searchResults"></div>
  </div>

  <div class="tab-content" id="tab-review">
    <div class="section-title">📊 预测复盘分析</div>
    <div class="review-subtitle">已完赛 <span id="rvPlayed">0</span> 场 · 总预测 <span id="rvTotal">0</span> 场 · 完赛率 <span id="rvRate">0</span>%</div>
    <div id="reviewContent"></div>
  </div>

  <div class="tab-content" id="tab-qualify">
    <div class="section-title">🏅 晋级分析 (基于已完赛 <span id="qTotalPlayed">72</span> 场真实积分)</div>
    <div class="review-subtitle">
      已踢 <span id="qPlayed">0</span>/72 场小组赛 ·
      小组前 2 + 8 个最好第 3 = 共 32 队晋级 32 强
    </div>
    <div class="predict-section-title">📊 各小组积分榜 + 晋级状态</div>
    <div id="qualifyGroups"></div>
    <div class="predict-section-title">🎯 12 支小组第 3 排名 (前 8 晋级 32 强)</div>
    <div id="qualifyThird"></div>
    <div class="predict-section-title">🆚 32 强淘汰赛对阵 (基于当前真实积分)</div>
    <div id="qualifyR32"></div>
  </div>

  <div class="footer">
    © Mavis PDP v2.1 · 数据 2026-06 · 单文件离线可跑 · <a href="https://github.com/Henrytudor-lee/worldcup2026" style="color:var(--accent)">Henrytudor-lee/worldcup2026</a>
  </div>
</div>

<!-- 详情 Modal -->
<div class="modal-overlay" id="detailModal" onclick="if(event.target===this)closeModal()">
  <div class="modal" id="modalContent"></div>
</div>

<!-- 比赛详情 Modal (旧版兼容) -->
<div class="modal-overlay" id="matchModal" onclick="if(event.target===this)closeMatchModal()">
  <div class="modal" id="matchModalContent"></div>
</div>

<!-- 已完赛比赛详情弹窗 (区别于预测抽屉, 显示真实数据) -->
<div class="modal-overlay" id="playedPopup" onclick="if(event.target===this)closePlayedMatchPopup()">
  <div class="pp-modal" id="playedPopupContent"></div>
</div>

<!-- 比赛详情 抽屉 (新版: 左右滑出两队详情) -->
<div id="matchDrawer" class="match-drawer">
  <div class="drawer-overlay" onclick="closeMatchDrawer()"></div>
  <aside class="drawer-side left"><div class="side-inner" id="drawerLeft"></div></aside>
  <div class="drawer-center">
    <button class="drawer-close" onclick="closeMatchDrawer()">×</button>
    <div class="center-mini" id="drawerCenter"></div>
  </div>
  <aside class="drawer-side right"><div class="side-inner" id="drawerRight"></div></aside>
</div>

<!-- 嵌入数据 -->
<script id="data-weights" type="application/json">__WEIGHTS__</script>
<script id="data-weights-presets" type="application/json">__WEIGHTS_PRESETS__</script>
<script id="data-weights-presets-meta" type="application/json">__WEIGHTS_PRESETS_META__</script>
<script id="data-ranking" type="application/json">__RANKING__</script>
<script id="data-predictions" type="application/json">__PREDICTIONS__</script>
<script id="data-players" type="application/json">__PLAYERS__</script>
<script id="data-team-stats" type="application/json">__TEAM_STATS__</script>
<script id="data-match-players" type="application/json">__MATCH_PLAYERS__</script>
<script id="data-match-events" type="application/json">__MATCH_EVENTS__</script>

<script>
// ============== 数据加载 ==============
const WEIGHTS = JSON.parse(document.getElementById('data-weights').textContent);
const RANKING = JSON.parse(document.getElementById('data-ranking').textContent);
const PREDICTIONS = JSON.parse(document.getElementById('data-predictions').textContent);
const PLAYERS = JSON.parse(document.getElementById('data-players').textContent);
const TEAM_STATS = JSON.parse(document.getElementById('data-team-stats').textContent);
const MATCH_PLAYERS = JSON.parse(document.getElementById('data-match-players').textContent);
const MATCH_EVENTS = JSON.parse(document.getElementById('data-match-events').textContent);

// 当前权重 (可变)
let currentWeights = JSON.parse(JSON.stringify(WEIGHTS));

// v2.3.2: 6 个预设从 build-time 嵌入的 weights_presets 读, 与后端 weights_schema.PRESETS 同源
const WEIGHTS_PRESETS = JSON.parse(document.getElementById('data-weights-presets').textContent);
const WEIGHTS_PRESETS_META = JSON.parse(document.getElementById('data-weights-presets-meta').textContent);
// 6 个 preset 的 emoji + 名字映射 (UI 显示, 与后端 schema 同步)
const PRESET_ICONS = { 'default': '⚖️', 'high_value': '💰', 'high_form': '🔥', 'low_value': '📉', 'coach_heavy': '👔', 'balance_343': '⚔️' };
const PRESETS = {};
for (const [key, w] of Object.entries(WEIGHTS_PRESETS)) {
  PRESETS[key] = {
    name: WEIGHTS_PRESETS_META[key] || key,
    icon: PRESET_ICONS[key] || '⭐',
    weights: w,
  };
}

// ============== 48 强国旗 + 组别映射 ==============
const FLAGS = {
  // 亚洲 (8)
  '韩国': '🇰🇷', '日本': '🇯🇵', '伊朗': '🇮🇷', '沙特阿拉伯': '🇸🇦', '沙特': '🇸🇦',
  '澳大利亚': '🇦🇺', '卡塔尔': '🇶🇦', '阿联酋': '🇦🇪', '伊拉克': '🇮🇶',
  '约旦': '🇯🇴', '乌兹别克斯坦': '🇺🇿', '海地': '🇭🇹', '库拉索': '🇨🇼', '巴拿马': '🇵🇦',
  // 欧洲 (16)
  '英格兰': '🏴󠁧󠁢󠁥󠁮󠁧󠁿', '法国': '🇫🇷', '西班牙': '🇪🇸', '德国': '🇩🇪',
  '葡萄牙': '🇵🇹', '荷兰': '🇳🇱', '比利时': '🇧🇪', '意大利': '🇮🇹',
  '克罗地亚': '🇭🇷', '瑞士': '🇨🇭', '奥地利': '🇦🇹', '捷克': '🇨🇿',
  '丹麦': '🇩🇰', '瑞典': '🇸🇪', '挪威': '🇳🇴', '波兰': '🇵🇱',
  '苏格兰': '🏴󠁧󠁢󠁳󠁣󠁴󠁿', '土耳其': '🇹🇷', '塞尔维亚': '🇷🇸', '罗马尼亚': '🇷🇴',
  // 美洲 (8)
  '巴西': '🇧🇷', '阿根廷': '🇦🇷', '乌拉圭': '🇺🇾', '哥伦比亚': '🇨🇴',
  '厄瓜多尔': '🇪🇨', '智利': '🇨🇱', '巴拉圭': '🇵🇾', '秘鲁': '🇵🇪',
  '墨西哥': '🇲🇽', '美国': '🇺🇸', '加拿大': '🇨🇦',
  // 非洲 (8)
  '摩洛哥': '🇲🇦', '塞内加尔': '🇸🇳', '尼日利亚': '🇳🇬', '加纳': '🇬🇭',
  '喀麦隆': '🇨🇲', '科特迪瓦': '🇨🇮', '埃及': '🇪🇬', '突尼斯': '🇹🇳',
  '阿尔及利亚': '🇩🇿', '南非': '🇿🇦', '民主刚果': '🇨🇩', '佛得角': '🇨🇻',
  // 大洋洲 (1)
  '新西兰': '🇳🇿',
  // 欧亚混合
  '波黑': '🇧🇦', '乌克兰': '🇺🇦', '威尔士': '🏴󠁧󠁢󠁷󠁬󠁳󠁿', '以色列': '🇮🇱',
  '挪威': '🇳🇴', '俄罗斯': '🇷🇺', '北马其顿': '🇲🇰', '格鲁吉亚': '🇬🇪'
};

// 从 group matches 算出每组的最终排名 (1/2/3/4)
function computeGroupRankings() {
  const gs = {};  // { group: { team: {p, gf, ga, gp} } }
  PREDICTIONS.filter(p => p.stage === 'group').forEach(p => {
    if (!gs[p.group]) gs[p.group] = {};
    if (!gs[p.group][p.home]) gs[p.group][p.home] = {p:0, gf:0, ga:0, gp:0};
    if (!gs[p.group][p.away]) gs[p.group][p.away] = {p:0, gf:0, ga:0, gp:0};
    if (!p.actual_score) return;  // 未开赛不计入
    const [hs, as] = p.actual_score.split('-').map(Number);
    gs[p.group][p.home].gp++;
    gs[p.group][p.away].gp++;
    gs[p.group][p.home].gf += hs;
    gs[p.group][p.away].gf += as;
    gs[p.group][p.home].ga += as;
    gs[p.group][p.away].ga += hs;
    if (p.home_pts === 3) gs[p.group][p.home].p += 3;
    else if (p.home_pts === 1) { gs[p.group][p.home].p += 1; gs[p.group][p.away].p += 1; }
    else gs[p.group][p.away].p += 3;
  });
  const rank = {};  // { team: 'A1'/'A2'/... }
  Object.keys(gs).forEach(g => {
    const sorted = Object.entries(gs[g])
      .map(([team, s]) => ({ team, ...s, gd: s.gf - s.ga }))
      .sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf);
    sorted.forEach((t, i) => { rank[t.team] = `${g}${i + 1}`; });
  });
  return rank;
}
const GROUP_RANK = computeGroupRankings();

function teamTag(team) {
  const flag = FLAGS[team] || '🏳️';
  const rk = GROUP_RANK[team] || '?';
  return { flag, rk };
}

// ============== 工具函数 ==============
function $id(id) { return document.getElementById(id); }
function escHtml(s) { return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]); }
function fmtNum(n) { return Number(n).toLocaleString('zh-CN', {maximumFractionDigits: 1}); }

// 未开赛比赛是否在未来 24h 内 (高亮 - 红)
function isWithin24h(dateStr) {
  if (!dateStr) return false;
  const m = new Date(dateStr.replace(' ', 'T'));
  if (isNaN(m.getTime())) return false;
  const diff = m.getTime() - Date.now();
  return diff > -3600000 && diff < 24 * 3600000;
}

// 未开赛比赛是否在 24-48h 内 (明天开赛 - 橙)
function isTomorrow(dateStr) {
  if (!dateStr) return false;
  const m = new Date(dateStr.replace(' ', 'T'));
  if (isNaN(m.getTime())) return false;
  const diff = m.getTime() - Date.now();
  return diff >= 24 * 3600000 && diff < 48 * 3600000;
}

// 未开赛比赛的时间描述
function whenLabel(dateStr) {
  if (!dateStr) return '';
  const m = new Date(dateStr.replace(' ', 'T'));
  if (isNaN(m.getTime())) return '';
  const now = new Date();
  const days = Math.round((m - now) / 86400000);
  const hhmm = String(m.getHours()).padStart(2,'0') + ':' + String(m.getMinutes()).padStart(2,'0');
  if (days === 0) return '今天 ' + hhmm;
  if (days === 1) return '明天 ' + hhmm;
  if (days === 2) return '后天 ' + hhmm;
  if (days > 0 && days <= 7) return days + ' 天后';
  return dateStr;
}

// ============== 主题切换 ==============
function toggleTheme() {
  const html = document.documentElement;
  const isLight = html.getAttribute('data-theme') === 'light';
  html.setAttribute('data-theme', isLight ? 'dark' : 'light');
  $id('themeBtn').textContent = isLight ? '☀️ 亮色' : '🌙 暗色';
  localStorage.setItem('theme', isLight ? 'dark' : 'light');
}
(function initTheme() {
  const saved = localStorage.getItem('theme') || 'dark';
  if (saved === 'light') { document.documentElement.setAttribute('data-theme', 'light'); $id('themeBtn').textContent = '☀️ 亮色'; }
})();

// ============== Tab 切换 ==============
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    $id('tab-' + tab.dataset.tab).classList.add('active');
    // 切到预测时重画
    if (tab.dataset.tab === 'predict') renderBracket();
    // 切到复盘时加载分析
    if (tab.dataset.tab === 'review') renderReview();
    // 切到晋级时加载分析
    if (tab.dataset.tab === 'qualify') renderQualify();
  });
});

// ============== 球队分组渲染 ==============
function renderTeams() {
  // 按组聚合
  const byGroup = {};
  RANKING.forEach(t => {
    // 从原始数据补 group 字段 (这里用字母推断 A-L)
    if (!byGroup[t.group || 'A']) byGroup[t.group || 'A'] = [];
    byGroup[t.group || 'A'].push(t);
  });
  // 实际我们需要从 predictions 拿组别
  // 简化: 用 RANKING 顺序 4 个一组分 12 组
  const groups = {};
  for (let i = 0; i < RANKING.length; i += 4) {
    const g = String.fromCharCode(65 + (i / 4)); // A, B, C...
    groups[g] = RANKING.slice(i, i + 4);
  }
  // 实际分组从 predictions 推
  const realGroups = {};
  PREDICTIONS.filter(p => p.stage === 'group').forEach(p => {
    if (!realGroups[p.group]) realGroups[p.group] = new Set();
    realGroups[p.group].add(p.home);
    realGroups[p.group].add(p.away);
  });
  
  let html = '';
  Object.keys(realGroups).sort().forEach(g => {
    const teams = Array.from(realGroups[g]);
    // 找每队的 ranking 信息
    const teamsWithRank = teams.map(name => {
      const r = RANKING.find(x => x.team === name);
      return { name, rank: r ? r.rank_r : 0, fifa: r ? r.fifa_rank : 0 };
    }).sort((a, b) => b.rank - a.rank);
    
    html += `<div class="group-card">
      <div class="group-header">第 ${g} 组</div>
      ${teamsWithRank.map(t => `
        <div class="team-card" onclick="openTeamDetail('${escHtml(t.name)}')">
          <span class="team-rank">${fmtNum(t.rank)}</span>
          <span class="team-name">${escHtml(t.name)}</span>
          <span class="team-rating">FIFA ${t.fifa}</span>
        </div>
      `).join('')}
    </div>`;
  });
  $id('teamsContainer').innerHTML = html;
}

// ============== 球队详情 ==============
function openTeamDetail(teamName) {
  const r = RANKING.find(x => x.team === teamName);
  if (!r) return;
  const players = PLAYERS[teamName] || [];
  
  // 球员按位置分
  const byPos = { '前锋': [], '中场': [], '后卫': [], '门将': [] };
  players.forEach(p => {
    if (byPos[p.p]) byPos[p.p].push(p);
  });
  
  let html = `<div class="modal-header">
    <h2>${escHtml(teamName)} · ${fmtNum(r.rank_r)} 分</h2>
    <button class="modal-close" onclick="closeModal()">×</button>
  </div>
  <div class="tabs-mini" id="teamModalTabs">
    <button class="tab-mini active" data-mini="overview">概览</button>
    <button class="tab-mini" data-mini="players">球员 (${players.length})</button>
    <button class="tab-mini" data-mini="matches">赛程</button>
  </div>
  
  <div class="mini-content" data-mini="overview">
    <div class="detail-section">
      <h4>📊 4 维评分</h4>
      <div class="lambda-grid">
        <div class="lambda-card">
          <h5>前锋 Top 3</h5>
          <div class="lam-val">${fmtNum(r.fw_score)}</div>
          <div class="lam-detail">${(r.fw_top_names || []).map(escHtml).join(' / ')}</div>
        </div>
        <div class="lambda-card">
          <h5>中场 Top 3</h5>
          <div class="lam-val">${fmtNum(r.mid_score)}</div>
          <div class="lam-detail">${(r.mid_top_names || []).map(escHtml).join(' / ')}</div>
        </div>
        <div class="lambda-card">
          <h5>后卫 Top 4</h5>
          <div class="lam-val">${fmtNum(r.def_score)}</div>
          <div class="lam-detail">${(r.def_top_names || []).map(escHtml).join(' / ')}</div>
        </div>
        <div class="lambda-card">
          <h5>门将 Top 1</h5>
          <div class="lam-val">${fmtNum(r.gk_score)}</div>
          <div class="lam-detail">${(r.gk_top_names || []).map(escHtml).join(' / ')}</div>
        </div>
      </div>
    </div>
    <div class="detail-section">
      <h4>👔 教练详情</h4>
      ${r.coach_name ? `
        <div class="coach-block">
          <div class="coach-name">${escHtml(r.coach_name)}</div>
          <div class="coach-meta">
            ${r.coach_age ? `<span class="coach-tag">${escHtml(r.coach_age)}</span>` : ''}
            ${r.coach_tenure ? `<span class="coach-tag">任期 ${escHtml(r.coach_tenure)}</span>` : ''}
            <span class="coach-tag">评分 <strong>${fmtNum(r.coach_score)}</strong></span>
            <span class="coach-tag">系数 ${fmtNum(r.coach_r)}</span>
          </div>
          ${r.coach_career ? `<div class="coach-row"><b>履历:</b> ${escHtml(r.coach_career)}</div>` : ''}
          ${r.coach_honors ? `<div class="coach-row"><b>荣誉:</b> ${escHtml(r.coach_honors)}</div>` : ''}
        </div>
      ` : '<p>暂无教练数据</p>'}
    </div>
    <div class="detail-section">
      <h4>🏆 球队总分</h4>
      <p>球员: <strong>${fmtNum(r.player_score)}</strong> · 总: <strong>${fmtNum(r.total)}</strong> · 排名分: ${fmtNum(r.rank_r)}</p>
    </div>
  </div>
  
  <div class="mini-content" data-mini="players" style="display:none">
    <div class="detail-section">
      <h4>⚽ 球员 (${players.length})</h4>
      <div class="player-by-pos">
        ${['门将','后卫','中场','前锋'].map(pos => {
          const list = byPos[pos] || [];
          if (!list.length) return '';
          // 按号码排序
          const sorted = list.slice().sort((a, b) => (parseInt(a.j)||99) - (parseInt(b.j)||99));
          return `
            <div class="pos-block">
              <div class="pos-header">${pos} <span class="pos-count">${list.length} 人</span></div>
              <div class="pos-list">
                ${sorted.map(p => `
                  <div class="player-item-click" onclick="openPlayerDetail('${escHtml(teamName)}', '${escHtml(p.n)}')">
                    <span class="p-jersey">#${p.j||'?'}</span>
                    <span class="p-name">${escHtml(p.n)}</span>
                    <span class="p-club">${escHtml(p.c)}</span>
                    <span class="p-val">€${p.v}万</span>
                  </div>
                `).join('')}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  </div>
  
  <div class="mini-content" data-mini="matches" style="display:none">
    <div class="detail-section">
      <h4>📅 赛程</h4>
      <div class="schedule-list">
        ${PREDICTIONS.filter(p => p.home === teamName || p.away === teamName).map(p => {
          const isUnplayed = p.played === false;
          const soon = isUnplayed && isWithin24h(p.date);
          const tomorrow = isUnplayed && !soon && isTomorrow(p.date);
          const rc = ['match-row'];
          if (isUnplayed) rc.push('unplayed');
          if (soon) rc.push('upcoming-soon');
          else if (tomorrow) rc.push('upcoming-tomorrow');
          return `
          <div class="${rc.join(' ')}" onclick="openMatchByState('${p.match_id}')">
            <div class="match-date">${p.date || ''}</div>
            <div class="match-teams">${escHtml(p.home)} <span class="match-vs">vs</span> ${escHtml(p.away)}</div>
            <div class="match-meta">${p.actual_score || (p.played === false ? '<span class="muted">预测 ' + (p.best_score || '?') + '</span>' + (p.date ? ' · ' + escHtml(whenLabel(p.date)) : '') : '')} ${p.went_to_pen ? '(点球)' : ''}</div>
          </div>
        `;}).join('')}
      </div>
    </div>
  </div>
  `;
  
  $id('modalContent').innerHTML = html;
  $id('detailModal').classList.add('open');
  
  // mini tabs
  document.querySelectorAll('#teamModalTabs .tab-mini').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#teamModalTabs .tab-mini').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('#modalContent .mini-content').forEach(c => c.style.display = 'none');
      document.querySelector(`#modalContent .mini-content[data-mini="${btn.dataset.mini}"]`).style.display = 'block';
    });
  });
}

function closeModal() { $id('detailModal').classList.remove('open'); }

// ============== 球员详情 (复用 detailModal) ==============
function openPlayerDetail(teamName, playerName) {
  const list = PLAYERS[teamName] || [];
  const p = list.find(x => x.n === playerName);
  if (!p) return;
  const r = RANKING.find(x => x.team === teamName);

  // 从 4 维 details 里找 (apps_2025_26/goals_2025_26/assists_2025_26/whoscored)
  const posKey = p.p === '门将' ? 'gk_details' : p.p === '后卫' ? 'def_details' : p.p === '中场' ? 'mid_details' : 'fw_details';
  const full = (r && r[posKey]) ? r[posKey].find(x => x.name === playerName) : null;

  // 优先级: PLAYERS(v22) wg/wa/ng/na > RANKING details > X待核实
  // goals/assists 显示: 优先 wg/wa (v22), fallback goals_2025_26/assists_2025_26 (ranking)
  const ng = p.ng || (full ? full.nat_goals : '');
  const na = p.na || (full ? full.nat_assists : '');
  const wg = p.wg || (full ? full.goals_2025_26 : '');
  const wa = p.wa || (full ? full.assists_2025_26 : '');
  const apps = full && full.apps_2025_26 && full.apps_2025_26 !== '—' ? full.apps_2025_26 : '';
  const goals = wg || (full && full.goals_2025_26 && full.goals_2025_26 !== '—' ? full.goals_2025_26 : '');
  const assists = wa || (full && full.assists_2025_26 && full.assists_2025_26 !== '—' ? full.assists_2025_26 : '');
  const who = full && full.whoscored && full.whoscored !== '—' ? full.whoscored : '';

  const statFields = [
    { v: ng, l: '🏳️ 国家队进球' },
    { v: na, l: '🏳️ 国家队助攻' },
    { v: apps, l: '⚽ 25-26 出场' },
    { v: goals, l: '⚽ 25-26 进球' },
    { v: assists, l: '🅰️ 25-26 助攻' },
    { v: who, l: '⭐ whoscored 评分' },
  ];

  const statsHtml = statFields.filter(f => f.v && f.v !== '—').map(f =>
    `<div class="pd-stat"><div class="pd-stat-v">${escHtml(String(f.v))}</div><div class="pd-stat-l">${f.l}</div></div>`
  ).join('');

  let html = `<div class="modal-header">
    <h2>${escHtml(p.n)} <span style="color:var(--text-3);font-weight:normal;font-size:14px">${escHtml(teamName)}</span></h2>
    <button class="modal-close" onclick="closeModal()">×</button>
  </div>

  <div class="player-detail">
    <div class="pd-header">
      <div class="pd-jersey">#${p.j || '?'}</div>
      <div class="pd-info">
        <div class="pd-pos">${escHtml(p.p)}</div>
        <div class="pd-club">${escHtml(p.c)} · ${escHtml(p.l)}</div>
        <div class="pd-val">€${p.v}万</div>
      </div>
    </div>

    <div class="pd-section">
      <h4>📊 25-26 赛季数据</h4>
      <div class="pd-stats">
        ${statsHtml || '<p class="muted">暂无赛季数据 (X待核实)</p>'}
      </div>
    </div>

    ${p.h ? `
      <div class="pd-section">
        <h4>🏆 荣誉 / 履历</h4>
        <p>${escHtml(p.h)}</p>
      </div>
    ` : ''}
  </div>
  `;

  $id('modalContent').innerHTML = html;
  $id('detailModal').classList.add('open');
}

// ============== 赛程 ==============
let scheduleFilter = 'all';
function renderSchedule() {
  let matches = PREDICTIONS;
  if (scheduleFilter !== 'all') matches = matches.filter(p => p.stage === scheduleFilter);
  // 排序: group 按日期; KO 按 stage 顺序
  matches.sort((a, b) => {
    if (a.stage === 'group' && b.stage === 'group') return (a.date || '').localeCompare(b.date || '');
    if (a.stage !== 'group' && b.stage !== 'group') {
      const order = ['R32','R16','QF','SF','FINAL','3RD'];
      return order.indexOf(a.stage) - order.indexOf(b.stage);
    }
    return a.stage === 'group' ? -1 : 1;
  });
  
  $id('scheduleList').innerHTML = matches.map(p => {
    const isUnplayed = p.played === false;
    const soon = isUnplayed && isWithin24h(p.date);
    const tomorrow = isUnplayed && !soon && isTomorrow(p.date);
    const rowClasses = ['match-row'];
    if (isUnplayed) rowClasses.push('unplayed');
    if (soon) rowClasses.push('upcoming-soon');
    else if (tomorrow) rowClasses.push('upcoming-tomorrow');
    return `
    <div class="${rowClasses.join(' ')}" onclick="openMatchByState('${p.match_id}')">
      <div class="match-date">${p.date || '-'} <br>${p.round || p.stage || ''}</div>
      <div class="match-teams">${escHtml(p.home)} <span class="match-vs">vs</span> ${escHtml(p.away)}</div>
      <div class="match-meta">${p.actual_score ? p.actual_score + (p.went_to_pen ? ' (点球)' : '') : (p.played === false ? '预测 ' + (p.best_score || '?') + (p.date ? ' · ' + escHtml(whenLabel(p.date)) : '') : '')}<br>λ ${fmtNum(p.lambda_home)} vs ${fmtNum(p.lambda_away)}</div>
    </div>
  `;}).join('');
}
document.querySelectorAll('#scheduleStageTabs .schedule-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#scheduleStageTabs .schedule-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    scheduleFilter = btn.dataset.stage;
    renderSchedule();
  });
});

// ============== 比赛详情 ==============
function openMatchDetail(matchId) {
  const p = PREDICTIONS.find(x => x.match_id === matchId);
  if (!p) return;

  // 计算 Top 5 比分概率 (Poisson 简化)
  const topScores = computeTopScores(p.lambda_home, p.lambda_away, 6);

  // 横向概率条 (主胜 / 平 / 客胜)
  const ph = (p.p_home_win * 100).toFixed(1);
  const pd = (p.p_draw * 100).toFixed(1);
  const pa = (p.p_away_win * 100).toFixed(1);
  const barHtml = `
    <div class="prob-bar">
      <div class="prob-seg home" style="width:${ph}%"><span>${ph}%</span></div>
      <div class="prob-seg draw" style="width:${pd}%"><span>${pd}%</span></div>
      <div class="prob-seg away" style="width:${pa}%"><span>${pa}%</span></div>
    </div>
    <div class="prob-bar-labels">
      <span>主胜 ${escHtml(p.home)}</span>
      <span>平局</span>
      <span>客胜 ${escHtml(p.away)}</span>
    </div>`;

  // 比分概率矩阵 (Top 6)
  const scoreRows = topScores.map(s => {
    const pct = (s.p * 100).toFixed(1);
    const w = Math.min(s.p * 100 * 3, 100);  // 视觉宽度放大
    return `<tr>
      <td><strong>${s.h}-${s.a}</strong></td>
      <td><div class="score-bar-track"><div class="score-bar-fill" style="width:${w}%"></div></div></td>
      <td class="num">${pct}%</td>
    </tr>`;
  }).join('');

  let html = `<div class="modal-header">
    <h2>${escHtml(p.home)} <span class="vs-tag">vs</span> ${escHtml(p.away)}</h2>
    <button class="modal-close" onclick="closeMatchModal()">×</button>
  </div>

  <div class="detail-section">
    <div class="match-meta-line">
      <span>📅 ${escHtml(p.date || '-')}</span>
      <span>🏷️ ${escHtml(p.round || p.stage || '')}</span>
      ${p.group ? `<span>第 ${escHtml(p.group)} 组</span>` : ''}
      ${p.stadium ? `<span>🏟️ ${escHtml(p.stadium)} · ${escHtml(p.city || '')}</span>` : ''}
    </div>
  </div>

  <div class="lambda-grid">
    <div class="lambda-card">
      <h5>${escHtml(p.home)} (主)</h5>
      <div class="lam-val">λ = ${fmtNum(p.lambda_home)}</div>
      <div class="lam-detail">胜率: ${ph}%</div>
    </div>
    <div class="lambda-card">
      <h5>平局</h5>
      <div class="lam-val">${pd}%</div>
      <div class="lam-detail">预测比分: ${escHtml(p.best_score || '-')}</div>
    </div>
    <div class="lambda-card">
      <h5>${escHtml(p.away)} (客)</h5>
      <div class="lam-val">λ = ${fmtNum(p.lambda_away)}</div>
      <div class="lam-detail">胜率: ${pa}%</div>
    </div>
  </div>

  <div class="detail-section">
    <h4>📈 胜负概率分布</h4>
    ${barHtml}
  </div>

  <div class="detail-section">
    <h4>⚽ 比分概率 Top 6</h4>
    <table class="score-prob-table">
      <thead><tr><th style="width:60px">比分</th><th></th><th style="width:70px">概率</th></tr></thead>
      <tbody>${scoreRows}</tbody>
    </table>
  </div>

  <div class="detail-section">
    <h4>📊 比赛结果</h4>
    <p>比分: <strong>${p.actual_score ? escHtml(p.actual_score) : (p.played === false ? '预测 ' + escHtml(p.best_score || '?') : '-')}</strong> ${p.went_to_pen ? '(点球大战)' : ''} ${p.home_pts !== undefined && p.home_pts !== null ? `· 主队 ${p.home_pts} 分 客队 ${p.away_pts} 分` : ''}</p>
    ${p.played === false && p.best_score ? `<p class="muted">最可能比分: ${escHtml(p.best_score)} (${(p.best_score_prob*100).toFixed(1)}%)</p>` : ''}
    <p>预期总进球: <strong>${fmtNum(p.expected_total || 0)}</strong> · 预期净胜: <strong>${fmtNum(p.expected_diff || 0)}</strong></p>
  </div>

  ${p.venue_alt || p.venue_temp ? `<div class="detail-section">
    <h4>🌡️ 场地环境</h4>
    <div class="env-grid">
      ${p.venue_alt !== undefined ? `<div class="env-card"><div class="env-label">⛰️ 海拔</div><div class="env-val">${p.venue_alt} m</div></div>` : ''}
      ${p.venue_temp !== undefined ? `<div class="env-card"><div class="env-label">🌡️ 温度</div><div class="env-val">${p.venue_temp} °C</div></div>` : ''}
      ${p.venue_humidity !== undefined ? `<div class="env-card"><div class="env-label">💧 湿度</div><div class="env-val">${p.venue_humidity}%</div></div>` : ''}
      ${p.roof ? `<div class="env-card"><div class="env-label">🏟️ 顶棚</div><div class="env-val">${escHtml(p.roof)}</div></div>` : ''}
    </div>
    ${p.weather_note ? `<p class="muted" style="margin-top:8px">${escHtml(p.weather_note)}</p>` : ''}
  </div>` : ''}
  `;

  $id('matchModalContent').innerHTML = html;
  $id('matchModal').classList.add('open');
}

// Poisson PMF + Top N 比分
const _logFact = [0, 0];
for (let i = 2; i <= 10; i++) _logFact[i] = _logFact[i-1] + Math.log(i);
function _poisPmf(k, lambda) {
  if (k < 0 || lambda <= 0) return 0;
  return Math.exp(-lambda + k * Math.log(lambda) - _logFact[k]);
}
function computeTopScores(lambdaH, lambdaA, n = 6) {
  const arr = [];
  for (let h = 0; h <= 5; h++) {
    for (let a = 0; a <= 5; a++) {
      arr.push({ h, a, p: _poisPmf(h, lambdaH) * _poisPmf(a, lambdaA) });
    }
  }
  arr.sort((a, b) => b.p - a.p);
  return arr.slice(0, n);
}
function closeMatchModal() { $id('matchModal').classList.remove('open'); }

// 清理 round 字段重复的「第」和「轮」(如"小组A第第1轮轮" → "小组A第1轮")
function cleanRound(s) {
  if (!s) return '';
  return String(s).replace(/第+/g, '第').replace(/轮+/g, '轮');
}

// ============== 已完赛比赛详情弹窗 (区别于预测抽屉, 显示真实数据) ==============
function openPlayedMatchPopup(matchId) {
  const p = PREDICTIONS.find(x => x.match_id === matchId);
  if (!p || !p.actual_score) return;
  const homeFlag = FLAGS[p.home] || '';
  const awayFlag = FLAGS[p.away] || '';
  const homeRank = RANKING.find(t => t.team === p.home);
  const awayRank = RANKING.find(t => t.team === p.away);
  const homeRk = homeRank ? `#${homeRank.rank}` : '';
  const awayRk = awayRank ? `#${awayRank.rank}` : '';
  const [hs, as] = p.actual_score.split('-').map(Number);
  const homeWin = hs > as;
  const awayWin = as > hs;
  const isDraw = hs === as;
  const winnerText = isDraw ? '🤝 平局' : (homeWin ? `🏆 ${p.home} 胜` : `🏆 ${p.away} 胜`);
  const winnerCls = isDraw ? 'draw' : (homeWin ? 'home-win' : 'away-win');
  const stageText = p.stage === 'group' ? `小组${p.group || ''}` : (p.round ? cleanRound(p.round) : (p.stage || '淘汰赛'));

  // 拉详情数据
  const k = `${p.home}_vs_${p.away}`;
  const ts = TEAM_STATS[k];
  const players = MATCH_PLAYERS[k] || {home: [], away: []};
  const events = MATCH_EVENTS[k] || [];

  // ===== 控球率条 =====
  let possessionBar = '';
  if (ts && ts.h_poss != null) {
    const hp = ts.h_poss, ap = ts.a_poss;
    possessionBar = `
      <div class="pp-possession">
        <div class="pp-poss-label"><b style="color:var(--accent)">${hp}%</b> <span class="muted">控球</span></div>
        <div class="pp-poss-track">
          <div class="pp-poss-fill home" style="width:${hp}%"></div>
          <div class="pp-poss-fill away" style="width:${ap}%"></div>
        </div>
        <div class="pp-poss-label"><span class="muted">控球</span> <b style="color:var(--accent-2)">${ap}%</b></div>
      </div>`;
  }

  // ===== 8 项技术统计 =====
  let statsGrid = '';
  if (ts) {
    const stats = [
      { label: '射门', h: ts.h_shots, a: ts.a_shots },
      { label: '射正', h: ts.h_sot, a: ts.a_sot },
      { label: '角球', h: ts.h_corners, a: ts.a_corners },
      { label: '犯规', h: ts.h_fouls, a: ts.a_fouls },
      { label: '黄牌', h: ts.h_yc, a: ts.a_yc, warn: true },
      { label: '红牌', h: ts.h_rc, a: ts.a_rc, warn: true },
      { label: '越位', h: ts.h_off, a: ts.a_off },
      { label: '扑救', h: ts.h_saves, a: ts.a_saves },
    ];
    statsGrid = `<div class="pp-stats">
      ${stats.map(s => {
        const cls = s.warn ? 'warn' : '';
        return `<div class="pp-stat-row ${cls}">
          <span class="pp-stat-h ${s.h > s.a ? 'lead' : ''}">${s.h}</span>
          <span class="pp-stat-lbl">${s.label}</span>
          <span class="pp-stat-a ${s.a > s.h ? 'lead' : ''}">${s.a}</span>
        </div>`;
      }).join('')}
    </div>
    <div class="pp-stats-extra">
      <div><span class="muted">传球</span> <b>${ts.h_pass}</b> · <b>${ts.a_pass}</b></div>
      <div><span class="muted">传球准确率</span> <b style="color:var(--accent)">${ts.h_pass_pct != null ? (ts.h_pass_pct*100).toFixed(0)+'%' : '-'}</b> · <b style="color:var(--accent-2)">${ts.a_pass_pct != null ? (ts.a_pass_pct*100).toFixed(0)+'%' : '-'}</b></div>
    </div>`;
  }

  // ===== 比赛事件时间轴 =====
  let eventsHtml = '';
  if (events.length) {
    const evtIcon = {
      'Goal': '⚽', 'Yellow Card': '🟨', 'Red Card': '🟥',
      'Substitution': '🔄', 'Penalty - Scored': '⚽', 'Penalty - Missed': '❌',
      'VAR': '📺', 'Offside': '🚩',
    };
    eventsHtml = `<div class="pp-events">
      ${events.map(e => {
        const isHome = e.team === p.home;
        const icon = evtIcon[e.type] || '•';
        const side = isHome ? 'home' : 'away';
        const typeLabel = ({'Goal':'进球', 'Yellow Card':'黄牌', 'Red Card':'红牌', 'Substitution':'换人', 'Penalty - Scored':'点球', 'Penalty - Missed':'点球罚失', 'VAR':'VAR', 'Offside':'越位'})[e.type] || e.type;
        return `<div class="pp-event ${side}">
          <span class="pp-event-clock">${escHtml(e.clock)}</span>
          <span class="pp-event-icon">${icon}</span>
          <span class="pp-event-info">
            <b>${escHtml(e.player)}</b>
            <span class="muted"> · ${escHtml(typeLabel)} · ${escHtml(e.team)}</span>
          </span>
        </div>`;
      }).join('')}
    </div>`;
  } else if (!ts) {
    eventsHtml = `<div class="pp-missing">📋 详细事件数据待核实<br><span class="pp-missing-sub">ESPN 原始数据未抓到这场比赛的详情</span></div>`;
  }

  // ===== 球员亮点 (Top 进球 / 助攻 / 红黄牌) =====
  let playersHtml = '';
  if (players.home.length || players.away.length) {
    const all = [...players.home, ...players.away];
    const scorers = all.filter(x => x.g > 0).sort((a,b) => b.g - a.g || b.a - a.a);
    const assisters = all.filter(x => x.a > 0 && x.g === 0).sort((a,b) => b.a - a.a);
    const carded = all.filter(x => x.yc > 0 || x.rc > 0 || x.og > 0).sort((a,b) => (b.rc*10+b.yc) - (a.rc*10+a.yc)).slice(0, 4);
    const topMin = all.filter(x => x.min > 0).sort((a,b) => b.min - a.min).slice(0, 4);

    const sectionHtml = (title, list, render, empty) => {
      if (!list.length) return empty ? `<div class="pp-player-section"><h5>${title}</h5><p class="muted">${empty}</p></div>` : '';
      return `<div class="pp-player-section">
        <h5>${title}</h5>
        <div class="pp-player-list">${list.map(render).join('')}</div>
      </div>`;
    };

    const pRow = (pl) => {
      const side = players.home.includes(pl) ? p.home : p.away;
      const flag = FLAGS[side] || '';
      return `<div class="pp-player-row">
        <span class="pp-pr-flag">${flag}</span>
        <span class="pp-pr-name">${escHtml(pl.n)}</span>
        <span class="pp-pr-meta">#${pl.j || '?'} · ${escHtml(pl.pos || '')} · ${pl.min}'</span>
      </div>`;
    };

    playersHtml = `
      <div class="pp-player-grid">
        ${sectionHtml('⚽ 进球', scorers, (pl) => `<div class="pp-player-row">
          <span class="pp-pr-flag">${FLAGS[(players.home.includes(pl)?p.home:p.away)]||''}</span>
          <span class="pp-pr-name">${escHtml(pl.n)}</span>
          <span class="pp-pr-stats"><b style="color:var(--green)">${pl.g} 球</b>${pl.a ? ` · ${pl.a} 助攻` : ''}</span>
        </div>`, '无进球')}
        ${sectionHtml('🅰️ 助攻 (无进球)', assisters, (pl) => `<div class="pp-player-row">
          <span class="pp-pr-flag">${FLAGS[(players.home.includes(pl)?p.home:p.away)]||''}</span>
          <span class="pp-pr-name">${escHtml(pl.n)}</span>
          <span class="pp-pr-stats"><b style="color:var(--accent-2)">${pl.a} 助攻</b></span>
        </div>`, '')}
        ${sectionHtml('🟨🟥 红黄牌', carded, (pl) => `<div class="pp-player-row">
          <span class="pp-pr-flag">${FLAGS[(players.home.includes(pl)?p.home:p.away)]||''}</span>
          <span class="pp-pr-name">${escHtml(pl.n)}</span>
          <span class="pp-pr-stats">${pl.rc ? `<b style="color:var(--red)">${pl.rc} 红</b>` : ''}${pl.yc ? ` <b style="color:var(--gold)">${pl.yc} 黄</b>` : ''}${pl.og ? ` <b style="color:var(--red)">${pl.og} 乌龙</b>` : ''}</span>
        </div>`, '无')}
        ${sectionHtml('⏱ 出场时间 Top 4', topMin, pRow, '')}
      </div>`;
  }

  $id('playedPopupContent').innerHTML = `
    <div class="pp-header">
      <button class="modal-close" onclick="closePlayedMatchPopup()">×</button>
      <div class="pp-stage">${escHtml(stageText)}</div>
      <div class="pp-title">
        <div class="pp-team home ${homeWin ? 'winner' : ''}">
          <div class="pp-flag">${homeFlag}</div>
          <div class="pp-name">${escHtml(p.home)} <span class="pp-rk">${homeRk}</span></div>
        </div>
        <div class="pp-score">
          <div class="pp-score-num">${hs}<span class="pp-score-sep">-</span>${as}</div>
          <div class="pp-score-lbl">全场结束</div>
        </div>
        <div class="pp-team away ${awayWin ? 'winner' : ''}">
          <div class="pp-flag">${awayFlag}</div>
          <div class="pp-name">${escHtml(p.away)} <span class="pp-rk">${awayRk}</span></div>
        </div>
      </div>
      <div class="pp-result ${winnerCls}">${winnerText} · 主队 ${p.home_pts} 分 / 客队 ${p.away_pts} 分</div>
    </div>
    <div class="pp-body-grid">
      <div class="pp-section col-l">
        <h4>📅 比赛信息</h4>
        <div class="pp-grid">
          <div><span class="pp-lbl">日期</span><span class="pp-val">${escHtml(p.date || '-')}</span></div>
          <div><span class="pp-lbl">球场</span><span class="pp-val">${escHtml(p.stadium || ts?.venue || '-')}</span></div>
          <div><span class="pp-lbl">城市</span><span class="pp-val">${escHtml(p.city || '-')}</span></div>
          <div><span class="pp-lbl">分组</span><span class="pp-val">第 ${escHtml(p.group || '?')} 组</span></div>
          <div><span class="pp-lbl">⛰️ 海拔</span><span class="pp-val">${p.venue_alt || '-'} m</span></div>
          <div><span class="pp-lbl">🌡️ 温度</span><span class="pp-val">${p.venue_temp || '-'} °C</span></div>
          ${p.weather_note ? `<div class="pp-info-full">${escHtml(p.weather_note)}</div>` : ''}
        </div>
      </div>

      ${ts ? `
      <div class="pp-section col-r">
        <h4>📊 比赛统计</h4>
        ${possessionBar}
        ${statsGrid}
      </div>
      ` : ''}

      ${events.length ? `
      <div class="pp-section col-l">
        <h4>⏱ 比赛事件 (${events.length})</h4>
        ${eventsHtml}
      </div>
      ` : ''}

      ${playersHtml ? `
      <div class="pp-section col-r">
        <h4>⭐ 球员亮点</h4>
        ${playersHtml}
      </div>
      ` : ''}

      <div class="pp-section full">
        <h4>📊 算法预测 vs 实际</h4>
        <div class="pp-pred-compare">
          <div class="pp-pc-cell"><span class="muted">最可能比分</span><b>${escHtml(p.best_score || '-')}</b>${p.best_score_prob ? ` <span class="muted">(${(p.best_score_prob*100).toFixed(1)}%)</span>` : ''}</div>
          <div class="pp-pc-cell"><span class="muted">实际比分</span><b style="color:var(--green)">${escHtml(p.actual_score)}</b></div>
          <div class="pp-pc-cell"><span class="muted">主胜</span><b>${(p.p_home_win*100).toFixed(1)}%</b></div>
          <div class="pp-pc-cell"><span class="muted">平局</span><b>${(p.p_draw*100).toFixed(1)}%</b></div>
          <div class="pp-pc-cell"><span class="muted">客胜</span><b>${(p.p_away_win*100).toFixed(1)}%</b></div>
        </div>
      </div>
    </div>
  `;
  $id('playedPopup').classList.add('open');
  // 关闭抽屉避免遮挡
  const dr = $id('matchDrawer');
  if (dr && dr.classList.contains('open')) dr.classList.remove('open');
}
function closePlayedMatchPopup() { $id('playedPopup').classList.remove('open'); }

// 调度器: 已完赛 → 弹窗, 未开赛 → 抽屉
function openMatchByState(matchId) {
  const p = PREDICTIONS.find(x => x.match_id === matchId);
  if (!p) return;
  if (p.actual_score) openPlayedMatchPopup(matchId);
  else openMatchDrawer(matchId);
}

// ============== 比赛详情抽屉 (新版左右滑出) ==============
function openMatchDrawer(matchId) {
  const p = PREDICTIONS.find(x => x.match_id === matchId);
  if (!p) return;
  const homeData = RANKING.find(t => t.team === p.home);
  const awayData = RANKING.find(t => t.team === p.away);
  $id('drawerLeft').innerHTML = renderTeamPanel(p.home, homeData, 'home');
  $id('drawerRight').innerHTML = renderTeamPanel(p.away, awayData, 'away');
  $id('drawerCenter').innerHTML = renderCenterPanel(p);
  $id('matchDrawer').classList.add('open');
  // bind expand toggles
  document.querySelectorAll('.pos-header').forEach(h => {
    h.addEventListener('click', () => h.nextElementSibling.classList.toggle('collapsed'));
  });
  document.querySelectorAll('.player-row[data-pid]').forEach(r => {
    r.addEventListener('click', e => {
      e.stopPropagation();
      const det = document.getElementById('pd-' + r.dataset.pid);
      if (det) det.style.display = det.style.display === 'none' ? 'block' : 'none';
    });
  });
}
function closeMatchDrawer() { $id('matchDrawer').classList.remove('open'); }
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    const d = $id('matchDrawer');
    const pp = $id('playedPopup');
    if (pp && pp.classList.contains('open')) closePlayedMatchPopup();
    else if (d && d.classList.contains('open')) closeMatchDrawer();
  }
});

function renderCenterPanel(p) {
  const ph = (p.p_home_win * 100).toFixed(1);
  const pd = (p.p_draw * 100).toFixed(1);
  const pa = (p.p_away_win * 100).toFixed(1);
  const homeFlag = FLAGS[p.home] || '';
  const awayFlag = FLAGS[p.away] || '';
  const homeRank = RANKING.find(t => t.team === p.home);
  const awayRank = RANKING.find(t => t.team === p.away);
  const homeRk = homeRank ? `#${homeRank.rank}` : '';
  const awayRk = awayRank ? `#${awayRank.rank}` : '';
  const topScores = computeTopScores(p.lambda_home, p.lambda_away, 6);
  return `
    <div class="cm-title">
      <span class="cm-flag">${homeFlag}</span>
      <span>${escHtml(p.home)} <span style="color:var(--text-3);font-weight:normal;font-size:13px">${homeRk}</span></span>
      <span class="cm-vs-tag">vs</span>
      <span>${awayFlag ? `<span class="cm-flag">${awayFlag}</span>` : ''}${escHtml(p.away)} <span style="color:var(--text-3);font-weight:normal;font-size:13px">${awayRk}</span></span>
    </div>
    <div class="cm-meta">
      <span>📅 ${escHtml(p.date || '-')}</span>
      ${p.round ? `<span>🏷️ ${escHtml(cleanRound(p.round))}</span>` : ''}
      ${p.group ? `<span>第 ${escHtml(p.group)} 组</span>` : ''}
      ${p.stadium ? `<span>🏟️ ${escHtml(p.stadium)}</span>` : ''}
      ${p.city ? `<span>📍 ${escHtml(p.city)}</span>` : ''}
    </div>
    <div class="cm-lam">
      <div>
        <div class="cm-team-name">${homeFlag} ${escHtml(p.home)} (主)</div>
        <div>λ = <b>${fmtNum(p.lambda_home)}</b> · 胜率 <b style="color:var(--green)">${ph}%</b></div>
      </div>
      <div>
        <div class="cm-team-name">${awayFlag} ${escHtml(p.away)} (客)</div>
        <div>λ = <b>${fmtNum(p.lambda_away)}</b> · 胜率 <b style="color:var(--red)">${pa}%</b></div>
      </div>
    </div>
    <div class="cm-prob">
      <div class="h" style="width:${ph}%">${ph}%</div>
      <div class="d" style="width:${pd}%">${pd}%</div>
      <div class="a" style="width:${pa}%">${pa}%</div>
    </div>
    <div class="cm-prob-labels">
      <span>主胜</span><span>平局 ${pd}%</span><span>客胜</span>
    </div>

    <div class="cm-section">
      <h4>⚽ 比分概率 Top 6</h4>
      <table class="cm-scores">
        ${topScores.map(s => {
          const pct = (s.p * 100).toFixed(1);
          const w = Math.min(s.p * 100 * 3, 100);
          return `<tr>
            <td style="width:50px"><strong>${s.h}-${s.a}</strong></td>
            <td><div class="sc-bar-track"><div class="sc-bar-fill" style="width:${w}%"></div></div></td>
            <td style="width:60px">${pct}%</td>
          </tr>`;
        }).join('')}
      </table>
    </div>

    <div class="cm-section">
      <h4>📊 比赛结果</h4>
      <div class="cm-result">
        比分: <strong>${p.actual_score ? escHtml(p.actual_score) : (p.played === false ? '预测 ' + escHtml(p.best_score || '?') : '-')}</strong>
        ${p.went_to_pen ? '<span style="font-size:11px;color:var(--text-3)"> (点球大战)</span>' : ''}
        ${p.home_pts !== undefined && p.home_pts !== null ? ` · 主队 <b>${p.home_pts}</b> 分 客队 <b>${p.away_pts}</b> 分` : ''}
      </div>
      ${p.played === false && p.best_score ? `<div class="cm-result">最可能比分: <strong>${escHtml(p.best_score)}</strong> (${(p.best_score_prob*100).toFixed(1)}%)</div>` : ''}
      <div class="cm-result">预期总进球: <strong>${fmtNum(p.expected_total || 0)}</strong> · 预期净胜: <strong>${fmtNum(p.expected_diff || 0)}</strong></div>
    </div>

    ${p.venue_alt || p.venue_temp ? `<div class="cm-section">
      <h4>🌡️ 场地环境</h4>
      <div class="cm-env">
        ${p.venue_alt !== undefined ? `<div><div class="ce-label">⛰️ 海拔</div><div class="ce-val">${p.venue_alt} m</div></div>` : ''}
        ${p.venue_temp !== undefined ? `<div><div class="ce-label">🌡️ 温度</div><div class="ce-val">${p.venue_temp} °C</div></div>` : ''}
        ${p.venue_humidity !== undefined ? `<div><div class="ce-label">💧 湿度</div><div class="ce-val">${p.venue_humidity}%</div></div>` : ''}
        ${p.roof ? `<div><div class="ce-label">🏟️ 顶棚</div><div class="ce-val">${escHtml(p.roof)}</div></div>` : ''}
      </div>
      ${p.weather_note ? `<div class="cm-info">${escHtml(p.weather_note)}</div>` : ''}
    </div>` : ''}

    <div class="cm-tips">👈 左抽屉 = ${escHtml(p.home)} 完整资料 (教练/主力 11/26人大名单/赛程)<br>👉 右抽屉 = ${escHtml(p.away)} 完整资料</div>
  `;
}

function renderTeamPanel(teamName, data, side) {
  if (!data) return `<div class="team-hdr"><div class="th-name">${escHtml(teamName)}</div><div class="muted">无数据</div></div>`;
  const flag = FLAGS[teamName] || '';
  const fw = data.fw_top_full || [];
  const mid = data.mid_top_full || [];
  const def = data.def_top_full || [];
  const gk = data.gk_top_full || [];
  const fwDet = data.fw_details || [];
  const midDet = data.mid_details || [];
  const defDet = data.def_details || [];
  const gkDet = data.gk_details || [];
  const coach = data.coach_name || '—';
  const coachAge = data.coach_age || '—';
  const coachTenure = data.coach_tenure || '';
  const coachCareer = data.coach_career || '';
  const coachHonors = (data.coach_honors || '').split(/[,，、]/).map(s => s.trim()).filter(Boolean);

  // 球队赛程
  const teamMatches = PREDICTIONS.filter(x => x.home === teamName || x.away === teamName)
    .sort((a, b) => (a.date || '').localeCompare(b.date || ''));
  const schedHtml = teamMatches.map(m => renderSchedRow(m, teamName)).join('');

  // 完整 26 人名单
  const roster = (PLAYERS[teamName] || []).slice().sort((a, b) => {
    const posOrder = { '门将': 0, '后卫': 1, '中场': 2, '前锋': 3 };
    return (posOrder[a.p] ?? 9) - (posOrder[b.p] ?? 9) || (parseInt(b.v) || 0) - (parseInt(a.v) || 0);
  });
  const rosterHtml = roster.map(pl => `
    <div class="roster-row" title="${escHtml(pl.c || '')} · ${escHtml(pl.h || '')}">
      <span class="rr-jersey">${pl.j || '-'}</span>
      <span class="rr-name">${escHtml(pl.n)}</span>
      <span class="rr-pos">${escHtml(pl.p || '')}</span>
      <span class="rr-value">${pl.v ? pl.v + '万€' : '-'}</span>
    </div>
  `).join('');

  return `
    <div class="team-hdr">
      <div class="th-flag">${flag}</div>
      <div class="th-name">${escHtml(teamName)}</div>
      <div class="th-ranks">
        <span class="rk-chip">FIFA #${data.fifa_rank || '-'}</span>
        <span class="rk-chip">实力 #${data.rank || '-'}</span>
        <span class="rk-chip">分 ${fmtNum(data.total || 0)}</span>
      </div>
      <div class="th-4d">
        <div>FW<b>${fmtNum(data.fw_score || 0)}</b></div>
        <div>MID<b>${fmtNum(data.mid_score || 0)}</b></div>
        <div>DEF<b>${fmtNum(data.def_score || 0)}</b></div>
        <div>GK<b>${fmtNum(data.gk_score || 0)}</b></div>
      </div>
    </div>

    <section class="side-section">
      <h3>👔 主教练</h3>
      <div class="coach-card">
        <div class="c-name">${escHtml(coach)}</div>
        <div class="c-meta">${escHtml(coachAge)} · 任期 ${escHtml(coachTenure || '—')}</div>
        ${coachCareer ? `<div class="c-row"><span class="c-label">生涯:</span>${escHtml(coachCareer)}</div>` : ''}
        ${coachHonors.length ? `<div class="c-honors">${coachHonors.map(h => `<span>🏆 ${escHtml(h)}</span>`).join('')}</div>` : ''}
      </div>
    </section>

    <section class="side-section">
      <h3>⭐ 主力 11 人 <span class="ss-count">${fwDet.length + midDet.length + defDet.length + gkDet.length}</span></h3>
      ${renderPosBlock('🔴 前锋 FW', 'fw', fwDet)}
      ${renderPosBlock('🟡 中场 MID', 'mid', midDet)}
      ${renderPosBlock('🟢 后卫 DEF', 'def', defDet)}
      ${renderPosBlock('🟣 门将 GK', 'gk', gkDet)}
    </section>

    <section class="side-section">
      <h3>📋 大名单 26 人 <span class="ss-count">${roster.length}</span></h3>
      <div class="roster-mini">${rosterHtml}</div>
    </section>

    <section class="side-section">
      <h3>📅 世界杯赛程 <span class="ss-count">${teamMatches.length} 场</span></h3>
      ${schedHtml}
    </section>
  `;
}

function renderPosBlock(title, key, players) {
  if (!players || !players.length) return '';
  const rows = players.map((pl, i) => {
    const pid = `${key}-${i}-${(pl.name || '').replace(/\s/g, '')}`;
    const detail = `
      <div class="player-detail" id="pd-${pid}" style="display:none">
        <div class="pd-row"><span class="pd-label">俱乐部</span><span class="pd-val">${escHtml(pl.club || '-')} (${escHtml(pl.league || '-')})</span></div>
        <div class="pd-row"><span class="pd-label">身价</span><span class="pd-val">${pl.value || '-'} 万€</span></div>
        <div class="pd-row"><span class="pd-label">国脚进球</span><span class="pd-val">${pl.nat_goals || 0}</span></div>
        <div class="pd-row"><span class="pd-label">国脚助攻</span><span class="pd-val">${pl.nat_assists || 0}</span></div>
        <div class="pd-row"><span class="pd-label">WhoScored</span><span class="pd-val">${pl.whoscored || '-'}</span></div>
        ${pl.apps_2025_26 || pl.goals_2025_26 ? `<div class="pd-season">📊 2025-26 赛季:<br>${escHtml(pl.apps_2025_26 || '-')}<br>⚽ ${escHtml(pl.goals_2025_26 || '-')}<br>🎯 ${escHtml(pl.assists_2025_26 || '-')}</div>` : ''}
      </div>`;
    return `
      <div class="player-row" data-pid="${pid}">
        <span class="pr-jersey">${i+1}</span>
        <span class="pr-name">${escHtml(pl.name || '')}</span>
        <span class="pr-club">${escHtml((pl.league || '').slice(0, 6))}</span>
        <span class="pr-value">${pl.value || '-'}</span>
      </div>
      ${detail}
    `;
  }).join('');
  return `
    <div class="pos-block">
      <div class="pos-header">
        <span class="pos-icon">${title.split(' ')[0]}</span>
        <span>${title.split(' ').slice(1).join(' ')}</span>
        <span class="pos-count">${players.length}</span>
      </div>
      <div class="pos-body">${rows}</div>
    </div>
  `;
}

function renderSchedRow(m, teamName) {
  const isHome = m.home === teamName;
  const opponent = isHome ? m.away : m.home;
  const oppFlag = FLAGS[opponent] || '';
  const played = !!m.actual_score;
  const soon = !played && isWithin24h(m.date);
  const tomorrow = !played && !soon && isTomorrow(m.date);
  const result = played
    ? (isHome ? (m.home_pts > m.away_pts ? 'win' : m.home_pts < m.away_pts ? 'lose' : 'draw')
              : (m.away_pts > m.home_pts ? 'win' : m.away_pts < m.home_pts ? 'lose' : 'draw'))
    : 'future';
  const cls = ['sched-row', played ? 'played' : 'future', soon ? 'soon' : '', tomorrow ? 'tomorrow' : '', played ? result : ''].filter(Boolean).join(' ');
  // 已完赛 → 新弹窗; 未开赛 → 抽屉
  const onclick = played ? `openPlayedMatchPopup('${m.match_id}')` : `openMatchDrawer('${m.match_id}')`;
  const dateLbl = m.date ? escHtml(m.date) : (played ? '已完赛' : '待定');
  const roundLbl = m.round ? cleanRound(m.round) : (m.stage || '');
  let scoreHtml;
  if (played) {
    const pts = isHome ? `${m.home_pts}-${m.away_pts}` : `${m.away_pts}-${m.home_pts}`;
    const winTag = result === 'win' ? '<span class="sr-meta" style="color:var(--green)">胜</span>' :
                   result === 'lose' ? '<span class="sr-meta" style="color:var(--red)">负</span>' :
                   '<span class="sr-meta">平</span>';
    scoreHtml = `<span class="sr-score ${result}">${m.actual_score}${winTag}<br><span class="sr-meta">${pts}分</span></span>`;
  } else {
    const pred = m.best_score || '?';
    const prob = m.best_score_prob ? `(${(m.best_score_prob*100).toFixed(0)}%)` : '';
    let wlabel = '';
    if (soon) wlabel = `⏰ ${whenLabel(m.date) || '24h内'}`;
    else if (tomorrow) wlabel = `📅 ${whenLabel(m.date) || '明天'}`;
    else if (m.date) wlabel = escHtml(whenLabel(m.date));
    scoreHtml = `<span class="sr-score future">预测 ${pred}<br><span class="sr-meta">${prob}</span>${wlabel ? '<br><span class="sr-meta">' + wlabel + '</span>' : ''}</span>`;
  }
  return `
    <div class="${cls}" onclick="${onclick}">
      <div class="sr-left">
        <div class="sr-date">${dateLbl} · ${escHtml(roundLbl)}</div>
        <div class="sr-opp"><span class="sr-home">${isHome ? '主场' : '客场'}</span>vs ${oppFlag} ${escHtml(opponent)}</div>
      </div>
      ${scoreHtml}
    </div>
  `;
}

// ============== 配置 (滑块) ==============
function renderSliders() {
  const cats = [
    { key: 'position_top_n', label: '位置 Top N', icon: '📊', sub: [
      { f: 'FW', label: '前锋数' }, { f: 'MID', label: '中场数' },
      { f: 'DEF', label: '后卫数' }, { f: 'GK', label: '门将数' }
    ]},
    { key: 'status_weights', label: '俱乐部状态', icon: '⚽', sub: [
      { f: 'g_per_goal', label: '进球/粒 (分)' },
      { f: 'a_per_assist', label: '助攻/次 (分)' },
      { f: 'who_bonus_base', label: 'WHO 基础分' },
      { f: 'who_bonus_denom', label: 'WHO 分母' }
    ]},
    { key: 'nat_intl', label: '国家队进球', icon: '🌍', sub: [
      { f: 'g_per_goal', label: '进球/粒' }, { f: 'a_per_assist', label: '助攻/次' }
    ]},
    { key: 'def_gk_weights', label: '后卫/门将', icon: '🛡️', sub: [
      { f: 'base_factor', label: '基础系数' },
      { f: 'honors_per_champ', label: '荣誉/项' },
      { f: 'starter_jersey_max', label: '首发球衣号阈值' },
      { f: 'starter_bonus', label: '首发加成' },
      { f: 'wc_per_ga', label: '世界杯失球惩罚' }
    ]},
    { key: 'player_to_total', label: '球员/教练占比', icon: '⚖️', sub: [
      { f: 'player_share', label: '球员权重' }, { f: 'coach_share', label: '教练权重' }
    ]},
    { key: 'smoothing', label: '平滑系数', icon: '🎚️', sub: [
      { f: 'player_div', label: '球员分母' },
      { f: 'coach_div', label: '教练分母' },
      { f: 'rank_div', label: '排名分母' }
    ]}
  ];
  
  let html = '';
  cats.forEach(cat => {
    html += `<h3 style="margin-top:14px;color:var(--accent);font-size:14px">${cat.icon} ${cat.label}</h3>`;
    cat.sub.forEach(s => {
      const v = currentWeights[cat.key][s.f];
      const min = (s.f === 'player_share' || s.f === 'coach_share') ? 0 : 0;
      const max = (s.f === 'player_share' || s.f === 'coach_share') ? 1 : (cat.key === 'smoothing' ? 15000 : 500);
      const step = (s.f === 'player_share' || s.f === 'coach_share') ? 0.05 : 1;
      html += `<div class="slider-group">
        <label>${s.label} <span class="value" id="slider-${cat.key}-${s.f}">${typeof v === 'number' && step === 0.05 ? v.toFixed(2) : v}</span></label>
        <input type="range" min="${min}" max="${max}" step="${step}" value="${v}" 
          oninput="updateSlider('${cat.key}', '${s.f}', this.value)">
      </div>`;
    });
  });
  $id('slidersContainer').innerHTML = html;
}

function updateSlider(cat, field, val) {
  const v = parseFloat(val);
  currentWeights[cat][field] = v;
  $id(`slider-${cat}-${field}`).textContent = (cat === 'player_to_total') ? v.toFixed(2) : v;
}

function renderPresets() {
  let html = '';
  Object.entries(PRESETS).forEach(([key, p]) => {
    html += `<button class="preset-btn" data-preset="${key}" onclick="loadPreset('${key}')">${p.icon} ${p.name}</button>`;
  });
  $id('presetList').innerHTML = html;
}

function loadPreset(key) {
  currentWeights = JSON.parse(JSON.stringify(PRESETS[key].weights));
  renderSliders();
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.preset-btn[data-preset="${key}"]`)?.classList.add('active');
}

function resetConfig() {
  currentWeights = JSON.parse(JSON.stringify(WEIGHTS));
  renderSliders();
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
}

function saveAsPreset() {
  const name = prompt('预设名称:');
  if (!name) return;
  const key = 'user_' + Date.now();
  PRESETS[key] = { name, icon: '⭐', weights: JSON.parse(JSON.stringify(currentWeights)) };
  renderPresets();
  // 刷新对比 tab 的下拉
  populateCompareSelects();
}

let savedPresets = {};  // 用户保存的预设

// ============== 预测运行 (浏览器 JS 重算) ==============
async function runPredictionLive() {
  // v2.3.2: 调后端 /api/predictions?weights=... 拿真实 4 维 λ 重算
  // 有后端时优先用后端结果, 没后端时降级为 runPrediction()
  const btn = $id('btnLiveRecalc');
  btn.disabled = true; btn.textContent = '⏳ 调后端...';
  const weightsParam = encodeURIComponent(JSON.stringify(currentWeights));
  try {
    const r = await fetch(`http://localhost:8765/api/predictions?weights=${weightsParam}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    // 用后端结果刷新 PREDICTIONS + ranking + group_standings
    if (data.predictions && Array.isArray(data.predictions)) {
      // 仅替换预测, 保留 player_stats / team_stats
      window.PREDICTIONS = data.predictions;
      if (data.ranking) window.RANKING = data.ranking;
      // 重渲染 KO bracket / 赛程 / 球队
      if (typeof renderBracket === 'function') renderBracket();
      if (typeof renderSchedule === 'function') renderSchedule();
      if (typeof renderTeams === 'function') renderTeams();
      // 更新顶部统计
      const f = data.final;
      if (f) {
        $id('statChampion').textContent = f.winner || '?';
        $id('statRunnerUp').textContent = f.loser || '?';
      }
      const tp = data.third_place;
      if (tp) $id('statThird').textContent = tp.winner || '?';
      btn.textContent = '✅ 已实时刷新';
      setTimeout(() => { btn.textContent = '🔄 实时刷新（需后端）'; }, 2000);
    } else {
      throw new Error('后端返回格式异常 (无 predictions)');
    }
  } catch (e) {
    btn.textContent = '❌ 后端未启动';
    alert(`实时刷新失败: ${e.message}\n\n请先启动后端:\n  cd backend && python3 server.py\n\n将降级到离线预测 (runPrediction)`);
    btn.textContent = '🔄 实时刷新（需后端）';
    runPrediction();  // fallback
  } finally {
    btn.disabled = false;
  }
}

function runPrediction() {
  // 简化版: 基于 RANKING 重新算 λ + R32
  // 这部分我们用排名分直接驱动 (跳过详细的球员重算, 但用 JS 重新模拟 R32→Final)
  
  // 1. 计算每个球队的 attack/defense (基于排名分简化)
  const teamStats = RANKING.map(t => ({
    team: t.team,
    attack: (t.fw_score / 50000 * 1.0 + t.mid_score / 40000 * 0.7),
    defense: (t.def_score / 25000 * 0.6 + t.gk_score / 5000 * 0.4),
    rank: t.rank_r
  })).sort((a, b) => b.rank - a.rank);
  
  // 2. 模拟 32 强 (R32 配对按 FIFA 2026 官方规则, 但用 lambda)
  // 简化: 把小组赛 actual_score 算积分
  const groupStandings = computeGroupStandings();
  const koMatches = simulateKnockout(groupStandings, teamStats);
  
  // 3. 渲染预览
  renderPreview(teamStats, koMatches);
  
  // 4. 刷新预测 tab
  currentKoMatches = koMatches;
  renderBracket();
  
  // 5. 刷新顶部冠军
  const final = koMatches.find(m => m.stage === 'FINAL');
  const third = koMatches.find(m => m.stage === '3RD');
  const sf = koMatches.filter(m => m.stage === 'SF');
  if (final) {
    $id('statChampion').textContent = final.winner;
    $id('statRunnerUp').textContent = final.loser;
  }
  if (third) $id('statThird').textContent = third.winner;
}

function computeGroupStandings() {
  const groups = {};
  PREDICTIONS.filter(p => p.stage === 'group').forEach(p => {
    if (!p.actual_score) return;  // 未开赛不计入积分
    if (!groups[p.group]) groups[p.group] = {};
    if (!groups[p.group][p.home]) groups[p.group][p.home] = { pts: 0, gf: 0, ga: 0, gp: 0, w: 0, d: 0, l: 0 };
    if (!groups[p.group][p.away]) groups[p.group][p.away] = { pts: 0, gf: 0, ga: 0, gp: 0, w: 0, d: 0, l: 0 };
    const [hs, as] = p.actual_score.split('-').map(Number);
    const h = groups[p.group][p.home], a = groups[p.group][p.away];
    h.gp++; a.gp++;
    h.gf += hs; a.gf += as;
    h.ga += as; a.ga += hs;
    if (p.home_pts === 3) { h.pts += 3; h.w++; a.l++; }
    else if (p.home_pts === 1) { h.pts += 1; a.pts += 1; h.d++; a.d++; }
    else { a.pts += 3; a.w++; h.l++; }
  });
  return groups;
}

function simulateKnockout(standings, teamStats) {
  // 排序每组, 取 1st/2nd
  const sorted = {};
  Object.keys(standings).forEach(g => {
    sorted[g] = Object.entries(standings[g])
      .map(([team, s]) => ({ team, ...s, gd: s.gf - s.ga }))
      .sort((a, b) => b.pts - a.pts || b.gd - a.gd || b.gf - a.gf);
  });
  
  // 32 强配对 (FIFA 2026 跨组规则简化)
  const groups = Object.keys(sorted).sort();
  const r32Pairs = [];
  // v2.3.7: 32 强配对严格按 FIFA 2026 官方对阵表 (来源: ESPN API 2026-06-28)
  // 硬编码跨组配对: [home_group, home_pos, away_group, away_pos]
  // 顺序严格匹配用户要求的"顺读 5 列": M1..M16 从上到下
  const OFFICIAL_R32 = [
    ['A',2,'B',2], ['C',1,'F',2], ['E',1,'D',3], ['F',1,'C',2],
    ['E',2,'I',2], ['I',1,'F',3], ['A',1,'E',3], ['L',1,'K',3],
    ['G',1,'I',3], ['D',1,'B',3], ['H',1,'J',2], ['K',2,'L',2],
    ['B',1,'J',3], ['D',2,'G',2], ['J',1,'H',2], ['K',1,'L',3],
  ];
  function teamAt(g, pos) {
    if (!sorted[g]) return null;
    const idx = pos - 1;
    return sorted[g][idx]?.team || null;
  }
  const finalR32 = [];
  for (const [hg, hp, ag, ap] of OFFICIAL_R32) {
    const h = teamAt(hg, hp);
    const a = teamAt(ag, ap);
    if (h && a) finalR32.push([h, a]);
  }
  
  // 模拟 R32
  const statsMap = {};
  teamStats.forEach(t => statsMap[t.team] = t);
  function playMatch(home, away) {
    const h = statsMap[home] || { attack: 0.5, defense: 0.5 };
    const a = statsMap[away] || { attack: 0.5, defense: 0.5 };
    const lam_h = 1.3 + (h.attack - a.defense) * 1.5;
    const lam_a = 1.3 + (a.attack - h.defense) * 1.5;
    const p_h = lam_h / (lam_h + lam_a) * 0.85;
    const p_a = lam_a / (lam_h + lam_a) * 0.85;
    const p_d = 0.15;
    const r = Math.random();
    if (r < p_h) return { winner: home, loser: away, score: '2-1', pen: false };
    if (r > 1 - p_a) return { winner: away, loser: home, score: '1-2', pen: false };
    // 平局 → 加时 → 点球
    const et_lam = 0.3 * (1 + (lam_h - lam_a) * 0.3);
    if (et_lam > 0.3) return { winner: home, loser: away, score: '2-1', pen: true };
    return { winner: away, loser: home, score: '1-2', pen: true };
  }
  
  const r32 = finalR32.map(([h, a], i) => ({ ...playMatch(h, a), stage: 'R32', match_id: 'JS_R32_' + i, home: h, away: a }));
  // v2.3.7: R16 配对按 FIFA 真实表 (bracket 几何相邻合并)
  // 上半 (M1..M8) 4 场: M1-M3, M2-M5, M4-M6, M7-M8
  // 下半 (M9..M16) 4 场: M11-M12, M9-M10, M14-M16, M13-M15
  const r16Indices = [[0,2],[1,4],[3,5],[6,7],[10,11],[8,9],[13,15],[12,14]];
  const r16 = [];
  r16Indices.forEach(([a, b], i) => {
    const m = playMatch(r32[a].winner, r32[b].winner);
    r16.push({ ...m, stage: 'R16', match_id: 'JS_R16_' + i, home: r32[a].winner, away: r32[b].winner });
  });
  // QF: 上半 (R16-1 vs R16-2), (R16-3 vs R16-4); 下半 (R16-5 vs R16-6), (R16-7 vs R16-8)
  const qf = [];
  for (let i = 0; i < 8; i += 2) {
    const m = playMatch(r16[i].winner, r16[i+1].winner);
    qf.push({ ...m, stage: 'QF', match_id: 'JS_QF_' + (i/2), home: r16[i].winner, away: r16[i+1].winner });
  }
  // SF: QF-1 vs QF-2 (上+下交叉), QF-3 vs QF-4
  const sf = [];
  for (let i = 0; i < 4; i += 2) {
    const m = playMatch(qf[i].winner, qf[i+1].winner);
    sf.push({ ...m, stage: 'SF', match_id: 'JS_SF_' + (i/2), home: qf[i].winner, away: qf[i+1].winner });
  }
  const finalM = playMatch(sf[0].winner, sf[1].winner);
  finalM.stage = 'FINAL';
  finalM.match_id = 'JS_FINAL';
  finalM.home = sf[0].winner;
  finalM.away = sf[1].winner;
  
  // 季军赛
  const third = playMatch(sf[0].loser, sf[1].loser);
  third.stage = '3RD';
  third.match_id = 'JS_3RD';
  third.home = sf[0].loser;
  third.away = sf[1].loser;
  
  return [...r32, ...r16, ...qf, ...sf, finalM, third];
}

function renderPreview(teamStats, koMatches) {
  const champ = koMatches.find(m => m.stage === 'FINAL')?.winner || '-';
  let html = `<p style="margin-bottom:12px">🏆 当前权重下预测冠军: <strong style="color:var(--gold);font-size:18px">${escHtml(champ)}</strong></p>`;
  html += '<div class="section-title" style="font-size:14px;margin:12px 0 8px">Top 16 排名</div>';
  html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:12px">';
  teamStats.slice(0, 16).forEach((t, i) => {
    html += `<div style="background:var(--bg-3);padding:6px;border-radius:4px"><strong>${i+1}.</strong> ${escHtml(t.team)} <span class="muted">${fmtNum(t.rank)}</span></div>`;
  });
  html += '</div>';
  $id('previewArea').innerHTML = html;
}

let currentKoMatches = [];
// KO 赛程 (FIFA 2026 官方 R32→Final 日期+主办城市)
// 数据来源: zhhans.wikipedia.org/wiki/2026年世界杯足球赛_淘汰赛阶段
// 索引按 R32 sortById 顺序 (R32_A_vs_B, R32_B_vs_A, R32_C_vs_D...)
const KO_SCHEDULE_BY_INDEX = [
  // R32 16 场 (按 M73-M88 FIFA 编号顺序, 即 R32_BRACKET 顺序)
  // 数据源: ESPN FIFA World Cup scoreboard 2026-06-28 拉取
  { date: '6月29日', city: '洛杉矶' },     // 0  M73 南非 vs 加拿大        | 6/28 美东 SoFi Stadium
  { date: '7月4日',  city: '堪萨斯城' },   // 1  M87 哥伦比亚 vs 加纳      | 7/3 美东 GEHA Field
  { date: '7月1日',  city: '墨西哥城' },   // 2  M79 墨西哥 vs 厄瓜多尔   | 6/30 美东 Estadio Banorte
  { date: '6月30日', city: '休斯敦' },     // 3  M76 巴西 vs 日本          | 6/29 美东 NRG Stadium
  { date: '6月30日', city: '福克斯伯勒' }, // 4  M74 德国 vs 巴拉圭       | 6/29 美东 Gillette Stadium
  { date: '7月2日',  city: '西雅图' },     // 5  M82 比利时 vs 塞内加尔   | 7/1 美东 Lumen Field
  { date: '7月1日',  city: '东卢瑟福' },   // 6  M77 法国 vs 瑞典          | 6/30 美东 MetLife Stadium
  { date: '7月4日',  city: '阿灵顿' },     // 7  M88 澳大利亚 vs 埃及     | 7/3 美东 AT&T Stadium
  { date: '7月3日',  city: '温哥华' },     // 8  M85 瑞士 vs 阿尔及利亚   | 7/2 美东 BC Place
  { date: '7月1日',  city: '阿灵顿' },     // 9  M78 科特迪瓦 vs 挪威     | 6/30 美东 AT&T Stadium
  { date: '7月3日',  city: '多伦多' },     // 10 M83 葡萄牙 vs 克罗地亚   | 7/2 美东 BMO Field
  { date: '7月2日',  city: '亚特兰大' },   // 11 M80 英格兰 vs 民主刚果   | 7/1 美东 Mercedes-Benz Stadium
  { date: '6月30日', city: '瓜达卢佩' },   // 12 M75 荷兰 vs 摩洛哥       | 6/29 美东 Estadio BBVA (Guadalupe, Nuevo León)
  { date: '7月4日',  city: '迈阿密' },     // 13 M86 阿根廷 vs 佛得角     | 7/3 美东 Hard Rock Stadium
  { date: '7月3日',  city: '洛杉矶' },     // 14 M84 西班牙 vs 奥地利     | 7/2 美东 SoFi Stadium
  { date: '7月2日',  city: '圣克拉拉' },   // 15 M81 美国 vs 波黑          | 7/1 美东 Levi's Stadium
];
const KO_SCHEDULE_R16 = [
  // R16 8 场 (按 match_id 字母序, 对应 FIFA 2026 官方对阵图)
  // M89-M96 配对: M73vM75, M74vM78, M76vM79, M77vM81, M83vM84, M82vM80, M85vM88, M86vM87
  // 数据源: ESPN 2026-07-04~07 scoreboard
  { date: '7月4日', city: '休斯敦' },     // 0 R16_M73胜_vs_M75胜  (M89)  → NRG Stadium
  { date: '7月5日', city: '东卢瑟福' },   // 1 R16_M74胜_vs_M78胜  (M91)  → MetLife Stadium
  { date: '7月4日', city: '费城' },       // 2 R16_M76胜_vs_M79胜  (M90)  → Lincoln Financial Field
  { date: '7月5日', city: '墨西哥城' },   // 3 R16_M77胜_vs_M81胜  (M92)  → Estadio Banorte
  { date: '7月6日', city: '西雅图' },     // 4 R16_M82胜_vs_M80胜  (M94)  → Lumen Field
  { date: '7月6日', city: '阿灵顿' },     // 5 R16_M83胜_vs_M84胜  (M93)  → AT&T Stadium
  { date: '7月7日', city: '温哥华' },     // 6 R16_M85胜_vs_M88胜  (M96)  → BC Place
  { date: '7月7日', city: '亚特兰大' }    // 7 R16_M86胜_vs_M87胜  (M95)  → Mercedes-Benz Stadium
];
const KO_SCHEDULE_QF = [
  // QF 4 场 (按 match_id 字母序, 对应 FIFA 2026 官方对阵图)
  // M97-M100 配对: M89vM90, M93vM94, M91vM92, M95vM96
  // 数据源: ESPN 2026-07-09~11 scoreboard
  { date: '7月9日',  city: '福克斯伯勒' },   // 0 QF_M89胜_vs_M90胜  (M97) → Gillette Stadium
  { date: '7月11日', city: '迈阿密' },       // 1 QF_M91胜_vs_M92胜  (M99) → Hard Rock Stadium
  { date: '7月10日', city: '洛杉矶' },       // 2 QF_M93胜_vs_M94胜  (M98) → SoFi Stadium
  { date: '7月11日', city: '堪萨斯城' }      // 3 QF_M95胜_vs_M96胜  (M100) → GEHA Field
];

// FIFA 官方 100 场编号 (KO R32 73-88, R16 89-96, QF 97-100, SF 101-102, Final 103...)
const MATCH_NUM_BY_STAGE = { R32: 73, R16: 89, QF: 97, SF: 101, FINAL: 103, '3RD': 104 };

// ========== 按当前真实积分计算 R32 实际对阵 (FIFA 2026 标准) ==========
function computeActualR32() {
  // 1. 收集所有 group 比赛, 按组聚合
  const groups = {};
  PREDICTIONS.filter(p => p.stage === 'group').forEach(p => {
    if (!p.actual_score) return;  // 只算已完赛
    if (!groups[p.group]) groups[p.group] = {};
    const t1 = groups[p.group][p.home] = groups[p.group][p.home] || { p: 0, gf: 0, ga: 0, gp: 0 };
    const t2 = groups[p.group][p.away] = groups[p.group][p.away] || { p: 0, gf: 0, ga: 0, gp: 0 };
    const [hs, as] = p.actual_score.split('-').map(Number);
    t1.gp++; t2.gp++;
    t1.gf += hs; t1.ga += as;
    t2.gf += as; t2.ga += hs;
    if (hs > as) { t1.p += 3; } else if (hs < as) { t2.p += 3; } else { t1.p += 1; t2.p += 1; }
  });

  // 2. 排名
  const sorted = {};
  Object.keys(groups).sort().forEach(g => {
    const teams = Object.entries(groups[g]).map(([team, s]) => ({ team, ...s, gd: s.gf - s.ga }));
    teams.sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf);
    sorted[g] = teams;
  });

  // 3. 12 个第 3 名排名 (FIFA 规则)
  const thirds = [];
  Object.keys(sorted).forEach(g => {
    if (sorted[g][2]) thirds.push({ ...sorted[g][2], group: g });
  });
  thirds.sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf);
  const qualifiedThirds = thirds.slice(0, 8);
  const qualifiedGroupKeys = qualifiedThirds.map(t => t.group).sort().join('');

  // 4. 查 FIFA 495 组合表, 把 1v3 的 3rd 组映射出来
  // f3rdMap['A'] = 3rd 组字母 (e.g. 'E'), 1v3 slot 顺序: A,B,E,D,K,I,G,L
  let f3rdMap = {};
  if (FIFA_3RD_TABLE[qualifiedGroupKeys]) {
    const arr = FIFA_3RD_TABLE[qualifiedGroupKeys];
    R32_SLOT_TO_FIRST.forEach((g, i) => { f3rdMap[g] = arr[i]; });
  }

  // 5. 查 (g, r) 队: g='*3rd' 用 slot 索引取自 f3rdMap[R32_SLOT_TO_FIRST[slot]]
  const lookup = (spec) => {
    if (spec.g === '*3rd') {
      const grpLetter = f3rdMap[R32_SLOT_TO_FIRST[spec.slot]];
      if (!grpLetter) return null;
      const t = thirds.find(t => t.group === grpLetter);
      return t?.team || null;
    }
    return sorted[spec.g]?.[spec.r - 1]?.team || null;
  };

  // 6. 按 R32_BRACKET 顺序生成 16 场
  const matches = R32_BRACKET.map((slot, idx) => {
    const h = lookup(slot.a);
    const a = lookup(slot.b);
    if (!h || !a) return null;
    const mid = `R32_${h}_vs_${a}`;
    return {
      stage: 'R32',
      match_id: mid,
      home: h,
      away: a,
      n: slot.n,
      winner: null,
      loser: null,
      actual_score: null,
      went_to_pen: false,
    };
  }).filter(m => m);

  // 按 match_id 字母序排 (与现有 KO_SCHEDULE_BY_INDEX 索引对齐)
  matches.sort((x, y) => x.match_id.localeCompare(y.match_id));
  return matches;
}

function renderBracket() {
  if (!currentKoMatches.length) {
    currentKoMatches = PREDICTIONS.filter(p => ['R32','R16','QF','SF','FINAL','3RD'].includes(p.stage));
  }
  
  // ============ 小组赛: 上半 A-H, 下半 I-L ============
  renderUpperGroups();
  renderLowerGroups();
  
  // ============ KO bracket: wiki 5 列顺读 (R32 单列 16 场) ============
  // 5 列: R32(16场单列) → R16(8场) → QF(4场) → SF(2场) → FINAL(1场) + 3RD(1场, 紧贴决赛下方)
  // 决赛在第 5 列上方, 季军赛在第 5 列下方 (不是中央)
  
  // 响应式: 根据视口宽度动态调整卡片尺寸
  // R32 卡片: 3 段 (日期+城市 / 队1 / 队2), 高度 66-78px (桌面)
  // R16/QF/SF/决赛/季军赛卡片: 2 段 (队1/队2), 高度 50-56px (桌面, 紧凑)
  // R32 之间 8-10px gap, R16/QF/SF 之间 18-24px gap (视觉对齐到 R32 折半中点)
  const vw = window.innerWidth;
  let CARD_W, COL_GAP, FINAL_W, FINAL_H;
  let R32_SLOT_H, R32_GAP, R32_CARD_H;
  let R16_CARD_H, R16_GAP;
  if (vw <= 480) {
    CARD_W = 130; COL_GAP = 10; FINAL_W = 160; FINAL_H = 110;
    R32_SLOT_H = 58; R32_GAP = 6; R32_CARD_H = 52;
    R16_CARD_H = 46; R16_GAP = 14;
  } else if (vw <= 768) {
    CARD_W = 150; COL_GAP = 16; FINAL_W = 190; FINAL_H = 122;
    R32_SLOT_H = 68; R32_GAP = 8; R32_CARD_H = 60;
    R16_CARD_H = 52; R16_GAP = 18;
  } else {
    CARD_W = 170; COL_GAP = 20; FINAL_W = 230; FINAL_H = 130;
    R32_SLOT_H = 78; R32_GAP = 10; R32_CARD_H = 68;
    R16_CARD_H = 58; R16_GAP = 22;
  }
  const HEADER_H = 30;
  const STAGE_PAD = 20;
  
  // === 5 列 x 坐标: R32 → R16 → QF → SF → Final ===
  const xR32 = 20;
  const xR16 = xR32 + CARD_W + COL_GAP;
  const xQF  = xR16 + CARD_W + COL_GAP;
  const xSF  = xQF  + CARD_W + COL_GAP;
  const xF   = xSF  + CARD_W + COL_GAP;
  
  const totalWidth = xF + FINAL_W + 20;
  
  // === y 坐标: R32 单列 16 场, 卡片之间有 gap ===
  const R32_BASE_TOP = HEADER_H + STAGE_PAD;
  const R32_END = R32_BASE_TOP + 16 * R32_SLOT_H;  // 16 场 R32 总高 (含 gap)
  
  // R32 每场中心 y
  const r32Y = [];
  for (let i = 0; i < 16; i++) r32Y.push(R32_BASE_TOP + i * R32_SLOT_H + R32_CARD_H / 2);
  
  // R16: 8 场, 每 2 场 R32 中点
  const r16Y = [];
  for (let i = 0; i < 8; i++) r16Y.push((r32Y[i*2] + r32Y[i*2+1]) / 2);
  
  // QF: 4 场
  const qfY = [];
  for (let i = 0; i < 4; i++) qfY.push((r16Y[i*2] + r16Y[i*2+1]) / 2);
  
  // SF: 2 场
  const sfY = [];
  for (let i = 0; i < 2; i++) sfY.push((qfY[i*2] + qfY[i*2+1]) / 2);
  
    // 决赛 y: SF 两场中点
  const finalY = (sfY[0] + sfY[1]) / 2;
  // 季军赛 y: 紧贴决赛下方 (决赛卡高 R16_CARD_H, 季军赛 R16_CARD_H, 间距 30)
  const thirdY = finalY + R16_CARD_H / 2 + R16_CARD_H / 2 + 30;
  
  // KO 容器高度: 三者取最大
  // - R32 末场底: R32_END
  // - 决赛卡底: finalY + R16_CARD_H/2
  // - 季军赛卡底: thirdY + R16_CARD_H/2
  const finalBottom = finalY + R16_CARD_H / 2;
  const thirdBottom = thirdY + R16_CARD_H / 2;
  const totalHeight = Math.max(R32_END, finalBottom, thirdBottom) + 10;
  
  // === R32 顺序映射 (按字母序) ===
  const sortById = (a, b) => a.match_id.localeCompare(b.match_id);
  
  const allR32 = computeActualR32();
  const allR16 = currentKoMatches.filter(m => m.stage === 'R16').sort(sortById);
  const allQF  = currentKoMatches.filter(m => m.stage === 'QF').sort(sortById);
  const allSF  = currentKoMatches.filter(m => m.stage === 'SF').sort(sortById);
  const final  = currentKoMatches.find(m => m.stage === 'FINAL');
  const third  = currentKoMatches.find(m => m.stage === '3RD');
  
  const svgDefs = `
    <defs>
      <linearGradient id="winGradient" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#3fb950" stop-opacity="0.5"/>
        <stop offset="50%" stop-color="#3fb950" stop-opacity="1"/>
        <stop offset="100%" stop-color="#3fb950" stop-opacity="0.5"/>
      </linearGradient>
    </defs>
  `;
  
  const flowEl = $id('bracketFlow');
  flowEl.style.minWidth = totalWidth + 'px';
  
  let html = `<div style="position:relative; width:${totalWidth}px; min-height:${totalHeight}px; padding:10px;">`;
  html += `<svg class="bracket-connector" style="left:0;top:0;width:${totalWidth}px;height:${totalHeight}px" viewBox="0 0 ${totalWidth} ${totalHeight}">${svgDefs}`;
  
  // === 卡片渲染函数 (wiki 风格: 日期+城市顶 / 两队+组别中, 不显示胜方行) ===
  function renderMatchCard(m, x, y, isFinal = false, isThird = false, slotH = SLOT_H, schedInfo = null) {
    if (!m) return '';
    const h = teamTag(m.home);
    const a = teamTag(m.away);
    const hs = m.actual_score ? m.actual_score.split('-')[0] : '?';
    const as_ = m.actual_score ? m.actual_score.split('-')[1] : '?';
    const penTag = m.went_to_pen ? '<span class="pen">点</span>' : '';
    const hasWin = !!m.winner;
    const w = isFinal ? FINAL_W : CARD_W;
    const h_ = isFinal ? R16_CARD_H : slotH - 4;
    
    // 顶部: 日期 + 主办城市 (仅 R32 卡片显示)
    const dateCityHtml = schedInfo
      ? `<div class="match-date-city">${escHtml(schedInfo.date)} <span class="sep">—</span> ${escHtml(schedInfo.city)}</div>`
      : '';
    
    const classes = ['bracket-match'];
    if (isFinal) classes.push('final');
    if (isThird) classes.push('third');
    if (hasWin) classes.push('has-winner');
    if (schedInfo) classes.push('has-sched');
    if (!m.winner && !hasWin) classes.push('unplayed');
    // 状态徽章: real (真实赛果) / pending (待定)
    let statusBadge = '';
    let statusCls = '';
    if (m.actual_score && m.data_status === 'real') {
      statusBadge = '<span class="status-badge real">✓</span>';
      statusCls = 'status-real';
    } else if (!m.actual_score) {
      statusBadge = '<span class="status-badge pending">待定</span>';
      statusCls = 'status-pending';
    } else {
      // 有 actual_score 但 data_status != real (旧数据)
      statusBadge = '<span class="status-badge predicted">预测</span>';
      statusCls = 'status-predicted';
    }
    classes.push(statusCls);
    
    return `<div class="${classes.join(' ')}"
      onclick="openMatchByState('${m.match_id}')"
      title="${escHtml(m.home)} vs ${escHtml(m.away)}"
      style="position:absolute; left:${x}px; top:${y}px; width:${w}px; height:${h_}px;">
      ${statusBadge}
      ${dateCityHtml}
      <div class="team">
        <span class="${m.winner === m.home ? 'winner' : 'loser'}">
          <span class="flag">${h.flag}</span>${escHtml(m.home)}<span class="team-rank">${h.rk}</span>${m.winner === m.home ? penTag : ''}
        </span>
        <span class="score">${hs}</span>
      </div>
      <div class="team">
        <span class="${m.winner === m.away ? 'winner' : 'loser'}">
          <span class="flag">${a.flag}</span>${escHtml(m.away)}<span class="team-rank">${a.rk}</span>${m.winner === m.away ? penTag : ''}
        </span>
        <span class="score">${as_}</span>
      </div>
    </div>`;
  }
  
  function addPath(x1, y1, x2, y2, isWin) {
    const xMid = (x1 + x2) / 2;
    if (isWin) {
      return `<path d="M${x1},${y1} L${xMid},${y1} L${xMid},${y2} L${x2},${y2}" 
        stroke="url(#winGradient)" stroke-width="2.5" fill="none" 
        class="winner-path" stroke-linecap="round" stroke-linejoin="round"/>`;
    } else {
      return `<path d="M${x1},${y1} L${xMid},${y1} L${xMid},${y2} L${x2},${y2}" 
        stroke="#30363d" stroke-width="1" fill="none" opacity="0.5" 
        stroke-dasharray="3,3" stroke-linecap="round"/>`;
    }
  }
  
  // === 渲染所有卡片 (用数组索引匹配 sched) ===
  allR32.forEach((m, idx) => {
    const sched = KO_SCHEDULE_BY_INDEX[idx] || { date: 'X待核实', city: 'X待核实' };
    html += renderMatchCard(m, xR32, r32Y[idx] - R32_CARD_H / 2, false, false, R32_CARD_H, sched);
  });
  allR16.forEach((m, idx) => {
    const sched = KO_SCHEDULE_R16[idx] || { date: 'X待核实', city: 'X待核实' };
    html += renderMatchCard(m, xR16, r16Y[idx] - R16_CARD_H / 2, false, false, R16_CARD_H, null);
  });
  allQF.forEach((m, idx) => {
    const sched = KO_SCHEDULE_QF[idx] || { date: 'X待核实', city: 'X待核实' };
    html += renderMatchCard(m, xQF, qfY[idx] - R16_CARD_H / 2, false, false, R16_CARD_H, null);
  });
  allSF.forEach((m, idx) => {
    const isSF1 = idx === 0;
    const sched = isSF1 ? { date: '7月14日', city: '阿灵顿' } : { date: '7月15日', city: '亚特兰大' };
    html += renderMatchCard(m, xSF, sfY[idx] - R16_CARD_H / 2, false, false, R16_CARD_H, null);
  });
  if (final) {
    html += renderMatchCard(final, xF, finalY - R16_CARD_H / 2, true, false, R16_CARD_H, null);
    html += `<div style="position:absolute; left:${xF}px; top:${finalY - R16_CARD_H / 2 - 32}px; width:${FINAL_W}px; text-align:center; color:var(--gold); font-size:14px; font-weight:bold; letter-spacing:3px; text-shadow: 0 0 8px rgba(255,215,0,0.5);">🏆 F I N A L</div>`;
  }
  if (third) {
    html += renderMatchCard(third, xF, thirdY, false, true, R16_CARD_H, null);
    html += `<div style="position:absolute; left:${xF}px; top:${thirdY + R16_CARD_H + 8}px; width:${FINAL_W}px; text-align:center; color:var(--bronze); font-size:12px; font-weight:bold; letter-spacing:3px; text-shadow: 0 0 8px rgba(205,127,50,0.4);">🥉 B R O N Z E</div>`;
  }
  
  // === 折线连接 ===
  for (let i = 0; i < 16; i += 2) {
    if (i+1 >= allR32.length) break;
    html += addPath(xR32 + CARD_W, r32Y[i], xR16, r16Y[i/2], !!allR32[i].winner);
    html += addPath(xR32 + CARD_W, r32Y[i+1], xR16, r16Y[i/2], !!allR32[i+1].winner);
  }
  for (let i = 0; i < 8; i += 2) {
    if (i+1 >= allR16.length) break;
    html += addPath(xR16 + CARD_W, r16Y[i], xQF, qfY[i/2], !!allR16[i].winner);
    html += addPath(xR16 + CARD_W, r16Y[i+1], xQF, qfY[i/2], !!allR16[i+1].winner);
  }
  for (let i = 0; i < 4; i += 2) {
    if (i+1 >= allQF.length) break;
    html += addPath(xQF + CARD_W, qfY[i], xSF, sfY[i/2], !!allQF[i].winner);
    html += addPath(xQF + CARD_W, qfY[i+1], xSF, sfY[i/2], !!allQF[i+1].winner);
  }
  if (allSF[0]) html += addPath(xSF + CARD_W, sfY[0], xF, finalY, true);
  if (allSF[1]) html += addPath(xSF + CARD_W, sfY[1], xF, finalY, true);
  
  // === 列标题 (5 列 wiki 风格) ===
  const stageLabels = [
    { text: '三十二强', x: xR32, w: CARD_W },
    { text: '十六强',   x: xR16, w: CARD_W },
    { text: '四分之一决赛', x: xQF, w: CARD_W },
    { text: '半决赛',   x: xSF, w: CARD_W },
    { text: '决赛 / 三、四名决赛', x: xF, w: FINAL_W }
  ];
  stageLabels.forEach(({ text, x: cx, w: cw }) => {
    html += `<div class="stage-label" style="position:absolute; left:${cx}px; top:${STAGE_PAD}px; width:${cw}px; text-align:center; color:var(--accent); font-weight:bold; font-size:13px;">${text}</div>`;
  });
  
  html += '</svg>';
  html += '</div>';
  $id('bracketFlow').innerHTML = html;
  $id('koMatchCount').textContent = `· ${currentKoMatches.length} 场`;

  // === KO 阶段进度条 ===
  const stageCount = (stage) => currentKoMatches.filter(m => m.stage === stage && m.actual_score).length;
  const stageTotal = { R32: 16, R16: 8, QF: 4, SF: 2, FINAL: 1 };
  const realGroup = PREDICTIONS.filter(p => p.stage === 'group' && p.actual_score).length;
  const updateProg = (stage, total, elFill, elText) => {
    const done = stageCount(stage);
    const pct = total > 0 ? (done / total * 100) : 0;
    if ($id(elFill)) $id(elFill).style.width = pct + '%';
    if ($id(elText)) $id(elText).textContent = `${done}/${total}`;
  };
  // 小组赛进度: 用实际数据
  if ($id('groupProgressText')) $id('groupProgressText').textContent = `${realGroup}/72`;
  if ($id('groupProgressFill')) $id('groupProgressFill').style.width = (realGroup/72*100) + '%';
  updateProg('R32', 16, 'r32ProgressFill', 'r32ProgressText');
  updateProg('R16', 8, 'r16ProgressFill', 'r16ProgressText');
  updateProg('QF', 4, 'qfProgressFill', 'qfProgressText');
  updateProg('SF', 2, 'sfProgressFill', 'sfProgressText');
  updateProg('FINAL', 1, 'finalProgressFill', 'finalProgressText');
}

// 小组赛: 上半 A-H, 下半 I-L (FIFA 2026 官方分法)
function buildGroupsHTML(groupsToShow) {
  const groupMatches = PREDICTIONS.filter(p => p.stage === 'group' && groupsToShow.includes(p.group));
  const groups = {};
  groupMatches.forEach(m => {
    if (!groups[m.group]) groups[m.group] = [];
    groups[m.group].push(m);
  });
  
  // 算积分榜
  const standings = {};
  Object.keys(groups).forEach(g => {
    standings[g] = {};
    groups[g].forEach(m => {
      if (!m.actual_score) return;  // 未开赛不计入积分
      if (!standings[g][m.home]) standings[g][m.home] = { p:0, w:0, d:0, l:0, gf:0, ga:0 };
      if (!standings[g][m.away]) standings[g][m.away] = { p:0, w:0, d:0, l:0, gf:0, ga:0 };
      const [hs, as] = m.actual_score.split('-').map(Number);
      const h = standings[g][m.home], a = standings[g][m.away];
      h.gf += hs; h.ga += as; a.gf += as; a.ga += hs;
      if (m.home_pts === 3) { h.p += 3; h.w++; a.l++; }
      else if (m.home_pts === 1) { h.p += 1; h.d++; a.d++; }
      else if (m.home_pts === 0) { a.p += 3; a.w++; h.l++; }
    });
  });
  
  let html = '';
  Object.keys(groups).sort().forEach(g => {
    const sorted = Object.entries(standings[g])
      .map(([team, s]) => ({ team, ...s, gd: s.gf - s.ga }))
      .sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf);
    
    html += `<div class="group-block">
      <div class="group-block-header">第 ${g} 组</div>
      <table class="standings-mini">
        <thead><tr><th>#</th><th>球队</th><th>赛</th><th>胜</th><th>平</th><th>负</th><th>净</th><th>分</th></tr></thead>
        <tbody>
          ${sorted.map((t, i) => `<tr class="pos-${i+1}">
            <td class="rank-cell">${i+1}</td>
            <td>${FLAGS[t.team] || ''} ${escHtml(t.team)}</td>
            <td>${t.w + t.d + t.l}</td>
            <td>${t.w}</td>
            <td>${t.d}</td>
            <td>${t.l}</td>
            <td>${t.gd > 0 ? '+' : ''}${t.gd}</td>
            <td><strong>${t.p}</strong></td>
          </tr>`).join('')}
        </tbody>
      </table>
      <div class="matches-mini">
        ${groups[g].map(m => {
          const isUnplayed = m.played === false;
          const soon = isUnplayed && isWithin24h(m.date);
          const tomorrow = isUnplayed && !soon && isTomorrow(m.date);
          const miniClasses = ['match-mini'];
          if (isUnplayed) miniClasses.push('unplayed');
          if (soon) miniClasses.push('upcoming-soon');
          else if (tomorrow) miniClasses.push('upcoming-tomorrow');
          return `
          <div class="${miniClasses.join(' ')}" onclick="openMatchByState('${m.match_id}')">
            <span>
              <span class="${m.winner === m.home || (m.home_pts === 1 && m.winner === m.home) ? 'winner' : 'loser'}">${FLAGS[m.home] || ''} ${escHtml(m.home)}</span>
              <span class="muted">vs</span>
              <span class="${m.winner === m.away ? 'winner' : 'loser'}">${FLAGS[m.away] || ''} ${escHtml(m.away)}</span>
            </span>
            <span class="score">${m.actual_score || '<span class="muted">预测 ' + (m.best_score || '?') + '</span>'}</span>
          </div>
        `;}).join('')}
      </div>
    </div>`;
  });
  
  return { html, count: groupMatches.length };
}

function renderUpperGroups() {
  const { html, count } = buildGroupsHTML(['A','B','C','D','E','F']);
  $id('upperGroupContainer').innerHTML = html;
  $id('upperGroupCount').textContent = `· ${count} 场 (6 组 × 6 场)`;
}

function renderLowerGroups() {
  const { html, count } = buildGroupsHTML(['G','H','I','J','K','L']);
  $id('lowerGroupContainer').innerHTML = html;
  $id('lowerGroupCount').textContent = `· ${count} 场 (6 组 × 6 场)`;
}

// ============== 对比 ==============
function populateCompareSelects() {
  const sel = (id) => `<option value="${id}">${PRESETS[id].icon} ${PRESETS[id].name}</option>`;
  const opts = Object.keys(PRESETS).map(sel).join('');
  $id('cmpLeft').innerHTML = opts;
  $id('cmpRight').innerHTML = opts;
  $id('cmpLeft').value = 'default';
  $id('cmpRight').value = 'high_value';
}

function runCompare() {
  // 简化: 对比两套预设的 32 强排名
  const a = simulateForPreset('cmpLeft');
  const b = simulateForPreset('cmpRight');
  
  const champA = a.find(m => m.stage === 'FINAL')?.winner || '-';
  const champB = b.find(m => m.stage === 'FINAL')?.winner || '-';
  
  $id('cmpLeftOut').innerHTML = `<h3>${PRESETS[$id('cmpLeft').value].name}</h3>
    <p>🏆 冠军: <strong style="color:var(--gold)">${escHtml(champA)}</strong></p>
    <p>Top 8:</p>
    <ol style="padding-left:20px;font-size:12px">${RANKING.slice(0,8).map(t => `<li>${escHtml(t.team)} (${fmtNum(t.rank_r)})</li>`).join('')}</ol>`;
  $id('cmpRightOut').innerHTML = `<h3>${PRESETS[$id('cmpRight').value].name}</h3>
    <p>🏆 冠军: <strong style="color:var(--gold)">${escHtml(champB)}</strong></p>
    <p>Top 8:</p>
    <ol style="padding-left:20px;font-size:12px">${RANKING.slice(0,8).map(t => `<li>${escHtml(t.team)} (${fmtNum(t.rank_r)})</li>`).join('')}</ol>`;
}

function simulateForPreset(selectId) {
  // 简化: 复用默认的 currentWeights 重跑
  const oldWeights = JSON.parse(JSON.stringify(currentWeights));
  currentWeights = JSON.parse(JSON.stringify(PRESETS[$id(selectId).value].weights));
  const standings = computeGroupStandings();
  const teamStats = RANKING.map(t => ({
    team: t.team,
    attack: (t.fw_score / 50000 * 1.0 + t.mid_score / 40000 * 0.7),
    defense: (t.def_score / 25000 * 0.6 + t.gk_score / 5000 * 0.4),
    rank: t.rank_r
  })).sort((a, b) => b.rank - a.rank);
  const result = simulateKnockout(standings, teamStats);
  currentWeights = oldWeights;
  return result;
}

$id('cmpLeft').addEventListener('change', runCompare);
$id('cmpRight').addEventListener('change', runCompare);

// ============== 搜索 ==============
function doSearch(q) {
  q = q.trim();
  if (!q) { $id('searchResults').innerHTML = '<p class="muted">输入关键词开始搜索...</p>'; return; }
  const lower = q.toLowerCase();
  const results = [];
  
  // 球队
  RANKING.forEach(t => {
    if (t.team.toLowerCase().includes(lower)) {
      results.push({ type: '球队', name: t.team, meta: `FIFA ${t.fifa_rank} · 排名分 ${fmtNum(t.rank_r)}`, action: `openTeamDetail('${t.team}')` });
    }
  });
  
  // 球员
  Object.entries(PLAYERS).forEach(([team, players]) => {
    players.forEach(p => {
      if (p.n.toLowerCase().includes(lower) || (p.c && p.c.toLowerCase().includes(lower))) {
        results.push({ type: '球员', name: p.n, meta: `${team} · ${p.p} · ${p.c}`, action: `openTeamDetail('${team}')` });
      }
    });
  });
  
  // 比赛
  PREDICTIONS.forEach(p => {
    if ((p.stadium && p.stadium.toLowerCase().includes(lower)) || (p.city && p.city.toLowerCase().includes(lower))) {
      results.push({ type: '比赛', name: `${p.home} vs ${p.away}`, meta: `${p.stadium} · ${p.city}`, action: `openMatchByState('${p.match_id}')` });
    }
  });
  
  $id('searchResults').innerHTML = results.slice(0, 30).map(r => `
    <div class="search-result" onclick="${r.action}">
      <span class="sr-type">${r.type}</span>
      <span class="sr-name">${escHtml(r.name)}</span>
      <span class="muted">${escHtml(r.meta)}</span>
    </div>
  `).join('') || '<p class="muted">无结果</p>';
}

// ============== 复盘分析 ==============
function analyzeReview() {
  const played = PREDICTIONS.filter(p => p.played && p.actual_score);
  const total = PREDICTIONS.length;
  if (!played.length) return null;

  // 1. 胜平负准确率
  let hdaCorrect = 0;
  const hdaMatrix = { H: {H:0,D:0,A:0}, D: {H:0,D:0,A:0}, A: {H:0,D:0,A:0} };
  const predHDACount = { H: 0, D: 0, A: 0 };
  const actHDACount = { H: 0, D: 0, A: 0 };
  let exactScore = 0;
  let scoreWithin1 = 0;  // |预测进球 - 实际进球| ≤ 1

  // 2. λ 偏差
  let lambdaErrHome = 0, lambdaErrAway = 0;
  let actualHomeGoals = 0, actualAwayGoals = 0;
  let predHomeGoals = 0, predAwayGoals = 0;
  const surprises = [];  // |误差| 最大的 Top 10

  for (const p of played) {
    const [ah, aa] = p.actual_score.split('-').map(Number);
    const predH = p.p_home_win > p.p_draw && p.p_home_win > p.p_away_win ? 'H'
                : p.p_away_win > p.p_draw ? 'A' : 'D';
    const actH = ah > aa ? 'H' : (ah < aa ? 'A' : 'D');
    if (predH === actH) hdaCorrect++;
    hdaMatrix[predH][actH]++;
    predHDACount[predH]++;
    actHDACount[actH]++;

    if (p.best_score === p.actual_score) exactScore++;
    if (Math.abs(parseInt(p.best_score?.split('-')[0] || 0) - ah) <= 1 &&
        Math.abs(parseInt(p.best_score?.split('-')[1] || 0) - aa) <= 1) scoreWithin1++;

    const eH = p.lambda_home - ah;
    const eA = p.lambda_away - aa;
    lambdaErrHome += eH * eH;
    lambdaErrAway += eA * eA;
    actualHomeGoals += ah;
    actualAwayGoals += aa;
    predHomeGoals += p.lambda_home;
    predAwayGoals += p.lambda_away;

    const err = Math.abs(eH) + Math.abs(eA);
    surprises.push({ p, err, eH, eA, ah, aa });
  }

  surprises.sort((a, b) => b.err - a.err);

  // 3. 按 group
  const byGroup = {};
  for (const p of played) {
    const g = p.group || '?';
    if (!byGroup[g]) byGroup[g] = { total: 0, correct: 0, exact: 0, lh: 0, la: 0, ah: 0, aa: 0 };
    byGroup[g].total++;
    const [ah, aa] = p.actual_score.split('-').map(Number);
    const predH = p.p_home_win > p.p_draw && p.p_home_win > p.p_away_win ? 'H'
                : p.p_away_win > p.p_draw ? 'A' : 'D';
    const actH = ah > aa ? 'H' : (ah < aa ? 'A' : 'D');
    if (predH === actH) byGroup[g].correct++;
    if (p.best_score === p.actual_score) byGroup[g].exact++;
    byGroup[g].lh += p.lambda_home; byGroup[g].la += p.lambda_away;
    byGroup[g].ah += ah; byGroup[g].aa += aa;
  }

  // 4. 按 round
  const byRound = {};
  for (const p of played) {
    const r = p.round || '?';
    if (!byRound[r]) byRound[r] = { total: 0, correct: 0, exact: 0 };
    byRound[r].total++;
    const [ah, aa] = p.actual_score.split('-').map(Number);
    const predH = p.p_home_win > p.p_draw && p.p_home_win > p.p_away_win ? 'H'
                : p.p_away_win > p.p_draw ? 'A' : 'D';
    const actH = ah > aa ? 'H' : (ah < aa ? 'A' : 'D');
    if (predH === actH) byRound[r].correct++;
    if (p.best_score === p.actual_score) byRound[r].exact++;
  }

  // 5. λ 校准 (按预测概率分桶)
  const buckets = [
    { range: '50-60%', min: 0.5, max: 0.6, total: 0, correct: 0 },
    { range: '60-70%', min: 0.6, max: 0.7, total: 0, correct: 0 },
    { range: '70-80%', min: 0.7, max: 0.8, total: 0, correct: 0 },
    { range: '80-90%', min: 0.8, max: 0.9, total: 0, correct: 0 },
    { range: '90-100%', min: 0.9, max: 1.01, total: 0, correct: 0 },
  ];
  for (const p of played) {
    const maxP = Math.max(p.p_home_win, p.p_draw, p.p_away_win);
    const [ah, aa] = p.actual_score.split('-').map(Number);
    const actH = ah > aa ? 'H' : (ah < aa ? 'A' : 'D');
    let predH = 'D';
    if (p.p_home_win === maxP) predH = 'H';
    else if (p.p_away_win === maxP) predH = 'A';
    for (const b of buckets) {
      if (maxP >= b.min && maxP < b.max) {
        b.total++;
        if (predH === actH) b.correct++;
        break;
      }
    }
  }

  return {
    total, played: played.length,
    hdaAcc: hdaCorrect / played.length,
    exactScore, exactScoreRate: exactScore / played.length,
    scoreWithin1, scoreWithin1Rate: scoreWithin1 / played.length,
    hdaMatrix, predHDACount, actHDACount,
    rmseHome: Math.sqrt(lambdaErrHome / played.length),
    rmseAway: Math.sqrt(lambdaErrAway / played.length),
    biasHome: (predHomeGoals - actualHomeGoals) / played.length,
    biasAway: (predAwayGoals - actualAwayGoals) / played.length,
    avgGoals: (actualHomeGoals + actualAwayGoals) / played.length,
    predAvgGoals: (predHomeGoals + predAwayGoals) / played.length,
    byGroup, byRound, buckets, surprises
  };
}

function renderReview() {
  const a = analyzeReview();
  if (!a) {
    $id('reviewContent').innerHTML = '<p class="muted">还没有已完赛比赛数据</p>';
    return;
  }
  $id('rvPlayed').textContent = a.played;
  $id('rvTotal').textContent = a.total;
  $id('rvRate').textContent = (a.played / a.total * 100).toFixed(1);

  const matrix = a.hdaMatrix;
  const totalMatrix = matrix.H.H + matrix.H.D + matrix.H.A + matrix.D.H + matrix.D.D + matrix.D.A + matrix.A.H + matrix.A.D + matrix.A.A;

  // Group rows
  const groupRows = Object.keys(a.byGroup).sort().map(g => {
    const d = a.byGroup[g];
    const acc = (d.correct / d.total * 100).toFixed(0);
    const exact = (d.exact / d.total * 100).toFixed(0);
    const lhErr = (d.lh / d.total - d.ah / d.total).toFixed(2);
    const laErr = (d.la / d.total - d.aa / d.total).toFixed(2);
    return `<tr>
      <td><b>第 ${g} 组</b></td>
      <td>${d.total}</td>
      <td><span style="color:${parseFloat(acc) >= 60 ? 'var(--green)' : parseFloat(acc) >= 40 ? 'var(--text)' : 'var(--red)'}">${acc}%</span></td>
      <td>${exact}%</td>
      <td>${lhErr > 0 ? '+' : ''}${lhErr}</td>
      <td>${laErr > 0 ? '+' : ''}${laErr}</td>
    </tr>`;
  }).join('');

  // Round rows
  const roundRows = Object.entries(a.byRound).map(([r, d]) => {
    const acc = (d.correct / d.total * 100).toFixed(0);
    return `<tr>
      <td>${escHtml(r.replace(/第+/g, '第').replace(/轮+/g, '轮'))}</td>
      <td>${d.total}</td>
      <td><span style="color:${parseFloat(acc) >= 60 ? 'var(--green)' : parseFloat(acc) >= 40 ? 'var(--text)' : 'var(--red)'}">${acc}%</span></td>
      <td>${d.exact}</td>
    </tr>`;
  }).join('');

  // Bucket bars (λ calibration)
  const bucketRows = a.buckets.filter(b => b.total > 0).map(b => {
    const acc = b.total > 0 ? (b.correct / b.total * 100).toFixed(0) : 0;
    const expected = ((b.min + Math.min(b.max, 1)) / 2 * 100).toFixed(0);
    const width = Math.max(acc, 5);
    const color = parseFloat(acc) >= parseFloat(expected) - 5 ? 'var(--green)' : 'var(--red)';
    return `<tr>
      <td>${b.range}</td>
      <td>${b.total}</td>
      <td><div class="rv-bar-track"><div class="rv-bar-fill" style="width:${width}%;background:${color}">${acc}%</div></div></td>
      <td>${expected}%</td>
      <td>${parseFloat(acc) >= parseFloat(expected) - 5 ? '✅' : '⚠️'}</td>
    </tr>`;
  }).join('');

  // Surprise Top 10
  const surpriseRows = a.surprises.slice(0, 10).map((s, i) => {
    const p = s.p;
    return `<tr>
      <td>${i+1}</td>
      <td>${escHtml(p.home)} vs ${escHtml(p.away)}</td>
      <td>${escHtml((p.group ? '第'+p.group+'组' : (p.round || '')).replace(/第+/g, '第').replace(/轮+/g, '轮'))}</td>
      <td><span class="rv-pred">${escHtml(p.best_score || '?')}</span></td>
      <td><b style="color:var(--red)">${p.actual_score}</b></td>
      <td>${s.eH > 0 ? '+' : ''}${s.eH.toFixed(1)}</td>
      <td>${s.eA > 0 ? '+' : ''}${s.eA.toFixed(1)}</td>
    </tr>`;
  }).join('');

  $id('reviewContent').innerHTML = `
    <div class="rv-grid">
      <div class="rv-card">
        <div class="rv-card-num">${(a.hdaAcc * 100).toFixed(1)}%</div>
        <div class="rv-card-lbl">胜平负准确率</div>
        <div class="rv-card-sub">${a.hdaAcc > 0.5 ? '✅ 优于随机' : '⚠️ 接近随机'}</div>
      </div>
      <div class="rv-card">
        <div class="rv-card-num">${a.exactScore}/${a.played}</div>
        <div class="rv-card-lbl">比分完全正确</div>
        <div class="rv-card-sub">${(a.exactScoreRate*100).toFixed(1)}% 命中率</div>
      </div>
      <div class="rv-card">
        <div class="rv-card-num">${a.scoreWithin1}/${a.played}</div>
        <div class="rv-card-lbl">±1 球正确</div>
        <div class="rv-card-sub">${(a.scoreWithin1Rate*100).toFixed(1)}% 命中率</div>
      </div>
      <div class="rv-card">
        <div class="rv-card-num">${a.rmseHome.toFixed(2)} / ${a.rmseAway.toFixed(2)}</div>
        <div class="rv-card-lbl">λ RMSE (主/客)</div>
        <div class="rv-card-sub">越小越准</div>
      </div>
      <div class="rv-card">
        <div class="rv-card-num">${a.biasHome > 0 ? '+' : ''}${a.biasHome.toFixed(2)} / ${a.biasAway > 0 ? '+' : ''}${a.biasAway.toFixed(2)}</div>
        <div class="rv-card-lbl">进球偏差 (主/客)</div>
        <div class="rv-card-sub">${a.biasHome > 0 ? '高估主队' : '低估主队'} · ${a.biasAway > 0 ? '高估客队' : '低估客队'}</div>
      </div>
      <div class="rv-card">
        <div class="rv-card-num">${a.avgGoals.toFixed(1)} / ${a.predAvgGoals.toFixed(1)}</div>
        <div class="rv-card-lbl">场均进球 (实际/预测)</div>
        <div class="rv-card-sub">${a.avgGoals > a.predAvgGoals ? '⚠️ 实际比预测高 ' + (a.avgGoals - a.predAvgGoals).toFixed(1) : '✅ 预测接近'}</div>
      </div>
    </div>

    <section class="rv-section">
      <h3>🎯 胜平负预测矩阵 (预测 vs 实际)</h3>
      <table class="rv-table">
        <thead>
          <tr>
            <th>预测 \\ 实际</th>
            <th>🏠 主胜</th>
            <th>🤝 平局</th>
            <th>✈️ 客胜</th>
            <th>合计</th>
            <th>准确率</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><b>🏠 主胜预测</b></td>
            <td class="rv-correct">${matrix.H.H}</td>
            <td>${matrix.H.D}</td>
            <td>${matrix.H.A}</td>
            <td>${a.predHDACount.H}</td>
            <td>${a.predHDACount.H > 0 ? (matrix.H.H / a.predHDACount.H * 100).toFixed(0) : 0}%</td>
          </tr>
          <tr>
            <td><b>🤝 平局预测</b></td>
            <td>${matrix.D.H}</td>
            <td class="rv-correct">${matrix.D.D}</td>
            <td>${matrix.D.A}</td>
            <td>${a.predHDACount.D}</td>
            <td>${a.predHDACount.D > 0 ? (matrix.D.D / a.predHDACount.D * 100).toFixed(0) : 0}%</td>
          </tr>
          <tr>
            <td><b>✈️ 客胜预测</b></td>
            <td>${matrix.A.H}</td>
            <td>${matrix.A.D}</td>
            <td class="rv-correct">${matrix.A.A}</td>
            <td>${a.predHDACount.A}</td>
            <td>${a.predHDACount.A > 0 ? (matrix.A.A / a.predHDACount.A * 100).toFixed(0) : 0}%</td>
          </tr>
          <tr>
            <td><b>实际合计</b></td>
            <td>${a.actHDACount.H}</td>
            <td>${a.actHDACount.D}</td>
            <td>${a.actHDACount.A}</td>
            <td>${totalMatrix}</td>
            <td>—</td>
          </tr>
        </tbody>
      </table>
      <div class="rv-info">📊 矩阵对角线（绿色）是预测正确的场次。行准确率 = 该预测方向下命中的占比；列合计 = 实际各结果的总数。</div>
    </section>

    <section class="rv-section">
      <h3>📈 概率校准 (按预测置信度分桶)</h3>
      <table class="rv-table">
        <thead>
          <tr>
            <th>预测概率区间</th>
            <th>场次</th>
            <th>实际准确率</th>
            <th>理论期望</th>
            <th>校准</th>
          </tr>
        </thead>
        <tbody>${bucketRows || '<tr><td colspan="5" class="muted">暂无数据</td></tr>'}</tbody>
      </table>
      <div class="rv-info">💡 如果算法校准良好，"实际准确率"应接近"理论期望"。偏差大说明算法高估或低估了胜率。</div>
    </section>

    <section class="rv-section">
      <h3>📋 小组表现 (各组预测准确率)</h3>
      <table class="rv-table">
        <thead>
          <tr>
            <th>组别</th>
            <th>已踢</th>
            <th>胜平负</th>
            <th>比分命中</th>
            <th>λ 偏差 (主)</th>
            <th>λ 偏差 (客)</th>
          </tr>
        </thead>
        <tbody>${groupRows || '<tr><td colspan="6" class="muted">暂无数据</td></tr>'}</tbody>
      </table>
      <div class="rv-info">📊 λ 偏差 > 0 表示算法高估该队进球，< 0 表示低估。</div>
    </section>

    <section class="rv-section">
      <h3>🔄 轮次表现 (各轮准确率)</h3>
      <table class="rv-table">
        <thead>
          <tr>
            <th>轮次</th>
            <th>已踢</th>
            <th>胜平负</th>
            <th>比分命中</th>
          </tr>
        </thead>
        <tbody>${roundRows || '<tr><td colspan="4" class="muted">暂无数据</td></tr>'}</tbody>
      </table>
    </section>

    <section class="rv-section">
      <h3>😱 最意外比赛 Top 10 (λ 误差最大)</h3>
      <table class="rv-table">
        <thead>
          <tr>
            <th>#</th>
            <th>比赛</th>
            <th>轮次</th>
            <th>预测比分</th>
            <th>实际比分</th>
            <th>主队误差</th>
            <th>客队误差</th>
          </tr>
        </thead>
        <tbody>${surpriseRows || '<tr><td colspan="7" class="muted">暂无数据</td></tr>'}</tbody>
      </table>
      <div class="rv-info">🔍 误差 = 实际进球 - 预测 λ。绝对值越大 = 越意外。</div>
    </section>
  `;
}

// ============== 晋级分析 ==============
function renderQualify() {
  // 0. 动态更新标题"已完赛 X 场"
  const realGroupCnt = PREDICTIONS.filter(p => p.stage === 'group' && p.actual_score).length;
  const qTotalEl = $id('qTotalPlayed');
  if (qTotalEl) qTotalEl.textContent = realGroupCnt;

  // 1. 收集所有 group 比赛, 按组聚合
  const groups = {};
  const groupMatches = {};
  PREDICTIONS.filter(p => p.stage === 'group').forEach(p => {
    if (!groups[p.group]) {
      groups[p.group] = {};
      groupMatches[p.group] = { played: [], remaining: [] };
    }
    const t1 = groups[p.group][p.home] = groups[p.group][p.home] || { p: 0, gf: 0, ga: 0, gp: 0, w: 0, d: 0, l: 0 };
    const t2 = groups[p.group][p.away] = groups[p.group][p.away] || { p: 0, gf: 0, ga: 0, gp: 0, w: 0, d: 0, l: 0 };
    groupMatches[p.group].played.push(p);
    if (!p.actual_score) {
      groupMatches[p.group].remaining.push(p);
      return;
    }
    const [hs, as] = p.actual_score.split('-').map(Number);
    t1.gp++; t2.gp++;
    t1.gf += hs; t1.ga += as;
    t2.gf += as; t2.ga += hs;
    if (hs > as) { t1.p += 3; t1.w++; t2.l++; }
    else if (hs < as) { t2.p += 3; t2.w++; t1.l++; }
    else { t1.p += 1; t1.d++; t2.p += 1; t2.d++; }
  });

  // 2. 排名 + 最坏/最好情况分析
  const groupResults = {};
  Object.keys(groups).sort().forEach(g => {
    const teams = Object.entries(groups[g]).map(([team, s]) => ({ team, ...s, gd: s.gf - s.ga }));
    teams.sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf || a.team.localeCompare(b.team));

    const totalMatchesPerTeam = 3;
    teams.forEach(t => {
      t.remaining = groupMatches[g].remaining.filter(m => m.home === t.team || m.away === t.team).length;
      t.worst_pts = t.p;
      t.best_pts = t.p + t.remaining * 3;
    });

    // 判定状态
    const sortedByWorst = [...teams].sort((a, b) => b.worst_pts - a.worst_pts);
    const sortedByBest = [...teams].sort((a, b) => a.best_pts - b.best_pts);
    // 第 3 名最好情况最好 pts = 3rd place team's best_pts
    const thirdBestMax = teams[2]?.best_pts ?? 0;
    const secondBestMin = sortedByBest[1]?.worst_pts ?? 99; // 第 2 名最低可达
    const thirdWorstMax = sortedByWorst[2]?.worst_pts ?? 99; // 第 3 名最低可达 (即当前第 3 名最低积分)
    teams.forEach((t, idx) => {
      if (t.remaining === 0) {
        // 全部踢完, 位置确定
        if (idx === 0) t.status = 'locked-q1';
        else if (idx === 1) t.status = 'locked-q2';
        else if (idx === 2) t.status = 'third';
        else t.status = 'out';
      } else {
        // 还有场次
        if (idx === 0) {
          // 第 1 名: 最坏分 > 第 3 名最好情况?
          t.status = (t.worst_pts > thirdBestMax) ? 'locked-q1' : 'battle-q';
        } else if (idx === 1) {
          // 第 2 名: 最坏分 > 第 3 名最好情况?
          t.status = (t.worst_pts > thirdBestMax) ? 'locked-q2' : 'battle-q';
        } else if (idx === 2) {
          // 当前第 3: 还有机会但悬
          t.status = 'battle-q';
        } else {
          // 第 4: 即使全赢能否超第 2?
          t.status = (t.best_pts < sortedByBest[1]?.p) ? 'out' : 'battle-out';
        }
      }
    });

    groupResults[g] = { teams, remaining: groupMatches[g].remaining };
  });

  // 3. 渲染各小组卡片
  let html = '';
  Object.keys(groupResults).sort().forEach(g => {
    const { teams, remaining } = groupResults[g];
    const totalPlayed = teams.reduce((sum, t) => sum + t.gp, 0) / 2;
    const progress = `${Math.round(totalPlayed)}/6`;
    html += `<div class="qualify-group-card">
      <div class="qualify-group-head">
        <span class="qualify-group-title">第 ${g} 组</span>
        <span class="qualify-group-progress">已踢 ${progress} 场 · 共 18 场</span>
      </div>
      <table class="qualify-table">
        <thead><tr><th class="rank-cell">#</th><th>球队</th><th class="num">赛</th><th class="num">胜-平-负</th><th class="num">净</th><th class="num">进</th><th class="num">失</th><th class="num">积分</th><th>状态</th></tr></thead>
        <tbody>`;
    teams.forEach((t, i) => {
      const rank = `${g}${i + 1}`;
      const flag = FLAGS[t.team] || '🏳️';
      const rowCls = `row-${t.status.startsWith('locked-q1') ? 'q' : t.status.startsWith('locked-q2') ? 'q2' : t.status === 'third' ? 'battle' : t.status === 'battle-q' ? 'battle' : t.status === 'battle-out' ? 'battle' : 'out'}`;
      const badge = ({
        'locked-q1': '<span class="qbadge qbadge-locked-q">🔒 锁定第 1</span>',
        'locked-q2': '<span class="qbadge qbadge-locked-q2">🔒 锁定前 2</span>',
        'third': '<span class="qbadge qbadge-third">当前第 3</span>',
        'battle-q': '<span class="qbadge qbadge-battle-q">争 top 2</span>',
        'battle-out': '<span class="qbadge qbadge-battle-out">争第 3</span>',
        'out': '<span class="qbadge qbadge-out">出局</span>',
      })[t.status] || '';
      html += `<tr class="${rowCls}">
        <td class="rank-cell">${rank}</td>
        <td class="team-cell">${flag} ${escHtml(t.team)}</td>
        <td class="num">${t.gp}</td>
        <td class="num">${t.w}-${t.d}-${t.l}</td>
        <td class="num">${t.gd > 0 ? '+' + t.gd : t.gd}</td>
        <td class="num">${t.gf}</td>
        <td class="num">${t.ga}</td>
        <td class="num"><b>${t.p}</b></td>
        <td>${badge}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
    if (remaining.length > 0) {
      html += `<div class="qremaining">
        <div class="qremaining-title">🕐 剩余 ${remaining.length} 场</div>`;
      remaining.forEach(m => {
        const homeFlag = FLAGS[m.home] || '';
        const awayFlag = FLAGS[m.away] || '';
        const dateShort = (m.date || '').slice(5);
        html += `<div class="qremaining-match">
          <span>${homeFlag} ${escHtml(m.home)} <span class="muted">vs</span> ${awayFlag} ${escHtml(m.away)}</span>
          <span class="date">${dateShort}</span>
        </div>`;
      });
      html += `</div>`;
    }
    html += `</div>`;
  });
  $id('qualifyGroups').innerHTML = `<div class="qualify-grid">${html}</div>`;

  // 4. 12 支第 3 名排名
  const thirdTeams = [];
  Object.keys(groupResults).sort().forEach(g => {
    const t = groupResults[g].teams[2];
    if (t) thirdTeams.push({ ...t, group: g });
  });
  thirdTeams.sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf || a.gd - b.gd);

  // 摘要统计
  let locked_q = 0, locked_q2 = 0, battle_q = 0, battle_out = 0, eliminated = 0;
  Object.values(groupResults).forEach(({ teams }) => {
    teams.forEach(t => {
      if (t.status === 'locked-q1') locked_q++;
      else if (t.status === 'locked-q2') locked_q2++;
      else if (t.status === 'battle-q') battle_q++;
      else if (t.status === 'battle-out' || t.status === 'third') battle_out++;
      else eliminated++;
    });
  });

  let summaryHtml = `<div class="q-summary">
    <div class="q-stat-card locked-q"><div class="q-stat-num">${locked_q}</div><div class="q-stat-lbl">🔒 锁定第 1</div></div>
    <div class="q-stat-card locked-q"><div class="q-stat-num">${locked_q2}</div><div class="q-stat-lbl">🔒 锁定前 2</div></div>
    <div class="q-stat-card battle-q"><div class="q-stat-num">${battle_q}</div><div class="q-stat-lbl">⚔️ 争 top 2</div></div>
    <div class="q-stat-card battle-out"><div class="q-stat-num">${battle_out}</div><div class="q-stat-lbl">🎯 争第 3</div></div>
  </div>`;

  // 第 3 名榜
  let thirdHtml = summaryHtml + `<table class="qthird-table">
    <thead><tr>
      <th>#</th><th>组</th><th>球队</th><th class="num">已踢</th><th class="num">积分</th><th class="num">净胜</th><th class="num">进球</th><th class="num">失球</th><th>晋级状态</th>
    </tr></thead><tbody>`;
  thirdTeams.forEach((t, i) => {
    const rank = i + 1;
    const qualify = i < 8;
    const flag = FLAGS[t.team] || '🏳️';
    const remaining = groupResults[t.group].remaining.length;
    const status = qualify
      ? (remaining === 0 ? '<span class="qbadge qbadge-locked-q">✅ 锁定晋级</span>' : '<span class="qbadge qbadge-battle-q">⚔️ 需保住第 3</span>')
      : (remaining === 0 ? '<span class="qbadge qbadge-out">❌ 出局</span>' : '<span class="qbadge qbadge-battle-out">⚠️ 需挤进前 8</span>');
    thirdHtml += `<tr class="${qualify ? 'qualify' : 'eliminated'}">
      <td><b>${rank}</b></td>
      <td>${t.group}</td>
      <td>${flag} ${escHtml(t.team)}</td>
      <td class="num">${t.gp}/3</td>
      <td class="num"><b>${t.p}</b></td>
      <td class="num">${t.gd > 0 ? '+' + t.gd : t.gd}</td>
      <td class="num">${t.gf}</td>
      <td class="num">${t.ga}</td>
      <td>${status}</td>
    </tr>`;
    if (i === 7) {
      thirdHtml += `<tr class="cutoff-row"><td colspan="9">━━━ 第 8 名分界线 (上 8 队晋级 32 强, 下 4 队出局) ━━━</td></tr>`;
    }
  });
  thirdHtml += `</tbody></table>`;
  $id('qualifyThird').innerHTML = thirdHtml;

  // 顶部统计
  const totalPlayed = Object.values(groupResults).reduce((s, g) => s + g.teams.reduce((a, t) => a + t.gp, 0), 0) / 2;
  $id('qPlayed').textContent = Math.round(totalPlayed);

  // 5. 32 强淘汰赛对阵
  renderR32Bracket(groupResults);
}

// FIFA 2026 官方 32 强对阵规则 (来源: zh.wikipedia.org/wiki/2026年國際足協世界盃淘汰賽)
// 8 场 1v2/2v2: 4 场跨组 2nd 对决 + 4 场 1v2 镜像
// 8 场 1v3: 1A/1B/1D/1E/1G/1I/1K/1L 各打一个晋级 3rd, 具体分配由 FIFA 495 组合表决定
const R32_BRACKET = [
  // 上半区 (M73-M80): 跨组 2nd + 镜像 1v2 + 前 4 个 1v3
  { n: 73, a: { g: 'A', r: 2 }, b: { g: 'B', r: 2 } },                          // 2A vs 2B
  { n: 74, a: { g: 'E', r: 1 }, b: { g: '*3rd', slot: 3, pool: 'ABCDF' } },     // 1E vs 3rd(A/B/C/D/F)
  { n: 75, a: { g: 'F', r: 1 }, b: { g: 'C', r: 2 } },                          // 1F vs 2C
  { n: 76, a: { g: 'C', r: 1 }, b: { g: 'F', r: 2 } },                          // 1C vs 2F
  { n: 77, a: { g: 'I', r: 1 }, b: { g: '*3rd', slot: 5, pool: 'CDFGH' } },     // 1I vs 3rd(C/D/F/G/H)
  { n: 78, a: { g: 'E', r: 2 }, b: { g: 'I', r: 2 } },                          // 2E vs 2I
  { n: 79, a: { g: 'A', r: 1 }, b: { g: '*3rd', slot: 0, pool: 'CEFHI' } },     // 1A vs 3rd(C/E/F/H/I)
  { n: 80, a: { g: 'L', r: 1 }, b: { g: '*3rd', slot: 7, pool: 'EHIJK' } },     // 1L vs 3rd(E/H/I/J/K)
  // 下半区 (M81-M88): 后 4 个 1v3 + 镜像 1v2 + 跨组 2nd
  { n: 81, a: { g: 'D', r: 1 }, b: { g: '*3rd', slot: 2, pool: 'BEFIJ' } },     // 1D vs 3rd(B/E/F/I/J)
  { n: 82, a: { g: 'G', r: 1 }, b: { g: '*3rd', slot: 4, pool: 'AEHIJ' } },     // 1G vs 3rd(A/E/H/I/J)
  { n: 83, a: { g: 'K', r: 2 }, b: { g: 'L', r: 2 } },                          // 2K vs 2L
  { n: 84, a: { g: 'H', r: 1 }, b: { g: 'J', r: 2 } },                          // 1H vs 2J
  { n: 85, a: { g: 'B', r: 1 }, b: { g: '*3rd', slot: 1, pool: 'EFGIJ' } },     // 1B vs 3rd(E/F/G/I/J)
  { n: 86, a: { g: 'J', r: 1 }, b: { g: 'H', r: 2 } },                          // 1J vs 2H
  { n: 87, a: { g: 'K', r: 1 }, b: { g: '*3rd', slot: 6, pool: 'DEIJL' } },     // 1K vs 3rd(D/E/I/J/L)
  { n: 88, a: { g: 'D', r: 2 }, b: { g: 'G', r: 2 } },                          // 2D vs 2G
];

// slot 索引对应 FIFA 表 8 列的 1st (按 Wikipedia 列顺序): 0=1A, 1=1B, 2=1D, 3=1E, 4=1G, 5=1I, 6=1K, 7=1L
const R32_SLOT_TO_FIRST = ['A','B','D','E','G','I','K','L'];

const FIFA_3RD_TABLE = {
"EFGHIJKL":"EJIFHGL",
"DFGHIJKL":"HGIDJFLK",
"DEGHIJKL":"EJIDHGLK",
"DEFHIJKL":"EJIDHFLK",
"DEFGIJKL":"EGIDJFLK",
"DEFGHJKL":"EGJDHFLK",
"DEFGHIKL":"EGIDHFLK",
"DEFGHIJL":"EGJDHFLI",
"DEFGHIJK":"EGJDHFIK",
"CFGHIJKL":"HGICJFLK",
"CEGHIJKL":"EJICHGLK",
"CEFHIJKL":"EJICHFLK",
"CEFGIJKL":"EGICJFLK",
"CEFGHJKL":"EGJCHFLK",
"CEFGHIKL":"EGICHFLK",
"CEFGHIJL":"EGJCHFLI",
"CEFGHIJK":"EGJCHFIK",
"CDGHIJKL":"HGICJDLK",
"CDFHIJKL":"CJIDHFLK",
"CDFGIJKL":"CGIDJFLK",
"CDFGHJKL":"CGJDHFLK",
"CDFGHIKL":"CGIDHFLK",
"CDFGHIJL":"CGJDHFLI",
"CDFGHIJK":"CGJDHFIK",
"CDEHIJKL":"EJICHDLK",
"CDEGIJKL":"EGICJDLK",
"CDEGHJKL":"EGJCHDLK",
"CDEGHIKL":"EGICHDLK",
"CDEGHIJL":"EGJCHDLI",
"CDEGHIJK":"EGJCHDIK",
"CDEFIJKL":"CJEDIFLK",
"CDEFHJKL":"CJEDHFLK",
"CDEFHIKL":"CEIDHFLK",
"CDEFHIJL":"CJEDHFLI",
"CDEFHIJK":"CJEDHFIK",
"CDEFGJKL":"CGEDJFLK",
"CDEFGIKL":"CGEDIFLK",
"CDEFGIJL":"CGEDJFLI",
"CDEFGIJK":"CGEDJFIK",
"CDEFGHKL":"CGEDHFLK",
"CDEFGHJL":"CGJDHFLE",
"CDEFGHJK":"CGJDHFEK",
"CDEFGHIL":"CGEDHFLI",
"CDEFGHIK":"CGEDHFIK",
"CDEFGHIJ":"CGJDHFEI",
"BFGHIJKL":"HJBFIGLK",
"BEGHIJKL":"EJIBHGLK",
"BEFHIJKL":"EJBFIHLK",
"BEFGIJKL":"EJBFIGLK",
"BEFGHJKL":"EJBFHGLK",
"BEFGHIKL":"EGBFIHLK",
"BEFGHIJL":"EJBFHGLI",
"BEFGHIJK":"EJBFHGIK",
"BDGHIJKL":"HJBDIGLK",
"BDFHIJKL":"HJBDIFLK",
"BDFGIJKL":"IGBDJFLK",
"BDFGHJKL":"HGBDJFLK",
"BDFGHIKL":"HGBDIFLK",
"BDFGHIJL":"HGBDJFLI",
"BDFGHIJK":"HGBDJFIK",
"BDEHIJKL":"EJBDIHLK",
"BDEGIJKL":"EJBDIGLK",
"BDEGHJKL":"EJBDHGLK",
"BDEGHIKL":"EGBDIHLK",
"BDEGHIJL":"EJBDHGLI",
"BDEGHIJK":"EJBDHGIK",
"BDEFIJKL":"EJBDIFLK",
"BDEFHJKL":"EJBDHFLK",
"BDEFHIKL":"EIBDHFLK",
"BDEFHIJL":"EJBDHFLI",
"BDEFHIJK":"EJBDHFIK",
"BDEFGJKL":"EGBDJFLK",
"BDEFGIKL":"EGBDIFLK",
"BDEFGIJL":"EGBDJFLI",
"BDEFGIJK":"EGBDJFIK",
"BDEFGHKL":"EGBDHFLK",
"BDEFGHJL":"HGBDJFLE",
"BDEFGHJK":"HGBDJFEK",
"BDEFGHIL":"EGBDHFLI",
"BDEFGHIK":"EGBDHFIK",
"BDEFGHIJ":"HGBDJFEI",
"BCGHIJKL":"HJBCIGLK",
"BCFHIJKL":"HJBCIFLK",
"BCFGIJKL":"IGBCJFLK",
"BCFGHJKL":"HGBCJFLK",
"BCFGHIKL":"HGBCIFLK",
"BCFGHIJL":"HGBCJFLI",
"BCFGHIJK":"HGBCJFIK",
"BCEHIJKL":"EJBCIHLK",
"BCEGIJKL":"EJBCIGLK",
"BCEGHJKL":"EJBCHGLK",
"BCEGHIKL":"EGBCIHLK",
"BCEGHIJL":"EJBCHGLI",
"BCEGHIJK":"EJBCHGIK",
"BCEFIJKL":"EJBCIFLK",
"BCEFHJKL":"EJBCHFLK",
"BCEFHIKL":"EIBCHFLK",
"BCEFHIJL":"EJBCHFLI",
"BCEFHIJK":"EJBCHFIK",
"BCEFGJKL":"EGBCJFLK",
"BCEFGIKL":"EGBCIFLK",
"BCEFGIJL":"EGBCJFLI",
"BCEFGIJK":"EGBCJFIK",
"BCEFGHKL":"EGBCHFLK",
"BCEFGHJL":"HGBCJFLE",
"BCEFGHJK":"HGBCJFEK",
"BCEFGHIL":"EGBCHFLI",
"BCEFGHIK":"EGBCHFIK",
"BCEFGHIJ":"HGBCJFEI",
"BCDHIJKL":"HJBCIDLK",
"BCDGIJKL":"IGBCJDLK",
"BCDGHJKL":"HGBCJDLK",
"BCDGHIKL":"HGBCIDLK",
"BCDGHIJL":"HGBCJDLI",
"BCDGHIJK":"HGBCJDIK",
"BCDFIJKL":"CJBDIFLK",
"BCDFHJKL":"CJBDHFLK",
"BCDFHIKL":"CIBDHFLK",
"BCDFHIJL":"CJBDHFLI",
"BCDFHIJK":"CJBDHFIK",
"BCDFGJKL":"CGBDJFLK",
"BCDFGIKL":"CGBDIFLK",
"BCDFGIJL":"CGBDJFLI",
"BCDFGIJK":"CGBDJFIK",
"BCDFGHKL":"CGBDHFLK",
"BCDFGHJL":"CGBDHFLJ",
"BCDFGHJK":"HGBCJFDK",
"BCDFGHIL":"CGBDHFLI",
"BCDFGHIK":"CGBDHFIK",
"BCDFGHIJ":"HGBCJFDI",
"BCDEIJKL":"EJBCIDLK",
"BCDEHJKL":"EJBCHDLK",
"BCDEHIKL":"EIBCHDLK",
"BCDEHIJL":"EJBCHDLI",
"BCDEHIJK":"EJBCHDIK",
"BCDEGJKL":"EGBCJDLK",
"BCDEGIKL":"EGBCIDLK",
"BCDEGIJL":"EGBCJDLI",
"BCDEGIJK":"EGBCJDIK",
"BCDEGHKL":"EGBCHDLK",
"BCDEGHJL":"HGBCJDLE",
"BCDEGHJK":"HGBCJDEK",
"BCDEGHIL":"EGBCHDLI",
"BCDEGHIK":"EGBCHDIK",
"BCDEGHIJ":"HGBCJDEI",
"BCDEFJKL":"CJBDEFLK",
"BCDEFIKL":"CEBDIFLK",
"BCDEFIJL":"CJBDEFLI",
"BCDEFIJK":"CJBDEFIK",
"BCDEFHKL":"CEBDHFLK",
"BCDEFHJL":"CJBDHFLE",
"BCDEFHJK":"CJBDHFEK",
"BCDEFHIL":"CEBDHFLI",
"BCDEFHIK":"CEBDHFIK",
"BCDEFHIJ":"CJBDHFEI",
"BCDEFGKL":"CGBDEFLK",
"BCDEFGJL":"CGBDJFLE",
"BCDEFGJK":"CGBDJFEK",
"BCDEFGIL":"CGBDEFLI",
"BCDEFGIK":"CGBDEFIK",
"BCDEFGIJ":"CGBDJFEI",
"BCDEFGHL":"CGBDHFLE",
"BCDEFGHK":"CGBDHFEK",
"BCDEFGHJ":"HGBCJFDE",
"BCDEFGHI":"CGBDHFEI",
"AFGHIJKL":"HJIFAGLK",
"AEGHIJKL":"EJIAHGLK",
"AEFHIJKL":"EJIFAHLK",
"AEFGIJKL":"EJIFAGLK",
"AEFGHJKL":"EGJFAHLK",
"AEFGHIKL":"EGIFAHLK",
"AEFGHIJL":"EGJFAHLI",
"AEFGHIJK":"EGJFAHIK",
"ADGHIJKL":"HJIDAGLK",
"ADFHIJKL":"HJIDAFLK",
"ADFGIJKL":"IGJDAFLK",
"ADFGHJKL":"HGJDAFLK",
"ADFGHIKL":"HGIDAFLK",
"ADFGHIJL":"HGJDAFLI",
"ADFGHIJK":"HGJDAFIK",
"ADEHIJKL":"EJIDAHLK",
"ADEGIJKL":"EJIDAGLK",
"ADEGHJKL":"EGJDAHLK",
"ADEGHIKL":"EGIDAHLK",
"ADEGHIJL":"EGJDAHLI",
"ADEGHIJK":"EGJDAHIK",
"ADEFIJKL":"EJIDAFLK",
"ADEFHJKL":"HJEDAFLK",
"ADEFHIKL":"HEIDAFLK",
"ADEFHIJL":"HJEDAFLI",
"ADEFHIJK":"HJEDAFIK",
"ADEFGJKL":"EGJDAFLK",
"ADEFGIKL":"EGIDAFLK",
"ADEFGIJL":"EGJDAFLI",
"ADEFGIJK":"EGJDAFIK",
"ADEFGHKL":"HGEDAFLK",
"ADEFGHJL":"HGJDAFLE",
"ADEFGHJK":"HGJDAFEK",
"ADEFGHIL":"HGEDAFLI",
"ADEFGHIK":"HGEDAFIK",
"ADEFGHIJ":"HGJDAFEI",
"ACGHIJKL":"HJICAGLK",
"ACFHIJKL":"HJICAFLK",
"ACFGIJKL":"IGJCAFLK",
"ACFGHJKL":"HGJCAFLK",
"ACFGHIKL":"HGICAFLK",
"ACFGHIJL":"HGJCAFLI",
"ACFGHIJK":"HGJCAFIK",
"ACEHIJKL":"EJICAHLK",
"ACEGIJKL":"EJICAGLK",
"ACEGHJKL":"EGJCAHLK",
"ACEGHIKL":"EGICAHLK",
"ACEGHIJL":"EGJCAHLI",
"ACEGHIJK":"EGJCAHIK",
"ACEFIJKL":"EJICAFLK",
"ACEFHJKL":"HJECAFLK",
"ACEFHIKL":"HEICAFLK",
"ACEFHIJL":"HJECAFLI",
"ACEFHIJK":"HJECAFIK",
"ACEFGJKL":"EGJCAFLK",
"ACEFGIKL":"EGICAFLK",
"ACEFGIJL":"EGJCAFLI",
"ACEFGIJK":"EGJCAFIK",
"ACEFGHKL":"HGECAFLK",
"ACEFGHJL":"HGJCAFLE",
"ACEFGHJK":"HGJCAFEK",
"ACEFGHIL":"HGECAFLI",
"ACEFGHIK":"HGECAFIK",
"ACEFGHIJ":"HGJCAFEI",
"ACDHIJKL":"HJICADLK",
"ACDGIJKL":"IGJCADLK",
"ACDGHJKL":"HGJCADLK",
"ACDGHIKL":"HGICADLK",
"ACDGHIJL":"HGJCADLI",
"ACDGHIJK":"HGJCADIK",
"ACDFIJKL":"CJIDAFLK",
"ACDFHJKL":"HJFCADLK",
"ACDFHIKL":"HFICADLK",
"ACDFHIJL":"HJFCADLI",
"ACDFHIJK":"HJFCADIK",
"ACDFGJKL":"CGJDAFLK",
"ACDFGIKL":"CGIDAFLK",
"ACDFGIJL":"CGJDAFLI",
"ACDFGIJK":"CGJDAFIK",
"ACDFGHKL":"HGFCADLK",
"ACDFGHJL":"CGJDAFLH",
"ACDFGHJK":"HGJCAFDK",
"ACDFGHIL":"HGFCADLI",
"ACDFGHIK":"HGFCADIK",
"ACDFGHIJ":"HGJCAFDI",
"ACDEIJKL":"EJICADLK",
"ACDEHJKL":"HJECADLK",
"ACDEHIKL":"HEICADLK",
"ACDEHIJL":"HJECADLI",
"ACDEHIJK":"HJECADIK",
"ACDEGJKL":"EGJCADLK",
"ACDEGIKL":"EGICADLK",
"ACDEGIJL":"EGJCADLI",
"ACDEGIJK":"EGJCADIK",
"ACDEGHKL":"HGECADLK",
"ACDEGHJL":"HGJCADLE",
"ACDEGHJK":"HGJCADEK",
"ACDEGHIL":"HGECADLI",
"ACDEGHIK":"HGECADIK",
"ACDEGHIJ":"HGJCADEI",
"ACDEFJKL":"CJEDAFLK",
"ACDEFIKL":"CEIDAFLK",
"ACDEFIJL":"CJEDAFLI",
"ACDEFIJK":"CJEDAFIK",
"ACDEFHKL":"HEFCADLK",
"ACDEFHJL":"HJFCADLE",
"ACDEFHJK":"HJECAFDK",
"ACDEFHIL":"HEFCADLI",
"ACDEFHIK":"HEFCADIK",
"ACDEFHIJ":"HJECAFDI",
"ACDEFGKL":"CGEDAFLK",
"ACDEFGJL":"CGJDAFLE",
"ACDEFGJK":"CGJDAFEK",
"ACDEFGIL":"CGEDAFLI",
"ACDEFGIK":"CGEDAFIK",
"ACDEFGIJ":"CGJDAFEI",
"ACDEFGHL":"HGFCADLE",
"ACDEFGHK":"HGECAFDK",
"ACDEFGHJ":"HGJCAFDE",
"ACDEFGHI":"HGECAFDI",
"ABGHIJKL":"HJBAIGLK",
"ABFHIJKL":"HJBAIFLK",
"ABFGIJKL":"IJBFAGLK",
"ABFGHJKL":"HJBFAGLK",
"ABFGHIKL":"HGBAIFLK",
"ABFGHIJL":"HJBFAGLI",
"ABFGHIJK":"HJBFAGIK",
"ABEHIJKL":"EJBAIHLK",
"ABEGIJKL":"EJBAIGLK",
"ABEGHJKL":"EJBAHGLK",
"ABEGHIKL":"EGBAIHLK",
"ABEGHIJL":"EJBAHGLI",
"ABEGHIJK":"EJBAHGIK",
"ABEFIJKL":"EJBAIFLK",
"ABEFHJKL":"EJBFAHLK",
"ABEFHIKL":"EIBFAHLK",
"ABEFHIJL":"EJBFAHLI",
"ABEFHIJK":"EJBFAHIK",
"ABEFGJKL":"EJBFAGLK",
"ABEFGIKL":"EGBAIFLK",
"ABEFGIJL":"EJBFAGLI",
"ABEFGIJK":"EJBFAGIK",
"ABEFGHKL":"EGBFAHLK",
"ABEFGHJL":"HJBFAGLE",
"ABEFGHJK":"HJBFAGEK",
"ABEFGHIL":"EGBFAHLI",
"ABEFGHIK":"EGBFAHIK",
"ABEFGHIJ":"HJBFAGEI",
"ABDHIJKL":"IJBDAHLK",
"ABDGIJKL":"IJBDAGLK",
"ABDGHJKL":"HJBDAGLK",
"ABDGHIKL":"IGBDAHLK",
"ABDGHIJL":"HJBDAGLI",
"ABDGHIJK":"HJBDAGIK",
"ABDFIJKL":"IJBDAFLK",
"ABDFHJKL":"HJBDAFLK",
"ABDFHIKL":"HIBDAFLK",
"ABDFHIJL":"HJBDAFLI",
"ABDFHIJK":"HJBDAFIK",
"ABDFGJKL":"FJBDAGLK",
"ABDFGIKL":"IGBDAFLK",
"ABDFGIJL":"FJBDAGLI",
"ABDFGIJK":"FJBDAGIK",
"ABDFGHKL":"HGBDAFLK",
"ABDFGHJL":"HGBDAFLJ",
"ABDFGHJK":"HGBDAFJK",
"ABDFGHIL":"HGBDAFLI",
"ABDFGHIK":"HGBDAFIK",
"ABDFGHIJ":"HGBDAFIJ",
"ABDEIJKL":"EJBAIDLK",
"ABDEHJKL":"EJBDAHLK",
"ABDEHIKL":"EIBDAHLK",
"ABDEHIJL":"EJBDAHLI",
"ABDEHIJK":"EJBDAHIK",
"ABDEGJKL":"EJBDAGLK",
"ABDEGIKL":"EGBAIDLK",
"ABDEGIJL":"EJBDAGLI",
"ABDEGIJK":"EJBDAGIK",
"ABDEGHKL":"EGBDAHLK",
"ABDEGHJL":"HJBDAGLE",
"ABDEGHJK":"HJBDAGEK",
"ABDEGHIL":"EGBDAHLI",
"ABDEGHIK":"EGBDAHIK",
"ABDEGHIJ":"HJBDAGEI",
"ABDEFJKL":"EJBDAFLK",
"ABDEFIKL":"EIBDAFLK",
"ABDEFIJL":"EJBDAFLI",
"ABDEFIJK":"EJBDAFIK",
"ABDEFHKL":"HEBDAFLK",
"ABDEFHJL":"HJBDAFLE",
"ABDEFHJK":"HJBDAFEK",
"ABDEFHIL":"HEBDAFLI",
"ABDEFHIK":"HEBDAFIK",
"ABDEFHIJ":"HJBDAFEI",
"ABDEFGKL":"EGBDAFLK",
"ABDEFGJL":"EGBDAFLJ",
"ABDEFGJK":"EGBDAFJK",
"ABDEFGIL":"EGBDAFLI",
"ABDEFGIK":"EGBDAFIK",
"ABDEFGIJ":"EGBDAFIJ",
"ABDEFGHL":"HGBDAFLE",
"ABDEFGHK":"HGBDAFEK",
"ABDEFGHJ":"HGBDAFEJ",
"ABDEFGHI":"HGBDAFEI",
"ABCHIJKL":"IJBCAHLK",
"ABCGIJKL":"IJBCAGLK",
"ABCGHJKL":"HJBCAGLK",
"ABCGHIKL":"IGBCAHLK",
"ABCGHIJL":"HJBCAGLI",
"ABCGHIJK":"HJBCAGIK",
"ABCFIJKL":"IJBCAFLK",
"ABCFHJKL":"HJBCAFLK",
"ABCFHIKL":"HIBCAFLK",
"ABCFHIJL":"HJBCAFLI",
"ABCFHIJK":"HJBCAFIK",
"ABCFGJKL":"CJBFAGLK",
"ABCFGIKL":"IGBCAFLK",
"ABCFGIJL":"CJBFAGLI",
"ABCFGIJK":"CJBFAGIK",
"ABCFGHKL":"HGBCAFLK",
"ABCFGHJL":"HGBCAFLJ",
"ABCFGHJK":"HGBCAFJK",
"ABCFGHIL":"HGBCAFLI",
"ABCFGHIK":"HGBCAFIK",
"ABCFGHIJ":"HGBCAFIJ",
"ABCEIJKL":"EJBAICLK",
"ABCEHJKL":"EJBCAHLK",
"ABCEHIKL":"EIBCAHLK",
"ABCEHIJL":"EJBCAHLI",
"ABCEHIJK":"EJBCAHIK",
"ABCEGJKL":"EJBCAGLK",
"ABCEGIKL":"EGBAICLK",
"ABCEGIJL":"EJBCAGLI",
"ABCEGIJK":"EJBCAGIK",
"ABCEGHKL":"EGBCAHLK",
"ABCEGHJL":"HJBCAGLE",
"ABCEGHJK":"HJBCAGEK",
"ABCEGHIL":"EGBCAHLI",
"ABCEGHIK":"EGBCAHIK",
"ABCEGHIJ":"HJBCAGEI",
"ABCEFJKL":"EJBCAFLK",
"ABCEFIKL":"EIBCAFLK",
"ABCEFIJL":"EJBCAFLI",
"ABCEFIJK":"EJBCAFIK",
"ABCEFHKL":"HEBCAFLK",
"ABCEFHJL":"HJBCAFLE",
"ABCEFHJK":"HJBCAFEK",
"ABCEFHIL":"HEBCAFLI",
"ABCEFHIK":"HEBCAFIK",
"ABCEFHIJ":"HJBCAFEI",
"ABCEFGKL":"EGBCAFLK",
"ABCEFGJL":"EGBCAFLJ",
"ABCEFGJK":"EGBCAFJK",
"ABCEFGIL":"EGBCAFLI",
"ABCEFGIK":"EGBCAFIK",
"ABCEFGIJ":"EGBCAFIJ",
"ABCEFGHL":"HGBCAFLE",
"ABCEFGHK":"HGBCAFEK",
"ABCEFGHJ":"HGBCAFEJ",
"ABCEFGHI":"HGBCAFEI",
"ABCDIJKL":"IJBCADLK",
"ABCDHJKL":"HJBCADLK",
"ABCDHIKL":"HIBCADLK",
"ABCDHIJL":"HJBCADLI",
"ABCDHIJK":"HJBCADIK",
"ABCDGJKL":"CJBDAGLK",
"ABCDGIKL":"IGBCADLK",
"ABCDGIJL":"CJBDAGLI",
"ABCDGIJK":"CJBDAGIK",
"ABCDGHKL":"HGBCADLK",
"ABCDGHJL":"HGBCADLJ",
"ABCDGHJK":"HGBCADJK",
"ABCDGHIL":"HGBCADLI",
"ABCDGHIK":"HGBCADIK",
"ABCDGHIJ":"HGBCADIJ",
"ABCDFJKL":"CJBDAFLK",
"ABCDFIKL":"CIBDAFLK",
"ABCDFIJL":"CJBDAFLI",
"ABCDFIJK":"CJBDAFIK",
"ABCDFHKL":"HFBCADLK",
"ABCDFHJL":"CJBDAFLH",
"ABCDFHJK":"HJBCAFDK",
"ABCDFHIL":"HFBCADLI",
"ABCDFHIK":"HFBCADIK",
"ABCDFHIJ":"HJBCAFDI",
"ABCDFGKL":"CGBDAFLK",
"ABCDFGJL":"CGBDAFLJ",
"ABCDFGJK":"CGBDAFJK",
"ABCDFGIL":"CGBDAFLI",
"ABCDFGIK":"CGBDAFIK",
"ABCDFGIJ":"CGBDAFIJ",
"ABCDFGHL":"CGBDAFLH",
"ABCDFGHK":"HGBCAFDK",
"ABCDFGHJ":"HGBCAFDJ",
"ABCDFGHI":"HGBCAFDI",
"ABCDEJKL":"EJBCADLK",
"ABCDEIKL":"EIBCADLK",
"ABCDEIJL":"EJBCADLI",
"ABCDEIJK":"EJBCADIK",
"ABCDEHKL":"HEBCADLK",
"ABCDEHJL":"HJBCADLE",
"ABCDEHJK":"HJBCADEK",
"ABCDEHIL":"HEBCADLI",
"ABCDEHIK":"HEBCADIK",
"ABCDEHIJ":"HJBCADEI",
"ABCDEGKL":"EGBCADLK",
"ABCDEGJL":"EGBCADLJ",
"ABCDEGJK":"EGBCADJK",
"ABCDEGIL":"EGBCADLI",
"ABCDEGIK":"EGBCADIK",
"ABCDEGIJ":"EGBCADIJ",
"ABCDEGHL":"HGBCADLE",
"ABCDEGHK":"HGBCADEK",
"ABCDEGHJ":"HGBCADEJ",
"ABCDEGHI":"HGBCADEI",
"ABCDEFKL":"CEBDAFLK",
"ABCDEFJL":"CJBDAFLE",
"ABCDEFJK":"CJBDAFEK",
"ABCDEFIL":"CEBDAFLI",
"ABCDEFIK":"CEBDAFIK",
"ABCDEFIJ":"CJBDAFEI",
"ABCDEFHL":"HFBCADLE",
"ABCDEFHK":"HEBCAFDK",
"ABCDEFHJ":"HJBCAFDE",
"ABCDEFHI":"HEBCAFDI",
"ABCDEFGL":"CGBDAFLE",
"ABCDEFGK":"CGBDAFEK",
"ABCDEFGJ":"CGBDAFEJ",
"ABCDEFGI":"CGBDAFEI",
"ABCDEFGH":"HGBCAFDE",
};

// R32 比赛日期 (FIFA 2026 计划: 6-29 到 7-03)
const R32_DATES = ['06-29', '06-29', '06-30', '06-30', '07-01', '07-01', '07-02', '07-02',
                   '07-02', '07-02', '07-03', '07-03', '07-03', '07-03', '07-03', '07-03'];

function renderR32Bracket(groupResults) {
  // 1. 收集所有组第 3 名 + 排名
  const thirdList = [];
  Object.keys(groupResults).sort().forEach(g => {
    const t = groupResults[g].teams[2];
    if (t) thirdList.push({ ...t, group: g, g: g, r: 3 });
  });
  // FIFA 规则: 积分 → 净胜球 → 进球数
  thirdList.sort((a, b) => b.p - a.p || b.gd - a.gd || b.gf - a.gf);
  thirdList.forEach((t, i) => { t.qualify = i < 8; t.rank = i + 1; });
  const qualifiedThirds = thirdList.filter(t => t.qualify);
  const qualifiedGroupKeys = qualifiedThirds.map(t => t.g).sort().join('');

  // 2. 查 FIFA 495 组合表, 得到每个 1v3 的具体 3rd 分配
  // FIFA_3RD_TABLE[key] 是 8 字符串, 索引 = R32_SLOT_TO_FIRST 顺序: 0=1A, 1=1B, 2=1E, 3=1D, 4=1K, 5=1I, 6=1G, 7=1L
  let f3rdMap = {};  // { '1A': 'E', '1E': 'D', ... } 1st group letter -> 3rd group letter
  let tableFound = false;
  if (FIFA_3RD_TABLE[qualifiedGroupKeys]) {
    const arr = FIFA_3RD_TABLE[qualifiedGroupKeys];
    R32_SLOT_TO_FIRST.forEach((g, i) => { f3rdMap[g] = arr[i]; });
    tableFound = true;
  }

  // 检测"第 3 名"组合是否还可能变 (G-L 组未完赛)
  const uncertainGroups = Object.keys(groupResults).filter(g => groupResults[g].remaining.length > 0);
  const uncertain3rd = uncertainGroups.length > 0;

  // 3. 查找指定 (g, r) 的队 — 现在 g 可以是 '1A','1B','1D','1E','1G','1I','1K','1L' (1st 队)
  const findTeam = (spec) => {
    if (spec.g === '*3rd') {
      const grpLetter = f3rdMap[R32_SLOT_TO_FIRST[spec.slot]];
      if (!grpLetter) return null;
      return thirdList.find(t => t.g === grpLetter) || null;
    }
    if (spec.r === 3) {
      return thirdList.find(t => t.g === spec.g);
    }
    const grp = groupResults[spec.g];
    if (!grp) return null;
    return grp.teams[spec.r - 1] || null;
  };

  // 4. 渲染 16 场 — 上下半区切分
  const renderMatch = (slot, idx) => {
    const a = findTeam(slot.a);
    const b = findTeam(slot.b);
    // 组未完赛 → 当前排名可能变化 → 标记待定
    const grpA = slot.a.g === '*3rd' ? null : groupResults[slot.a.g];
    const grpB = slot.b.g === '*3rd' ? null : groupResults[slot.b.g];
    const aLocked = !a || (grpA && grpA.remaining.length === 0);
    const bLocked = !b || (grpB && grpB.remaining.length === 0);
    // 1v3 比赛: 还要看 G-L 组是否踢完 (决定 8 个 3rd 是否确定)
    const slot3rdA = slot.a.g === '*3rd' ? (uncertain3rd ? null : f3rdMap[R32_SLOT_TO_FIRST[slot.a.slot]]) : null;
    const slot3rdB = slot.b.g === '*3rd' ? (uncertain3rd ? null : f3rdMap[R32_SLOT_TO_FIRST[slot.b.slot]]) : null;
    const aUncertain = !aLocked || (slot.a.g === '*3rd' && !slot3rdA);
    const bUncertain = !bLocked || (slot.b.g === '*3rd' && !slot3rdB);
    const isTbd = aUncertain || bUncertain;

    // Tag (用于显示原定的 1st/2nd 位置)
    const tagA = slot.a.g === '*3rd' ? `1${R32_SLOT_TO_FIRST[slot.a.slot]} vs 3rd` : `${slot.a.g}${slot.a.r}`;
    const tagB = slot.b.g === '*3rd' ? `1${R32_SLOT_TO_FIRST[slot.b.slot]} vs 3rd` : `${slot.b.g}${slot.b.r}`;

    // 3rd 来源组 (实际)
    const thirdGroupA = slot.a.g === '*3rd' ? f3rdMap[R32_SLOT_TO_FIRST[slot.a.slot]] : null;
    const thirdGroupB = slot.b.g === '*3rd' ? f3rdMap[R32_SLOT_TO_FIRST[slot.b.slot]] : null;

    // 队名 + 国旗
    const teamNameA = a ? a.team : (slot.a.g === '*3rd' && thirdGroupA ? `3rd ${thirdGroupA}组` : '待定');
    const teamNameB = b ? b.team : (slot.b.g === '*3rd' && thirdGroupB ? `3rd ${thirdGroupB}组` : '待定');
    const flagA = a ? (FLAGS[a.team] || '🏳️') : '❓';
    const flagB = b ? (FLAGS[b.team] || '🏳️') : '❓';
    const tagSuffixA = aUncertain ? ' (待定)' : '';
    const tagSuffixB = bUncertain ? ' (待定)' : '';

    // 3rd 池子提示 (悬而未决时)
    const poolHint = (slot) => {
      if (slot.g !== '*3rd') return '';
      if (!slot.pool) return '';
      const groups = slot.pool.split('').map(g => `${g}组第3`).join('/');
      return `<div class="qr32-pool-hint">候选: ${groups}</div>`;
    };

    return `<div class="qr32-match ${isTbd ? 'tbd' : ''}">
      <div class="qr32-match-num">R32 · M${slot.n}</div>
      <div class="qr32-match-date">2026-${R32_DATES[idx]}</div>
      <div class="qr32-team ${aUncertain ? 'uncertain' : 'qualified'}">
        <span>${flagA} ${escHtml(teamNameA)}</span>
        <span class="rank-tag">${tagA}${tagSuffixA}</span>
      </div>
      ${poolHint(slot.a)}
      <div class="qr32-vs">vs</div>
      <div class="qr32-team ${bUncertain ? 'uncertain' : 'qualified'}">
        <span>${flagB} ${escHtml(teamNameB)}</span>
        <span class="rank-tag">${tagB}${tagSuffixB}</span>
      </div>
      ${poolHint(slot.b)}
    </div>`;
  };

  let html = `<div class="qr32-legend">
    <b>32 强对阵规则</b> · 上半区 M73-M80: 跨组 2nd + 1v2 镜像 + 1v3 · 下半区 M81-M88: 1v3 + 1v2 镜像 + 跨组 2nd
    <br>1v3 候选 5 个组 (FIFA 规则) · 实际分配由 FIFA 495 组合表按当前 8 强 3rd 决定
    ${uncertain3rd ? '<br>⚠️ G-L 组未踢完, 3rd 名次待定' : ''}
  </div>`;

  // 上半区: M73-M80
  html += `<div class="qr32-half qr32-half-upper">
    <div class="qr32-half-title">🔼 上半区 (M73-M80)</div>
    <div class="qr32-half-sub">2A↔2B · 1E vs 3rd · 1F↔2C · 1C↔2F · 1I vs 3rd · 2E↔2I · 1A vs 3rd · 1L vs 3rd</div>
    <div class="qr32-grid">`;
  R32_BRACKET.slice(0, 8).forEach((slot, idx) => {
    html += renderMatch(slot, idx);
  });
  html += `</div></div>`;

  // 下半区: M81-M88
  html += `<div class="qr32-half qr32-half-lower">
    <div class="qr32-half-title">🔽 下半区 (M81-M88)</div>
    <div class="qr32-half-sub">1D vs 3rd · 1G vs 3rd · 2K↔2L · 1H↔2J · 1B vs 3rd · 1J↔2H · 1K vs 3rd · 2D↔2G</div>
    <div class="qr32-grid">`;
  R32_BRACKET.slice(8, 16).forEach((slot, idx) => {
    html += renderMatch(slot, idx + 8);
  });
  html += `</div></div>`;

  $id('qualifyR32').innerHTML = html;
}

// ============== 导出 ==============
function exportConfig() {
  const data = {
    weights: currentWeights,
    timestamp: new Date().toISOString(),
    note: 'Mavis PDP v2.1 配置快照'
  };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'mavis_pdp_config.json';
  a.click();
  URL.revokeObjectURL(url);
}

// ============== 初始化 ==============
renderTeams();
renderSchedule();
renderSliders();
renderPresets();
populateCompareSelects();
renderBracket();
renderQualify();
runCompare();
// 顶部冠军初值
$id('statChampion').textContent = PREDICTIONS.find(p => p.stage === 'FINAL')?.winner || '-';
$id('statRunnerUp').textContent = PREDICTIONS.find(p => p.stage === 'FINAL')?.loser || '-';
$id('statThird').textContent = PREDICTIONS.find(p => p.stage === '3RD')?.winner || '-';
</script>
</body>
</html>
"""

HTML = HTML.replace("__WEIGHTS__", weights_json)
HTML = HTML.replace("__WEIGHTS_PRESETS__", weights_presets_json)
HTML = HTML.replace("__WEIGHTS_PRESETS_META__", weights_presets_meta_json)
HTML = HTML.replace("__RANKING__", ranking_json)
HTML = HTML.replace("__PREDICTIONS__", predictions_json)
HTML = HTML.replace("__PLAYERS__", players_json)
HTML = HTML.replace("__TEAM_STATS__", team_stats_json)
HTML = HTML.replace("__MATCH_PLAYERS__", match_players_json)
HTML = HTML.replace("__MATCH_EVENTS__", match_events_json)

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"\n✅ 写入: {OUT_FILE}")
print(f"   文件大小: {os.path.getsize(OUT_FILE)/1024:.1f}KB")
