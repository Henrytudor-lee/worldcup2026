"""
Round 2 Group Stage Predictor v1.0
===================================
- Red card suspension detection
- Round 1 form scoring (result 30% + team stats 40% + player stats 30%)
- 50/50 Mavis PDP fusion
- Coaching aggression model (points situation × opponent strength)
- Tactical style extraction + matchup matrix
- Full 24-match round 2 Poisson prediction

Does NOT modify existing predictor.py / weights_schema.py / dynamic_factors.py.
"""

import csv, json, math, sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".mavis/cache/scripts"))

import predictor  # Mavis PDP core (compute_ranking, predict_match, etc.)
from weights_schema import DEFAULT, merge_with_default, validate

DATA_DIR = PROJECT_ROOT / "1_数据基础"

# ============================================================
# 1. DATA LOADING
# ============================================================

def _load_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_round1_results():
    """match_results.csv → {('home','away'): {date, home_score, away_score, ...}}"""
    results = {}
    for r in _load_csv("match_results.csv"):
        key = (r['home'], r['away'])
        results[key] = {
            'date': r['date'],
            'home_score': int(r['home_score']),
            'away_score': int(r['away_score']),
        }
    return results


def load_round1_team_stats():
    """match_team_stats.csv indexed by (home, away)"""
    stats = {}
    for r in _load_csv("match_team_stats.csv"):
        key = (r['home_team_cn'], r['away_team_cn'])
        stats[key] = r
    return stats


def load_round1_player_stats():
    """match_player_stats.csv → {(match_id, team, player_en): {...}}"""
    stats = {}
    for r in _load_csv("match_player_stats.csv"):
        key = (r['match_id'], r['team_cn'], r['player_en'])
        stats[key] = r
    return stats


def load_round1_events():
    """match_events.csv as list"""
    return _load_csv("match_events.csv")


def load_round2_schedule():
    """world_cup_2026_group_schedule.csv filtered to 第2轮"""
    all_matches = _load_csv("world_cup_2026_group_schedule.csv")
    return [m for m in all_matches if m.get('轮次') == '第2轮']


def load_player_master():
    """world_cup_2026_complete.csv indexed by (country, name)"""
    players = {}
    for p in _load_csv("world_cup_2026_complete.csv"):
        key = (p['国家'], p['球员'])
        players[key] = p
    return players


# ============================================================
# 2. RED CARD / SUSPENSION SYSTEM
# ============================================================

def detect_suspensions():
    """
    Parse match_events for red cards → suspended for round 2.
    Returns {team_cn: [{'player_en': ..., 'jersey': ..., 'date': ..., 'impact': 'high'|'medium'|'low'}]}
    """
    events = load_round1_events()
    player_stats = load_round1_player_stats()
    player_master = load_player_master()

    red_cards = []
    for e in events:
        et = e.get('event_type', '')
        if 'Red' in et:
            red_cards.append(e)

    suspensions = defaultdict(list)
    for rc in red_cards:
        team = rc['team_cn']
        player_en = rc['player_en']
        date = rc['date']

        # Find player position from master table
        pos = '?'
        for (country, name), pm in player_master.items():
            if country == team and (player_en.lower() in name.lower() or name.lower() in player_en.lower()):
                pos = pm.get('位置', '?')
                break

        # Determine impact based on position and starter status
        impact = 'medium'
        if pos in ('后卫', '中后卫', '左后卫', '右后卫', '边后卫'):
            impact = 'high'  # defenders are harder to replace
        elif pos in ('门将', '守门员'):
            impact = 'high'
        elif pos in ('前锋', '前腰'):
            impact = 'high'

        # Check if player was a starter
        was_starter = False
        for (mid, t, pname), ps in player_stats.items():
            if t == team and player_en.lower() in pname.lower():
                if ps.get('starter') == 'True':
                    was_starter = True
                break

        if not was_starter:
            impact = 'low'

        suspensions[team].append({
            'player_en': player_en,
            'date': date,
            'position': pos,
            'starter': was_starter,
            'impact': impact,
        })

    return dict(suspensions)


def apply_suspension_penalty(team, position_counts, suspensions):
    """
    Reduce positional depth counts based on suspended players.
    position_counts: {'FW': n, 'MID': n, 'DEF': n, 'GK': n}
    Returns adjusted counts + penalty_details.
    """
    if team not in suspensions:
        return position_counts, []

    suspended = suspensions[team]
    adjusted = dict(position_counts)
    details = []

    for sp in suspended:
        pos = sp['position']
        detail = f"{sp['player_en']}({pos})"

        if pos in ('后卫', '中后卫', '左后卫', '右后卫', '边后卫'):
            adjusted['DEF'] = max(0, adjusted.get('DEF', 0) - 1)
            detail += f" → DEF-1"
        elif pos in ('前锋', '前腰'):
            adjusted['FW'] = max(0, adjusted.get('FW', 0) - 1)
            detail += f" → FW-1"
        elif pos in ('中场', '后腰'):
            adjusted['MID'] = max(0, adjusted.get('MID', 0) - 1)
            detail += f" → MID-1"
        elif pos in ('门将', '守门员'):
            adjusted['GK'] = max(0, adjusted.get('GK', 0) - 1)
            detail += f" → GK-1"

        details.append(detail)

    # Depth penalty: each suspension reduces total by ~3%
    total_original = sum(position_counts.values())
    total_new = sum(adjusted.values())
    if total_original > 0:
        depth_penalty = (total_original - total_new) / total_original * 0.15
    else:
        depth_penalty = 0

    return adjusted, details, depth_penalty


# ============================================================
# 3. ROUND 1 FORM SCORING
# ============================================================

