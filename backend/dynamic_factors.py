"""
Mavis PDP 动态因子层 (v2.2 - 校准版)

设计目标: 把 ranking_v2.py 里所有"硬编码关键词计数"逻辑抽出来, 让 30+ 因子
        都变成 weights 滑块可调, 贝叶斯可优化.

3 个动态因子族:
1. coach_bio_keywords  教练履历关键词 (U-20 世青赛冠军, 5届世界杯, 欧冠... 30+ 项)
2. player_bio_keywords 球员荣誉关键词 (U-20 世青赛, 世界杯4强功臣... 同源 substring 问题)
3. formation_tendency  阵型倾向 (4-3-3 vs 4-2-3-1 vs 3-4-3 对每队的 4 维影响)

每个因子 = {
    key: 字符串标识
    label: 中文标签 (UI 显示)
    pattern: regex 或 substring
    target: 适用对象 ('coach' / 'player_fw_mid' / 'player_def_gk' / 'all_players')
    base_score: 命中时加的基准分
    range: (min, max) 校准范围
    pitfall_note: 易踩的坑 (e.g. 'U-20 世青赛冠军' 包含 '世界杯冠军')
}
"""
import re
from copy import deepcopy

# ============================================================
# 1. 教练履历关键词 (30 项)
# ============================================================
COACH_KEYWORDS = {
    # === 大赛冠军 ===
    'wc_champion':        {'label': '世界杯冠军',     'pattern': r'(?<![U-u\-])(世界杯冠军|世界杯 冠军)',       'base': 50, 'range': (0, 100), 'pitfall': ''},
    'wc_finalist':       {'label': '世界杯亚军',     'pattern': r'(世界杯亚军|世界杯 亚军)',                   'base': 30, 'range': (0, 80),  'pitfall': ''},
    'wc_sf':             {'label': '世界杯4强',      'pattern': r'世界杯.{0,5}(4强|半决赛)',                   'base': 18, 'range': (0, 50),  'pitfall': ''},
    'wc_qf':             {'label': '世界杯8强',      'pattern': r'世界杯.{0,5}(8强|八强)',                     'base': 10, 'range': (0, 30),  'pitfall': ''},
    'u20_wc_champion':   {'label': 'U-20 世青赛冠军', 'pattern': r'U.?20.{0,3}世青赛冠军|世青赛冠军',           'base': 8,  'range': (0, 25),  'pitfall': '容易被 senior "世界杯冠军" substring 误触发'},
    'u17_wc_champion':   {'label': 'U-17 世少赛冠军', 'pattern': r'U.?17.{0,3}世少赛冠军|世少赛冠军',           'base': 6,  'range': (0, 20),  'pitfall': '同上'},
    'ec_champion':       {'label': '欧洲杯冠军',     'pattern': r'欧洲杯冠军|欧洲杯 冠军',                     'base': 40, 'range': (0, 80),  'pitfall': ''},
    'ec_finalist':       {'label': '欧洲杯亚军',     'pattern': r'欧洲杯.{0,5}(亚军|4强|半决赛)',               'base': 20, 'range': (0, 50),  'pitfall': ''},
    'camerica_champion': {'label': '美洲杯冠军',     'pattern': r'美洲杯冠军|美洲杯 冠军',                     'base': 35, 'range': (0, 70),  'pitfall': ''},
    'afcon_champion':    {'label': '非洲杯冠军',     'pattern': r'非洲杯冠军|非洲杯 冠军',                     'base': 30, 'range': (0, 60),  'pitfall': ''},
    'ac_champion':       {'label': '亚洲杯冠军',     'pattern': r'亚洲杯冠军|亚洲杯 冠军',                     'base': 25, 'range': (0, 50),  'pitfall': ''},
    # === 俱乐部冠军 ===
    'ucl_champion':      {'label': '欧冠冠军',       'pattern': r'欧冠冠军|欧冠联赛冠军',                       'base': 30, 'range': (0, 60),  'pitfall': ''},
    'uel_champion':      {'label': '欧联杯冠军',     'pattern': r'欧联杯冠军|欧罗巴联赛冠军',                   'base': 12, 'range': (0, 30),  'pitfall': ''},
    'cwc_champion':      {'label': '世俱杯冠军',     'pattern': r'世俱杯冠军|世俱杯 冠军',                     'base': 10, 'range': (0, 25),  'pitfall': ''},
    # === 履历届数 ===
    'wc_5plus':          {'label': '5届+世界杯/欧洲杯', 'pattern': r'(5届|5 次|五次).{0,5}(世界杯|欧洲杯)',     'base': 50, 'range': (0, 100), 'pitfall': ''},
    'wc_4':              {'label': '4届世界杯/欧洲杯', 'pattern': r'(4届|4 次|四次).{0,5}(世界杯|欧洲杯)',      'base': 35, 'range': (0, 80),  'pitfall': ''},
    'wc_3':              {'label': '3届世界杯/欧洲杯', 'pattern': r'(3届|3 次|三次).{0,5}(世界杯|欧洲杯)',      'base': 25, 'range': (0, 60),  'pitfall': ''},
    'wc_2':              {'label': '2届世界杯/欧洲杯', 'pattern': r'(2届|2 次|两次).{0,5}(世界杯|欧洲杯)',      'base': 15, 'range': (0, 40),  'pitfall': ''},
    'wc_1':              {'label': '1届世界杯/欧洲杯', 'pattern': r'(1届|1 次|一次).{0,5}(世界杯|欧洲杯)',      'base': 8,  'range': (0, 25),  'pitfall': ''},
    # === 个人荣誉 ===
    'best_coach_award':  {'label': '最佳教练/年度最佳', 'pattern': r'年度最佳教练|最佳教练|FIFA Best',          'base': 10, 'range': (0, 30),  'pitfall': ''},
    'best_player_coach': {'label': '执教过金球/先生',  'pattern': r'金球奖|世界足球先生',                         'base': 8,  'range': (0, 25),  'pitfall': ''},
    # === 联赛冠军 ===
    'league_champ_n':    {'label': '联赛冠军 (N次累加)', 'pattern': r'(联赛冠军|英超冠军|西甲冠军|德甲冠军|意甲冠军|法甲冠军)', 'base': 3, 'range': (0, 12), 'pitfall': 'substring 累加, 一个教练多次联赛冠军会重复计分'},
    # === 阵型/战术 ===
    'tactic_433':        {'label': '惯用 4-3-3',      'pattern': r'4-3-3|433',                                  'base': 4,  'range': (0, 15),  'pitfall': 'BIO 文本里出现 1 次就 +4'},
    'tactic_352':        {'label': '惯用 3-5-2',      'pattern': r'3-5-2|352',                                  'base': 4,  'range': (0, 15),  'pitfall': ''},
    'tactic_4231':       {'label': '惯用 4-2-3-1',    'pattern': r'4-2-3-1|4231',                               'base': 4,  'range': (0, 15),  'pitfall': ''},
    # === 任期 ===
    'tenure_long':       {'label': '任期 5+ 年',       'pattern': r'(5\+ ?年|5 年|5年|六载|七载|八载|九载|十载|201[0-9]年起|2020 年起)', 'base': 8, 'range': (0, 25), 'pitfall': 'regex 较复杂, 容易漏匹配'},
    'tenure_short':      {'label': '任期 <1 年',       'pattern': r'(临时|代理|救火|0[0-9]天|新任)',              'base': -10, 'range': (-30, 0),'pitfall': '负分惩罚'},
    # === 战绩 ===
    'undefeated_long':   {'label': '长期不败 (30+ 场)', 'pattern': r'(30\+ ?场不败|连续 \d+ 场不败|不败纪录)',  'base': 12, 'range': (0, 30),  'pitfall': ''},
    'win_streak_long':   {'label': '连胜 10+ 场',      'pattern': r'(10\+ ?连胜|连胜纪录)',                      'base': 8,  'range': (0, 25),  'pitfall': ''},
    'high_win_rate':     {'label': '胜率 70%+',        'pattern': r'(70%|七成|胜率.{0,3}高)',                    'base': 6,  'range': (0, 20),  'pitfall': ''},
}


