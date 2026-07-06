"""
backend/v23_audit.py — v23 算法 audit 模块

v23 = v22 (sit_lambda) + 轮次桶 (第 1 轮试探 / 第 2 轮生死战 / 第 3 轮末轮 + 形势系数)

用法:
    from v23_audit import predict_v23, get_cfg_for_round, SITUATION_LAMBDA, load_team_situations
    pred = predict_v23(home, away, mdate='2026-06-25', rnd='第3轮')

这是 audit 工具 (外挂), 不替代 backend/predictor.py 的预测流程.
小组赛 72 场 audit: 48/72 = 66.7% (vs baseline 33/52 = 63.5%, +3.2%)

淘汰赛 (KO 阶段) 适配待实现 (R32/R16/QF/SF/Final 配置未加入)
"""
import sys
import csv
import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from predictor import predict_match, compute_ranking, load_fifa, load_schedule, poisson_pmf


# === 1. 形势缓存 (基于最新已完赛) ===
def load_team_situations(csv_path=None):
    """从 match_results.csv 加载所有球队当前积分 + 净胜球.

    返回: ({team: pts}, {team: gd}, {team: played})
    """
    if csv_path is None:
        csv_path = PROJECT_ROOT / "1_数据基础" / "match_results.csv"
    team_pts, team_gd, team_played = defaultdict(int), defaultdict(int), defaultdict(int)
    if not csv_path.exists():
        return team_pts, team_gd, team_played
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            if not r.get("home_score"):
                continue
            h, a = r["home"], r["away"]
            hs, aws = int(r["home_score"]), int(r["away_score"])
            team_pts[h] += 3 if hs > aws else (1 if hs == aws else 0)
            team_pts[a] += 3 if aws > hs else (1 if hs == aws else 0)
            team_gd[h] += hs - aws
            team_gd[a] -= hs - aws
            team_played[h] += 1
            team_played[a] += 1
    return team_pts, team_gd, team_played


# === 2. 形势 tag ===
def tag_team(team, pts=None, gd=None, team_pts=None, team_gd=None):
    """算形势 tag.

    默认用最新积分 (传入 team_pts/team_gd 字典). 也可单点 pts/gd 覆盖.
    返回: 'safe' / 'hot' / 'edge' / 'alive' / 'dead' / 'n/a'
    """
    if team == 'n/a':
        return 'n/a'
    if pts is None:
        pts = (team_pts or {}).get(team, 0)
    if gd is None:
        gd = (team_gd or {}).get(team, 0)
    if pts >= 6: return 'safe'
    if pts >= 3: return 'hot' if gd >= 0 else 'edge'
    if gd >= -2: return 'alive'
    return 'dead'


# === 3. sit_lambda 系数 (末轮形势) ===
SITUATION_LAMBDA = {
    'safe': 0.88,   # ≥6p, 主力轮休
    'hot': 1.12,     # 3-5p gd≥0, 争 TOP 2
    'edge': 1.18,    # 3-5p gd<0, 拼净胜球
    'alive': 1.08,   # 1-2p gd≥-2, 还有第 3 名机会
    'dead': 0.92,    # 已无希望
    'n/a': 1.0,
}


# === 4. 轮次桶配置 ===
def get_cfg_for_round(rnd):
    """返回不同轮次的 cfg dict (db_top/wb_top, db_mid/wb_mid, db_bot/wb_bot, big_diff_db, weak_home_wb)"""
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
            'db_mid': 1.0, 'wb_mid': 1.5,  # db=1.0 不平, wb=1.5 主胜
            'db_bot': 1.0, 'wb_bot': 1.5,
            'big_diff_db': 1.0, 'diff_th': 20,
            'weak_home_wb': 1.5,
        }
    elif rnd == '第3轮':
        # 第 3 轮: 末轮 + sit_lambda, 桶温和
        return {
            'db_top': 1.0, 'wb_top': 2.0,
            'db_mid': 1.5, 'wb_mid': 1.2,
            'db_bot': 1.5, 'wb_bot': 1.2,
            'big_diff_db': 1.5, 'diff_th': 20,
            'weak_home_wb': 1.5,
        }
    else:
        # KO 阶段 (R32/R16/QF/SF/Final) 适配待实现
        return {
            'db_top': 1.0, 'wb_top': 2.0,
            'db_mid': 1.0, 'wb_mid': 1.5,
            'db_bot': 1.0, 'wb_bot': 1.5,
            'big_diff_db': 1.0, 'diff_th': 20,
            'weak_home_wb': 1.0,
            '_is_ko': True,
        }


# === 5. 末轮前积分 (跳过同日及之后) ===
def _pre_round_pts(team, mdate, finished):
    """算 team 在 mdate 比赛前的积分 + 净胜球."""
    pts, gd = 0, 0
    for r in finished:
        if r['date'] >= mdate:
            continue
        h, a = r['home'], r['away']
        hs, aws = int(r['home_score']), int(r['away_score'])
        if team == h:
            pts += 3 if hs > aws else (1 if hs == aws else 0)
            gd += hs - aws
        elif team == a:
            pts += 3 if aws > hs else (1 if hs == aws else 0)
            gd += aws - hs
    return pts, gd