def safe_float(val, default=0.0):
    """Safely convert string to float"""
    if val is None or str(val).strip() in ('', '-', 'X待核实', 'nan', 'None'):
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def compute_team_form_scores():
    """
    Compute round 1 form score [0,100] for each team from 3 data layers:
    30% result + 40% team stats + 30% player performance.
    """
    results = load_round1_results()
    team_stats = load_round1_team_stats()
    player_stats = load_round1_player_stats()

    raw_scores = {}

    # --- Layer 1: Result score (0-100) ---
    result_scores = {}
    for (home, away), r in results.items():
        hs, aws = r['home_score'], r['away_score']

        # Home team result
        if hs > aws:
            result_scores[home] = 80 + min(hs - aws, 5) * 4  # win: 80-100
        elif hs == aws:
            result_scores[home] = 50  # draw: 50
        else:
            result_scores[home] = max(10, 30 - min(aws - hs, 5) * 4)  # loss: 10-30

        # Away team result
        if aws > hs:
            result_scores[away] = 80 + min(aws - hs, 5) * 4
        elif aws == hs:
            result_scores[away] = 50
        else:
            result_scores[away] = max(10, 30 - min(hs - aws, 5) * 4)

    # --- Layer 2: Team performance score (0-100) ---
    team_perf_scores = {}
    team_raw_stats = defaultdict(list)  # collect stats per team

    for (home, away), ts in team_stats.items():
        for side, team in [('home', home), ('away', away)]:
            prefix = f"{side}_"
            stats = {
                'possession': safe_float(ts.get(f'{prefix}possession_pct', 0)),
                'total_shots': safe_float(ts.get(f'{prefix}total_shots', 0)),
                'shots_on_target': safe_float(ts.get(f'{prefix}shots_on_target', 0)),
                'shot_pct': safe_float(ts.get(f'{prefix}shot_pct', 0)),
                'pass_pct': safe_float(ts.get(f'{prefix}pass_pct', 0)),
                'corners': safe_float(ts.get(f'{prefix}corners', 0)),
                'fouls': safe_float(ts.get(f'{prefix}fouls', 0)),
                'tackles_effective': safe_float(ts.get(f'{prefix}tackles_effective', 0)),
                'interceptions': safe_float(ts.get(f'{prefix}interceptions', 0)),
                'clearances': safe_float(ts.get(f'{prefix}clearances', 0)),
                'saves': safe_float(ts.get(f'{prefix}saves', 0)),
                'goals_scored': safe_float(ts.get(f'{prefix}goals', 0)) if f'{prefix}goals' in ts else (
                    safe_float(ts.get('home_score', 0)) if side == 'home' else safe_float(ts.get('away_score', 0))
                ),
                'goals_conceded': safe_float(ts.get(f'{prefix}goals_conceded', 0)),
            }
            team_raw_stats[team].append(stats)

    # Z-score normalize across all 48 teams
    all_metrics = defaultdict(list)
    for team, stats_list in team_raw_stats.items():
        s = stats_list[0]  # only 1 match per team
        # Composite team perf score
        attack_metric = (
            s['total_shots'] * 1.5 +
            s['shots_on_target'] * 3.0 +
            s['goals_scored'] * 5.0 +
            s['shot_pct'] * 0.5 +
            s['corners'] * 0.3
        )
        defense_metric = (
            s['tackles_effective'] * 1.5 +
            s['interceptions'] * 1.5 +
            s['clearances'] * 0.5 +
            s['saves'] * 2.0 -
            s['goals_conceded'] * 4.0
        )
        control_metric = (
            s['possession'] * 0.5 +
            s['pass_pct'] * 0.3 -
            s['fouls'] * 0.3
        )
        raw = attack_metric + defense_metric + control_metric
        all_metrics[team] = raw

    # Normalize to 0-100
    if all_metrics:
        min_v, max_v = min(all_metrics.values()), max(all_metrics.values())
        span = max(max_v - min_v, 1)
        team_perf_scores = {t: (v - min_v) / span * 100 for t, v in all_metrics.items()}

    # --- Layer 3: Player performance score (0-100) ---
    player_perf_scores = {}
    team_player_data = defaultdict(list)

    for (mid, team, pname), ps in player_stats.items():
        is_starter = ps.get('starter') == 'True'
        data = {
            'goals': safe_float(ps.get('goals', 0)),
            'assists': safe_float(ps.get('assists', 0)),
            'shots_on_target': safe_float(ps.get('shots_on_target', 0)),
            'saves': safe_float(ps.get('saves', 0)),
            'is_starter': is_starter,
            'minutes': safe_float(ps.get('minutes', 0)),
        }
        team_player_data[team].append(data)

    for team, players in team_player_data.items():
        total = 0
        for p in players:
            score = (
                p['goals'] * 8.0 +
                p['assists'] * 5.0 +
                p['shots_on_target'] * 1.5 +
                p['saves'] * 3.0 +
                (3.0 if p['is_starter'] else 0.5)
            )
            total += score
        player_perf_scores[team] = total

    # Normalize
    if player_perf_scores:
        min_v, max_v = min(player_perf_scores.values()), max(player_perf_scores.values())
        span = max(max_v - min_v, 1)
        player_perf_scores = {t: (v - min_v) / span * 100 for t, v in player_perf_scores.items()}

    # --- Combine: 30% result + 40% team + 30% player ---
    all_teams = set(list(result_scores.keys()) + list(team_perf_scores.keys()) + list(player_perf_scores.keys()))
    form_scores = {}
    form_breakdown = {}

    for team in all_teams:
        rs = result_scores.get(team, 50)
        ts_val = team_perf_scores.get(team, 50)
        ps = player_perf_scores.get(team, 50)
        combined = rs * 0.30 + ts_val * 0.40 + ps * 0.30
        form_scores[team] = round(combined, 2)
        form_breakdown[team] = {
            'result': round(rs, 1),
            'team_perf': round(ts_val, 1),
            'player_perf': round(ps, 1),
            'combined': round(combined, 2),
        }

    return form_scores, form_breakdown


# ============================================================
# 4. TACTICAL STYLE EXTRACTION
# ============================================================

def extract_tactical_styles():
    """
    From round 1 team_stats, classify each team into tactical dimensions.
    Returns {team: {attack_style, defense_style, press, efficiency, solidity}}
    """
    team_stats = load_round1_team_stats()
    team_data = defaultdict(list)

    for (home, away), ts in team_stats.items():
        for side, team in [('home', home), ('away', away)]:
            pfx = f"{side}_"
            team_data[team].append({
                'possession': safe_float(ts.get(f'{pfx}possession_pct', 50)),
                'total_shots': safe_float(ts.get(f'{pfx}total_shots', 10)),
                'shots_on_target': safe_float(ts.get(f'{pfx}shots_on_target', 4)),
                'pass_pct': safe_float(ts.get(f'{pfx}pass_pct', 0.80)),
                'passes_total': safe_float(ts.get(f'{pfx}passes_total', 400)),
                'tackles_total': safe_float(ts.get(f'{pfx}tackles_total', 10)),
                'tackles_effective': safe_float(ts.get(f'{pfx}tackles_effective', 5)),
                'clearances': safe_float(ts.get(f'{pfx}clearances', 15)),
                'interceptions': safe_float(ts.get(f'{pfx}interceptions', 8)),
                'saves': safe_float(ts.get(f'{pfx}saves', 3)),
                'shots_faced': safe_float(ts.get(f'{pfx}shots_faced', 10)),
                'goals_scored': (safe_float(ts.get('home_score', 0)) if side == 'home'
                                 else safe_float(ts.get('away_score', 0))),
                'goals_conceded': (safe_float(ts.get('away_score', 0)) if side == 'home'
                                   else safe_float(ts.get('home_score', 0))),
                'corners': safe_float(ts.get(f'{pfx}corners', 4)),
            })

    styles = {}
    for team, matches in team_data.items():
        m = matches[0]  # single match

        # Attack style: possession-based vs direct
        if m['possession'] >= 55:
            attack_style = 'possession'
        elif m['possession'] >= 40:
            attack_style = 'balanced'
        else:
            attack_style = 'direct_counter'

        # Press intensity: tackles per opposition pass
        opp_passes = m['passes_total'] * 0.8  # rough estimate of opponent passes
        press_ratio = m['tackles_total'] / max(opp_passes, 1)
        if press_ratio > 0.18:
            press = 'high_press'
        elif press_ratio > 0.10:
            press = 'mid_block'
        else:
            press = 'low_block'

        # Defensive block depth
        if m['clearances'] > 30:
            defense_block = 'deep_block'
        elif m['clearances'] > 15:
            defense_block = 'mid_block'
        else:
            defense_block = 'high_line'

        # Attack efficiency: goals per shot_on_target
        if m['shots_on_target'] > 0:
            efficiency = m['goals_scored'] / m['shots_on_target']
        else:
            efficiency = 0

        # Defensive solidity: saves per shots_faced
        if m['shots_faced'] > 0:
            solidity = m['saves'] / m['shots_faced']
        else:
            solidity = 1.0

        attack_efficiency = 'high' if efficiency > 0.30 else ('medium' if efficiency > 0.15 else 'low')
        defensive_solidity = 'high' if solidity > 0.5 else ('medium' if solidity > 0.25 else 'low')

        styles[team] = {
            'attack_style': attack_style,
            'press': press,
            'defense_block': defense_block,
            'attack_efficiency': attack_efficiency,
            'defensive_solidity': defensive_solidity,
            'stats': {
                'possession': m['possession'],
                'shots': m['total_shots'],
                'shots_on_target': m['shots_on_target'],
                'clearances': m['clearances'],
                'tackles': m['tackles_total'],
                'goals_scored': m['goals_scored'],
                'goals_conceded': m['goals_conceded'],
            }
        }

    return styles


