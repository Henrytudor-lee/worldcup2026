"""
竞彩足球投注策略引擎 v1.0
=======================
基于 Mavis PDP 预测数据，生成多套最优竞彩方案。

规则:
- 小组赛: 同天比赛组合
- 淘汰赛: 同周比赛组合
- 最多 3串1 (3-leg parlay)
- 多套方案: 保守型 / 均衡型 / 激进型

核心: 找出预测概率 > 市场隐含概率的"价值投注"
"""

import json, math
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "1_数据基础"

# ============================================================
# 1. 市场赔率数据 (中国竞彩官方, 定期更新)
# ============================================================
# 格式: {match_key: {'home': odds, 'draw': odds, 'away': odds}}
# 数据来源: sporttery.cn / lottery.gov.cn
MARKET_ODDS = {
    # === 小组赛第1轮 ===
    '墨西哥_vs_南非':    {'home': 1.45, 'draw': 3.80, 'away': 6.50},
    '韩国_vs_捷克':      {'home': 2.10, 'draw': 3.10, 'away': 3.40},
    '加拿大_vs_波黑':    {'home': 1.85, 'draw': 3.30, 'away': 3.90},
    '美国_vs_巴拉圭':    {'home': 1.55, 'draw': 3.70, 'away': 5.50},
    '卡塔尔_vs_瑞士':    {'home': 5.00, 'draw': 3.50, 'away': 1.60},
    '巴西_vs_摩洛哥':    {'home': 1.35, 'draw': 4.20, 'away': 8.00},
    '海地_vs_苏格兰':    {'home': 4.50, 'draw': 3.30, 'away': 1.75},
    '德国_vs_库拉索':    {'home': 1.12, 'draw': 7.50, 'away': 15.00},
    '澳大利亚_vs_土耳其': {'home': 2.40, 'draw': 3.10, 'away': 2.80},
    '瑞典_vs_突尼斯':    {'home': 1.50, 'draw': 3.80, 'away': 6.00},
    '科特迪瓦_vs_厄瓜多尔': {'home': 2.30, 'draw': 3.00, 'away': 3.10},
    '荷兰_vs_日本':      {'home': 1.70, 'draw': 3.40, 'away': 4.80},
    '伊朗_vs_新西兰':    {'home': 2.00, 'draw': 3.10, 'away': 3.60},
    '比利时_vs_埃及':    {'home': 1.55, 'draw': 3.70, 'away': 5.50},
    '沙特_vs_乌拉圭':    {'home': 5.50, 'draw': 3.50, 'away': 1.55},
    '西班牙_vs_佛得角':  {'home': 1.18, 'draw': 6.00, 'away': 12.00},
    '法国_vs_塞内加尔':  {'home': 1.31, 'draw': 4.23, 'away': 7.70},
    '阿根廷_vs_阿尔及利亚': {'home': 1.26, 'draw': 4.40, 'away': 9.20},
    '伊拉克_vs_挪威':    {'home': 7.00, 'draw': 4.50, 'away': 1.35},
    '奥地利_vs_约旦':    {'home': 1.65, 'draw': 3.50, 'away': 4.80},
    '英格兰_vs_克罗地亚': {'home': 1.53, 'draw': 3.50, 'away': 5.25},
    '加纳_vs_巴拿马':    {'home': 2.10, 'draw': 3.00, 'away': 3.50},
    '葡萄牙_vs_民主刚果': {'home': 1.13, 'draw': 5.86, 'away': 13.50},
    '乌兹别克斯坦_vs_哥伦比亚': {'home': 5.00, 'draw': 3.60, 'away': 1.60},

    # === 小组赛第2轮 (部分) ===
    '捷克_vs_南非':      {'home': 1.80, 'draw': 3.20, 'away': 4.50},
    '墨西哥_vs_韩国':    {'home': 2.00, 'draw': 3.00, 'away': 3.80},
    '瑞士_vs_波黑':      {'home': 1.55, 'draw': 3.60, 'away': 5.50},
    '加拿大_vs_卡塔尔':  {'home': 1.17, 'draw': 5.45, 'away': 11.00},
    '美国_vs_澳大利亚':  {'home': 1.60, 'draw': 3.50, 'away': 5.20},
    '土耳其_vs_巴拉圭':  {'home': 2.50, 'draw': 3.10, 'away': 2.70},
    '德国_vs_科特迪瓦':  {'home': 1.40, 'draw': 4.15, 'away': 5.75},
    '厄瓜多尔_vs_库拉索': {'home': 1.45, 'draw': 3.90, 'away': 6.50},
    '荷兰_vs_瑞典':      {'home': 1.59, 'draw': 3.58, 'away': 4.52},
    '突尼斯_vs_日本':    {'home': 5.75, 'draw': 3.70, 'away': 1.46},
    '比利时_vs_伊朗':    {'home': 1.42, 'draw': 4.00, 'away': 6.80},
    '新西兰_vs_埃及':    {'home': 3.80, 'draw': 3.20, 'away': 1.90},
    '西班牙_vs_沙特':    {'home': 1.16, 'draw': 6.50, 'away': 12.00},
    '乌拉圭_vs_佛得角':  {'home': 1.50, 'draw': 3.70, 'away': 6.20},
    '法国_vs_伊拉克':    {'home': 1.13, 'draw': 6.80, 'away': 14.00},
    '挪威_vs_塞内加尔':  {'home': 1.55, 'draw': 3.60, 'away': 5.50},
    '阿根廷_vs_奥地利':  {'home': 1.52, 'draw': 3.60, 'away': 6.00},
    '约旦_vs_阿尔及利亚': {'home': 3.50, 'draw': 3.10, 'away': 2.05},
    '葡萄牙_vs_乌兹别克斯坦': {'home': 1.14, 'draw': 6.00, 'away': 13.00},
    '哥伦比亚_vs_民主刚果': {'home': 1.25, 'draw': 4.55, 'away': 9.10},
    '英格兰_vs_加纳':    {'home': 1.40, 'draw': 4.00, 'away': 7.00},
    '巴拿马_vs_克罗地亚': {'home': 5.50, 'draw': 3.60, 'away': 1.55},
    '苏格兰_vs_摩洛哥':  {'home': 2.80, 'draw': 3.10, 'away': 2.40},
    '巴西_vs_海地':      {'home': 1.15, 'draw': 6.50, 'away': 14.00},
}


