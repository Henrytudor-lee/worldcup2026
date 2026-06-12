"""
Mavis PDP Predictor
- 直接读 1_数据基础/*.csv
- 接受 weights dict，注入到 ranking + predictions 计算
- 提供 3 个核心函数: compute_ranking / compute_predictions / get_players_by_team
"""
import csv, json, math, re
from collections import defaultdict
from pathlib import Path
import sys

# 让 backend/ 能 import 5_算法/ 下的 ranking_v2 工具
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".mavis/cache/scripts"))

import ranking_v2  # 复用 parse_num / parse_value / get_league_factor / calc_status_weight / parse_honors / calc_coach_score

# 数据路径
DATA_DIR = PROJECT_ROOT / "1_数据基础"
CSV_PLAYERS = DATA_DIR / "world_cup_2026_complete.csv"
CSV_COACHES = DATA_DIR / "world_cup_2026_coaches.csv"
CSV_FIFA = DATA_DIR / "world_cup_2026_fifa_ranking.csv"
CSV_SCHEDULE = DATA_DIR / "world_cup_2026_group_schedule.csv"
CSV_STATUS = DATA_DIR / "world_cup_2026_player_status_all.csv"


# ============================================================
# 联赛 -> 典型主场位置 (海拔米 + 6月历史均温°C)
# 用作"球员适应度"参考 (球员当前所在联赛 = 习惯环境)
# ============================================================
LEAGUE_LOCATION = {
    # 顶级联赛
    '英超':  {'alt': 50,   'temp': 20},
    '西甲':  {'alt': 660,  'temp': 28},
    '意甲':  {'alt': 50,   'temp': 28},
    '德甲':  {'alt': 500,  'temp': 22},
    '法甲':  {'alt': 35,   'temp': 22},
    '葡超':  {'alt': 100,  'temp': 25},
    '荷甲':  {'alt': -2,   'temp': 18},
    '土超':  {'alt': 100,  'temp': 28},
    '比甲':  {'alt': 50,   'temp': 20},
    '苏超':  {'alt': 50,   'temp': 15},
    '丹超':  {'alt': 30,   'temp': 18},
    '瑞超':  {'alt': 30,   'temp': 18},
    '挪超':  {'alt': 50,   'temp': 16},
    '奥超':  {'alt': 500,  'temp': 20},
    # 美国/墨西哥
    '美职联':{'alt': 50,   'temp': 32},
    'MLS':   {'alt': 50,   'temp': 32},
    '美乙':  {'alt': 50,   'temp': 32},
    '墨超':  {'alt': 2200, 'temp': 25},
    '墨超联':{'alt': 2200, 'temp': 25},
    # 南美
    '巴甲':  {'alt': 760,  'temp': 25},
    '阿超':  {'alt': 25,   'temp': 18},
    # 中东/亚洲
    '沙特联':{'alt': 600,  'temp': 42},
    '沙特超':{'alt': 600,  'temp': 42},
    '日联':  {'alt': 50,   'temp': 26},
    'K联':   {'alt': 50,   'temp': 26},
    '伊超':  {'alt': 1300, 'temp': 32},
    '卡超':  {'alt': 20,   'temp': 40},
    '阿联酋超':{'alt': 30,'temp': 40},
    '泰超':  {'alt': 5,    'temp': 33},
    # 非洲
    '埃超':  {'alt': 75,   'temp': 32},
    '南非超':{'alt': 1750, 'temp': 18},
    '北非超':{'alt': 100,  'temp': 30},
    '摩超':  {'alt': 500,  'temp': 26},
    '突超':  {'alt': 50,   'temp': 30},
    '尼日超':{'alt': 50,  'temp': 28},
    '民主刚果联赛':{'alt': 300, 'temp': 26},
    # 其他
    '俄超':  {'alt': 150,  'temp': 22},
    '乌超':  {'alt': 200,  'temp': 23},
    '克甲':  {'alt': 100,  'temp': 25},
    '捷甲':  {'alt': 250,  'temp': 22},
    '波超':  {'alt': 100,  'temp': 22},
    '希超':  {'alt': 100,  'temp': 28},
    '塞超':  {'alt': 100,  'temp': 24},
    '罗超':  {'alt': 100,  'temp': 25},
    '保甲':  {'alt': 550,  'temp': 24},
    '乌克超':{'alt': 200,  'temp': 23},
    '苏冠':  {'alt': 50,   'temp': 16},
    '英冠':  {'alt': 50,   'temp': 18},
    '意乙':  {'alt': 50,   'temp': 28},
    '西乙':  {'alt': 660,  'temp': 28},
    '法乙':  {'alt': 35,   'temp': 22},
    '德乙':  {'alt': 500,  'temp': 22},
    '英甲':  {'alt': 50,   'temp': 18},
    '葡甲':  {'alt': 100,  'temp': 25},
    '法甲乙级':{'alt': 35, 'temp': 22},
    'NBA':  {'alt': 0,     'temp': 25},  # 噪音
    '非洲联赛':{'alt': 200,'temp': 28},
    '南美低':{'alt': 300,  'temp': 25},
    '玻超':  {'alt': 2800, 'temp': 18},
    '南美其他':{'alt': 500,'temp': 23},
    '中北美其他':{'alt': 1000, 'temp': 24},
}