# ============================================================
# 5. TACTICAL MATCHUP MATRIX
# ============================================================

# matchup_adj[attack_style][defense_block] = (attack_eff_adj, counter_risk)
MATCHUP_MATRIX = {
    ('possession', 'deep_block'):     {'attack_adj': 0.78, 'counter_risk': 1.12, 'note': '控球渗透难破密集防守'},
    ('possession', 'mid_block'):      {'attack_adj': 0.92, 'counter_risk': 1.05, 'note': '控球渗透中等克制'},
    ('possession', 'high_line'):      {'attack_adj': 1.12, 'counter_risk': 0.95, 'note': '控球渗透克制高位防线'},
    ('balanced', 'deep_block'):       {'attack_adj': 0.88, 'counter_risk': 1.08, 'note': '均衡对深防守略降'},
    ('balanced', 'mid_block'):        {'attack_adj': 1.00, 'counter_risk': 1.00, 'note': '均衡对中位防守正常'},
    ('balanced', 'high_line'):        {'attack_adj': 1.08, 'counter_risk': 1.02, 'note': '均衡对高位微优'},
    ('direct_counter', 'deep_block'): {'attack_adj': 0.90, 'counter_risk': 1.05, 'note': '反击对深防守空间有限'},
    ('direct_counter', 'mid_block'):  {'attack_adj': 1.05, 'counter_risk': 1.10, 'note': '反击对中位有空间'},
    ('direct_counter', 'high_line'):  {'attack_adj': 1.18, 'counter_risk': 1.15, 'note': '反击克制高位防线'},
}


def get_matchup_adjustment(home_style, away_style):
    """Get attack adjustment and counter risk for home team vs away defense"""
    key = (home_style.get('attack_style', 'balanced'),
           away_style.get('defense_block', 'mid_block'))
    matchup = MATCHUP_MATRIX.get(key, {'attack_adj': 1.00, 'counter_risk': 1.00, 'note': '默认无特殊克制'})
    return matchup


# ============================================================
# 6. COACHING AGGRESSION MODEL
# ============================================================

def compute_group_standings_from_results():
    """Compute actual group standings from round 1 results."""
    results = load_round1_results()
    schedule = _load_csv("world_cup_2026_group_schedule.csv")

    # Map (home, away) to group
    match_to_group = {}
    for s in schedule:
        match_to_group[(s['主队'], s['客队'])] = s['组别']

    pts = defaultdict(lambda: [0, 0, 0, 0])  # pts, GF, GA, played
    group_teams = defaultdict(set)

    for (home, away), r in results.items():
        hs, aws = r['home_score'], r['away_score']
        g = match_to_group.get((home, away), match_to_group.get((away, home), '?'))

        group_teams[g].add(home)
        group_teams[g].add(away)

        # Home
        pts[(g, home)][0] += 3 if hs > aws else (1 if hs == aws else 0)
        pts[(g, home)][1] += hs
        pts[(g, home)][2] += aws
        pts[(g, home)][3] += 1

        # Away
        pts[(g, away)][0] += 3 if aws > hs else (1 if hs == aws else 0)
        pts[(g, away)][1] += aws
        pts[(g, away)][2] += hs
        pts[(g, away)][3] += 1

    standings = {}
    for g in sorted(group_teams.keys()):
        st = [(t, pts[(g, t)][0], pts[(g, t)][1], pts[(g, t)][2], pts[(g, t)][3])
              for t in group_teams[g]]
        st.sort(key=lambda x: (-x[1], -(x[2]-x[3]), -x[2], x[0]))
        standings[g] = st

    return standings


def find_team_group(team):
    """Find which group a team belongs to."""
    schedule = _load_csv("world_cup_2026_group_schedule.csv")
    for s in schedule:
        if s['主队'] == team or s['客队'] == team:
            return s['组别']
    return '?'


def compute_aggression(team, team_strength, opponent_strength, standings, group):
    """
    Compute coach aggression level [0,1].
    0 = ultra-defensive, 0.5 = balanced, 1 = ultra-attacking.

    Factors:
    - Points situation (need to win?)
    - Opponent strength ratio
    - Can advance with draw?
    - Team's natural style from round 1
    """
    # Find team's current points
    team_pts = 0
    team_gd = 0
    team_rank_in_group = 4
    if group in standings:
        for i, (t, p, gd, gf, ga) in enumerate(standings[group]):
            if t == team:
                team_pts = p
                team_gd = gd
                team_rank_in_group = i + 1
                break

    # Base aggression
    aggression = 0.50

    # Points situation
    if team_pts == 0:
        aggression += 0.18  # must win
    elif team_pts == 1:
        aggression += 0.06  # need result
    else:  # 3 pts
        aggression -= 0.08  # can play conservatively

    # Opponent strength ratio: opponent_strength / team_strength
    if team_strength > 0:
        strength_ratio = opponent_strength / team_strength
    else:
        strength_ratio = 1.0

    if strength_ratio > 1.3:
        aggression -= 0.12  # opponent much stronger → defensive
    elif strength_ratio > 1.1:
        aggression -= 0.06
    elif strength_ratio < 0.8:
        aggression += 0.08  # opponent weaker → attack more
    elif strength_ratio < 0.9:
        aggression += 0.04

    # Can advance with a draw?
    # Simple heuristic: if team is top 2 and GD is good
    if group in standings:
        st = standings[group]
        if team_rank_in_group == 1 and team_pts >= 1:
            aggression -= 0.05
        if team_rank_in_group == 2 and team_pts >= 1:
            # Check gap to 3rd place
            if len(st) >= 3 and st[2][1] <= team_pts - 1:
                aggression -= 0.03

    # Clamp
    aggression = max(0.10, min(0.90, aggression))

    return round(aggression, 3)


