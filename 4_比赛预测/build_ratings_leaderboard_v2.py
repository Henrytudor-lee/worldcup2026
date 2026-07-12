#!/usr/bin/env python3
"""Build WhoScored player ratings leaderboard HTML v2 with full player data."""
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
    for f in sorted(PLAYER_RATINGS_DIR.glob("match_*.json")):
        with open(f) as fh:
            all_ratings.extend(json.load(fh))
    print(f"Total ratings loaded: {len(all_ratings)}")

    # Group ratings by player
    player_stats = defaultdict(lambda: {
        'ratings': [],
        'matches': [],
        'goals': 0,
        'assists': 0,
        'yellow': 0,
        'red': 0,
        'mom_count': 0,
        'passes_key': 0,
        'shots_on_target': 0,
        'penalty_goals': 0,
        'penalty_missed': 0,
        'tackle_successful': 0,
        'dribbles_attempted': 0,
        'aerials_won': 0,
        'teams': set(),
        'positions': set(),
        'opponents': set(),
        'shirt_nos': set(),
    })

    for r in all_ratings:
        pid = r['player_id']
        s = player_stats[pid]
        s['name'] = r['player_name']
        s['ratings'].append(r['final_rating'])
        # Store full match data for drill-down
        s['matches'].append({
            'match_id': r['match_id'],
            'date': r.get('date', ''),
            'team': r['team'],
            'opponent': r['opponent'],
            'home_away': r['home_away'],
            'shirt_no': r.get('shirt_no', ''),
            'position': r.get('position', ''),
            'rating': r['final_rating'],
            'max_minute': r.get('max_minute', 0),
            'goals': r.get('goals', 0),
            'assists': r.get('assists', 0),
            'total_shots': r.get('total_shots', 0),
            'shots_on_target': r.get('shots_on_target', 0),
            'passes_key': r.get('passes_key', 0),
            'penalty_goals': r.get('penalty_goals', 0),
            'penalty_missed': r.get('penalty_missed', 0),
            'yellow_cards': r.get('yellow_cards', 0),
            'red_cards': r.get('red_cards', 0),
            'is_man_of_match': r.get('is_man_of_match', False),
            'is_first_eleven': r.get('is_first_eleven', False),
            'age': r.get('age', 0),
            'score': r.get('score', ''),
        })
        s['goals'] += r.get('goals', 0)
        s['assists'] += r.get('assists', 0)
        s['yellow'] += r.get('yellow_cards', 0)
        s['red'] += r.get('red_cards', 0)
        s['mom_count'] += 1 if r.get('is_man_of_match') else 0
        s['passes_key'] += r.get('passes_key', 0)
        s['shots_on_target'] += r.get('shots_on_target', 0)
        s['penalty_goals'] += r.get('penalty_goals', 0)
        s['penalty_missed'] += r.get('penalty_missed', 0)
        s['tackle_successful'] += r.get('tackle_successful', 0)
        s['dribbles_attempted'] += r.get('dribbles_attempted', 0)
        s['aerials_won'] += r.get('aerials_won', 0)
        s['teams'].add(r['team'])
        s['positions'].add(r.get('position', ''))
        s['opponents'].add(r['opponent'])
        if r.get('shirt_no'):
            s['shirt_nos'].add(r['shirt_no'])

    # Determine nationality by team
    # Map WhoScored team names to FIFA country codes/names
    # WhoScored uses English team names; main CSV has Chinese team names
    # We'll map by team (national team)

    # Load team code mapping from main CSV
    # Country in WhoScored may be "England", "USA", "South Korea" etc.
    # We need a mapping: WS team name -> main CSV 国家
    # Since main CSV has "英格兰", "美国", "韩国" etc., we need a lookup

    # Strategy: For each player, count their team appearances in WS data
    # Most frequent team = their national team
    # Then map WS team -> FIFA country name -> main CSV 国家 column

    # WS team to FIFA country name mapping (most common)
    ws_to_country = {
        'Argentina': '阿根廷', 'Australia': '澳大利亚', 'Austria': '奥地利',
        'Belgium': '比利时', 'Brazil': '巴西', 'Canada': '加拿大',
        'Cape Verde': '佛得角', 'Colombia': '哥伦比亚', 'Croatia': '克罗地亚',
        'Czech Republic': '捷克', 'Denmark': '丹麦', 'Egypt': '埃及',
        'England': '英格兰', 'France': '法国', 'Germany': '德国',
        'Ghana': '加纳', 'Haiti': '海地', 'Iran': '伊朗', 'Iraq': '伊拉克',
        'Italy': '意大利', 'Ivory Coast': '科特迪瓦', 'Jamaica': '牙买加',
        'Japan': '日本', 'Jordan': '约旦', 'Mexico': '墨西哥', 'Morocco': '摩洛哥',
        'Netherlands': '荷兰', 'New Zealand': '新西兰', 'Nigeria': '尼日利亚',
        'North Korea': '朝鲜', 'Norway': '挪威', 'Panama': '巴拿马',
        'Paraguay': '巴拉圭', 'Poland': '波兰', 'Portugal': '葡萄牙',
        'Qatar': '卡塔尔', 'Saudi Arabia': '沙特', 'Scotland': '苏格兰',
        'Senegal': '塞内加尔', 'Serbia': '塞尔维亚', 'Slovakia': '斯洛伐克',
        'Slovenia': '斯洛文尼亚', 'South Africa': '南非', 'South Korea': '韩国',
        'Spain': '西班牙', 'Sweden': '瑞典', 'Switzerland': '瑞士',
        'Tunisia': '突尼斯', 'Turkey': '土耳其', 'Ukraine': '乌克兰',
        'United Arab Emirates': '阿联酋', 'United States': '美国',
        'Uruguay': '乌拉圭', 'Wales': '威尔士', "Côte d'Ivoire": '科特迪瓦',
        'Curacao': '库拉索', 'South Korea': '韩国', 'Curaçao': '库拉索',
        'Algeria': '阿尔及利亚', 'Türkiye': '土耳其', 'Korea Republic': '韩国',
        'USA': '美国', 'Saudi': '沙特', 'Korea DPR': '朝鲜',
        'IR Iran': '伊朗', 'Cape Verde Islands': '佛得角',
        'Cabo Verde': '佛得角', 'Curacao': '库拉索', 'Czechia': '捷克',
    }

    # Build player country mapping
    # For each player, the most common team they played for in WS = their national team
    player_country = {}
    player_country_en = {}
    for pid, s in player_stats.items():
        # team counts
        team_counts = defaultdict(int)
        for m in s['matches']:
            team_counts[m['team']] += 1
        if team_counts:
            top_team = max(team_counts, key=team_counts.get)
            player_country[pid] = ws_to_country.get(top_team, top_team)
            player_country_en[pid] = top_team

    # Also build player_id -> main CSV player name mapping
    # Use a fuzzy approach: team + position + name similarity
    # But for now, we'll just show WhoScored name (English) + nationality
    # (we can show Chinese name if we find match)

    # Build summary
    summary = []
    for pid, s in player_stats.items():
        if s['matches'] == 0:
            continue
        ratings = [m['rating'] for m in s['matches']]
        # Sort matches by date
        s['matches'].sort(key=lambda m: m.get('date', ''))
        summary.append({
            'player_id': pid,
            'name': s['name'],
            'country': player_country.get(pid, '?'),
            'country_en': player_country_en.get(pid, '?'),
            'team_count': len(s['teams']),
            'matches': len(s['matches']),
            'avg_rating': sum(ratings) / len(ratings),
            'max_rating': max(ratings),
            'min_rating': min(ratings),
            'goals': s['goals'],
            'assists': s['assists'],
            'yellow': s['yellow'],
            'red': s['red'],
            'mom': s['mom_count'],
            'passes_key': s['passes_key'],
            'shots_on_target': s['shots_on_target'],
            'penalty_goals': s['penalty_goals'],
            'penalty_missed': s['penalty_missed'],
            'tackle_successful': s['tackle_successful'],
            'dribbles_attempted': s['dribbles_attempted'],
            'aerials_won': s['aerials_won'],
            'positions': list(s['positions']),
            'shirt_nos': list(s['shirt_nos']),
            'all_matches': s['matches'],
        })

    # Sort by avg_rating desc, then by matches desc
    summary.sort(key=lambda x: (-x['avg_rating'], -x['matches'], -x['goals'] - x['assists']))

    # Stats
    total_goals = sum(p['goals'] for p in summary)
    total_assists = sum(p['assists'] for p in summary)
    max_avg = max((p['avg_rating'] for p in summary if p['matches'] >= 3), default=0)

    # Build match HTML for each player (drill-down)
    def render_match_rows(player):
        rows = []
        for m in player['all_matches']:
            match_label = f"{m['team']} vs {m['opponent']}"
            score = m.get('score', '')
            date = m.get('date', '')[:10] if m.get('date') else ''
            pos = m.get('position', '')
            jersey = m.get('shirt_no', '')
            # Rating color
            rating = m['rating']
            if rating >= 8.0:
                badge = 'gold'
            elif rating >= 7.0:
                badge = 'green'
            elif rating >= 6.0:
                badge = 'neutral'
            else:
                badge = 'red'

            rows.append(f'''
              <tr>
                <td class="date">{date}</td>
                <td class="match">{html_lib.escape(match_label)}</td>
                <td class="score">{html_lib.escape(score)}</td>
                <td class="pos">#{jersey} {pos}</td>
                <td><span class="rating-badge {badge}">{rating:.2f}</span></td>
                <td class="goals">{m['goals']}</td>
                <td class="assists">{m['assists']}</td>
                <td class="shots">{m['total_shots']}</td>
                <td class="cards">{('🟨' if m['yellow_cards'] else '')}{('🟥' if m['red_cards'] else '')}</td>
                <td>{'⭐' if m['is_man_of_match'] else ''}</td>
                <td>{'首发' if m['is_first_eleven'] else '替补'}</td>
                <td>{m['max_minute']}'</td>
              </tr>
            ''')
        return ''.join(rows)

    # Main rows for table
    rows = []
    for rank, p in enumerate(summary, 1):
        rows.append(f'''
        <tr class="player-row" data-player-id="{p['player_id']}" data-name="{html_lib.escape(p['name'])}" data-matches="{p['matches']}">
          <td class="rank">{rank}</td>
          <td class="player"><strong>{html_lib.escape(p['name'])}</strong></td>
          <td class="natl">{html_lib.escape(p['country'])}</td>
          <td class="pos">{','.join(p['positions'])}</td>
          <td class="mp">{p['matches']}</td>
          <td class="avg">{p['avg_rating']:.2f}</td>
          <td class="hi">{p['max_rating']:.2f}</td>
          <td class="lo">{p['min_rating']:.2f}</td>
          <td class="g">{p['goals']}</td>
          <td class="a">{p['assists']}</td>
          <td>{'⭐' if p['mom'] else ''}</td>
        </tr>
        ''')

    # Full player data as JSON for drill-down
    # NOTE: 'match_count' = number, 'all_matches' = list (for modal)
    player_data_json = json.dumps([{
        'player_id': p['player_id'],
        'name': p['name'],
        'country': p['country'],
        'country_en': p['country_en'],
        'avg_rating': p['avg_rating'],
        'max_rating': p['max_rating'],
        'min_rating': p['min_rating'],
        'goals': p['goals'],
        'assists': p['assists'],
        'yellow': p['yellow'],
        'red': p['red'],
        'mom': p['mom'],
        'passes_key': p.get('passes_key', 0),
        'shots_on_target': p.get('shots_on_target', 0),
        'penalty_goals': p.get('penalty_goals', 0),
        'penalty_missed': p.get('penalty_missed', 0),
        'tackle_successful': p.get('tackle_successful', 0),
        'dribbles_attempted': p.get('dribbles_attempted', 0),
        'aerials_won': p.get('aerials_won', 0),
        'match_count': p['matches'],
        'all_matches': p['all_matches'],
        'positions': p['positions'],
        'shirt_nos': p['shirt_nos'],
    } for p in summary], ensure_ascii=False)

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
  --yellow: #facc15;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  padding: 20px; line-height: 1.5;
}}
.container {{ max-width: 1500px; margin: 0 auto; }}
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
tbody tr:hover {{ background: rgba(255,255,255,0.03); cursor: pointer; }}
.rank {{ font-weight: 700; color: var(--gold); width: 50px; text-align: center; }}
.player strong {{ color: var(--text); }}
.natl {{ color: var(--blue); font-weight: 500; }}
.pos {{ font-size: 0.85em; color: var(--muted); }}
.mp {{ text-align: center; color: var(--muted); }}
.avg {{ font-weight: 700; color: var(--gold); font-size: 1.1em; text-align: center; }}
.hi {{ color: var(--green); text-align: center; }}
.lo {{ color: var(--red); opacity: 0.8; text-align: center; }}
.g, .a {{ text-align: center; font-weight: 500; }}