# ============================================================
# 2. 球员 bio 关键词 (15 项, 主要荣誉字段)
# ============================================================
PLAYER_KEYWORDS = {
    'wc_champion_player':   {'label': '世界杯冠军',         'pattern': r'(?<![U-u\-])(世界杯冠军|世界杯 冠军)', 'base': 50, 'range': (0, 100), 'pitfall': ''},
    'wc_finalist_player':   {'label': '世界杯亚军',         'pattern': r'(世界杯亚军|世界杯 亚军)',              'base': 30, 'range': (0, 80),  'pitfall': ''},
    'wc_sf_player':         {'label': '世界杯4强',          'pattern': r'世界杯.{0,5}(4强|半决赛)',              'base': 15, 'range': (0, 40),  'pitfall': ''},
    'wc_qf_player':         {'label': '世界杯8强',          'pattern': r'世界杯.{0,5}(8强|八强)',                'base': 8,  'range': (0, 25),  'pitfall': ''},
    'u20_wc_champion_pl':   {'label': 'U-20 世青赛冠军',     'pattern': r'U.?20.{0,3}世青赛冠军|世青赛冠军',      'base': 6,  'range': (0, 20),  'pitfall': '同 ranking_v2 一样, substring 误触发'},
    'u17_wc_champion_pl':   {'label': 'U-17 世少赛冠军',     'pattern': r'U.?17.{0,3}世少赛冠军|世少赛冠军',      'base': 4,  'range': (0, 15),  'pitfall': '同上'},
    'ec_champion_player':   {'label': '欧洲杯冠军',         'pattern': r'欧洲杯冠军',                            'base': 30, 'range': (0, 80),  'pitfall': ''},
    'camerica_champ_pl':    {'label': '美洲杯冠军',         'pattern': r'美洲杯冠军',                            'base': 25, 'range': (0, 60),  'pitfall': ''},
    'afcon_champ_pl':       {'label': '非洲杯冠军',         'pattern': r'非洲杯冠军',                            'base': 20, 'range': (0, 50),  'pitfall': ''},
    'ac_champ_pl':          {'label': '亚洲杯冠军',         'pattern': r'亚洲杯冠军',                            'base': 15, 'range': (0, 40),  'pitfall': ''},
    'ucl_champ_player':     {'label': '欧冠冠军',           'pattern': r'欧冠冠军',                              'base': 25, 'range': (0, 60),  'pitfall': ''},
    'uel_champ_player':     {'label': '欧联杯冠军',         'pattern': r'欧联杯冠军|欧罗巴联赛冠军',              'base': 10, 'range': (0, 25),  'pitfall': ''},
    'golden_boot':          {'label': '金靴奖',             'pattern': r'金靴',                                  'base': 8,  'range': (0, 20),  'pitfall': 'substring 误触: 金靴奖+世青赛金靴都加'},
    'mvp':                  {'label': 'MVP / 最佳球员',     'pattern': r'(MVP|最佳球员)',                        'base': 6,  'range': (0, 18),  'pitfall': ''},
    'league_champ_player':  {'label': '联赛冠军',           'pattern': r'(联赛冠军|英超冠军|西甲冠军|德甲冠军|意甲冠军|法甲冠军)', 'base': 5, 'range': (0, 15), 'pitfall': '多次联赛冠军累加'},
}


