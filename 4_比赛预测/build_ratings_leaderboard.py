#!/usr/bin/env python3
"""Build WhoScored player ratings leaderboard HTML page."""
import json
import csv
from pathlib import Path
from collections import defaultdict
import html as html_lib

PLAYER_RATINGS_DIR = Path("/Users/garcia/Desktop/WorldCup2026/4_比赛预测/player_ratings")
PLAYERS_CSV = Path("/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv")
OUTPUT_HTML = Path("/Users/garcia/Desktop/WorldCup2026/4_比赛预测/player_ratings_leaderboard.html")


def main():
    # Load all match ratings
    all_ratings = []
    for f in PLAYER_RATINGS_DIR.glob("match_*.json"):
        with open(f) as fh:
            all_ratings.extend(json.load(fh))
    print(f"Total ratings loaded: {len(all_ratings)}")
    
    # Build player stats
    player_stats = defaultdict(lambda: {
        'ratings': [],
        'matches': 0,
        'goals': 0,
        'assists': 0,
        'yellow': 0,
        'red': 0,
        'mom_count': 0,
        'teams': set(),
        'positions': set(),
        'first_match': None,
        'last_match': None,
    })
    
    for r in all_ratings:
        pid = r['player_id']
        s = player_stats[pid]
        s['name'] = r['player_name']
        s['ratings'].append(r['final_rating'])
        s['matches'] += 1
        s['goals'] += r.get('goals', 0)
        s['assists'] += r.get('assists', 0)
        s['yellow'] += r.get('yellow_cards', 0)
        s['red'] += r.get('red_cards', 0)
        s['mom_count'] += 1 if r.get('is_man_of_match') else 0
        s['teams'].add(r['team'])
        s['positions'].add(r.get('position', ''))
        if r.get('is_first_eleven'):
            s['first_eleven_count'] = s.get('first_eleven_count', 0) + 1
        match_date = r.get('date', '')
        if s['first_match'] is None or (match_date and match_date < s['first_match']):
            s['first_match'] = match_date
        if s['last_match'] is None or (match_date and match_date > s['last_match']):
            s['last_match'] = match_date
    
    # Build summary list
    summary = []
    for pid, s in player_stats.items():
        if s['matches'] == 0:
            continue
        ratings = s['ratings']
        summary.append({
            'player_id': pid,
            'name': s['name'],
            'matches': s['matches'],
            'avg_rating': sum(ratings) / len(ratings),
            'max_rating': max(ratings),
            'min_rating': min(ratings),
            'goals': s['goals'],
            'assists': s['assists'],
            'yellow': s['yellow'],
            'red': s['red'],
            'mom': s['mom_count'],
            'teams': list(s['teams']),
            'positions': list(s['positions']),
        })
    
    # Sort by avg_rating desc, then by matches desc
    summary.sort(key=lambda x: (-x['avg_rating'], -x['matches'], -x['goals'] - x['assists']))
    
    # Load player nationality from main CSV
    player_nationality = {}
    if PLAYERS_CSV.exists():
        with open(PLAYERS_CSV) as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('球员', '').strip()
                if key:
                    player_nationality[key.lower()] = row.get('国家', '')
    
    # Build HTML
    rows = []
    for rank, p in enumerate(summary, 1):
        # Find nationality
        natl = player_nationality.get(p['name'].lower(), '?')
        # Format trajectory
        teams = ', '.join(p['teams'])
        pos = ', '.join(p['positions'])
        rows.append(f'''
        <tr data-matches="{p['matches']}" data-rating="{p['avg_rating']:.2f}" data-stage="all">
          <td class="rank">{rank}</td>
          <td class="player">
            <strong>{html_lib.escape(p['name'])}</strong>
            <div class="sub">#{p['player_id']} · {pos}</div>
          </td>
          <td class="natl">{html_lib.escape(natl)}</td>
          <td class="teams">{html_lib.escape(teams[:40])}</td>
          <td class="mp">{p['matches']}</td>
          <td class="avg"><strong>{p['avg_rating']:.2f}</strong></td>
          <td class="hi">{p['max_rating']:.2f}</td>
          <td class="lo">{p['min_rating']:.2f}</td>
          <td class="g">{p['goals']}</td>
          <td class="a">{p['assists']}</td>
          <td class="mom">{'⭐' if p['mom'] else ''}</td>
        </tr>
        ''')
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏆 2026 世界杯球员评分排行榜 (WhoScored)</title>
<style>
:root {{
  --bg: #0a0e1a; --card: #1a1f2e; --border: #2a3142; --text: #e4e7eb; --muted: #8b95a8;
  --gold: #fbbf24; --green: #10b981; --blue: #3b82f6; --red: #ef4444;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  padding: 20px; line-height: 1.5;
}}
.container {{ max-width: 1400px; margin: 0 auto; }}
header {{
  text-align: center; padding: 30px 0 20px;
  background: linear-gradient(135deg, #1e3a8a 0%, #7c2d12 100%);
  border-radius: 16px; margin-bottom: 30px; padding: 40px 20px;
}}
h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
.subtitle {{ color: rgba(255,255,255,0.7); font-size: 1.1em; }}
.stats {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px; margin: 30px 0;
}}
.stat {{
  background: var(--card); padding: 20px; border-radius: 12px; text-align: center;
  border: 1px solid var(--border);
}}
.stat-num {{ font-size: 2.2em; font-weight: 700; color: var(--gold); }}
.stat-label {{ color: var(--muted); font-size: 0.9em; margin-top: 5px; }}
.controls {{
  background: var(--card); padding: 20px; border-radius: 12px;
  border: 1px solid var(--border); margin-bottom: 20px;
  display: flex; flex-wrap: wrap; gap: 15px; align-items: center;
}}
.controls input, .controls select {{
  background: #0a0e1a; color: var(--text); border: 1px solid var(--border);
  padding: 8px 12px; border-radius: 6px; font-size: 0.95em;
}}
.controls input {{ flex: 1; min-width: 200px; }}
.controls label {{ color: var(--muted); font-size: 0.9em; }}
table {{
  width: 100%; border-collapse: collapse; background: var(--card);
  border-radius: 12px; overflow: hidden; border: 1px solid var(--border);
}}
thead th {{
  background: #0a0e1a; padding: 14px 10px; text-align: left;
  font-weight: 600; color: var(--muted); font-size: 0.85em;
  text-transform: uppercase; letter-spacing: 0.5px;
  border-bottom: 2px solid var(--border);
}}
tbody td {{
  padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 0.95em;
}}
tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
.rank {{ font-weight: 700; color: var(--gold); width: 50px; text-align: center; }}
.player strong {{ color: var(--text); }}
.player .sub {{ font-size: 0.8em; color: var(--muted); margin-top: 2px; }}
.natl {{ color: var(--blue); font-weight: 500; }}
.teams {{ font-size: 0.85em; color: var(--muted); }}
.mp {{ text-align: center; color: var(--muted); }}
.avg {{ font-weight: 700; color: var(--gold); font-size: 1.1em; text-align: center; }}
.hi {{ color: var(--green); text-align: center; }}
.lo {{ color: var(--red); opacity: 0.8; text-align: center; }}
.g, .a {{ text-align: center; font-weight: 500; }}
.mom {{ text-align: center; font-size: 1.2em; }}
@media (max-width: 768px) {{
  .controls {{ flex-direction: column; align-items: stretch; }}
  table {{ font-size: 0.85em; }}
  thead th, tbody td {{ padding: 8px 4px; }}
}}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🏆 2026 世界杯球员评分排行榜</h1>
    <p class="subtitle">数据源: WhoScored 真实评分 · 自动抓取 94 场比赛 · 2968 条球员评分记录</p>
  </header>

  <div class="stats">
    <div class="stat">
      <div class="stat-num">{len(summary)}</div>
      <div class="stat-label">已评分球员</div>
    </div>
    <div class="stat">
      <div class="stat-num">94</div>
      <div class="stat-label">已完赛比赛</div>
    </div>
    <div class="stat">
      <div class="stat-num">{sum(p['goals'] for p in summary)}</div>
      <div class="stat-label">进球总数</div>
    </div>
    <div class="stat">
      <div class="stat-num">{sum(p['assists'] for p in summary)}</div>
      <div class="stat-label">助攻总数</div>
    </div>
    <div class="stat">
      <div class="stat-num">{sum(p['mom'] for p in summary)}</div>
      <div class="stat-label">全场最佳</div>
    </div>
    <div class="stat">
      <div class="stat-num">{max(p['avg_rating'] for p in summary if p['matches']>=3):.2f}</div>
      <div class="stat-label">最高均分 (≥3场)</div>
    </div>
  </div>

  <div class="controls">
    <label>🔍 搜索:</label>
    <input type="text" id="searchInput" placeholder="按球员、国家、球队搜索...">
    <label>📅 比赛场数:</label>
    <select id="matchesFilter">
      <option value="0">全部</option>
      <option value="3">≥ 3 场</option>
      <option value="4">≥ 4 场</option>
      <option value="5">≥ 5 场</option>
      <option value="6">≥ 6 场</option>
      <option value="7">≥ 7 场</option>
    </select>
  </div>

  <table>
    <thead>
      <tr>
        <th>排名</th>
        <th>球员</th>
        <th>国家队</th>
        <th>球队</th>
        <th>场</th>
        <th>均分</th>
        <th>最高</th>
        <th>最低</th>
        <th>球</th>
        <th>助</th>
        <th>MOTM</th>
      </tr>
    </thead>
    <tbody id="ratingsBody">
      {''.join(rows)}
    </tbody>
  </table>
</div>

<script>
const searchInput = document.getElementById('searchInput');
const matchesFilter = document.getElementById('matchesFilter');
const tbody = document.getElementById('ratingsBody');

function applyFilter() {{
  const q = searchInput.value.toLowerCase();
  const minMatches = parseInt(matchesFilter.value);
  const rows = tbody.querySelectorAll('tr');
  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    const matches = parseInt(row.dataset.matches);
    const showSearch = !q || text.includes(q);
    const showMatches = !minMatches || matches >= minMatches;
    row.style.display = (showSearch && showMatches) ? '' : 'none';
  }});
}}

searchInput.addEventListener('input', applyFilter);
matchesFilter.addEventListener('change', applyFilter);
</script>
</body>
</html>'''
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    
    print(f"Top 10 by avg rating (≥3 matches):")
    for p in [s for s in summary if s['matches'] >= 3][:10]:
        print(f"  {p['name']:30} ({p['matches']}场) avg={p['avg_rating']:.2f} max={p['max_rating']:.2f}")
    
    print(f"\nTotal unique players: {len(summary)}")
    print(f"Output: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