# ============================================================
# 6.5 LINEUP-BASED PLAYER WEIGHTING
# ============================================================

def compute_lineup_strengths(ranking_dict):
    """
    Compute team strength based on Round 1 actual lineups.
    Starters get full weight, subs get partial, non-players get minimal.
    This replaces the simple 4-3-3 top-N value approach with actual coach selections.
    """
    stats = load_round1_player_stats()
    player_master = load_player_master()

    # Build jersey→ranking score map for each team
    team_jersey_scores = {}
    for team, r in ranking_dict.items():
        scores = {}
        # Collect all player scores from ranking: (name, fw/mid/def/gk score)
        for pos_key in ['fw_details', 'mid_details', 'def_details', 'gk_details']:
            for p in r.get(pos_key, []):
                if isinstance(p, dict):
                    pname = p.get('name', '')
                    # Find jersey from master
                    for (c, cn), pm in player_master.items():
                        if c == team and cn == pname:
                            j = pm.get('号码', '').strip()
                            if j:
                                scores[j] = {
                                    'name': pname,
                                    'score': float(p.get('value', 0) or 0),
                                    'pos': p.get('pos', '')
                                }
                            break
        team_jersey_scores[team] = scores

    lineup_strengths = {}
    for team in ranking_dict:
        starters = []
        subs = []
        bench = []

        # Collect R1 playing data
        for (mid, t, pname), ps in stats.items():
            if t != team:
                continue
            jersey = ps.get('jersey', '').strip()
            player_score_data = team_jersey_scores.get(team, {}).get(jersey, {})
            base_score = player_score_data.get('score', 0)

            is_starter = ps.get('starter') == 'True'
            was_subbed = ps.get('subbed_in') == 'True'
            minutes = safe_float(ps.get('minutes', 0) or 0)

            if is_starter:
                starters.append({'jersey': jersey, 'score': base_score, 'minutes': minutes})
            elif was_subbed:
                subs.append({'jersey': jersey, 'score': base_score, 'minutes': minutes})
            else:
                bench.append({'jersey': jersey, 'score': base_score, 'minutes': 0})

        # Compute lineup strength
        avg_starter = sum(s['score'] for s in starters) / max(len(starters), 1)
        avg_sub = sum(s['score'] for s in subs) / max(len(subs), 1) if subs else 0
        avg_bench = sum(s['score'] for s in bench) / max(len(bench), 1) if bench else 0

        # Weighted blend: starters dominate, subs contribute, bench barely
        lineup_score = avg_starter * 0.60 + avg_sub * 0.25 + avg_bench * 0.15
        # Scale to similar range as rank_r (0-100)
        lineup_score_scaled = min(100, max(10, lineup_score / 50))

        # Count positional distribution
        pos_counts = {'FW': 0, 'MID': 0, 'DEF': 0, 'GK': 0}
        for s in starters:
            pdata = team_jersey_scores.get(team, {}).get(s['jersey'], {})
            pos = pdata.get('pos', '')
            if pos in ('FW',):
                pos_counts['FW'] += 1
            elif pos in ('MID',):
                pos_counts['MID'] += 1
            elif pos in ('DEF',):
                pos_counts['DEF'] += 1
            elif pos in ('GK',):
                pos_counts['GK'] += 1

        lineup_strengths[team] = {
            'strength': round(lineup_score_scaled, 2),
            'starters': len(starters),
            'subs_used': len(subs),
            'formation': pos_counts,
            'avg_starter_score': round(avg_starter, 1),
        }

    return lineup_strengths


def compute_tactical_lineup_shift(team, team_strength, opponent_strength, standings, group):
    """
    Determine if a team should shift its tactical formation based on:
    - Points situation (0 pts → attack more, 3 pts → defend more)
    - Team strength (strong teams deviate less from normal)
    - Opponent strength

    Returns: (atk_shift, def_shift) multipliers for FW/MID vs DEF weights.
    atk_shift > 1.0 means more attacking, def_shift > 1.0 means more defensive.
    """
    # Find team's current points
    team_pts = 0
    if group in standings:
        for t, p, gd, gf, ga in standings[group]:
            if t == team:
                team_pts = p
                break

    # Base: no shift
    atk_shift = 1.0
    def_shift = 1.0

    # Determine team's strength tier (higher = less deviation from normal)
    # rank_r: 95+ = elite, 85-95 = strong, 75-85 = mid, <75 = weak
    strength_tier = 1.0  # elite teams barely shift
    if team_strength < 95:
        strength_tier = 0.85
    if team_strength < 85:
        strength_tier = 0.7
    if team_strength < 75:
        strength_tier = 0.5

    # Points situation
    if team_pts == 0:
        # Must win → more attacking
        atk_shift = 1.0 + 0.15 * strength_tier
        def_shift = 1.0 - 0.10 * strength_tier
    elif team_pts == 1:
        # Need result → slightly attacking
        atk_shift = 1.0 + 0.05 * strength_tier
        def_shift = 1.0
    else:  # 3 pts
        # Can play conservatively → slightly defensive
        atk_shift = 1.0 - 0.05 * strength_tier
        def_shift = 1.0 + 0.08 * strength_tier

    # Opponent strength modifier
    if opponent_strength > 0 and team_strength > 0:
        ratio = opponent_strength / team_strength
        if ratio > 1.2:
            # Opponent much stronger → more defensive
            atk_shift -= 0.05 * strength_tier
            def_shift += 0.10 * strength_tier
        elif ratio < 0.8:
            # Opponent much weaker → more attacking
            atk_shift += 0.08 * strength_tier
            def_shift -= 0.05 * strength_tier

    return atk_shift, def_shift


# ============================================================
# 7. MAIN PREDICTION FUNCTIONS
# ============================================================