def load_predictions():
    """加载预测数据"""
    from round2_predictor import compute_round2_predictions
    return compute_round2_predictions()


def implied_probability(odds):
    return 1.0 / odds


def expected_value(pred_prob, market_odds):
    return pred_prob * market_odds - 1.0


# ============================================================
# 让球胜平负 (Handicap) — 从泊松比分分布计算
# ============================================================
def calc_handicap_probs(score_dist, handicap):
    """
    从比分分布计算让球后的胜平负概率
    handicap > 0: 主队让球 (e.g., -2 means home needs to win by 3+)
    handicap < 0: 客队让球
    返回 {'home': P, 'draw': P, 'away': P}
    """
    p_home = 0.0  # 主队赢盘 (home_score + handicap > away_score)
    p_draw = 0.0  # 走盘 (home_score + handicap == away_score)
    p_away = 0.0  # 客队赢盘

    for score_str, prob in score_dist.items():
        try:
            h, a = [int(x) for x in score_str.split('-')]
        except (ValueError, AttributeError):
            continue
        adjusted = h + handicap
        if adjusted > a:
            p_home += prob
        elif adjusted == a:
            p_draw += prob
        else:
            p_away += prob

    return {'home': p_home, 'draw': p_draw, 'away': p_away}


def calc_total_goals_probs(score_dist):
    """从比分分布计算总进球数概率 {0: P, 1: P, 2: P, ...}"""
    totals = defaultdict(float)
    for score_str, prob in score_dist.items():
        try:
            h, a = [int(x) for x in score_str.split('-')]
        except (ValueError, AttributeError):
            continue
        totals[h + a] += prob
    return dict(totals)


def calc_score_probs(score_dist):
    """从比分分布提取各个比分的概率 (直接返回)"""
    return score_dist