def get_league_location(league):
    """查 LEAGUE_LOCATION, 没找到返回中性 (500m, 22°C)"""
    if not league:
        return {'alt': 500, 'temp': 22}
    league = str(league).strip()
    if league in LEAGUE_LOCATION:
        return LEAGUE_LOCATION[league]
    # 模糊匹配
    for k, v in LEAGUE_LOCATION.items():
        if k in league or league in k:
            return v
    return {'alt': 500, 'temp': 22}


def calc_adaptation(league, venue_alt, venue_temp):
    """算球员对比赛场地的适应度 (0~1)
    1.0 = 完全适应, 0.0 = 严重不适应
    """
    loc = get_league_location(league)
    diff_alt = abs(venue_alt - loc['alt'])
    diff_temp = abs(venue_temp - loc['temp'])
    # tanh 平滑: 海拔每 1500m 衰减 ~50%, 温度每 10°C 衰减 ~50%
    alt_penalty = 0.5 * math.tanh(diff_alt / 1500)
    temp_penalty = 0.4 * math.tanh(diff_temp / 10)
    score = 1.0 - alt_penalty - temp_penalty
    return max(0.0, min(1.0, score))


# ============================================================
# 加载函数
# ============================================================
def load_players():
    """读 1248 球员主表"""
    players = []
    with open(CSV_PLAYERS, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            players.append(row)
    return players


def load_coaches():
    """读 48 教练表"""
    coaches = {}
    with open(CSV_COACHES, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            coaches[row['国家']] = row
    return coaches


def load_fifa():
    """读 FIFA 排名"""
    fifa = {}
    with open(CSV_FIFA, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            fifa[row['国家']] = row
    return fifa


def load_status():
    """读 2025-26 状态数据（可选，文件不存在返回空）"""
    status = {}
    try:
        with open(CSV_STATUS, encoding='utf-8') as f:
            for rec in csv.DictReader(f):
                key = (rec['country'], rec['name_zh'])
                if key in status:
                    for fk in ['appearances', 'goals', 'assists', 'whoscored_rating',
                               'def_tackles_p90', 'def_interceptions_p90', 'def_clearances_p90', 'def_aerial_pct',
                               'gk_save_pct', 'gk_clean_sheets', 'gk_goals_conceded_p90']:
                        if not status[key].get(fk) and rec.get(fk):
                            status[key][fk] = rec[fk]
                else:
                    status[key] = dict(rec)
    except FileNotFoundError:
        pass
    return status


def load_schedule():
    """读 72 场小组赛赛程"""
    schedule = []
    with open(CSV_SCHEDULE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            schedule.append(row)
    return schedule


# ============================================================
# weights 注入的 player_score
# ============================================================
def calc_player_score_with_weights(player, status_rec, weights):
    """
    球员评分（接受 weights）
    区分前锋/中场 vs 后卫/门
    """
    pos = player.get('位置', '').strip()
    val = ranking_v2.parse_value(player.get('身价_万欧', '0'))
    league = player.get('联赛', '')
    league_factor = ranking_v2.get_league_factor(league)
    base = val * league_factor

    sw_cfg = weights['status_weights']
    nat_cfg = weights['nat_intl']
    def_cfg = weights['def_gk_weights']

    if pos in ('前锋', '中场', '前腰', '后腰'):
        # 状态加权
        sw = ranking_v2.calc_status_weight(
            status_rec.get('goals', '0'),
            status_rec.get('assists', '0'),
            status_rec.get('whoscored_rating', '0')
        )
        # 国家队进球/助攻
        nat_goals = ranking_v2.parse_value(player.get('国家队进球', '0'))
        nat_assists = ranking_v2.parse_value(player.get('国家队助攻', '0'))
        sw += nat_goals / nat_cfg['g_per_goal'] + nat_assists / nat_cfg['a_per_assist']
        return base * (1 + sw), base, sw
    else:
        # 后卫/门：用经验 + 荣誉
        honors = ranking_v2.parse_honors(player.get('主要荣誉', ''))
        score = base * def_cfg['base_factor'] + honors * def_cfg['honors_per_champ']
        return score, base, 0


# ============================================================
# compute_ranking(weights) → 48 队排名
# ============================================================
def compute_ranking(weights):
    """算 48 队排名（含 4 维分 + 教练分 + 总分）"""
    players = load_players()
    coaches = load_coaches()
    status = load_status()
    fifa_rank = {}
    with open(CSV_FIFA, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                fifa_rank[r['国家']] = int(r['FIFA排名'])
            except (ValueError, KeyError):
                pass

    # 按队分组 + 4-3-3 分桶
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

    top_n = weights['position_top_n']
    sm = weights['smoothing']
    pt = weights['player_to_total']

    results = []
    for country, slots in teams.items():
        scored_fw = [(calc_player_score_with_weights(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['fw']]
        scored_mid = [(calc_player_score_with_weights(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['mid']]
        scored_def = [(calc_player_score_with_weights(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['def']]
        scored_gk = [(calc_player_score_with_weights(p, status.get((country, p['球员']), {}), weights)[0], p) for p in slots['gk']]

        scored_fw.sort(reverse=True, key=lambda x: x[0])
        scored_mid.sort(reverse=True, key=lambda x: x[0])
        scored_def.sort(reverse=True, key=lambda x: x[0])
        scored_gk.sort(reverse=True, key=lambda x: x[0])

        fw_top = scored_fw[:top_n['FW']]
        mid_top = scored_mid[:top_n['MID']]
        def_top = scored_def[:top_n['DEF']]
        gk_top = scored_gk[:top_n['GK']]

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

        coach_score, coach_details = ranking_v2.calc_coach_score(coaches.get(country, {}))

        # 用 weights 控制的 player_share / coach_share
        total = player_score * pt['player_share'] + coach_score * pt['coach_share']

        player_r = player_score / (player_score + sm['player_div']) * 100
        coach_r = coach_score / (coach_score + sm['coach_div']) * 100
        rank_r = total / (total + sm['rank_div']) * 100

        results.append({
            'team': country,
            'fifa_rank': fifa_rank.get(country, '-'),
            'fw_score': round(fw_score, 2),
            'mid_score': round(mid_score, 2),
            'def_score': round(def_score, 2),
            'gk_score': round(gk_score, 2),
            'player_score': round(player_score, 2),
            'player_r': round(player_r, 2),
            'coach_score': coach_score,
            'coach_r': round(coach_r, 2),
            'total': round(total, 2),
            'rank_r': round(rank_r, 2),
            'fw_top_names': [p['球员'] for _, p in fw_top],
            'mid_top_names': [p['球员'] for _, p in mid_top],
            'def_top_names': [p['球员'] for _, p in def_top],
            'gk_top_name': gk_top[0][1]['球员'] if gk_top else '',
            'fw_top_full': [(p['球员'], p['身价_万欧'], p.get('联赛','')) for _, p in fw_top],
            'mid_top_full': [(p['球员'], p['身价_万欧'], p.get('联赛','')) for _, p in mid_top],
            'def_top_full': [(p['球员'], p['身价_万欧'], p.get('联赛','')) for _, p in def_top],
            'gk_top_full': (gk_top[0][1]['球员'], gk_top[0][1]['身价_万欧'], gk_top[0][1].get('联赛','')) if gk_top else None,
            # 球员联赛列表 (predict_match 算适应度用)
            'fw_leagues': [p.get('联赛', '') for _, p in fw_top],
            'mid_leagues': [p.get('联赛', '') for _, p in mid_top],
            'def_leagues': [p.get('联赛', '') for _, p in def_top],
            'gk_league': gk_top[0][1].get('联赛', '') if gk_top else '',
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
    return results


# ============================================================
# λ 计算（predict_match 核心）
# ============================================================
def fifa_coef(rank):
    """FIFA 排名 → 系数"""
    if not rank or rank == '-':
        return 1.00
    try:
        rank = int(rank)
    except (ValueError, TypeError):
        return 1.00
    if rank <= 10: return 1.05
    if rank <= 20: return 1.03
    if rank <= 30: return 1.00
    if rank <= 50: return 0.97
    if rank <= 70: return 0.94
    return 0.90


def team_metrics(country, ranking_dict, fifa_data, is_home=True, venue_alt=0, venue_temp=25,
                 venue_cfg=None, team_leagues=None, adaptation_weight=0.5):
    """算单队 λ 计算所需系数

    venue_cfg: {altitude_threshold, altitude_penalty, temp_threshold, temp_penalty}
              None = 用默认值 (2000m / 0.90 / 32°C / 0.97)
    team_leagues: dict {'fw': [league, ...], 'mid': [...], 'def': [...], 'gk': 'league'}
                  来自 ranking_dict 里的 fw_leagues 等字段
    adaptation_weight: 0~1, 控制适应度调节强度 (0=关闭, 1=全生效)
    """
    if venue_cfg is None:
        venue_cfg = {'altitude_threshold': 2000, 'altitude_penalty': 0.90,
                     'temp_threshold': 32, 'temp_penalty': 0.97}

    r = ranking_dict.get(country, {})
    rank_r = r.get('rank_r', 80)
    coach_score = r.get('coach_score', 0)

    fw = r.get('fw_score', 0)
    mid = r.get('mid_score', 0)
    def_ = r.get('def_score', 0)
    gk_ = r.get('gk_score', 0)
    attack = fw + mid
    defense = def_ + gk_ * 0.5

    # 持球率（基于 rank_r）
    if rank_r >= 95: poss = 0.62
    elif rank_r >= 90: poss = 0.58
    elif rank_r >= 80: poss = 0.54
    elif rank_r >= 70: poss = 0.50
    else: poss = 0.46

    coach_coef = 1.0 + min(coach_score / 200, 0.20)
    fifa_c = fifa_coef(fifa_data.get(country, {}).get('FIFA排名', '50'))

    # === 适应度计算 ===
    adaptation = None
    if team_leagues:
        # 算该队所有位置球员对当前场地的适应度均值
        leagues_list = []
        leagues_list.extend(team_leagues.get('fw', []))
        leagues_list.extend(team_leagues.get('mid', []))
        leagues_list.extend(team_leagues.get('def', []))
        gk_lg = team_leagues.get('gk', '')
        if gk_lg:
            leagues_list.append(gk_lg)
        if leagues_list:
            scores = [calc_adaptation(lg, venue_alt, venue_temp) for lg in leagues_list]
            adaptation = sum(scores) / len(scores)

    # === venue 系数: 原阈值 + 适应度调节 ===
    venue_coef = 1.00
    if venue_alt >= venue_cfg['altitude_threshold'] and not is_home:
        # 高原客队: 用适应度调节惩罚幅度
        # adaptation=1.0 (很适应) → penalty 1.0 (无惩罚)
        # adaptation=0.0 (完全不适应) → 原 penalty 全额
        if adaptation is not None and adaptation_weight > 0:
            # 在 [1.0, penalty] 之间按 (1 - adapt_weight * (1 - adaptation)) 调节
            # adapt_weight=0 → 不用适应度 → penalty 不变
            # adapt_weight=1, adapt=1 → penalty=1.0
            # adapt_weight=1, adapt=0 → penalty=原值
            use_factor = 1.0 - adaptation_weight * (1.0 - adaptation)
            adjusted = venue_cfg['altitude_penalty'] ** use_factor
        else:
            adjusted = venue_cfg['altitude_penalty']
        venue_coef *= adjusted
    if venue_temp > venue_cfg['temp_threshold']:
        if adaptation is not None and adaptation_weight > 0:
            use_factor = 1.0 - adaptation_weight * (1.0 - adaptation)
            adjusted = venue_cfg['temp_penalty'] ** use_factor
        else:
            adjusted = venue_cfg['temp_penalty']
        venue_coef *= adjusted

    return {'attack': attack, 'defense': defense, 'possession': poss,
            'coach_coef': coach_coef, 'fifa_coef': fifa_c, 'venue_coef': venue_coef,
            'rank_r': rank_r,
            'venue_alt': venue_alt, 'venue_temp': venue_temp,
            'venue_cfg': venue_cfg,
            'adaptation': round(adaptation, 3) if adaptation is not None else None}


def calc_lambda(home, away, ranking_dict, fifa_data, venue_alt=0, venue_temp=25, venue_cfg=None,
                 home_leagues=None, away_leagues=None, adaptation_weight=0.5):
    """算主/客队 λ（4 维对位）"""
    H = team_metrics(home, ranking_dict, fifa_data, is_home=True,
                     venue_alt=venue_alt, venue_temp=venue_temp, venue_cfg=venue_cfg,
                     team_leagues=home_leagues, adaptation_weight=adaptation_weight)
    A = team_metrics(away, ranking_dict, fifa_data, is_home=False,
                     venue_alt=venue_alt, venue_temp=venue_temp, venue_cfg=venue_cfg,
                     team_leagues=away_leagues, adaptation_weight=adaptation_weight)

    home_attack = H['attack']
    home_lambda = 1.3 * H['possession'] * math.sqrt(home_attack * 0.001) * H['coach_coef'] * H['venue_coef'] * H['fifa_coef']
    home_lambda = min(max(home_lambda, 0.3), 4.0)

    away_poss = 1 - H['possession']
    away_lambda = 1.3 * away_poss * math.sqrt(A['attack'] * 0.001) * A['coach_coef'] * A['venue_coef'] * A['fifa_coef']
    away_lambda = min(max(away_lambda, 0.3), 4.0)

    return home_lambda, away_lambda


def poisson_pmf(lam, k):
    if lam <= 0: return 0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def predict_match(home, away, ranking_dict, fifa_data, venue_alt=0, venue_temp=25,
                  venue_humidity=60, weather_note='', venue_cfg=None,
                  home_leagues=None, away_leagues=None, adaptation_weight=0.5):
    """预测单场比赛"""
    H = team_metrics(home, ranking_dict, fifa_data, is_home=True,
                     venue_alt=venue_alt, venue_temp=venue_temp, venue_cfg=venue_cfg,
                     team_leagues=home_leagues, adaptation_weight=adaptation_weight)
    A = team_metrics(away, ranking_dict, fifa_data, is_home=False,
                     venue_alt=venue_alt, venue_temp=venue_temp, venue_cfg=venue_cfg,
                     team_leagues=away_leagues, adaptation_weight=adaptation_weight)
    lh, la = calc_lambda(home, away, ranking_dict, fifa_data, venue_alt, venue_temp, venue_cfg,
                          home_leagues=home_leagues, away_leagues=away_leagues,
                          adaptation_weight=adaptation_weight)

    score_probs = {}
    for k in range(7):
        for m in range(7):
            p = poisson_pmf(lh, k) * poisson_pmf(la, m)
            score_probs[(k, m)] = p

    p_win = sum(p for (k, m), p in score_probs.items() if k > m)
    p_draw = sum(p for (k, m), p in score_probs.items() if k == m)
    p_lose = sum(p for (k, m), p in score_probs.items() if k < m)
    total_p = p_win + p_draw + p_lose
    if total_p > 0:
        p_win /= total_p; p_draw /= total_p; p_lose /= total_p

    best_score = max(score_probs.items(), key=lambda x: x[1])
    expected_total = lh + la
    expected_diff = lh - la

    # 算法分解（给前端 modal 展示用）
    algorithm_breakdown = {
        'home': {
            'team': home,
            'fw_score': H.get('attack', 0) * 0.59,  # 锋+中合=attack; fw 占比约 0.59 (匹配 calc_lambda)
            'mid_score': H.get('attack', 0) * 0.41,
            'attack': round(H.get('attack', 0), 2),
            'possession': round(H.get('possession', 0), 3),
            'coach_coef': round(H.get('coach_coef', 1), 3),
            'fifa_coef': round(H.get('fifa_coef', 1), 3),
            'venue_coef': round(H.get('venue_coef', 1), 3),
            'adaptation': H.get('adaptation'),
        },
        'away': {
            'team': away,
            'fw_score': A.get('attack', 0) * 0.59,
            'mid_score': A.get('attack', 0) * 0.41,
            'attack': round(A.get('attack', 0), 2),
            'possession': round(A.get('possession', 0), 3),
            'coach_coef': round(A.get('coach_coef', 1), 3),
            'fifa_coef': round(A.get('fifa_coef', 1), 3),
            'venue_coef': round(A.get('venue_coef', 1), 3),
            'adaptation': A.get('adaptation'),
        },
        'formula': 'λ = 1.3 × 持球率 × √(attack × 0.001) × 教练 × 场地 × FIFA',
        'poisson': f'P(X=k) = (λ^k × e^-λ) / k!  |  P(主{k}, 客{m}) = P_home(k) × P_away(m)',
        'venue': {
            'alt': H.get('venue_alt', 0),
            'temp': H.get('venue_temp', 25),
            'humidity': venue_humidity,
            'alt_triggered': H.get('venue_alt', 0) >= (venue_cfg or {}).get('altitude_threshold', 2000),
            'temp_triggered': H.get('venue_temp', 25) > (venue_cfg or {}).get('temp_threshold', 32),
            'alt_threshold': (venue_cfg or {}).get('altitude_threshold', 2000),
            'alt_penalty': (venue_cfg or {}).get('altitude_penalty', 0.90),
            'temp_threshold': (venue_cfg or {}).get('temp_threshold', 32),
            'temp_penalty': (venue_cfg or {}).get('temp_penalty', 0.97),
        },
    }

    # 36 个比分完整概率（前端渲染分布表用）
    score_dist = {f'{k}-{m}': round(p, 4) for (k, m), p in score_probs.items()}

    return {
        'home': home, 'away': away,
        'lambda_home': round(lh, 3), 'lambda_away': round(la, 3),
        'p_home_win': round(p_win, 4),
        'p_draw': round(p_draw, 4),
        'p_away_win': round(p_lose, 4),
        'best_score': f'{best_score[0][0]}-{best_score[0][1]}',
        'best_score_prob': round(best_score[1], 4),
        'expected_total': round(expected_total, 2),
        'expected_diff': round(expected_diff, 2),
        'venue_alt': venue_alt,
        'venue_temp': venue_temp,
        'venue_humidity': venue_humidity,
        'weather_note': weather_note,
        'algorithm_breakdown': algorithm_breakdown,
        'score_distribution': score_dist,
    }


# ============================================================
# compute_predictions(weights) → 104 场全预测
# ============================================================
def compute_predictions(weights):
    """跑 72 场小组 + 32 场 KO = 104 场"""
    ranking = compute_ranking(weights)
    ranking_dict = {r['team']: r for r in ranking}
    fifa_data = load_fifa()
    schedule = load_schedule()
    venue_cfg = weights.get('venue_weights', {
        'altitude_threshold': 2000, 'altitude_penalty': 0.90,
        'temp_threshold': 32, 'temp_penalty': 0.97,
    })
    adaptation_weight = weights.get('venue_adaptation_weight', 0.5)

    # === 1. 跑 72 场小组赛 ===
    group_matches = defaultdict(list)
    all_predictions = []

    for m in schedule:
        g = m['组别']
        try:
            alt = int(m.get('海拔(米)', 0) or 0)
        except (ValueError, TypeError):
            alt = 0
        try:
            temp = int(m.get('6月历史均高温(°C)', 25) or 25)
        except (ValueError, TypeError):
            temp = 25
        try:
            hum = int(m.get('6月历史均湿度(%)', 60) or 60)
        except (ValueError, TypeError):
            hum = 60
        roof = m.get('顶棚', '无顶露天')
        weather = f"{m.get('城市','')} {m.get('体育场','')} | 海拔{alt}m 高温{temp}°C 湿度{hum}% 顶棚:{roof}"

        pred = predict_match(m['主队'], m['客队'], ranking_dict, fifa_data,
                             venue_alt=alt, venue_temp=temp, venue_humidity=hum,
                             weather_note=weather, venue_cfg=venue_cfg,
                             home_leagues={'fw': ranking_dict.get(m['主队'], {}).get('fw_leagues', []),
                                           'mid': ranking_dict.get(m['主队'], {}).get('mid_leagues', []),
                                           'def': ranking_dict.get(m['主队'], {}).get('def_leagues', []),
                                           'gk': ranking_dict.get(m['主队'], {}).get('gk_league', '')},
                             away_leagues={'fw': ranking_dict.get(m['客队'], {}).get('fw_leagues', []),
                                           'mid': ranking_dict.get(m['客队'], {}).get('mid_leagues', []),
                                           'def': ranking_dict.get(m['客队'], {}).get('def_leagues', []),
                                           'gk': ranking_dict.get(m['客队'], {}).get('gk_league', '')},
                             adaptation_weight=adaptation_weight)
        pred['match_id'] = f"GS_{g}_{m['轮次']}_{m['主队']}_vs_{m['客队']}"
        pred['round'] = f"小组{m['组别']}{m['轮次']}"  # m['轮次'] 已是 "第1轮", 不要再加
        pred['stage'] = 'group'
        pred['group'] = g
        pred['date'] = m.get('北京时间', '')
        pred['stadium'] = m.get('体育场', '')
        pred['city'] = m.get('城市', '')
        pred['roof'] = roof
        pred['venue_alt'] = alt
        pred['venue_temp'] = temp
        pred['venue_humidity'] = hum

        k, m_ = [int(x) for x in pred['best_score'].split('-')]
        group_matches[g].append((m['主队'], m['客队'], k, m_, pred))
        pred['actual_score'] = f'{k}-{m_}'
        pred['home_pts'] = 3 if k > m_ else (1 if k == m_ else 0)
        pred['away_pts'] = 3 if m_ > k else (1 if k == m_ else 0)
        all_predictions.append(pred)

    # === 2. 算小组排名 ===
    group_standings = {}
    for g, matches in group_matches.items():
        pts = defaultdict(lambda: [0, 0, 0, 0])  # pts, GF, GA, played
        for home, away, k, m_, _ in matches:
            pts[home][0] += 3 if k > m_ else (1 if k == m_ else 0)
            pts[home][1] += k; pts[home][2] += m_
            pts[away][0] += 3 if m_ > k else (1 if k == m_ else 0)
            pts[away][1] += m_; pts[away][2] += k
            pts[home][3] += 1; pts[away][3] += 1
        # 排序：积分 → 净胜球 → 进球 → 字母
        standings = sorted(pts.items(),
                          key=lambda x: (-x[1][0], -(x[1][1]-x[1][2]), -x[1][1], x[0]))
        group_standings[g] = [(t, s[0], s[1]-s[2], s[1], s[2]) for t, s in standings]

    # === 3. 8 个最好第3 ===
    third_placed = []
    for g in sorted(group_standings.keys()):
        if len(group_standings[g]) >= 3:
            third = group_standings[g][2]
            third_placed.append((g, third[0], third[1], third[2], third[3], third[4]))
    third_placed.sort(key=lambda x: -x[2])
    top_8_third = third_placed[:8]

    # === 4. 构建 32 强对阵 (按"上下半区"分组, R32 顺序严格对应 R16) ===
    # 简化规则 (够用版, 强调位置连贯性):
    # 上半 M1-M8: A1-H1 各 1 场, 配对 1 个 (第 2 名 或 最好第 3), 保证不重复
    # 下半 M9-M16: I1-L1 各 1 场 + 4 个第 2 名配对 + 剩余第 3 名
    qualified = []
    for g in sorted(group_standings.keys()):
        qualified.append((group_standings[g][0][0], g, 1))
        qualified.append((group_standings[g][1][0], g, 2))
    for g, t, p, gd, gf, ga in top_8_third:
        qualified.append((t, g, 3))

    by_gp = {}
    for t, g, p in qualified:
        by_gp.setdefault(g, {})[p] = t

    # 各组第 1 / 第 2 / 第 3
    firsts = {g: by_gp[g][1] for g in sorted(by_gp.keys())}
    seconds = {g: by_gp[g][2] for g in sorted(by_gp.keys())}
    # 8 个晋级第 3 (按积分降序)
    thirds_ranked = sorted(
        [(g, by_gp[g][3]) for g in sorted(by_gp.keys()) if 3 in by_gp[g]],
        key=lambda x: -group_standings[x[0]][2][1]  # 按积分排
    )

    used = set()  # 记录已用队伍
    def pick(g, pos):
        """取某组第 1/2/3 名, 同时标记已用"""
        t = firsts.get(g) if pos == 1 else seconds.get(g) if pos == 2 else by_gp[g].get(3)
        if t and t not in used:
            used.add(t)
            return t
        return None

    round_of_32 = []
    # === 上半 M1-M8: A1..H1 各 1 场, 配对 (第 2 名 + 第 3 名) 交替 ===
    # M1: A1 vs (B2 或 第3), M2: B1 vs (C2 或 第3), M3: C1 vs (D2), M4: D1 vs (A3rd)
    # 规则: 8 个第 1 各出现 1 次; 8 个第 2 全部配对 (A2-H2 4 场, 第 3 名 4 场)
    upper_firsts_order = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    # 8 个第 3 名积分前 4 进上半, 后 4 进下半
    upper_thirds = [t for g, t in thirds_ranked[:4]]
    lower_thirds = [t for g, t in thirds_ranked[4:]]

    for i, g in enumerate(upper_firsts_order):
        t1 = firsts[g]
        used.add(t1)
        # 配对: 偶数位置用第 2 名, 奇数位置用第 3 名 (避免连续同组)
        if i % 2 == 0:
            # 用下一组的第 2 (B2, D2, F2, H2 选一个还没用的)
            next_g = upper_firsts_order[(i + 1) % 8]
            t2 = pick(next_g, 2) or (upper_thirds.pop(0) if upper_thirds else None)
        else:
            # 用 1 个上半第 3
            t2 = upper_thirds.pop(0) if upper_thirds else None
        if t2:
            used.add(t2)
        round_of_32.append((t1, t2))

    # === 下半 M9-M16: I1-L1 各 1 场 + 各组第 2 + 剩余第 3 ===
    # used 已含上半 16 队, 不重置
    for t, _ in round_of_32:
        used.add(t)
    # 收集所有下半还没用的队伍
    lower_pool = []
    for g in ['I', 'J', 'K', 'L']:
        if firsts.get(g) and firsts[g] not in used:
            lower_pool.append((firsts[g], 1))
        if seconds.get(g) and seconds[g] not in used:
            lower_pool.append((seconds[g], 2))
    # 加下半第 3
    for t in lower_thirds:
        if t not in used:
            lower_pool.append((t, 3))
    # 上半没用完的第 2 名 (B2/D2/F2/H2 偶数位置已用, 奇数位置没用)
    for g in upper_firsts_order:
        if seconds.get(g) and seconds[g] not in used:
            lower_pool.append((seconds[g], 2))
    # 重新排序: I1, J1, K1, L1 先出场, 然后第 2 名
    lower_pool_sorted = []
    for g in ['I', 'J', 'K', 'L']:
        if firsts.get(g) and firsts[g] not in used:
            lower_pool_sorted.append((firsts[g], g, 1))
    for g in sorted(by_gp.keys()):
        if seconds.get(g) and seconds[g] not in used:
            lower_pool_sorted.append((seconds[g], g, 2))
    for t in lower_thirds:
        if t not in used:
            lower_pool_sorted.append((t, '?', 3))

    # 下半配对: I1 vs J2, K1 vs L2, L1 vs (剩余第 2), (剩余第 2) vs (剩余第 3), ...
    # 简化: 头 4 个 vs 4 个, 后 4 个 vs 4 个, 尽量避免同组
    for i in range(8):
        t1 = lower_pool_sorted[i*2][0] if i*2 < len(lower_pool_sorted) else None
        t2 = lower_pool_sorted[i*2+1][0] if i*2+1 < len(lower_pool_sorted) else None
        if t1 and t2:
            round_of_32.append((t1, t2))

    # === 5. 跑淘汰赛 ===
    # FIFA 2026 淘汰赛日期 (基于官方公布时间表)
    KO_DATES = {
        'R32': ['2026-06-30', '2026-07-01', '2026-07-02', '2026-07-03'],  # 4 天 16 场, 每天 4 场
        'R16': ['2026-07-06', '2026-07-07'],  # 2 天 8 场, 每天 4 场
        'QF':  ['2026-07-10', '2026-07-11'],  # 2 天 4 场, 每天 2 场
        'SF':  ['2026-07-14', '2026-07-15'],  # 2 天 2 场, 每天 1 场
        '3RD': ['2026-07-18'],                # 季军赛
        'FINAL': ['2026-07-19'],              # 决赛
    }

    def make_ko_pred(home, away, stage, round_name, prefix, date):
        pred = predict_match(home, away, ranking_dict, fifa_data, venue_cfg=venue_cfg,
                             home_leagues={'fw': ranking_dict.get(home, {}).get('fw_leagues', []),
                                           'mid': ranking_dict.get(home, {}).get('mid_leagues', []),
                                           'def': ranking_dict.get(home, {}).get('def_leagues', []),
                                           'gk': ranking_dict.get(home, {}).get('gk_league', '')},
                             away_leagues={'fw': ranking_dict.get(away, {}).get('fw_leagues', []),
                                           'mid': ranking_dict.get(away, {}).get('mid_leagues', []),
                                           'def': ranking_dict.get(away, {}).get('def_leagues', []),
                                           'gk': ranking_dict.get(away, {}).get('gk_league', '')},
                             adaptation_weight=adaptation_weight)
        pred['match_id'] = f"{prefix}_{home}_vs_{away}"
        pred['round'] = round_name
        pred['stage'] = stage
        pred['date'] = date
        k, m_ = [int(x) for x in pred['best_score'].split('-')]
        pred['actual_score'] = f'{k}-{m_}'
        pred['home_pts'] = 3 if k > m_ else (1 if k == m_ else 0)
        pred['away_pts'] = 3 if m_ > k else (1 if k == m_ else 0)
        pred['winner'] = home if k > m_ else (away if m_ > k else home)
        pred['loser'] = away if k > m_ else (home if m_ > k else away)
        pred['went_to_pen'] = k == m_
        all_predictions.append(pred)
        return pred

    for i, (h, a) in enumerate(round_of_32):
        # R32 每天 4 场, M1-M4=第1天, M5-M8=第2天, M9-M12=第3天, M13-M16=第4天
        date = KO_DATES['R32'][i // 4]
        make_ko_pred(h, a, 'R32', '32强', 'R32', date)
    r32_winners = [p['winner'] for p in all_predictions[-16:]]

    r16_pairs = [(r32_winners[i], r32_winners[i+1]) for i in range(0, 16, 2)]
    for i, (h, a) in enumerate(r16_pairs):
        # R16 每天 4 场
        date = KO_DATES['R16'][i // 4]
        make_ko_pred(h, a, 'R16', '16强', 'R16', date)
    r16_winners = [p['winner'] for p in all_predictions[-8:]]

    qf_pairs = [(r16_winners[i], r16_winners[i+1]) for i in range(0, 8, 2)]
    for i, (h, a) in enumerate(qf_pairs):
        # QF 每天 2 场
        date = KO_DATES['QF'][i // 2]
        make_ko_pred(h, a, 'QF', '8强', 'QF', date)
    qf_winners = [p['winner'] for p in all_predictions[-4:]]

    sf_pairs = [(qf_winners[i], qf_winners[i+1]) for i in range(0, 4, 2)]
    for i, (h, a) in enumerate(sf_pairs):
        # SF 每天 1 场
        date = KO_DATES['SF'][i // 1]
        make_ko_pred(h, a, 'SF', '半决赛', 'SF', date)
    sf_winners = [p['winner'] for p in all_predictions[-2:]]
    sf_losers = [p['loser'] for p in all_predictions[-2:]]

    final_pred = make_ko_pred(sf_winners[0], sf_winners[1], 'FINAL', '决赛', 'FINAL', KO_DATES['FINAL'][0])
    third_pred = make_ko_pred(sf_losers[0], sf_losers[1], '3RD', '3-4名决赛', '3RD', KO_DATES['3RD'][0])

    return {
        'predictions': all_predictions,
        'ranking': ranking,
        'group_standings': {g: [[t, p, gd, gf, ga] for t, p, gd, gf, ga in st] for g, st in group_standings.items()},
        'top_8_third': [[g, t, p, gd, gf, ga] for g, t, p, gd, gf, ga in top_8_third],
        'round_of_32': [[h, a] for h, a in round_of_32],
        'final': {'home': final_pred['home'], 'away': final_pred['away'],
                  'winner': final_pred['winner'], 'best_score': final_pred['best_score']},
        'third_place': {'home': third_pred['home'], 'away': third_pred['away'],
                        'winner': third_pred['winner'], 'best_score': third_pred['best_score']},
    }


# ============================================================
# get_players_by_team(team)
# ============================================================
def get_players_by_team(team=None):
    """读 1248 球员，可选按队过滤"""
    players = load_players()
    if team:
        players = [p for p in players if p['国家'] == team]
    return players


# ============================================================
# 调试入口
# ============================================================
if __name__ == '__main__':
    from weights_schema import DEFAULT, validate
    print('测试: 默认权重计算 ranking + predictions')
    ok, msg = validate(DEFAULT)
    print(f'  weights validate: {ok} ({msg})')
    if ok:
        t0 = __import__('time').time()
        r = compute_ranking(DEFAULT)
        t1 = __import__('time').time()
        print(f'  ranking {len(r)} 队 耗时 {t1-t0:.2f}s')
        print(f'  Top 3: {[x["team"] for x in r[:3]]}')

        t2 = __import__('time').time()
        p = compute_predictions(DEFAULT)
        t3 = __import__('time').time()
        print(f'  predictions 耗时 {t3-t2:.2f}s')
        print(f'  决赛: {p["final"]["home"]} vs {p["final"]["away"]} → 冠军 {p["final"]["winner"]}')
        print(f'  季军: {p["third_place"]["home"]} vs {p["third_place"]["away"]} → {p["third_place"]["winner"]}')