def compute_round2_predictions(weights=None):
    """
    Main entry point: predict all 24 round 2 matches.

    Returns:
    {
        'round': '第2轮',
        'matches': [...],
        'group_projections': {...},
        'suspensions': {...},
        'form_scores': {...},
        'tactical_styles': {...},
    }
    """
    if weights is None:
        weights = dict(DEFAULT)

    # --- Load all data ---
    schedule_r2 = load_round2_schedule()
    results_r1 = load_round1_results()
    standings = compute_group_standings_from_results()
    suspensions = detect_suspensions()
    form_scores, form_breakdown = compute_team_form_scores()
    tactical_styles = extract_tactical_styles()

    # --- Mavis PDP baseline ranking ---
    mavis_ranking = predictor.compute_ranking(weights)
    ranking_dict = {r['team']: r for r in mavis_ranking}

    # --- FIFA & venue data ---
    fifa_data = {}
    with open(DATA_DIR / "world_cup_2026_fifa_ranking.csv", encoding='utf-8') as f:
        for row in csv.DictReader(f):
            fifa_data[row['国家']] = row

    venue_cfg = weights.get('venue_weights', {
        'altitude_threshold': 2000, 'altitude_penalty': 0.90,
        'temp_threshold': 32, 'temp_penalty': 0.97,
    })
    adaptation_weight = weights.get('venue_adaptation_weight', 0.5)

    # --- Compute R1 lineup strengths ---
    lineup_strengths = compute_lineup_strengths(ranking_dict)

    # --- Predict each match ---
    all_matches = []

    for m in schedule_r2:
        home = m['主队']
        away = m['客队']
        group = m['组别']

        # Fusion strength: 35% Mavis + 35% form + 30% R1 lineup
        h_mavis_rank_r = ranking_dict.get(home, {}).get('rank_r', 80)
        a_mavis_rank_r = ranking_dict.get(away, {}).get('rank_r', 80)
        h_form = form_scores.get(home, 50)
        a_form = form_scores.get(away, 50)
        h_lineup = lineup_strengths.get(home, {}).get('strength', h_mavis_rank_r)
        a_lineup = lineup_strengths.get(away, {}).get('strength', a_mavis_rank_r)

        h_fusion = h_mavis_rank_r * 0.35 + h_form * 0.35 + h_lineup * 0.30
        a_fusion = a_mavis_rank_r * 0.35 + a_form * 0.35 + a_lineup * 0.30

        # Suspension penalty
        h_susp = suspensions.get(home, [])
        a_susp = suspensions.get(away, [])
        h_susp_penalty = 0.03 * len([s for s in h_susp if s['impact'] == 'high']) + \
                         0.015 * len([s for s in h_susp if s['impact'] in ('medium', 'low')])
        a_susp_penalty = 0.03 * len([s for s in a_susp if s['impact'] == 'high']) + \
                         0.015 * len([s for s in a_susp if s['impact'] in ('medium', 'low')])

        h_fusion *= (1.0 - h_susp_penalty)
        a_fusion *= (1.0 - a_susp_penalty)

        # Tactical matchup
        h_style = tactical_styles.get(home, {'attack_style': 'balanced', 'defense_block': 'mid_block',
                                              'press': 'mid_block'})
        a_style = tactical_styles.get(away, {'attack_style': 'balanced', 'defense_block': 'mid_block',
                                              'press': 'mid_block'})
        matchup = get_matchup_adjustment(h_style, a_style)

        # Coaching aggression + tactical lineup shift
        h_aggr = compute_aggression(home, h_fusion, a_fusion, standings, group)
        a_aggr = compute_aggression(away, a_fusion, h_fusion, standings, group)
        h_atk_shift, h_def_shift = compute_tactical_lineup_shift(home, h_fusion, a_fusion, standings, group)
        a_atk_shift, a_def_shift = compute_tactical_lineup_shift(away, a_fusion, h_fusion, standings, group)

        # Build adjusted strength dicts for λ calculation
        h_adj = ranking_dict.get(home, {}).copy()
        a_adj = ranking_dict.get(away, {}).copy()

        if h_adj:
            # Aggression affects attack/defense ratio
            aggr_atk = 1.0 + (h_aggr - 0.5) * 0.4
            aggr_def = 1.0 - (h_aggr - 0.5) * 0.25
            # Tactical lineup shift from points situation
            atk_boost = aggr_atk * h_atk_shift
            def_adj_val = aggr_def * h_def_shift
            # Apply matchup
            atk_boost *= matchup['attack_adj']
            # Apply fusion
            fusion_ratio = h_fusion / max(h_mavis_rank_r, 1)
            atk_boost *= (0.5 + 0.5 * max(0.3, min(1.7, fusion_ratio)))
            def_adj_val *= (0.5 + 0.5 * max(0.3, min(1.7, fusion_ratio)))

            h_adj['fw_score'] = round(h_adj.get('fw_score', 0) * atk_boost, 2)
            h_adj['mid_score'] = round(h_adj.get('mid_score', 0) * atk_boost, 2)
            h_adj['def_score'] = round(h_adj.get('def_score', 0) * def_adj_val, 2)
            h_adj['rank_r'] = round(h_fusion, 2)

        if a_adj:
            a_aggr_atk = 1.0 + (a_aggr - 0.5) * 0.4
            a_aggr_def = 1.0 - (a_aggr - 0.5) * 0.25
            a_atk_boost = a_aggr_atk * a_atk_shift
            a_def_adj_val = a_aggr_def * a_def_shift
            a_atk_boost *= matchup.get('counter_risk', 1.0)
            a_fusion_ratio = a_fusion / max(a_mavis_rank_r, 1)
            a_atk_boost *= (0.5 + 0.5 * max(0.3, min(1.7, a_fusion_ratio)))
            a_def_adj_val *= (0.5 + 0.5 * max(0.3, min(1.7, a_fusion_ratio)))

            a_adj['fw_score'] = round(a_adj.get('fw_score', 0) * a_atk_boost, 2)
            a_adj['mid_score'] = round(a_adj.get('mid_score', 0) * a_atk_boost, 2)
            a_adj['def_score'] = round(a_adj.get('def_score', 0) * a_def_adj_val, 2)
            a_adj['rank_r'] = round(a_fusion, 2)

        # Parse venue
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

        # Build temporary ranking dict with adjusted scores
        temp_ranking = dict(ranking_dict)
        temp_ranking[home] = h_adj
        temp_ranking[away] = a_adj

        # Predict
        pred = predictor.predict_match(
            home, away, temp_ranking, fifa_data,
            venue_alt=alt, venue_temp=temp, venue_humidity=hum,
            weather_note=f"{m.get('城市','')} {m.get('体育场','')}",
            venue_cfg=venue_cfg,
            home_leagues={'fw': ranking_dict.get(home, {}).get('fw_leagues', []),
                          'mid': ranking_dict.get(home, {}).get('mid_leagues', []),
                          'def': ranking_dict.get(home, {}).get('def_leagues', []),
                          'gk': ranking_dict.get(home, {}).get('gk_league', '')},
            away_leagues={'fw': ranking_dict.get(away, {}).get('fw_leagues', []),
                          'mid': ranking_dict.get(away, {}).get('mid_leagues', []),
                          'def': ranking_dict.get(away, {}).get('def_leagues', []),
                          'gk': ranking_dict.get(away, {}).get('gk_league', '')},
            adaptation_weight=adaptation_weight,
            weights=weights,
        )

        # Enrich with round 2 specific data
        h_pts = 0
        a_pts = 0
        if group in standings:
            for t, p, gd, gf, ga in standings[group]:
                if t == home: h_pts = p
                if t == away: a_pts = p

        pred['round'] = '小组第2轮'
        pred['stage'] = 'group'
        pred['group'] = group
        pred['date'] = m.get('北京时间', '')
        pred['stadium'] = m.get('体育场', '')
        pred['city'] = m.get('城市', '')
        pred['roof'] = m.get('顶棚', '')
        pred['venue_alt'] = alt
        pred['venue_temp'] = temp
        pred['venue_humidity'] = hum
        pred['match_id'] = f"R2_{group}_{home}_vs_{away}"

        # Team detail data (for modal)
        pred['home_detail'] = get_team_details(home, ranking_dict)
        pred['away_detail'] = get_team_details(away, ranking_dict)

        # Algorithm logic steps (for modal)
        pred['algorithm_logic'] = {
            'step1_fusion': {
                'description': '50:50 纸面实力 + 第一轮表现融合',
                'home': {
                    'mavis_rank_r': round(h_mavis_rank_r, 2),
                    'form_score': round(h_form, 2),
                    'fusion_strength': round(h_fusion, 2),
                    'mavis_weight': 0.50,
                    'form_weight': 0.50,
                },
                'away': {
                    'mavis_rank_r': round(a_mavis_rank_r, 2),
                    'form_score': round(a_form, 2),
                    'fusion_strength': round(a_fusion, 2),
                },
            },
            'step2_suspension': {
                'description': '红牌停赛惩罚',
                'home': {'players': h_susp, 'penalty': round(h_susp_penalty, 3)},
                'away': {'players': a_susp, 'penalty': round(a_susp_penalty, 3)},
            },
            'step3_tactical': {
                'description': '战术风格 + 克制关系',
                'home_style': h_style,
                'away_style': a_style,
                'matchup': matchup,
            },
            'step4_aggression': {
                'description': '教练战术博弈 (0=纯守, 1=纯攻)',
                'home_aggression': h_aggr,
                'away_aggression': a_aggr,
            },
            'step5_lambda': {
                'description': 'λ 计算 → 泊松分布 → 比分概率',
                'lambda_home': pred.get('lambda_home', 0),
                'lambda_away': pred.get('lambda_away', 0),
                'formula': 'λ = 1.3 × poss × √(attack×0.001) × coach × venue × fifa × motivation × style_adj',
            },
        }

        # Round 2 specific enrichments
        pred['round2_enrichment'] = {
            'home_form': {
                'score': h_form,
                'breakdown': form_breakdown.get(home, {}),
                'mavis_rank_r': round(h_mavis_rank_r, 2),
                'fusion_strength': round(h_fusion, 2),
            },
            'away_form': {
                'score': a_form,
                'breakdown': form_breakdown.get(away, {}),
                'mavis_rank_r': round(a_mavis_rank_r, 2),
                'fusion_strength': round(a_fusion, 2),
            },
            'tactical': {
                'home_style': h_style,
                'away_style': a_style,
                'matchup_adjustment': matchup,
                'home_aggression': h_aggr,
                'away_aggression': a_aggr,
            },
            'suspensions': {
                'home': h_susp if h_susp else [],
                'away': a_susp if a_susp else [],
                'home_penalty': round(h_susp_penalty, 3),
                'away_penalty': round(a_susp_penalty, 3),
            },
            'group_context': {
                'group': group,
                'home_pts_before': h_pts,
                'away_pts_before': a_pts,
            },
        }

        all_matches.append(pred)

    # --- Project group standings after round 2 ---
    group_projections = _project_group_standings(all_matches, standings)

    # --- Build round 1 summary by group ---
    group_r1_summary = {}
    results_r1 = load_round1_results()
    for (home, away), r in results_r1.items():
        g = None
        for s in schedule_r2:
            if (s['主队'] == home and s['客队'] == away) or (s['主队'] == away and s['客队'] == home):
                g = s['组别']
                break
        if not g:
            for s in _load_csv("world_cup_2026_group_schedule.csv"):
                if (s['主队'] == home and s['客队'] == away):
                    g = s['组别']
                    break
        if g:
            if g not in group_r1_summary:
                group_r1_summary[g] = []
            group_r1_summary[g].append({
                'home': home, 'away': away,
                'score': f"{r['home_score']}-{r['away_score']}",
                'date': r['date'],
            })

    return {
        'round': '第2轮',
        'generated_at': __import__('datetime').datetime.now().isoformat(),
        'matches': all_matches,
        'count': len(all_matches),
        'group_projections': group_projections,
        'group_standings': {g: [{'team': t, 'pts': p, 'gd': gf - ga, 'gf': gf, 'ga': ga}
                               for t, p, gf, ga, mp in st]
                           for g, st in standings.items()},
        'group_r1_results': group_r1_summary,
        'suspensions': _format_suspensions(suspensions),
        'form_scores': {t: {'score': s, 'breakdown': form_breakdown.get(t, {})}
                        for t, s in form_scores.items()},
        'tactical_styles': tactical_styles,
    }


