"""
v23 = v22 + 轮次桶 (第 1 轮谨慎 / 第 2 轮生死战 / 第 3 轮用 sit_lambda)

关键修正:
- 第 1 轮 (6/11-6/18): v11 桶式 (db_mid=3.0, db_bot=5.0) 适用
- 第 2 轮 (6/19-6/28): 生死战, db 低 (1.0), wb 高 (1.5) → 更分胜负
- 第 3 轮 (6/25-6/28 末轮): sit_lambda (形势桶) + 生死战基础
"""
import sys, csv, json, math
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path('/Users/garcia/Desktop/WorldCup2026')
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from predictor import predict_match, compute_ranking, load_fifa, load_schedule, poisson_pmf

# === 1. 算形势 (基于 52 场最新已完赛) ===
with open(PROJECT_ROOT / '1_数据基础' / 'match_results.csv') as f:
    finished = [r for r in csv.DictReader(f) if r['home_score']]

team_pts = defaultdict(int)
team_gd = defaultdict(int)
team_played = defaultdict(int)
for r in finished:
    h, a = r['home'], r['away']
    hs, aws = int(r['home_score']), int(r['away_score'])
    team_pts[h] += 3 if hs > aws else (1 if hs == aws else 0)
    team_pts[a] += 3 if aws > hs else (1 if hs == aws else 0)
    team_gd[h] += hs - aws
    team_gd[a] -= hs - aws
    team_played[h] += 1
    team_played[a] += 1

def tag_team(team, pts_override=None, gd_override=None):
    """算形势 tag. 默认用最新积分, 末轮预测时应用 pts_override/gd_override (末轮前)"""
    p = pts_override if pts_override is not None else team_pts.get(team, 0)
    gd = gd_override if gd_override is not None else team_gd.get(team, 0)
    if p >= 6: return 'safe'
    if p >= 3: return 'hot' if gd >= 0 else 'edge'
    if gd >= -2: return 'alive'
    return 'dead'

SITUATION_LAMBDA = {
    'safe': 0.88, 'hot': 1.12, 'edge': 1.18, 'alive': 1.08, 'dead': 0.92,
}

# === 2. 加载 weights ===
ranking_weights = json.load(open(PROJECT_ROOT / '5_算法' / 'weights_v21.json'))
ranking_list = compute_ranking(ranking_weights)
ranking_dict = {r['team']: r for r in ranking_list}
rank_pos = {r['team']: r['rank'] for r in ranking_list}
fifa = load_fifa()
schedule = load_schedule()

# === 3. v23 配置 (按轮次) ===
# v23 改: 第 2 轮生死战 → db_mid 降到 1.0 (不平), wb_mid 升到 1.5
def get_cfg_for_round(rnd):
    """返回不同轮次的 cfg"""
    if rnd == '第1轮':
        # 第 1 轮: 试探性, draw 多 (跟 v11 一致)
        return {
            'db_top': 1.0, 'wb_top': 2.5,
            'db_mid': 3.0, 'wb_mid': 1.0,
            'db_bot': 5.0, 'wb_bot': 1.0,
            'big_diff_db': 2.5, 'diff_th': 20,
            'weak_home_wb': 2.5,
        }
    elif rnd == '第2轮':
        # 第 2 轮: 生死战, 分胜负 (draw 少)
        return {
            'db_top': 1.0, 'wb_top': 2.5,
            'db_mid': 1.0, 'wb_mid': 1.5,
            'db_bot': 1.0, 'wb_bot': 1.5,
            'big_diff_db': 1.0, 'diff_th': 20,
            'weak_home_wb': 1.5,
        }
    else:  # 第 3 轮
        # 第 3 轮: 形势情景系数 (sit_lambda) 已足够, 桶用温和
        return {
            'db_top': 1.0, 'wb_top': 2.0,
            'db_mid': 1.5, 'wb_mid': 1.2,
            'db_bot': 1.5, 'wb_bot': 1.2,
            'big_diff_db': 1.5, 'diff_th': 20,
            'weak_home_wb': 1.5,
        }