# ============================================================
# 让球盘赔率 (示例数据, 实际从竞彩API获取)
# ============================================================
MARKET_HANDICAP = {
    '西班牙_vs_沙特': {'handicap': -2, 'home': 2.05, 'draw': 3.60, 'away': 2.80},
    '比利时_vs_伊朗': {'handicap': -1, 'home': 1.85, 'draw': 3.30, 'away': 3.50},
    '乌拉圭_vs_佛得角': {'handicap': -1, 'home': 2.10, 'draw': 3.20, 'away': 3.00},
    '新西兰_vs_埃及': {'handicap': 1, 'home': 2.50, 'draw': 3.10, 'away': 2.60},
    '德国_vs_科特迪瓦': {'handicap': -1, 'home': 1.95, 'draw': 3.40, 'away': 3.10},
    '荷兰_vs_瑞典': {'handicap': -1, 'home': 2.20, 'draw': 3.30, 'away': 2.70},
    '突尼斯_vs_日本': {'handicap': 1, 'home': 2.80, 'draw': 3.20, 'away': 2.20},
    '加拿大_vs_卡塔尔': {'handicap': -2, 'home': 2.15, 'draw': 3.80, 'away': 2.50},
    '法国_vs_伊拉克': {'handicap': -3, 'home': 2.30, 'draw': 3.80, 'away': 2.30},
    '挪威_vs_塞内加尔': {'handicap': -1, 'home': 1.90, 'draw': 3.40, 'away': 3.20},
    '阿根廷_vs_奥地利': {'handicap': -1, 'home': 1.88, 'draw': 3.30, 'away': 3.40},
    '葡萄牙_vs_乌兹别克斯坦': {'handicap': -3, 'home': 2.40, 'draw': 3.80, 'away': 2.20},
    '英格兰_vs_加纳': {'handicap': -1, 'home': 1.78, 'draw': 3.40, 'away': 3.80},
    '巴拿马_vs_克罗地亚': {'handicap': 1, 'home': 2.60, 'draw': 3.20, 'away': 2.35},
    '巴西_vs_海地': {'handicap': -3, 'home': 2.10, 'draw': 3.80, 'away': 2.50},
    '美国_vs_澳大利亚': {'handicap': -1, 'home': 2.05, 'draw': 3.20, 'away': 3.10},
    '土耳其_vs_巴拉圭': {'handicap': 0, 'home': 2.30, 'draw': 3.10, 'away': 2.80},
}

# 总进球赔率 (over/under 2.5 球)
MARKET_TOTAL_GOALS = {
    '西班牙_vs_沙特': {'o2.5': 1.42, 'u2.5': 2.65},
    '比利时_vs_伊朗': {'o2.5': 1.65, 'u2.5': 2.10},
    '乌拉圭_vs_佛得角': {'o2.5': 1.70, 'u2.5': 2.00},
    '新西兰_vs_埃及': {'o2.5': 1.80, 'u2.5': 1.90},
    '德国_vs_科特迪瓦': {'o2.5': 1.48, 'u2.5': 2.45},
    '荷兰_vs_瑞典': {'o2.5': 1.55, 'u2.5': 2.25},
    '突尼斯_vs_日本': {'o2.5': 1.75, 'u2.5': 1.95},
    '加拿大_vs_卡塔尔': {'o2.5': 1.50, 'u2.5': 2.40},
    '法国_vs_伊拉克': {'o2.5': 1.35, 'u2.5': 2.90},
    '挪威_vs_塞内加尔': {'o2.5': 1.52, 'u2.5': 2.35},
    '阿根廷_vs_奥地利': {'o2.5': 1.58, 'u2.5': 2.20},
    '葡萄牙_vs_乌兹别克斯坦': {'o2.5': 1.40, 'u2.5': 2.70},
    '英格兰_vs_加纳': {'o2.5': 1.55, 'u2.5': 2.25},
    '巴拿马_vs_克罗地亚': {'o2.5': 1.70, 'u2.5': 2.00},
    '巴西_vs_海地': {'o2.5': 1.38, 'u2.5': 2.80},
    '美国_vs_澳大利亚': {'o2.5': 1.60, 'u2.5': 2.15},
    '土耳其_vs_巴拉圭': {'o2.5': 1.85, 'u2.5': 1.85},
}