def _format_suspensions(suspensions):
    """Format suspensions for API output"""
    result = []
    for team, players in suspensions.items():
        for p in players:
            result.append({
                'team': team,
                'player': p['player_en'],
                'position': p['position'],
                'impact': p['impact'],
                'date': p['date'],
            })
    return result


def get_team_details(team, ranking_dict):
    """Extract player roster + coach info for a team from Mavis ranking data."""
    r = ranking_dict.get(team, {})

    # Load player master for age data
    player_master = load_player_master()
    def enrich_player(p):
        """Add age from master CSV to player dict"""
        if isinstance(p, dict):
            name = p.get('name', '')
            for (c, pn), pm in player_master.items():
                if c == team and (name in pn or pn in name):
                    raw = pm.get('年龄', '')
                    age_val = raw
                    # Parse birth date → age
                    if raw and '-' in str(raw):
                        try:
                            parts = str(raw).strip().split('-')
                            by = int(parts[0])
                            age_val = 2026 - by  # World Cup year
                        except:
                            age_val = raw
                    p['age'] = str(age_val) if age_val else ''
                    break
            if 'age' not in p:
                p['age'] = ''
        return p

    return {
        'team': team,
        'rank': r.get('rank', '-'),
        'fifa_rank': r.get('fifa_rank', '-'),
        'rank_r': r.get('rank_r', 0),
        'scores': {
            'fw': r.get('fw_score', 0),
            'mid': r.get('mid_score', 0),
            'def': r.get('def_score', 0),
            'gk': r.get('gk_score', 0),
            'player_total': r.get('player_score', 0),
            'coach': round(r.get('coach_score', 0), 1),
            'total': r.get('total', 0),
        },
        'top_players': {
            'fw': r.get('fw_top_full', [])[:5],
            'mid': r.get('mid_top_full', [])[:5],
            'def': r.get('def_top_full', [])[:6],
            'gk': r.get('gk_top_full'),
        },
        'player_details': {
            'fw': [enrich_player(p) for p in r.get('fw_details', [])[:5]],
            'mid': [enrich_player(p) for p in r.get('mid_details', [])[:5]],
            'def': [enrich_player(p) for p in r.get('def_details', [])[:6]],
            'gk': [enrich_player(p) for p in r.get('gk_details', [])[:1]],
        },
        'coach': {
            'name': r.get('coach_name', '?'),
            'age': r.get('coach_age', ''),
            'tenure': r.get('coach_tenure', ''),
            'career': r.get('coach_career', ''),
            'honors': r.get('coach_honors', ''),
            'score': round(r.get('coach_score', 0), 1),
            'details': r.get('coach_details', []),
        },
        'depth_penalty': r.get('depth_penalty', {}),
        'round1_player_stats': _get_round1_player_perf(team),
        'round1_team_stats': _get_round1_team_stats(team),
    }