# === 4. predict_v23 函数 ===
def predict_v23(home, away, mdate, rnd, ranking_dict, fifa_data, weights):
    res = predict_match(home, away, ranking_dict, fifa_data, weights=None)
    lh, la = res['lambda_home'], res['lambda_away']
    lh = min(max(lh, 0.3), 3.5)
    la = min(max(la, 0.3), 3.5)

    cfg = get_cfg_for_round(rnd)

    h_pos = rank_pos.get(home, 24)
    a_pos = rank_pos.get(away, 24)
    pos_avg = (h_pos + a_pos) / 2
    pos_diff = abs(h_pos - a_pos)

    if pos_avg <= 8:
        db = cfg['db_top']; wb = cfg['wb_top']
    elif pos_avg >= 40:
        db = cfg['db_bot']; wb = cfg['wb_bot']
    else:
        db = cfg['db_mid']; wb = cfg['wb_mid']

    if cfg.get('big_diff_db', 0) and pos_diff > cfg.get('diff_th', 20):
        db *= cfg['big_diff_db']
    if cfg.get('weak_home_wb', 0) and h_pos > a_pos and pos_diff > 15:
        wb *= cfg['weak_home_wb']

    # 第 3 轮: sit_lambda (用末轮前积分, 不是最新积分)
    h_tag, a_tag = 'n/a', 'n/a'
    h_coef, a_coef = 1.0, 1.0
    if rnd == '第3轮':
        # 末轮前的形势: 该队在本次比赛日期之前的积分 (含之前所有轮次, 不含本次末轮)
        # 关键: 跳过日期 >= 本场比赛日期, 避免用"含本场"积分
        pre_r3_pts = {t: 0 for t in [home, away]}
        pre_r3_gd = {t: 0 for t in [home, away]}
        for r in finished:
            if r['date'] >= mdate:  # 跳过同日及之后的比赛 (包括末轮本场)
                continue
            h2, a2 = r['home'], r['away']
            hs2, aws2 = int(r['home_score']), int(r['away_score'])
            for t, sc, op_sc in [(h2, hs2, aws2), (a2, aws2, hs2)]:
                if t in pre_r3_pts:
                    pre_r3_pts[t] += 3 if sc > op_sc else (1 if sc == op_sc else 0)
                    pre_r3_gd[t] += sc - op_sc
        h_tag = tag_team(home, pre_r3_pts[home], pre_r3_gd[home])
        a_tag = tag_team(away, pre_r3_pts[away], pre_r3_gd[away])
        h_coef = SITUATION_LAMBDA[h_tag]
        a_coef = SITUATION_LAMBDA[a_tag]
        lh *= h_coef
        la *= a_coef

    score_probs = {}
    for k in range(7):
        for m_ in range(7):
            p = poisson_pmf(lh, k) * poisson_pmf(la, m_)
            score_probs[(k, m_)] = p
    p_w = sum(p for (k, m_), p in score_probs.items() if k > m_)
    p_d = sum(p for (k, m_), p in score_probs.items() if k == m_)
    p_l = sum(p for (k, m_), p in score_probs.items() if k < m_)
    p_w *= wb; p_d *= db
    t = p_w + p_d + p_l
    if t > 0: p_w /= t; p_d /= t; p_l /= t
    best = max(score_probs.items(), key=lambda x: x[1])

    return {
        'home': home, 'away': away, 'round': rnd, 'mdate': mdate,
        'p_h': round(p_w, 4), 'p_d': round(p_d, 4), 'p_a': round(p_l, 4),
        'best_score': f'{best[0][0]}-{best[0][1]}',
        'lambda_home': round(lh, 3), 'lambda_away': round(la, 3),
        'home_tag': h_tag, 'away_tag': a_tag,
        'home_coef': h_coef, 'away_coef': a_coef,
    }


# === 5. 跑 72 场 + 52 场 audit ===
print("=== v23 = 轮次桶 + sit_lambda 跑 72 场 ===\n")
all_preds = []
for m in schedule:
    g = m['组别']
    h, a = m['主队'], m['客队']
    rnd = m['轮次']
    date = m['北京时间'].split(' ')[0]
    pred = predict_v23(h, a, date, rnd, ranking_dict, fifa, ranking_weights)
    pred['date'] = date
    pred['group'] = g
    pred['match_id'] = f"GS_{g}_{rnd}_{h}_vs_{a}"
    all_preds.append(pred)

