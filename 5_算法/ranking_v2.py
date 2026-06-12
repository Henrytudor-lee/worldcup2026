"""
Mavis PDP Ranking v2.1
- 用真实2025-26状态数据替代估值
- 锋/中场：身价 × 联赛 × 状态加权（进球/助攻/WhoScored）
- 后/门：身价 × 联赛 × 经验加成 (v3.1 位置加权)
- 教练：履历×阵型
- 4-3-3 位置分桶：锋3+中3+后4+门1
- **v2.1**: 所有权重从 weights_v21.json 读, 默认值匹配旧行为
"""
import csv, json, re, sys, os
from collections import defaultdict
from pathlib import Path

# ============== 加载权重配置 ==============
ROOT = Path('/Users/garcia/Desktop/WorldCup2026')
WEIGHTS_PATH = ROOT / '5_算法' / 'weights_v21.json'
DEFAULT_WEIGHTS = {
    'position_top_n': {'FW': 3, 'MID': 3, 'DEF': 4, 'GK': 1},
    'status_weights': {'g_per_goal': 40, 'a_per_assist': 60, 'who_bonus_base': 6.5, 'who_bonus_denom': 4},
    'nat_intl': {'g_per_goal': 200, 'a_per_assist': 300},
    'def_gk_weights': {'base_factor': 0.95, 'honors_per_champ': 15, 'starter_jersey_max': 14, 'starter_bonus': 50, 'wc_per_ga': 100},
    'player_to_total': {'player_share': 0.70, 'coach_share': 0.30},
    'smoothing': {'player_div': 5000, 'coach_div': 100, 'rank_div': 1000},
    'lambda_match': {'base': 1.3, 'k': 1.5},
}

def load_weights(custom_path=None):
    p = Path(custom_path) if custom_path else WEIGHTS_PATH
    if not p.exists():
        print(f"⚠️  权重文件不存在: {p}, 用默认值")
        return DEFAULT_WEIGHTS
    with open(p, encoding='utf-8') as f:
        cfg = json.load(f)
    # 合并默认 + 用户 (用户配置覆盖默认)
    merged = json.loads(json.dumps(DEFAULT_WEIGHTS))  # 深 copy
    for k, v in cfg.items():
        if k.startswith('_') or k == '_meta': continue
        if isinstance(v, dict) and k in merged:
            merged[k].update(v)
        else:
            merged[k] = v
    return merged

# ============== 联赛系数 (基础数据, 不放 weights) ==============
LEAGUE_STRENGTH = {
    '英超': 1.00, '西甲': 0.97, '意甲': 0.95, '德甲': 0.93, '法甲': 0.85,
    '葡超': 0.78, '荷甲': 0.75, '比甲': 0.72, '土超': 0.65, '美职联': 0.65,
    '巴甲': 0.65, '阿超': 0.62, 'MLS': 0.60, '苏超': 0.58, '墨超': 0.50,
    '沙特联': 0.55, '沙特超': 0.55, '墨超联': 0.50, '乌超': 0.40,
    '克甲': 0.40, '丹超': 0.50, '瑞超': 0.50, '挪超': 0.50, '奥超': 0.40,
    '捷甲': 0.40, '波兰超': 0.40, '比超': 0.50, '苏超': 0.50, '希超': 0.50,
    '俄超': 0.55, '卡超': 0.45, '阿联酋超': 0.45, '伊超': 0.40,
    '泰超': 0.35, '印尼超': 0.30, '越南超': 0.30, '非洲联赛': 0.30,
    '北非超': 0.40, '玻超': 0.40, '南美低': 0.40,
    '英冠': 0.55, '意乙': 0.50, '西乙': 0.50, '德乙': 0.50, '法乙': 0.45,
    '英甲': 0.40, '比乙': 0.45, '荷乙': 0.45, '葡甲': 0.45,
    '瑞士超': 0.55, '美乙': 0.40, 'NBA': 0.001,
}

def get_league_factor(league):
    if not league:
        return 0.50
    league = str(league).strip()
    if league in LEAGUE_STRENGTH:
        return LEAGUE_STRENGTH[league]
    for k, v in LEAGUE_STRENGTH.items():
        if k in league or league in k:
            return v
    return 0.50

def parse_num(s):
    if not s or str(s).strip() in ('X待核实', '-', '', 'nan', 'None'):
        return 0
    s = str(s).strip()
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:球|助|场|首发|替补|次|分钟|铲断|解围|拦截)', s)
    if m:
        v = float(m.group(1))
        if v < 200: return v
    m = re.search(r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)', s)
    if m and ('球' in s or '助' in s or '场' in s):
        v1 = float(m.group(1))
        v2 = float(m.group(2))
        return v1 if v1 < 100 else v2
    m = re.match(r'^(\d+(?:\.\d+)?)', s)
    if m:
        v = float(m.group(1))
        if v >= 100 and ('赛季' in s or '20' in s[:6] or len(s) > 8):
            return 0
        return v if v < 100 else 0
    return 0