# 比分赔率 (部分常见比分)
MARKET_SCORE = {
    '西班牙_vs_沙特': {'2-0': 5.50, '3-0': 6.00, '1-0': 5.00, '2-1': 7.50},
    '比利时_vs_伊朗': {'2-0': 5.50, '1-0': 5.00, '2-1': 7.00, '3-0': 8.00},
    '乌拉圭_vs_佛得角': {'2-0': 5.50, '1-0': 5.50, '2-1': 7.00, '3-0': 8.50},
    '新西兰_vs_埃及': {'0-1': 6.00, '1-2': 7.00, '0-2': 7.50, '1-1': 6.50},
    '德国_vs_科特迪瓦': {'3-0': 7.00, '2-0': 5.50, '3-1': 8.00, '2-1': 7.00},
}


def find_value_bets_spf(predictions, min_ev=0.03):
    """胜平负价值投注"""
    value_bets = []
    for pred in predictions:
        match_key = f"{pred['home']}_vs_{pred['away']}"
        odds = MARKET_ODDS.get(match_key)
        if not odds:
            continue
        for bet_type in ['home', 'draw', 'away']:
            pred_prob = pred.get(f'p_{bet_type}_win' if bet_type != 'draw' else 'p_draw', 0)
            market_odds = odds.get(bet_type)
            if not market_odds or market_odds < 1.01:
                continue  # 赔率未开售或无效
            ev = expected_value(pred_prob, market_odds)
            if ev >= min_ev:
                value_bets.append({
                    'match': match_key, 'home': pred['home'], 'away': pred['away'],
                    'date': pred.get('date', ''), 'category': '胜平负',
                    'bet_type': bet_type, 'pred_prob': pred_prob,
                    'market_odds': market_odds, 'ev': ev,
                })
    return sorted(value_bets, key=lambda x: -x['ev'])


def find_value_bets_handicap(predictions, min_ev=0.03):
    """让球胜平负价值投注"""
    value_bets = []
    for pred in predictions:
        match_key = f"{pred['home']}_vs_{pred['away']}"
        hc = MARKET_HANDICAP.get(match_key)
        if not hc or 'score_distribution' not in pred:
            continue
        probs = calc_handicap_probs(pred['score_distribution'], hc['handicap'])
        for bt in ['home', 'draw', 'away']:
            market_odds = hc.get(bt)
            if not market_odds or market_odds < 1.01:
                continue  # 让球赔率未开售或无效
            ev = expected_value(probs[bt], market_odds)
            if ev >= min_ev:
                label = f"让{hc['handicap']:+d}球{'胜' if bt=='home' else '平' if bt=='draw' else '负'}"
                value_bets.append({
                    'match': match_key, 'home': pred['home'], 'away': pred['away'],
                    'date': pred.get('date', ''), 'category': '让球胜平负',
                    'bet_type': bt, 'bet_label': label, 'handicap': hc['handicap'],
                    'pred_prob': probs[bt], 'market_odds': market_odds, 'ev': ev,
                })
    return sorted(value_bets, key=lambda x: -x['ev'])


def find_value_bets_total(predictions, min_ev=0.03):
    """总进球数价值投注 (over/under 2.5)"""
    value_bets = []
    for pred in predictions:
        match_key = f"{pred['home']}_vs_{pred['away']}"
        odds = MARKET_TOTAL_GOALS.get(match_key)
        if not odds or 'score_distribution' not in pred:
            continue
        totals = calc_total_goals_probs(pred['score_distribution'])
        p_over = sum(p for t, p in totals.items() if t >= 3)
        p_under = 1.0 - p_over
        for bt, prob in [('over', p_over), ('under', p_under)]:
            market_odds = odds.get(f'o2.5' if bt == 'over' else f'u2.5', 0)
            if not market_odds:
                continue
            ev = expected_value(prob, market_odds)
            if ev >= min_ev:
                label = '大2.5球' if bt == 'over' else '小2.5球'
                value_bets.append({
                    'match': match_key, 'home': pred['home'], 'away': pred['away'],
                    'date': pred.get('date', ''), 'category': '总进球数',
                    'bet_type': bt, 'bet_label': label,
                    'pred_prob': prob, 'market_odds': market_odds, 'ev': ev,
                })
    return sorted(value_bets, key=lambda x: -x['ev'])