/* Modal */
.modal-overlay {{
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7); z-index: 1000;
  display: none; align-items: center; justify-content: center;
  padding: 20px;
}}
.modal-overlay.active {{ display: flex; }}
.modal {{
  background: var(--card); border-radius: 16px;
  max-width: 1200px; width: 100%; max-height: 90vh;
  overflow-y: auto; border: 1px solid var(--border);
}}
.modal-header {{
  padding: 20px 24px; border-bottom: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: flex-start;
  background: linear-gradient(135deg, #1e3a8a 0%, #581c87 100%);
  border-radius: 16px 16px 0 0;
}}
.modal-header h2 {{ margin: 0; font-size: 1.5em; }}
.modal-header .meta {{ color: rgba(255,255,255,0.7); font-size: 0.9em; margin-top: 6px; }}
.close-btn {{
  background: rgba(255,255,255,0.1); border: none; color: white;
  width: 36px; height: 36px; border-radius: 8px; cursor: pointer;
  font-size: 1.5em; line-height: 1;
}}
.close-btn:hover {{ background: rgba(255,255,255,0.2); }}
.modal-body {{ padding: 20px 24px; }}
.player-summary {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin-bottom: 20px;
}}
.ps-item {{
  background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; text-align: center;
}}
.ps-label {{ color: var(--muted); font-size: 0.8em; text-transform: uppercase; }}
.ps-value {{ font-size: 1.4em; font-weight: 700; color: var(--gold); margin-top: 4px; }}
.rating-badge {{
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-weight: 700; font-size: 0.95em;
}}
.rating-badge.gold {{ background: var(--gold); color: #000; }}
.rating-badge.green {{ background: var(--green); color: #000; }}
.rating-badge.neutral {{ background: var(--muted); color: #000; }}
.rating-badge.red {{ background: var(--red); color: #fff; }}
.matches-table {{ font-size: 0.9em; }}
.matches-table th {{ background: rgba(0,0,0,0.3); font-size: 0.75em; }}
.matches-table td {{ padding: 8px 6px; }}
.matches-table .date {{ white-space: nowrap; color: var(--muted); font-size: 0.85em; }}
.matches-table .match {{ font-weight: 500; }}
.matches-table .score {{ color: var(--muted); font-size: 0.85em; }}
.matches-table .pos {{ color: var(--muted); font-size: 0.8em; }}
.matches-table .goals, .matches-table .assists, .matches-table .shots {{ text-align: center; font-weight: 600; }}
.matches-table .cards {{ text-align: center; }}
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
    <p class="subtitle">数据源: WhoScored 真实评分 · 自动抓取 94 场比赛 · {len(all_ratings)} 条球员评分 · 点击球员查看详情</p>
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
      <div class="stat-num">{total_goals}</div>
      <div class="stat-label">进球总数</div>
    </div>
    <div class="stat">
      <div class="stat-num">{total_assists}</div>
      <div class="stat-label">助攻总数</div>
    </div>
    <div class="stat">
      <div class="stat-num">{sum(p['mom'] for p in summary)}</div>
      <div class="stat-label">全场最佳</div>
    </div>
    <div class="stat">
      <div class="stat-num">{max_avg:.2f}</div>
      <div class="stat-label">最高均分 (≥3场)</div>
    </div>
  </div>

  <div class="controls">
    <label>🔍 搜索:</label>
    <input type="text" id="searchInput" placeholder="按球员、国家、位置搜索...">
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
        <th>位置</th>
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

<!-- Player detail modal -->
<div class="modal-overlay" id="playerModal">
  <div class="modal">
    <div class="modal-header">
      <div>
        <h2 id="modalTitle">Player Detail</h2>
        <div class="meta" id="modalMeta"></div>
      </div>
      <button class="close-btn" onclick="closeModal()">×</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<script>
const playerData = {player_data_json};
const searchInput = document.getElementById('searchInput');
const matchesFilter = document.getElementById('matchesFilter');
const tbody = document.getElementById('ratingsBody');
const modal = document.getElementById('playerModal');

function applyFilter() {{
  const q = searchInput.value.toLowerCase();
  const minMatches = parseInt(matchesFilter.value);
  const rows = tbody.querySelectorAll('tr');
  rows.forEach(row => {{
    const text = row.textContent.toLowerCase();
    const matches = parseInt(row.dataset.matches || '0');
    const showSearch = !q || text.includes(q);
    const showMatches = !minMatches || matches >= minMatches;
    row.style.display = (showSearch && showMatches) ? '' : 'none';
  }});
}}

searchInput.addEventListener('input', applyFilter);
matchesFilter.addEventListener('change', applyFilter);

// Click on player row to show detail
tbody.addEventListener('click', (e) => {{
  const row = e.target.closest('tr');
  if (row && row.dataset.playerId) {{
    showPlayerDetail(parseInt(row.dataset.playerId));
  }}
}});

function showPlayerDetail(playerId) {{
  const p = playerData.find(x => x.player_id === playerId);
  if (!p) return;
  
  document.getElementById('modalTitle').textContent = p.name;
  document.getElementById('modalMeta').textContent =
    `${{p.country}} (${{p.country_en}}) · 位置: ${{p.positions.join('/')}} · ID: ${{p.player_id}}`;
  
  const body = document.getElementById('modalBody');
  
  // Build summary stats
  const summaryHtml = `
    <div class="player-summary">
      <div class="ps-item">
        <div class="ps-label">场数</div>
        <div class="ps-value">${{p.match_count}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">平均分</div>
        <div class="ps-value">${{p.avg_rating.toFixed(2)}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">最高分</div>
        <div class="ps-value" style="color:var(--green)">${{p.max_rating.toFixed(2)}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">最低分</div>
        <div class="ps-value" style="color:var(--red)">${{p.min_rating.toFixed(2)}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">进球</div>
        <div class="ps-value">${{p.goals}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">助攻</div>
        <div class="ps-value">${{p.assists}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">黄牌</div>
        <div class="ps-value">${{p.yellow}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">红牌</div>
        <div class="ps-value">${{p.red}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">MOTM</div>
        <div class="ps-value">${{p.mom}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">关键传球</div>
        <div class="ps-value">${{p.passes_key || 0}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">射正</div>
        <div class="ps-value">${{p.shots_on_target || 0}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">点球破门</div>
        <div class="ps-value">${{p.penalty_goals || 0}}</div>
      </div>
      <div class="ps-item">
        <div class="ps-label">争顶成功</div>
        <div class="ps-value">${{p.aerials_won || 0}}</div>
      </div>
    </div>

    <h3 style="margin: 20px 0 12px; color: var(--gold);">📅 比赛详情</h3>
    <table class="matches-table">
      <thead>
        <tr>
          <th>日期</th>
          <th>比赛</th>
          <th>比分</th>
          <th>位置</th>
          <th>评分</th>
          <th>球</th>
          <th>助</th>
          <th>射门</th>
          <th>射正</th>
          <th>关键</th>
          <th>点球</th>
          <th>牌</th>
          <th>MOTM</th>
          <th>状态</th>
          <th>分钟</th>
        </tr>
      </thead>
      <tbody>
        ${{p.all_matches.map(m => {{
          const rating = m.rating;
          const badge = rating >= 8.0 ? 'gold' : rating >= 7.0 ? 'green' : rating >= 6.0 ? 'neutral' : 'red';
          return `
            <tr>
              <td class="date">${{(m.date || '').slice(0,10)}}</td>
              <td class="match">${{m.team}} vs ${{m.opponent}}</td>
              <td class="score">${{m.score || ''}}</td>
              <td class="pos">#${{m.shirt_no || ''}} ${{m.position || ''}}</td>
              <td><span class="rating-badge ${{badge}}">${{rating.toFixed(2)}}</span></td>
              <td class="goals">${{m.goals || 0}}</td>
              <td class="assists">${{m.assists || 0}}</td>
              <td class="shots">${{m.total_shots || 0}}</td>
              <td class="sot">${{m.shots_on_target || 0}}</td>
              <td class="kp">${{m.passes_key || 0}}</td>
              <td class="pen">${{(m.penalty_goals || 0) ? '⚽PK' : ''}}${{(m.penalty_missed || 0) ? '❌' : ''}}</td>
              <td class="cards">${{(m.yellow_cards ? '🟨' : '')}}${{(m.red_cards ? '🟥' : '')}}</td>
              <td>${{m.is_man_of_match ? '⭐' : ''}}</td>
              <td>${{m.is_first_eleven ? '首发' : '替补'}}</td>
              <td>${{m.max_minute || 0}}'</td>
            </tr>
          `;
        }}).join('')}}
      </tbody>
    </table>
  `;
  
  body.innerHTML = summaryHtml;
  modal.classList.add('active');
}}

function closeModal() {{
  modal.classList.remove('active');
}}

modal.addEventListener('click', (e) => {{
  if (e.target === modal) closeModal();
}});
</script>
</body>
</html>'''
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    
    print(f"\nTop 15 by avg rating (≥3 matches):")
    for p in [s for s in summary if s['matches'] >= 3][:15]:
        print(f"  #{p['player_id']:6} {p['name']:30} ({p['country']:5}) {p['matches']}场 avg={p['avg_rating']:.2f} max={p['max_rating']:.2f} G={p['goals']} A={p['assists']}")
    
    print(f"\nTotal unique players: {len(summary)}")
    print(f"Output: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