def calc_status_weight(goals_str, assists_str, who_str, weights):
    sw = weights['status_weights']
    g = parse_num(goals_str)
    a = parse_num(assists_str)
    w = parse_num(who_str)
    if w == 0 or w < 5.5 or w > 9.0:
        w = 0
    w_bonus = max(0, (w - sw['who_bonus_base']) / sw['who_bonus_denom']) if w else 0
    return g / sw['g_per_goal'] + a / sw['a_per_assist'] + w_bonus

def parse_value(s):
    if not s: return 0
    s = str(s).strip()
    m = re.search(r'(\d+(?:\.\d+)?)', s)
    if m: return float(m.group(1))
    return 0

def parse_honors(s):
    if not s: return 0
    s = str(s)
    return s.count('冠军') * 5 + s.count('金靴') * 2 + s.count('最佳') * 3 + s.count('MVP') * 2

def load_status_data():
    status = {}
    with open('/Users/garcia/Desktop/WorldCup2026/2_数据补全/world_cup_2026_player_status_all.csv') as f:
        for rec in csv.DictReader(f):
            key = (rec['country'], rec['name_zh'])
            if key in status:
                for fld in ['appearances', 'goals', 'assists', 'whoscored_rating',
                            'def_tackles_p90', 'def_interceptions_p90', 'def_clearances_p90', 'def_aerial_pct',
                            'gk_save_pct', 'gk_clean_sheets', 'gk_goals_conceded_p90']:
                    if not status[key].get(fld) and rec.get(fld):
                        status[key][fld] = rec[fld]
            else:
                status[key] = dict(rec)
    return status

def calc_player_score(player, status, weights):
    """v2.1: 全部用 weights 配置"""
    pos = player.get('位置', '').strip()
    val = parse_value(player.get('身价_万欧', '0'))
    league = player.get('联赛', '')
    league_factor = get_league_factor(league)
    base = val * league_factor

    if pos in ('前锋', '中场'):
        sw = calc_status_weight(
            status.get('goals', '0'),
            status.get('assists', '0'),
            status.get('whoscored_rating', '0'),
            weights
        )
        nat_goals = parse_value(player.get('国家队进球', '0'))
        nat_assists = parse_value(player.get('国家队助攻', '0'))
        nat_cfg = weights['nat_intl']
        sw += nat_goals / nat_cfg['g_per_goal'] + nat_assists / nat_cfg['a_per_assist']
        return base * (1 + sw), base, sw
    else:
        # 后/门 v3.1
        dgw = weights['def_gk_weights']
        honors = parse_honors(player.get('主要荣誉', ''))
        honors_score = honors * dgw['honors_per_champ']

        jersey = parse_value(player.get('号码', '0'))
        starter_bonus = dgw['starter_bonus'] if 1 <= jersey <= dgw['starter_jersey_max'] else 0

        wc_goals = parse_value(player.get('世界杯进球', '0'))
        wc_assists = parse_value(player.get('世界杯助攻', '0'))
        wc_score = (wc_goals + wc_assists) * dgw['wc_per_ga']

        adjusted_base = base * dgw['base_factor']
        total_score = adjusted_base + honors_score + starter_bonus + wc_score
        return total_score, base, 0