def find_value_bets_score(predictions, min_ev=0.05):
    """比分价值投注 (高赔, 阈值提高到5%)"""
    value_bets = []
    for pred in predictions:
        match_key = f"{pred['home']}_vs_{pred['away']}"
        odds = MARKET_SCORE.get(match_key)
        if not odds or 'score_distribution' not in pred:
            continue
        for score, market_odds in odds.items():
            pred_prob = pred['score_distribution'].get(score, 0)
            ev = expected_value(pred_prob, market_odds)
            if ev >= min_ev:
                value_bets.append({
                    'match': match_key, 'home': pred['home'], 'away': pred['away'],
                    'date': pred.get('date', ''), 'category': '比分',
                    'bet_type': score, 'bet_label': f"比分 {score}",
                    'pred_prob': pred_prob, 'market_odds': market_odds, 'ev': ev,
                })
    return sorted(value_bets, key=lambda x: -x['ev'])


def find_all_value_bets(predictions, min_ev=0.03):
    """聚合所有玩法, 返回 {category: [bets]}"""
    return {
        '胜平负': find_value_bets_spf(predictions, min_ev),
        '让球胜平负': find_value_bets_handicap(predictions, min_ev),
        '总进球数': find_value_bets_total(predictions, min_ev),
        '比分': find_value_bets_score(predictions, max(min_ev, 0.05)),
    }


def generate_singles(value_bets, max_bets=5):
    """生成单场投注方案"""
    return value_bets[:max_bets]


def generate_parlays(value_bets, max_legs=3, same_day=True):
    """生成串关方案 (2串1, 3串1)

    same_day=True: 只组合同天比赛 (小组赛规则)
    same_day=False: 只组合同周比赛 (淘汰赛规则)
    """
    # 按日期/周分组
    groups = defaultdict(list)
    for vb in value_bets:
        if same_day:
            # 按日期分组
            date = vb['date'][:10] if vb['date'] else 'unknown'
            groups[date].append(vb)
        else:
            # 按周分组 (ISO week)
            try:
                d = datetime.strptime(vb['date'][:10], '%Y-%m-%d')
                week = d.strftime('%Y-W%W')
            except:
                week = 'unknown'
            groups[week].append(vb)

    parlays = []
    for group_key, bets in groups.items():
        if len(bets) < 2:
            continue

        n = len(bets)
        # 2串1
        for i in range(n):
            for j in range(i + 1, n):
                b1, b2 = bets[i], bets[j]
                combined_odds = b1['market_odds'] * b2['market_odds']
                combined_prob = b1['pred_prob'] * b2['pred_prob']
                ev = combined_prob * combined_odds - 1.0
                var = combined_prob * (1 - combined_prob) * (combined_odds ** 2)
                score = ev / (math.sqrt(var) + 0.01)  # Sharpe-like ratio
                parlays.append({
                    'type': '2串1',
                    'legs': [b1, b2],
                    'combined_odds': round(combined_odds, 2),
                    'combined_prob': round(combined_prob, 4),
                    'ev': round(ev, 4),
                    'sharpe': round(score, 3),
                    'group': group_key,
                })

        # 3串1
        if max_legs >= 3 and n >= 3:
            for i in range(n):
                for j in range(i + 1, n):
                    for k in range(j + 1, n):
                        b1, b2, b3 = bets[i], bets[j], bets[k]
                        combined_odds = b1['market_odds'] * b2['market_odds'] * b3['market_odds']
                        combined_prob = b1['pred_prob'] * b2['pred_prob'] * b3['pred_prob']
                        ev = combined_prob * combined_odds - 1.0
                        var = combined_prob * (1 - combined_prob) * (combined_odds ** 2)
                        score = ev / (math.sqrt(var) + 0.01)
                        parlays.append({
                            'type': '3串1',
                            'legs': [b1, b2, b3],
                            'combined_odds': round(combined_odds, 2),
                            'combined_prob': round(combined_prob, 4),
                            'ev': round(ev, 4),
                            'sharpe': round(score, 3),
                            'group': group_key,
                        })

    # 按sharpe排序 (平衡概率×收益)
    parlays.sort(key=lambda x: -x['sharpe'])
    # 精确过滤：只返回 leg 数 == max_legs 的组合
    return [p for p in parlays if len(p['legs']) == max_legs]