# ============================================================
# 3. 阵型倾向 (3 阵型 × 4 位置影响 = 12 因子)
# ============================================================
# 每种阵型对 4 维分的影响系数 (fw / mid / def / gk)
# 默认 1.0 = 不影响, >1 = 加权, <1 = 减权
FORMATION_TENDENCY = {
    # === 4-3-3 阵型 (主流, 攻守平衡) ===
    '433_fw_weight':  {'label': '4-3-3 锋线权重',     'base': 1.00, 'range': (0.7, 1.5)},
    '433_mid_weight': {'label': '4-3-3 中场权重',     'base': 1.05, 'range': (0.7, 1.5)},
    '433_def_weight': {'label': '4-3-3 后卫权重',     'base': 1.00, 'range': (0.7, 1.5)},
    '433_gk_weight':  {'label': '4-3-3 门将权重',     'base': 1.00, 'range': (0.7, 1.5)},
    # === 4-2-3-1 阵型 (中场密集) ===
    '4231_fw_weight':  {'label': '4-2-3-1 锋线权重',   'base': 1.00, 'range': (0.7, 1.5)},
    '4231_mid_weight': {'label': '4-2-3-1 中场权重',   'base': 1.15, 'range': (0.8, 1.6)},
    '4231_def_weight': {'label': '4-2-3-1 后卫权重',   'base': 0.95, 'range': (0.7, 1.4)},
    '4231_gk_weight':  {'label': '4-2-3-1 门将权重',   'base': 1.00, 'range': (0.7, 1.5)},
    # === 3-4-3 阵型 (激进进攻) ===
    '343_fw_weight':  {'label': '3-4-3 锋线权重',     'base': 1.15, 'range': (0.8, 1.6)},
    '343_mid_weight': {'label': '3-4-3 中场权重',     'base': 1.10, 'range': (0.8, 1.5)},
    '343_def_weight': {'label': '3-4-3 后卫权重',     'base': 0.85, 'range': (0.6, 1.3)},
    '343_gk_weight':  {'label': '3-4-3 门将权重',     'base': 1.00, 'range': (0.7, 1.5)},
}