def calc_coach_score(coach):
    if not coach: return 0, []
    text = str(coach.get('代表执教生涯', '')) + ' ' + str(coach.get('重大荣誉', ''))
    score = 0
    details = []
    if '5届' in text or '5 次' in text or '五次' in text:
        score += 50; details.append('5届+世界杯/欧洲杯')
    elif '4届' in text or '4 次' in text or '四次' in text:
        score += 35; details.append('4届')
    elif '3届' in text or '3 次' in text or '三次' in text:
        score += 25; details.append('3届')
    elif '2届' in text or '2 次' in text or '两次' in text:
        score += 15; details.append('2届')
    elif '1届' in text or '1 次' in text or '一次' in text:
        score += 8
    if '欧冠冠军' in text or '欧冠联赛冠军' in text:
        score += 30; details.append('欧冠冠军')
    elif '欧冠' in text:
        score += 15; details.append('欧冠经验')
    if '欧洲杯冠军' in text or '欧洲杯 冠军' in text:
        score += 40; details.append('欧洲杯冠军')
    elif '欧洲杯' in text and ('亚军' in text or '4强' in text or '半决赛' in text):
        score += 20; details.append('欧洲杯亚军/4强')
    elif '欧洲杯' in text:
        score += 10; details.append('欧洲杯经验')
    if '欧国联冠军' in text or '欧国联 冠军' in text:
        score += 25; details.append('欧国联冠军')
    elif '欧国联' in text and ('亚军' in text or '4强' in text or '半决赛' in text):
        score += 12; details.append('欧国联亚军/4强')
    elif '欧国联' in text:
        score += 6
    if '欧青赛' in text and ('冠军' in text):
        n = text.count('欧青赛冠军')
        score += min(n, 3) * 10
        details.append(f'欧青赛冠军×{n}')
    elif '欧青赛' in text:
        score += 5
    if '世界杯冠军' in text:
        score += 50; details.append('世界杯冠军')
    elif '世界杯亚军' in text or '世界杯 亚军' in text:
        score += 30; details.append('世界杯亚军')
    elif '世界杯' in text and ('4强' in text or '8强' in text):
        score += 15; details.append('世界杯4强/8强')
    elif '世界杯' in text:
        score += 5
    if '非洲杯冠军' in text:
        score += 25; details.append('非洲杯冠军')
    elif '非洲杯' in text:
        score += 12
    if '美洲杯冠军' in text:
        score += 25; details.append('美洲杯冠军')
    elif '美洲杯' in text:
        score += 10
    if '亚洲杯冠军' in text:
        score += 18; details.append('亚洲杯冠军')
    elif '亚洲杯' in text:
        score += 8
    if '奥运会金' in text or '奥运金牌' in text:
        score += 15; details.append('奥运金牌')
    elif '奥运' in text and ('银' in text or '铜' in text):
        score += 5
    league_champs = text.count('联赛冠军') + text.count('西甲冠军') + text.count('英超冠军') + text.count('德甲冠军') + text.count('意甲冠军') + text.count('法甲冠军')
    score += min(league_champs, 10) * 2
    if league_champs > 0:
        details.append(f'{league_champs}次联赛冠军')
    return score, details