def _get_round1_team_stats(team):
    """Get round 1 team-level match stats for a team, with cleaned keys + opponent info."""
    team_stats = load_round1_team_stats()
    for (home, away), ts in team_stats.items():
        if team == home:
            return {
                'opponent': away,
                'score': f"{ts.get('home_score','?')}-{ts.get('away_score','?')}",
                'venue': ts.get('venue', ''),
                'possession': safe_float(ts.get('home_possession_pct', 50)),
                'total_shots': safe_float(ts.get('home_total_shots', 0)),
                'shots_on_target': safe_float(ts.get('home_shots_on_target', 0)),
                'shot_accuracy': safe_float(ts.get('home_shot_pct', 0)),
                'corners': safe_float(ts.get('home_corners', 0)),
                'fouls': safe_float(ts.get('home_fouls', 0)),
                'yellow_cards': safe_float(ts.get('home_yellow_cards', 0)),
                'red_cards': safe_float(ts.get('home_red_cards', 0)),
                'offsides': safe_float(ts.get('home_offsides', 0)),
                'saves': safe_float(ts.get('home_saves', 0)),
                'passes_total': safe_float(ts.get('home_passes_total', 0)),
                'passes_accurate': safe_float(ts.get('home_passes_accurate', 0)),
                'pass_pct': safe_float(ts.get('home_pass_pct', 0)),
                'tackles_total': safe_float(ts.get('home_tackles_total', 0)),
                'tackles_effective': safe_float(ts.get('home_tackles_effective', 0)),
                'interceptions': safe_float(ts.get('home_interceptions', 0)),
                'clearances': safe_float(ts.get('home_clearances', 0)),
                'penalty_goals': safe_float(ts.get('home_penalty_goals', 0)),
            }
        elif team == away:
            return {
                'opponent': home,
                'score': f"{ts.get('home_score','?')}-{ts.get('away_score','?')}",
                'venue': ts.get('venue', ''),
                'possession': safe_float(ts.get('away_possession_pct', 50)),
                'total_shots': safe_float(ts.get('away_total_shots', 0)),
                'shots_on_target': safe_float(ts.get('away_shots_on_target', 0)),
                'shot_accuracy': safe_float(ts.get('away_shot_pct', 0)),
                'corners': safe_float(ts.get('away_corners', 0)),
                'fouls': safe_float(ts.get('away_fouls', 0)),
                'yellow_cards': safe_float(ts.get('away_yellow_cards', 0)),
                'red_cards': safe_float(ts.get('away_red_cards', 0)),
                'offsides': safe_float(ts.get('away_offsides', 0)),
                'saves': safe_float(ts.get('away_saves', 0)),
                'passes_total': safe_float(ts.get('away_passes_total', 0)),
                'passes_accurate': safe_float(ts.get('away_passes_accurate', 0)),
                'pass_pct': safe_float(ts.get('away_pass_pct', 0)),
                'tackles_total': safe_float(ts.get('away_tackles_total', 0)),
                'tackles_effective': safe_float(ts.get('away_tackles_effective', 0)),
                'interceptions': safe_float(ts.get('away_interceptions', 0)),
                'clearances': safe_float(ts.get('away_clearances', 0)),
                'penalty_goals': safe_float(ts.get('away_penalty_goals', 0)),
            }
    return None


def _get_round1_player_perf(team):
    """Get round 1 player performance for a team from match_player_stats.
    Uses a pre-built English→Chinese name mapping for accurate matching.
    Falls back to positional matching for unknown players.
    """
    stats = load_round1_player_stats()
    player_master = load_player_master()

    # Load name mapping
    import json
    name_map = {}
    map_path = PROJECT_ROOT / "1_数据基础" / "name_map_en_cn.json"
    if map_path.exists():
        with open(map_path, encoding='utf-8') as f:
            name_map = json.load(f)

    # Collect CSV players for position-group matching fallback
    csv_players = []
    for (c, cn_name), pm in player_master.items():
        if c == team:
            pos = pm.get('位置', '')
            pos_group = 'MID'
            if pos in ('门将', '守门员'): pos_group = 'GK'
            elif pos in ('后卫', '中后卫', '左后卫', '右后卫', '边后卫'): pos_group = 'DEF'
            elif pos in ('中场', '后腰', '前腰'): pos_group = 'MID'
            elif pos in ('前锋',): pos_group = 'FW'
            csv_players.append({'cn_name': cn_name, 'pos_group': pos_group})

    # Collect match stats
    match_entries = []
    for (mid, t, ename), ps in stats.items():
        if t != team:
            continue
        esp_pos = (ps.get('position', '') or '').upper()
        pos_group = 'MID'
        if any(x in esp_pos for x in ('GK','G')) and 'SUB' not in esp_pos: pos_group = 'GK'
        elif any(x in esp_pos for x in ('CD','LB','RB','CB','DF','SW','WB')): pos_group = 'DEF'
        elif any(x in esp_pos for x in ('CM','LM','RM','DM','AM','MF')): pos_group = 'MID'
        elif any(x in esp_pos for x in ('FW','F','LF','RF','CF','ST','LW','RW')): pos_group = 'FW'
        match_entries.append({'en_name': ename, 'pos_group': pos_group, 'ps': ps})

    # Sort for fallback matching
    pos_order = ['GK', 'DEF', 'MID', 'FW']
    csv_by_pos = {p: [] for p in pos_order}
    for cp in sorted(csv_players, key=lambda x: (x['pos_group'], x['cn_name'])):
        csv_by_pos[cp['pos_group']].append(cp)
    match_by_pos = {p: [] for p in pos_order}
    for me in sorted(match_entries, key=lambda x: (x['pos_group'], x['en_name'].lower())):
        match_by_pos[me['pos_group']].append(me)

    # Assign Chinese names: use name_map first, then positional fallback
    used_cn = set()
    players = []
    for pos_key in pos_order:
        cp_list = csv_by_pos[pos_key]
        me_list = match_by_pos[pos_key]
        for i, me in enumerate(me_list):
            ename = me['en_name']
            map_key = team + '|||' + ename
            cn = name_map.get(map_key, '')
            if not cn:
                # Fallback: sequential match, skip already-used names
                for cp in cp_list:
                    if cp['cn_name'] not in used_cn:
                        cn = cp['cn_name']
                        used_cn.add(cn)
                        break
            else:
                used_cn.add(cn)
            ps = me['ps']
            players.append({
                'name': ename,
                'name_cn': cn if cn else '',
                'jersey': ps.get('jersey', '?'),
                'position': ps.get('position', '?'),
                'starter': ps.get('starter') == 'True',
                'subbed_in': ps.get('subbed_in') == 'True',
                'minutes': ps.get('minutes', ''),
                'goals': ps.get('goals', ''),
                'assists': ps.get('assists', ''),
                'shots_on_target': ps.get('shots_on_target', ''),
                'fouls': ps.get('fouls_committed', ''),
                'yellow': ps.get('yellow_cards', ''),
                'red': ps.get('red_cards', ''),
                'saves': ps.get('saves', ''),
            })

    return sorted(players, key=lambda p: (
        0 if p['starter'] else 1,
        -int(p['goals']) if p['goals'] and p['goals'].isdigit() and int(p['goals']) > 0 else 0,
        -(int(p['minutes']) if p['minutes'] and p['minutes'].isdigit() else 0)
    ))


