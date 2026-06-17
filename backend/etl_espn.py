"""
ESPN 赛事数据 ETL
- 读 1_数据基础/espn_match_data/{event_id}.json
- 解析成 3 张 CSV:
  - match_team_stats.csv  (控球率/射门/射正/角球/犯规/黄红牌等, 每场每队 1 行)
  - match_player_stats.csv (每场每球员 1 行)
  - match_events.csv (每场每事件 1 行, 进球/换人/卡牌/关键事件)
- 球员中文名通过 (team_cn, jersey) 匹配主表 world_cup_2026_complete.csv

用法:
  python3 backend/etl_espn.py            # 处理全部
  python3 backend/etl_espn.py 760433     # 处理单场
"""
import json, csv, os, sys
from pathlib import Path

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
DATA = PROJECT / '1_数据基础'
RAW = DATA / 'espn_match_data'
BACKEND = PROJECT / 'backend'

# 中英文球队名映射
EN2CN = {
    'Mexico': '墨西哥', 'South Africa': '南非', 'South Korea': '韩国', 'Czechia': '捷克',
    'Canada': '加拿大', 'Bosnia-Herzegovina': '波黑', 'United States': '美国', 'Paraguay': '巴拉圭',
    'Qatar': '卡塔尔', 'Switzerland': '瑞士', 'Brazil': '巴西', 'Morocco': '摩洛哥',
    'Haiti': '海地', 'Scotland': '苏格兰', 'Australia': '澳大利亚', 'Türkiye': '土耳其',
    'Germany': '德国', 'Curaçao': '库拉索', 'Netherlands': '荷兰', 'Japan': '日本',
    'Ivory Coast': '科特迪瓦', 'Ecuador': '厄瓜多尔', 'Sweden': '瑞典', 'Tunisia': '突尼斯',
    'Spain': '西班牙', 'Cape Verde': '佛得角', 'Belgium': '比利时', 'Egypt': '埃及',
    'Saudi Arabia': '沙特', 'Uruguay': '乌拉圭', 'Iran': '伊朗', 'New Zealand': '新西兰',
    'France': '法国', 'Senegal': '塞内加尔', 'Iraq': '伊拉克', 'Norway': '挪威',
    'Argentina': '阿根廷', 'Algeria': '阿尔及利亚', 'Austria': '奥地利', 'Jordan': '约旦',
    'Portugal': '葡萄牙', 'Congo DR': '民主刚果', 'England': '英格兰', 'Croatia': '克罗地亚',
    'Ghana': '加纳', 'Panama': '巴拿马', 'Uzbekistan': '乌兹别克斯坦', 'Colombia': '哥伦比亚',
}