def main(custom_weights_path=None):
    weights = load_weights(custom_weights_path)
    pos_top_n = weights['position_top_n']
    pt = weights['player_to_total']
    sm = weights['smoothing']

    print(f"⚙️  加载权重: {custom_weights_path or WEIGHTS_PATH}")
    print(f"   Top N: FW={pos_top_n['FW']} MID={pos_top_n['MID']} DEF={pos_top_n['DEF']} GK={pos_top_n['GK']}")
    print(f"   总分: 球员{pt['player_share']} + 教练{pt['coach_share']}")
    print()

    players = []
    with open('/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv') as f:
        for p in csv.DictReader(f):
            players.append(p)

    status = load_status_data()

    coaches = {}
    with open('/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_coaches.csv') as f:
        for c in csv.DictReader(f):
            coaches[c['国家']] = c

    teams = defaultdict(lambda: {'fw': [], 'mid': [], 'def': [], 'gk': []})
    for p in players:
        c = p['国家']
        pos = p['位置']
        if pos in ('前锋', '前腰'):
            teams[c]['fw'].append(p)
        elif pos in ('中场', '后腰'):
            teams[c]['mid'].append(p)
        elif pos in ('后卫', '中后卫', '左后卫', '右后卫', '边后卫'):
            teams[c]['def'].append(p)
        elif pos in ('门将', '守门员'):
            teams[c]['gk'].append(p)

    fifa_rank = {}
    with open('/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_fifa_ranking.csv') as f:
        for r in csv.DictReader(f):
            try: fifa_rank[r['国家']] = int(r['FIFA排名'])
            except: pass

    results = []
    for country, slots in teams.items():
        scored_fw = [(calc_player_score(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['fw']]
        scored_mid = [(calc_player_score(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['mid']]
        scored_def = [(calc_player_score(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['def']]
        scored_gk = [(calc_player_score(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['gk']]

        scored_fw.sort(reverse=True, key=lambda x: x[0])
        scored_mid.sort(reverse=True, key=lambda x: x[0])
        scored_def.sort(reverse=True, key=lambda x: x[0])
        scored_gk.sort(reverse=True, key=lambda x: x[0])

        fw_top = scored_fw[:pos_top_n['FW']]
        mid_top = scored_mid[:pos_top_n['MID']]
        def_top = scored_def[:pos_top_n['DEF']]
        gk_top = scored_gk[:pos_top_n['GK']]

        def player_detail(p, pos_label):
            key = (country, p['球员'])
            st = status.get(key, {})
            return {
                'name': p['球员'],
                'pos': pos_label,
                'club': p.get('俱乐部', ''),
                'league': p.get('联赛', ''),
                'value': p.get('身价_万欧', '0'),
                'nat_goals': p.get('国家队进球', '0'),
                'nat_assists': p.get('国家队助攻', '0'),
                'apps_2025_26': st.get('appearances', ''),
                'goals_2025_26': st.get('goals', ''),
                'assists_2025_26': st.get('assists', ''),
                'whoscored': st.get('whoscored_rating', ''),
            }

        fw_details = [player_detail(p, 'FW') for _, p in fw_top]
        mid_details = [player_detail(p, 'MID') for _, p in mid_top]
        def_details = [player_detail(p, 'DEF') for _, p in def_top]
        gk_details = [player_detail(gk_top[0][1], 'GK')] if gk_top else []

        fw_score = sum(s for s, _ in fw_top)
        mid_score = sum(s for s, _ in mid_top)
        def_score = sum(s for s, _ in def_top)
        gk_score = sum(s for s, _ in gk_top)
        player_score = fw_score + mid_score + def_score + gk_score

        coach_score, coach_details = calc_coach_score(coaches.get(country, {}))

        total = player_score * pt['player_share'] + coach_score * pt['coach_share']

        player_r = player_score / (player_score + sm['player_div']) * 100
        coach_r = coach_score / (coach_score + sm['coach_div']) * 100
        rank_r = total / (total + sm['rank_div']) * 100

        results.append({
            'team': country,
            'fifa_rank': fifa_rank.get(country, '-'),
            'fw_score': fw_score,
            'mid_score': mid_score,
            'def_score': def_score,
            'gk_score': gk_score,
            'player_score': player_score,
            'player_r': round(player_r, 2),
            'coach_score': coach_score,
            'coach_r': round(coach_r, 2),
            'total': total,
            'rank_r': round(rank_r, 2),
            'fw_top_names': [p['球员'] for _, p in fw_top],
            'mid_top_names': [p['球员'] for _, p in mid_top],
            'def_top_names': [p['球员'] for _, p in def_top],
            'gk_top_name': gk_top[0][1]['球员'] if gk_top else '',
            'fw_top_full': [(p['球员'], p['身价_万欧'], p.get('联赛','')) for _, p in fw_top],
            'mid_top_full': [(p['球员'], p['身价_万欧'], p.get('联赛','')) for _, p in mid_top],
            'def_top_full': [(p['球员'], p['身价_万欧'], p.get('联赛','')) for _, p in def_top],
            'gk_top_full': (gk_top[0][1]['球员'], gk_top[0][1]['身价_万欧'], gk_top[0][1].get('联赛','')) if gk_top else None,
            'fw_details': fw_details,
            'mid_details': mid_details,
            'def_details': def_details,
            'gk_details': gk_details,
            'coach_name': coaches.get(country, {}).get('主教练', '?'),
            'coach_age': coaches.get(country, {}).get('国籍/年龄', ''),
            'coach_tenure': coaches.get(country, {}).get('任期', ''),
            'coach_career': coaches.get(country, {}).get('代表执教生涯', ''),
            'coach_honors': coaches.get(country, {}).get('重大荣誉', ''),
            'coach_details': coach_details,
        })

    results.sort(key=lambda x: x['rank_r'], reverse=True)
    for i, r in enumerate(results, 1):
        r['rank'] = i

    out_json = '/Users/garcia/Desktop/WorldCup2026/5_算法/ranking_v20.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    csv_fields = ['rank', 'team', 'fifa_rank', 'rank_r', 'player_r', 'coach_r',
                  'player_score', 'coach_score', 'total',
                  'fw_score', 'mid_score', 'def_score', 'gk_score',
                  'fw_top_names', 'mid_top_names', 'def_top_names', 'gk_top_name',
                  'coach_name', 'coach_details']
    with open('/Users/garcia/Desktop/WorldCup2026/3_排名v2.0/world_cup_2026_ranking_v2_0.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in results:
            r2 = {k: r.get(k, '') for k in csv_fields}
            for k in ['fw_top_names', 'mid_top_names', 'def_top_names']:
                if r2[k]: r2[k] = '; '.join(r2[k])
            w.writerow(r2)

    print(f'排名完成: {len(results)} 队')
    print(f'输出: {out_json}')
    print()
    print('=== Top 16 ===')
    for r in results[:16]:
        print(f"  {r['rank']:2d}. {r['team']:6s} | 评分={r['rank_r']:6.2f} | 球员={r['player_r']:6.2f}({r['player_score']:7.0f}) | 教练={r['coach_r']:6.2f}({r['coach_score']:4.0f})")
    print()
    print('=== 17-32 ===')
    for r in results[16:32]:
        print(f"  {r['rank']:2d}. {r['team']:6s} | 评分={r['rank_r']:6.2f} | 球员={r['player_r']:6.2f} | 教练={r['coach_r']:6.2f}")
    
    return results

if __name__ == '__main__':
    custom = sys.argv[1] if len(sys.argv) > 1 else None
    main(custom)