# ============================================================
# 默认 weights (和 schema 兼容)
# ============================================================
def default_weights():
    """返回默认动态因子权重 (每个 = base * 1.0)"""
    weights = {}
    for k, v in COACH_KEYWORDS.items():
        weights[k] = float(v['base'])
    for k, v in PLAYER_KEYWORDS.items():
        weights[k] = float(v['base'])
    for k, v in FORMATION_TENDENCY.items():
        weights[k] = float(v['base'])
    return weights


# ============================================================
# 范围表 (供后端 validate 用)
# ============================================================
def ranges():
    """返回每个因子的 (min, max) 范围"""
    r = {}
    for k, v in COACH_KEYWORDS.items():
        r[k] = v['range']
    for k, v in PLAYER_KEYWORDS.items():
        r[k] = v['range']
    for k, v in FORMATION_TENDENCY.items():
        r[k] = v['range']
    return r


def all_factors_meta():
    """返回所有因子的元数据 (UI 用): {key: {label, base, range, group, pitfall}}"""
    meta = {}
    for k, v in COACH_KEYWORDS.items():
        meta[k] = {**v, 'group': 'coach_bio', 'key': k}
    for k, v in PLAYER_KEYWORDS.items():
        meta[k] = {**v, 'group': 'player_bio', 'key': k}
    for k, v in FORMATION_TENDENCY.items():
        meta[k] = {**v, 'group': 'formation', 'key': k, 'pattern': '', 'pitfall': ''}
    return meta


# ============================================================
# 核心计算函数
# ============================================================
def score_coach_bio(coach, weights):
    """根据教练 bio + 当前 weights 算动态分

    coach: dict 来自 world_cup_2026_coaches.csv
    weights: dict, key 是 COACH_KEYWORDS, value 是当前权重

    返回 (score, details_list)
    """
    if not coach:
        return 0, []
    text = str(coach.get('代表执教生涯', '')) + ' ' + str(coach.get('重大荣誉', ''))
    score = 0
    details = []
    for key, meta in COACH_KEYWORDS.items():
        w = weights.get(key, meta['base'])
        if w == 0:
            continue
        try:
            if re.search(meta['pattern'], text):
                score += w
                details.append(f"{meta['label']} +{w:.0f}")
        except re.error:
            # regex 错误回退到 substring
            if meta['pattern'].replace('\\', '') in text:
                score += w
                details.append(f"{meta['label']} +{w:.0f} (substr)")
    return score, details