# 加载主表, 建 (team_cn, jersey) -> name_cn 索引
def load_roster_index():
    """返回 {(team_cn, jersey_str): name_cn}"""
    idx = {}
    with open(DATA / 'world_cup_2026_complete.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            team_cn = r.get('国家', '').strip()
            jersey = r.get('号码', '').strip()
            name = r.get('球员', '').strip()
            if team_cn and jersey and name:
                # 一个号码可能有多个球员 (如国家队 #10 经常换人) -> 取第一个
                idx.setdefault((team_cn, jersey), name)
    return idx

ROSTER_IDX = load_roster_index()

def get_player_cn(team_cn, jersey):
    """按 (team_cn, jersey) 查主表, 没找到返回空字符串"""
    if not jersey:
        return ''
    return ROSTER_IDX.get((team_cn, str(jersey).strip()), '')


def parse_event(event_id: str) -> tuple:
    """解析单场 ESPN summary.json, 返回 (team_stats_dict, player_stats_list, events_list)"""
    path = RAW / f'{event_id}.json'
    with open(path) as f:
        data = json.load(f)

    # 元数据
    header = data.get('header', {})
    comp = header.get('competitions', [{}])[0]
    competitors = comp.get('competitors', [])
    venue = data.get('gameInfo', {}).get('venue', {})
    venue_name = venue.get('fullName', '') or venue.get('shortName', '')

    # 主客队 (按 homeAway 字段)
    home_team = next((c for c in competitors if c.get('homeAway') == 'home'), {})
    away_team = next((c for c in competitors if c.get('homeAway') == 'away'), {})
    home_en = home_team.get('team', {}).get('displayName', '')
    away_en = away_team.get('team', {}).get('displayName', '')
    home_cn = EN2CN.get(home_en, home_en)
    away_cn = EN2CN.get(away_en, away_en)
    home_score = home_team.get('score', 0)
    away_score = away_team.get('score', 0)
    home_winner = home_team.get('winner', False)
    away_winner = away_team.get('winner', False)
    date_iso = comp.get('date', comp.get('startDate', ''))[:10]
    status_type = comp.get('status', {}).get('type', {}).get('description', '')

    match_id = f"{date_iso}_{home_cn}_vs_{away_cn}".replace(' ', '_')

    # === 1. 队伍统计 ===
    # boxscore.teams: [{team, statistics: [{name, displayValue}], homeAway}]
    bs_teams = data.get('boxscore', {}).get('teams', [])
    stats_by_team = {}
    for t in bs_teams:
        cn = EN2CN.get(t.get('team', {}).get('displayName', ''), '')
        s = {}
        for st in t.get('statistics', []):
            s[st['name']] = st.get('displayValue', '')
        stats_by_team[t.get('homeAway')] = s

    def s(home_away, key, default=''):
        return stats_by_team.get(home_away, {}).get(key, default)

    team_row = {
        'match_id': match_id,
        'espn_event_id': event_id,
        'date': date_iso,
        'home_team_cn': home_cn, 'away_team_cn': away_cn,
        'home_team_en': home_en, 'away_team_en': away_en,
        'home_score': home_score, 'away_score': away_score,
        'home_winner': home_winner, 'away_winner': away_winner,
        'venue': venue_name,
        'status': status_type,
        'source': 'ESPN',
        # 队级统计
        'home_possession_pct': s('home', 'possessionPct'),
        'away_possession_pct': s('away', 'possessionPct'),
        'home_total_shots': s('home', 'totalShots'),
        'away_total_shots': s('away', 'totalShots'),
        'home_shots_on_target': s('home', 'shotsOnTarget'),
        'away_shots_on_target': s('away', 'shotsOnTarget'),
        'home_shot_pct': s('home', 'shotPct'),
        'away_shot_pct': s('away', 'shotPct'),
        'home_corners': s('home', 'wonCorners'),
        'away_corners': s('away', 'wonCorners'),
        'home_penalty_goals': s('home', 'penaltyKickGoals'),
        'away_penalty_goals': s('away', 'penaltyKickGoals'),
        'home_penalty_kicks': s('home', 'penaltyKickShots'),
        'away_penalty_kicks': s('away', 'penaltyKickShots'),
        'home_fouls': s('home', 'foulsCommitted'),
        'away_fouls': s('away', 'foulsCommitted'),
        'home_yellow_cards': s('home', 'yellowCards'),
        'away_yellow_cards': s('away', 'yellowCards'),
        'home_red_cards': s('home', 'redCards'),
        'away_red_cards': s('away', 'redCards'),
        'home_offsides': s('home', 'offsides'),
        'away_offsides': s('away', 'offsides'),
        'home_saves': s('home', 'saves'),
        'away_saves': s('away', 'saves'),
        'home_passes_total': s('home', 'totalPasses'),
        'away_passes_total': s('away', 'totalPasses'),
        'home_passes_accurate': s('home', 'accuratePasses'),
        'away_passes_accurate': s('away', 'accuratePasses'),
        'home_pass_pct': s('home', 'passPct'),
        'away_pass_pct': s('away', 'passPct'),
        'home_tackles_total': s('home', 'totalTackles'),
        'away_tackles_total': s('away', 'totalTackles'),
        'home_tackles_effective': s('home', 'effectiveTackles'),
        'away_tackles_effective': s('away', 'effectiveTackles'),
        'home_interceptions': s('home', 'interceptions'),
        'away_interceptions': s('away', 'interceptions'),
        'home_clearances': s('home', 'totalClearance'),
        'away_clearances': s('away', 'totalClearance'),
    }

    # === 2. 球员统计 ===
    player_rows = []
    for r in data.get('rosters', []):
        team_cn = EN2CN.get(r.get('team', {}).get('displayName', ''), '')
        home_away = r.get('homeAway', '')
        for p in r.get('roster', []):
            ath = p.get('athlete', {})
            if not ath:
                continue
            player_en = ath.get('displayName', ath.get('fullName', ''))
            jersey = p.get('jersey', '')
            position = p.get('position', {}).get('abbreviation', '')
            starter = p.get('starter', False)
            did_not_play = p.get('didNotPlay', False)
            subbed_in = p.get('subbedIn', False)
            subbed_out = p.get('subbedOut', False)
            minutes = p.get('minutes')  # ESPN 不给具体分钟

            # stats dict by name
            ps = {st['name']: st.get('displayValue', '') for st in p.get('stats', [])}

            player_rows.append({
                'match_id': match_id,
                'espn_event_id': event_id,
                'date': date_iso,
                'team_cn': team_cn,
                'home_away': home_away,
                'player_en': player_en,
                'player_cn': '',  # 暂留空 (ESPN jersey 字段错位, 按 jersey 映射主表不可靠)
                'jersey': jersey,
                'position': position,
                'starter': starter,
                'did_not_play': did_not_play,
                'subbed_in': subbed_in,
                'subbed_out': subbed_out,
                'minutes': minutes or '',
                'goals': ps.get('totalGoals', '0'),
                'assists': ps.get('goalAssists', '0'),
                'shots': ps.get('totalShots', '0'),
                'shots_on_target': ps.get('shotsOnTarget', '0'),
                'fouls_committed': ps.get('foulsCommitted', '0'),
                'fouls_suffered': ps.get('foulsSuffered', '0'),
                'yellow_cards': ps.get('yellowCards', '0'),
                'red_cards': ps.get('redCards', '0'),
                'own_goals': ps.get('ownGoals', '0'),
                'offsides': ps.get('offsides', '0'),
                'goals_conceded': ps.get('goalsConceded', '0'),  # 门将
                'saves': ps.get('saves', '0'),                      # 门将
                'shots_faced': ps.get('shotsFaced', '0'),           # 门将
                'sub_ins': ps.get('subIns', '0'),
                'source': 'ESPN',
            })

    # === 3. 事件流 (keyEvents) ===
    event_rows = []
    for e in data.get('keyEvents', []):
        etype = e.get('type', {}).get('text', '')
        clock = e.get('clock', {}).get('displayValue', '')
        short = e.get('shortText', '')
        # 提取参与队伍
        team_data = e.get('team', {}) or {}
        team_en = team_data.get('displayName', '') if team_data else ''
        team_cn = EN2CN.get(team_en, team_en)
        # 参与者
        participants = e.get('participants', []) or []
        player_en = ''
        for pp in participants:
            if pp.get('athlete'):
                player_en = pp['athlete'].get('displayName', '')
                break
        # 跳过 Start/End Delay 等系统事件 (没意义)
        if etype in ('Start Delay', 'End Delay', 'Kickoff', 'Halftime',
                     'Start 2nd Half', 'End Regular Time', 'End 2nd Half'):
            continue
        event_rows.append({
            'match_id': match_id,
            'espn_event_id': event_id,
            'date': date_iso,
            'clock': clock,
            'event_type': etype,
            'team_cn': team_cn,
            'player_en': player_en,
            'description': short,
            'source': 'ESPN',
        })

    return team_row, player_rows, event_rows


def main(target_ids=None):
    """主入口: 处理所有或指定 event_id"""
    if target_ids:
        ids = target_ids
    else:
        ids = sorted(p.stem for p in RAW.glob('*.json'))
    print(f'处理 {len(ids)} 场')

    all_team, all_player, all_event = [], [], []
    for eid in ids:
        try:
            tr, pr, er = parse_event(eid)
            all_team.append(tr)
            all_player.extend(pr)
            all_event.extend(er)
            h_cn = tr['home_team_cn']; a_cn = tr['away_team_cn']
            print(f"  ✅ {eid} {h_cn} vs {a_cn} ({tr['home_score']}-{tr['away_score']}) "
                  f"-- {len(pr)} 球员, {len(er)} 事件")
        except Exception as ex:
            print(f"  ❌ {eid} 失败: {ex}")
            import traceback; traceback.print_exc()

    # 写 CSV
    out_team = DATA / 'match_team_stats.csv'
    out_player = DATA / 'match_player_stats.csv'
    out_event = DATA / 'match_events.csv'

    if all_team:
        with open(out_team, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(all_team[0].keys()))
            w.writeheader()
            w.writerows(all_team)
        print(f'\n✅ {out_team.name}: {len(all_team)} 行')

    if all_player:
        with open(out_player, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(all_player[0].keys()))
            w.writeheader()
            w.writerows(all_player)
        print(f'✅ {out_player.name}: {len(all_player)} 行')

    if all_event:
        with open(out_event, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(all_event[0].keys()))
            w.writeheader()
            w.writerows(all_event)
        print(f'✅ {out_event.name}: {len(all_event)} 行')


if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        main(args)
    else:
        main()