def generate_strategies(value_bets, is_group_stage=True):
    """生成三套策略: 保守 / 均衡 / 激进"""
    strategies = {}

    # 按 EV 分组
    high_confidence = [b for b in value_bets if b['pred_prob'] > 0.55]  # 高置信度
    medium_confidence = [b for b in value_bets if 0.35 <= b['pred_prob'] <= 0.55]
    all_bets = value_bets

    # --- 策略1: 保守型 (高置信度单关, 宁愿少赚不冒险) ---
    singles = generate_singles(high_confidence, 5)
    parlays_2 = generate_parlays(high_confidence, 2, same_day=is_group_stage)[:3]
    parlays_3 = generate_parlays(high_confidence, 3, same_day=is_group_stage)[:2]
    strategies['conservative'] = {
        'name': '保守型 🛡️',
        'desc': '只选高置信度(>55%)单关+2串1, 稳字当头',
        'singles': singles,
        'parlays_2': parlays_2,
        'parlays_3': parlays_3,
    }

    # --- 策略2: 均衡型 (平衡收益与风险) ---
    singles2 = generate_singles(all_bets, 5)
    parlays2_2 = generate_parlays(all_bets, 2, same_day=is_group_stage)[:4]
    parlays2_3 = generate_parlays(all_bets, 3, same_day=is_group_stage)[:3]
    strategies['balanced'] = {
        'name': '均衡型 ⚖️',
        'desc': '全部价值投注参与, 2串1为主 + 精选3串1',
        'singles': singles2,
        'parlays_2': parlays2_2,
        'parlays_3': parlays2_3,
    }

    # --- 策略3: 激进型 (追求高回报) ---
    high_return = [b for b in all_bets if b['ev'] > 0.10]
    parlays3_2 = generate_parlays(high_return, 2, same_day=is_group_stage)[:3]
    parlays3_3 = generate_parlays(high_return, 3, same_day=is_group_stage)[:3]
    strategies['aggressive'] = {
        'name': '激进型 🚀',
        'desc': '只选高EV(>10%)场次, 3串1博高赔',
        'singles': generate_singles(high_return, 3),
        'parlays_2': parlays3_2,
        'parlays_3': parlays3_3,
    }

    return strategies


_BET_LABELS = {
    'home': '主胜', 'draw': '平局', 'away': '客胜',
    'over': '大球', 'under': '小球',
    'over25': '大2.5', 'under25': '小2.5',
}