def score_player_bio(player, weights):
    """根据球员 bio + 当前 weights 算动态分 (后卫/门将用)"""
    if not player:
        return 0, []
    honors = str(player.get('主要荣誉', ''))
    if not honors:
        return 0, []
    score = 0
    details = []
    for key, meta in PLAYER_KEYWORDS.items():
        w = weights.get(key, meta['base'])
        if w == 0:
            continue
        try:
            if re.search(meta['pattern'], honors):
                score += w
                details.append(f"{meta['label']} +{w:.0f}")
        except re.error:
            if meta['pattern'].replace('\\', '') in honors:
                score += w
                details.append(f"{meta['label']} +{w:.0f} (substr)")
    return score, details


def apply_formation_weights(fw, mid, def_, gk, weights, formation='433'):
    """对 4 维分应用阵型倾向权重

    formation: '433' / '4231' / '343'
    返回 (fw', mid', def_', gk')
    """
    prefix = formation.replace('-', '')
    fw_w = weights.get(f'{prefix}_fw_weight', 1.0)
    mid_w = weights.get(f'{prefix}_mid_weight', 1.0)
    def_w = weights.get(f'{prefix}_def_weight', 1.0)
    gk_w = weights.get(f'{prefix}_gk_weight', 1.0)
    return fw * fw_w, mid * mid_w, def_ * def_w, gk * gk_w


# ============================================================
# 团队阵型识别 (从教练履历自动 detect)
# ============================================================
def detect_coach_formation(coach):
    """从教练 bio 文本中识别最常用的阵型
    返回 '433' / '4231' / '343' / 'unknown'
    """
    if not coach:
        return 'unknown'
    text = str(coach.get('代表执教生涯', '')) + ' ' + str(coach.get('重大荣誉', '')) + ' ' + str(coach.get('惯用阵型', ''))
    counts = {
        '433':  len(re.findall(r'4-3-3|433', text)),
        '4231': len(re.findall(r'4-2-3-1|4231', text)),
        '343':  len(re.findall(r'3-4-3|343', text)),
        '352':  len(re.findall(r'3-5-2|352', text)),
        '442':  len(re.findall(r'4-4-2|442', text)),
    }
    best = max(counts.items(), key=lambda x: x[1])
    if best[1] == 0:
        return 'unknown'
    return best[0]


# ============================================================
# 调试入口
# ============================================================
if __name__ == '__main__':
    print(f"=== Mavis PDP 动态因子 v2.2 ===")
    print(f"教练关键词: {len(COACH_KEYWORDS)} 项")
    print(f"球员关键词: {len(PLAYER_KEYWORDS)} 项")
    print(f"阵型倾向:   {len(FORMATION_TENDENCY)} 项 (3 阵型 × 4 位置)")
    print(f"总因子:     {len(COACH_KEYWORDS) + len(PLAYER_KEYWORDS) + len(FORMATION_TENDENCY)} 项")

    # 测试默认权重
    w = default_weights()
    print(f"\n默认权重示例:")
    print(f"  wc_champion = {w['wc_champion']}")
    print(f"  u20_wc_champion = {w['u20_wc_champion']} (U-20 世青赛冠军)")
    print(f"  433_mid_weight = {w['433_mid_weight']}")

    # 测试 coach 评分
    test_coach = {
        '代表执教生涯': '曾执教 5 届世界杯, 4-3-3 阵型, 获得欧冠冠军',
        '重大荣誉': '世界杯冠军, FIFA 最佳教练',
    }
    score, details = score_coach_bio(test_coach, w)
    print(f"\n测试教练评分: {score} 分")
    for d in details:
        print(f"  - {d}")

    # 测试 pitfall
    pitfall_coach = {
        '代表执教生涯': 'U-20 世青赛冠军教头, 也带过世青赛亚军队',
        '重大荣誉': '',
    }
    score, details = score_coach_bio(pitfall_coach, w)
    print(f"\n测试 pitfall (U-20 不应误触发 senior 冠军): {score} 分")
    for d in details:
        print(f"  - {d}")