# 52 场 audit (拆分轮次)
print("=== v23 audit 52 场 (按轮次) ===\n")
correct_total = 0
correct_by_round = defaultdict(lambda: [0, 0])
wrong_list_by_round = defaultdict(list)

for r in finished:
    h, a = r['home'], r['away']
    hs, aws = int(r['home_score']), int(r['away_score'])
    actual_outcome = 'H' if hs > aws else ('A' if aws > hs else 'D')

    # 找对应比赛 (按 home+away)
    pred = next((p for p in all_preds if p['home'] == h and p['away'] == a), None)
    if not pred: continue

    p = pred['p_h']; d = pred['p_d']; l = pred['p_a']
    pred_outcome = 'H' if p > d and p > l else ('A' if l > d and l > p else 'D')
    correct = pred_outcome == actual_outcome
    correct_total += correct

    rnd = pred['round']
    correct_by_round[rnd][0] += correct
    correct_by_round[rnd][1] += 1

    if not correct:
        wrong_list_by_round[rnd].append({
            'date': r['date'], 'home': h, 'away': a,
            'hs': hs, 'aws': aws, 'actual': actual_outcome, 'pred': pred_outcome,
            'p_h': p, 'p_d': d, 'p_a': l,
        })

for rnd in ['第1轮', '第2轮']:
    c, t = correct_by_round[rnd]
    print(f"  {rnd}: {c}/{t} = {c/t*100:.1f}%")

print(f"\n  总: {correct_total}/{len(finished)} = {correct_total/len(finished)*100:.1f}%")

# 错分场次
for rnd in ['第1轮', '第2轮']:
    if wrong_list_by_round[rnd]:
        print(f"\n  {rnd} 错分 ({len(wrong_list_by_round[rnd])} 场):")
        for w in wrong_list_by_round[rnd]:
            print(f"    ❌ {w['date']} {w['home']}({w['hs']}) vs {w['away']}({w['aws']}) actual {w['actual']}, pred {w['pred']} (p={w['p_h']:.2f} d={w['p_d']:.2f} a={w['p_a']:.2f})")

# === 6. 保存 ===
with open(PROJECT_ROOT / '4_比赛预测' / 'predictions_v23_full72.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['date', 'round', 'group', 'home', 'away', 'home_pts', 'away_pts',
                'lambda_home', 'lambda_away', 'home_tag', 'away_tag',
                'home_coef', 'away_coef',
                'p_h', 'p_d', 'p_a', 'best_score',
                'home_score_actual', 'away_score_actual', 'outcome_actual', 'predicted_outcome', 'correct'])
    actual_map = {(r['home'], r['away']): (r['home_score'], r['away_score']) for r in finished}
    for p in all_preds:
        h, a = p['home'], p['away']
        ha, aa = actual_map.get((h, a), ('', ''))
        actual_outcome = ''
        if ha != '' and aa != '':
            ha, aa = int(ha), int(aa)
            actual_outcome = 'H' if ha > aa else ('A' if aa > ha else 'D')
        pred_outcome = 'H' if p['p_h'] > p['p_d'] and p['p_h'] > p['p_a'] else ('A' if p['p_a'] > p['p_d'] and p['p_a'] > p['p_h'] else 'D')
        correct = '✓' if actual_outcome and actual_outcome == pred_outcome else ('' if not actual_outcome else '✗')
        w.writerow([p['date'], p['round'], p['group'], h, a, team_pts.get(h, 0), team_pts.get(a, 0),
                    p['lambda_home'], p['lambda_away'],
                    p['home_tag'], p['away_tag'],
                    p['home_coef'], p['away_coef'],
                    p['p_h'], p['p_d'], p['p_a'], p['best_score'],
                    ha, aa, actual_outcome, pred_outcome, correct])

print(f"\n✅ 4_比赛预测/predictions_v23_full72.csv ({len(all_preds)} 场)")