def _project_group_standings(matches, current_standings):
    """
    Project group standings after round 2 by adding predicted results.
    Simulates 2 scenarios: most likely result and worst case.
    """
    projections = {}
    for group in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
        # Start with current standings
        pts = defaultdict(lambda: [0, 0, 0, 0])
        if group in current_standings:
            for t, p, gd, gf, ga in current_standings[group]:
                pts[t] = [p, gf, ga, 1]

        # Add predicted round 2 results (using best_score as prediction)
        for pred in matches:
            if pred.get('group') != group:
                continue
            home, away = pred['home'], pred['away']
            best = pred.get('best_score', '1-1')
            try:
                k, m_ = [int(x) for x in best.split('-')]
            except (ValueError, TypeError):
                k, m_ = 1, 1

            pts[home][0] += 3 if k > m_ else (1 if k == m_ else 0)
            pts[home][1] += k
            pts[home][2] += m_
            pts[home][3] += 1

            pts[away][0] += 3 if m_ > k else (1 if k == m_ else 0)
            pts[away][1] += m_
            pts[away][2] += k
            pts[away][3] += 1

        # Sort
        st = sorted(pts.items(), key=lambda x: (-x[1][0], -(x[1][1]-x[1][2]), -x[1][1], x[0]))
        projections[group] = [
            {'team': t, 'pts': s[0], 'gd': s[1]-s[2], 'gf': s[1], 'ga': s[2], 'played': s[3]}
            for t, s in st
        ]

    return projections


# ============================================================
# 8. CLI DEBUG ENTRY
# ============================================================
if __name__ == '__main__':
    print("=" * 70)
    print("Round 2 Predictor — Debug Run")
    print("=" * 70)

    # Suspensions
    susp = detect_suspensions()
    print(f"\n🔴 停赛球员: {sum(len(v) for v in susp.values())} 人")
    for team, players in susp.items():
        for p in players:
            print(f"  {team}: {p['player_en']} ({p['position']}) impact={p['impact']}")

    # Form scores
    form_scores, breakdown = compute_team_form_scores()
    print(f"\n📊 第一轮表现 Top 10:")
    sorted_form = sorted(form_scores.items(), key=lambda x: -x[1])
    for i, (team, score) in enumerate(sorted_form[:10], 1):
        bd = breakdown[team]
        print(f"  {i:2d}. {team}: {score:6.2f}  (赛果{bd['result']:.0f} 团队{bd['team_perf']:.0f} 球员{bd['player_perf']:.0f})")

    print(f"\n📊 第一轮表现 Bottom 5:")
    for team, score in sorted_form[-5:]:
        bd = breakdown[team]
        print(f"     {team}: {score:6.2f}  (赛果{bd['result']:.0f} 团队{bd['team_perf']:.0f} 球员{bd['player_perf']:.0f})")

    # Tactical styles
    styles = extract_tactical_styles()
    print(f"\n🎯 战术标签 (部分):")
    for team in ['西班牙', '佛得角', '德国', '英格兰', '阿根廷', '巴西']:
        if team in styles:
            s = styles[team]
            print(f"  {team}: 进攻={s['attack_style']} 压迫={s['press']} 防守={s['defense_block']} 效率={s['attack_efficiency']}")

    # Group standings
    standings = compute_group_standings_from_results()
    print(f"\n📋 当前小组积分:")
    for g in ['A', 'E', 'H', 'K']:
        if g in standings:
            print(f"  {g}组: {', '.join(f'{t}({p}分)' for t,p,gd,gf,ga in standings[g])}")

    # Full predictions
    print(f"\n🏆 开始预测 24 场第二轮比赛...")
    result = compute_round2_predictions()

    print(f"\n{'='*70}")
    print("第二轮预测摘要")
    print(f"{'='*70}")
    for pred in result['matches']:
        h, a = pred['home'], pred['away']
        p_win = pred['p_home_win']
        p_draw = pred['p_draw']
        p_away = pred['p_away_win']
        best = pred['best_score']
        enr = pred['round2_enrichment']
        h_form = enr['home_form']['score']
        a_form = enr['away_form']['score']

        # Determine best pick
        if p_win >= p_draw and p_win >= p_away:
            pick = f"{h}胜 {p_win:.1%}"
        elif p_draw >= p_win and p_draw >= p_away:
            pick = f"平局 {p_draw:.1%}"
        else:
            pick = f"{a}胜 {p_away:.1%}"

        print(f"  {pred['group']}组 {h} vs {a}")
        print(f"    预测: {pick} | 最可能比分 {best}")
        print(f"    表现分: {h}({h_form:.0f}) vs {a}({a_form:.0f})")
        enr_tact = enr['tactical']
        print(f"    aggression: {h}({enr_tact['home_aggression']:.2f}) vs {a}({enr_tact['away_aggression']:.2f})")

        # Suspension info
        h_s = enr['suspensions']['home']
        a_s = enr['suspensions']['away']
        if h_s:
            print(f"    ⚠️ {h}停赛: {', '.join(s['player_en'] for s in h_s)}")
        if a_s:
            print(f"    ⚠️ {a}停赛: {', '.join(s['player_en'] for s in a_s)}")

        matchup = enr['tactical']['matchup_adjustment']
        if matchup.get('attack_adj', 1.0) != 1.0:
            print(f"    🎯 风格克制: {matchup.get('note', '')} (攻{matchup['attack_adj']:.0%})")

    print(f"\n📊 第二轮后小组排名预测:")
    for g in ['A', 'E', 'H', 'K']:
        if g in result['group_projections']:
            proj = result['group_projections'][g]
            team_strs = []
        for p in proj:
            team_strs.append(f"{p['team']}({p['pts']}分 GD{p['gd']:+d})")
        print(f"  {g}组: {', '.join(team_strs)}")