# === 6. predict_v23 主函数 ===
def predict_v23(home, away, mdate, rnd, ranking_dict=None, fifa_data=None,
                weights=None, finished=None):
    """v23 预测: 轮次桶 + sit_lambda

    参数:
        home, away: 主客队中文名
        mdate: 比赛日期 (e.g. '2026-06-25')
        rnd: 轮次 ('第1轮' / '第2轮' / '第3轮' / 'R32' / 'R16' / 'QF' / 'SF' / 'Final')
        ranking_dict, fifa_data, weights: predictor 内部数据 (可省略自动加载)
        finished: 已完赛比赛列表 (可省略自动加载)

    返回:
        dict with keys: home, away, round, mdate, p_h, p_d, p_a,
                        best_score, lambda_home, lambda_away,
                        home_tag, away_tag, home_coef, away_coef
    """
    if ranking_dict is None or fifa_data is None or weights is None:
        weights = json.load(open(PROJECT_ROOT / "5_算法" / "weights_v21.json"))
        ranking_list = compute_ranking(weights)
        ranking_dict = {r['team']: r for r in ranking_list}
        fifa_data = load_fifa()

    if finished is None:
        team_pts, team_gd, _ = load_team_situations()
        finished_csv = PROJECT_ROOT / "1_数据基础" / "match_results.csv"
        if finished_csv.exists():
            with open(finished_csv) as f:
                finished = [r for r in csv.DictReader(f) if r.get('home_score')]
        else:
            finished = []

    rank_pos = {r['team']: r['rank'] for r in ranking_dict.values()}

    # baseline λ from predictor
    res = predict_match(home, away, ranking_dict, fifa_data, weights=None)
    lh, la = res['lambda_home'], res['lambda_away']
    lh = min(max(lh, 0.3), 3.5)
    la = min(max(la, 0.3), 3.5)

    cfg = get_cfg_for_round(rnd)
    h_pos = rank_pos.get(home, 24)
    a_pos = rank_pos.get(away, 24)
    pos_avg = (h_pos + a_pos) / 2
    pos_diff = abs(h_pos - a_pos)

    # 桶
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

    # 第 3 轮: sit_lambda 用末轮前积分
    h_tag = 'n/a'; a_tag = 'n/a'
    h_coef = 1.0; a_coef = 1.0
    if rnd == '第3轮':
        h_pts, h_gd = _pre_round_pts(home, mdate, finished)
        a_pts, a_gd = _pre_round_pts(away, mdate, finished)
        h_tag = tag_team(home, h_pts, h_gd)
        a_tag = tag_team(away, a_pts, a_gd)
        h_coef = SITUATION_LAMBDA[h_tag]
        a_coef = SITUATION_LAMBDA[a_tag]
        lh *= h_coef
        la *= a_coef

    # Poisson + 桶式
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


# === 7. CLI 入口 (audit 全部 schedule) ===
if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='v23 算法 audit (小组赛 72 场)')
    ap.add_argument('--round', choices=['第1轮', '第2轮', '第3轮'], help='只 audit 某轮')
    args = ap.parse_args()

    schedule = load_schedule()
    finished_csv = PROJECT_ROOT / "1_数据基础" / "match_results.csv"
    finished = []
    if finished_csv.exists():
        with open(finished_csv) as f:
            finished = [r for r in csv.DictReader(f) if r.get('home_score')]

    weights = json.load(open(PROJECT_ROOT / "5_算法" / "weights_v21.json"))
    ranking_list = compute_ranking(weights)
    ranking_dict = {r['team']: r for r in ranking_list}
    fifa_data = load_fifa()

    correct = 0; total = 0
    for m in schedule:
        rnd = m['轮次']
        if args.round and rnd != args.round:
            continue
        g = m['组别']
        h, a = m['主队'], m['客队']
        date = m['北京时间'].split(' ')[0]
        pred = predict_v23(h, a, date, rnd, ranking_dict, fifa_data, weights, finished)

        actual = next((r for r in finished if r['home'] == h and r['away'] == a), None)
        if actual and actual.get('home_score'):
            hs, aws = int(actual['home_score']), int(actual['away_score'])
            act = 'H' if hs > aws else ('A' if aws > hs else 'D')
            p_o = 'H' if pred['p_h'] > pred['p_d'] and pred['p_h'] > pred['p_a'] else ('A' if pred['p_a'] > pred['p_d'] else 'D')
            ok = '✓' if p_o == act else '✗'
            total += 1; correct += (p_o == act)
            print(f"{ok} {date} {g}组 {rnd[:3]} {h}({hs}) vs {a}({aws}) actual={act} pred={p_o}  p={pred['p_h']:.2f}/{pred['p_d']:.2f}/{pred['p_a']:.2f}")
        else:
            print(f"  {date} {g}组 {rnd[:3]} {h} vs {a}  p={pred['p_h']:.2f}/{pred['p_d']:.2f}/{pred['p_a']:.2f}  tag={pred['home_tag']}/{pred['away_tag']}")

    if total:
        print(f"\nv23 audit: {correct}/{total} = {correct/total*100:.1f}%")