def format_strategy(strategy):
    """格式化输出一套策略"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"  {strategy['name']}")
    lines.append(f"  {strategy['desc']}")
    lines.append(f"{'='*60}")

    if strategy['singles']:
        lines.append(f"\n📌 单关推荐 ({len(strategy['singles'])}场):")
        for i, b in enumerate(strategy['singles'], 1):
            bet_cn = _BET_LABELS.get(b['bet_type'], b.get('bet_label', b['bet_type']))
            lines.append(f"  {i}. {b['home']} vs {b['away']} → {bet_cn}")
            lines.append(f"     预测概率:{b['pred_prob']*100:.1f}%  赔率:{b['market_odds']}  EV:{b['ev']*100:+.1f}%")

    if strategy['parlays_2']:
        lines.append(f"\n🔗 2串1推荐 ({len(strategy['parlays_2'])}组):")
        for i, p in enumerate(strategy['parlays_2'][:3], 1):
            legs_desc = " + ".join(
                f"{l['home']}vs{l['away']}({l['market_odds']})"
                for l in p['legs']
            )
            lines.append(f"  {i}. {legs_desc}")
            lines.append(f"     综合赔率:{p['combined_odds']}  胜率:{p['combined_prob']*100:.1f}%  EV:{p['ev']*100:+.1f}%")

    if strategy['parlays_3']:
        lines.append(f"\n🔗 3串1推荐 ({len(strategy['parlays_3'])}组):")
        for i, p in enumerate(strategy['parlays_3'][:2], 1):
            legs_desc = " + ".join(
                f"{l['home']}vs{l['away']}({l['market_odds']})"
                for l in p['legs']
            )
            lines.append(f"  {i}. {legs_desc}")
            lines.append(f"     综合赔率:{p['combined_odds']}  胜率:{p['combined_prob']*100:.1f}%  EV:{p['ev']*100:+.1f}%")

    return '\n'.join(lines)


def _get_target_date():
    """获取竞彩目标日期: 明天(北京时区 UTC+8)"""
    from datetime import timezone, timedelta as td
    beijing_tz = timezone(td(hours=8))
    now_bj = datetime.now(beijing_tz)
    target = now_bj + timedelta(days=1)
    return target.strftime('%Y-%m-%d')


def _get_target_week():
    """获取竞彩目标周 (ISO week, 用于淘汰赛)"""
    now = datetime.now()
    target = now + timedelta(days=7)  # 下周
    return target.strftime('%Y-W%W')


def run():
    """主入口: 生成完整竞彩方案"""
    target_date = _get_target_date()
    print("=" * 60)
    print("  Mavis 竞彩策略引擎 v1.2")
    print(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  竞彩目标日: {target_date} (小组赛-明天)")
    print("=" * 60)

    # 加载预测
    data = load_predictions()
    predictions = data['matches']

    # 只保留目标日的比赛 (小组赛规则: 只赌明天)
    target_predictions = [
        p for p in predictions
        if p.get('stage') == 'group' and (p.get('date', '') or '')[:10] == target_date
    ]
    if not target_predictions:
        # 如果没有明天的比赛, 尝试用最近的未来比赛日
        from datetime import timezone, timedelta as td
        beijing_tz = timezone(td(hours=8))
        today_str = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        future_dates = sorted(set(
            (p.get('date', '') or '')[:10]
            for p in predictions
            if p.get('stage') == 'group' and (p.get('date', '') or '')[:10] >= today_str
        ))
        if future_dates:
            target_date = future_dates[0]
            target_predictions = [
                p for p in predictions
                if p.get('stage') == 'group' and (p.get('date', '') or '')[:10] == target_date
            ]
            print(f"  ⚠️ 明天无比赛, 改用最近比赛日: {target_date}")
        else:
            print("  ⚠️ 无未来比赛可投注")

    print(f"  目标比赛数: {len(target_predictions)} 场")

    # 找所有玩法价值投注 (只从目标日比赛中找)
    print("\n🔍 扫描全部玩法价值投注...")
    all_value_bets = find_all_value_bets(target_predictions, min_ev=0.03)

    total_count = sum(len(v) for v in all_value_bets.values())
    print(f"  找到 {total_count} 个正期望值投注机会:")
    for cat, bets in all_value_bets.items():
        if bets:
            print(f"    {cat}: {len(bets)} 个")

    # 展示各玩法 Top picks
    for cat, bets in all_value_bets.items():
        if not bets:
            continue
        print(f"\n📊 {cat} Top 5:")
        for i, b in enumerate(bets[:5], 1):
            label = b.get('bet_label', b.get('bet_type', '?'))
            print(f"  {i:2d}. {b['home']} vs {b['away']} → {label}")
            print(f"      概率:{b['pred_prob']*100:.1f}%  赔率:{b['market_odds']}  EV:{b['ev']*100:+.1f}%")

    # ===== 每个玩法类别各自生成策略 =====
    # (跨玩法不混合串关，同玩法内自由组合)
    category_strategies = {}
    cat_order = ['胜平负', '让球胜平负', '总进球数', '比分']
    for cat in cat_order:
        bets = all_value_bets.get(cat, [])
        if not bets:
            continue
        strategies = generate_strategies(bets, is_group_stage=True)
        category_strategies[cat] = strategies
        print(f"\n{'='*40}")
        print(f"  {cat} 策略")
        print(f"{'='*40}")
        for key in ['conservative', 'balanced', 'aggressive']:
            if key in strategies:
                print(format_strategy(strategies[key]))

    # 合并所有价值投注用于跨玩法汇总 (只用胜平负做串关)
    spf_bets = all_value_bets.get('胜平负', [])
    strategies = generate_strategies(spf_bets, is_group_stage=True)

    return all_value_bets, strategies, category_strategies


if __name__ == '__main__':
    value_bets, strategies = run()
