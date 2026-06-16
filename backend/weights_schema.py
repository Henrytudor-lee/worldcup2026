"""
Mavis PDP weights schema (v2.1)
- 6 类 16 系数：用户通过前端滑块调整
- 数值范围 + 默认值集中在这里，方便后端校验
"""
from copy import deepcopy

# 默认权重（来自 5_算法/weights_v21.json + 一些实操校正）
DEFAULT = {
    "position_top_n": {
        "FW": 3,        # 前锋取 Top N
        "MID": 3,       # 中场取 Top N
        "DEF": 4,       # 后卫取 Top N
        "GK": 1,        # 门将取 Top N
    },
    "status_weights": {
        "g_per_goal": 40,        # 本赛季进 1 球的贡献 = 1/40
        "a_per_assist": 60,      # 本赛季 1 助攻 = 1/60
        "who_bonus_base": 6.5,   # WhoScored 评分基准
        "who_bonus_denom": 4,    # WhoScored 加权分母
    },
    "nat_intl": {
        "g_per_goal": 400,       # 国家队 1 球 = 1/400 (v2.1 调小, 状态数据权重更高)
        "a_per_assist": 600,     # 国家队 1 助 = 1/600
    },
    "def_gk_weights": {
        "base_factor": 0.75,     # 后卫/门身价基础系数 (v2.2.4 0.95→0.75, 修'身价压制过度')
        "honors_per_champ": 15,  # 荣誉每个冠军加权
        "wc_per_ga": 100,        # 世界杯/欧战 1 场/球 = 1/100
    },
    "player_to_total": {
        "player_share": 0.70,    # 球员占比
        "coach_share": 0.30,     # 教练占比
    },
    "smoothing": {
        "player_div": 5000,      # 球员分平滑分母
        "coach_div": 100,        # 教练分平滑分母
        "rank_div": 1000,        # 总分平滑分母
    },
    "venue_weights": {
        "altitude_threshold": 2000,  # 海拔阈值 (米) - 超过则客队受罚
        "altitude_penalty": 0.90,    # 客队高原惩罚 (0.90 = -10%)
        "temp_threshold": 32,        # 温度阈值 (°C) - 超过则双方都受罚
        "temp_penalty": 0.97,        # 高温惩罚 (0.97 = -3%)
    },
    "venue_adaptation_weight": 0.8,  # 球员适应度调节强度 (v2.2.4 0.5→0.8, 让湿热气候真正起作用)
    "depth": {
        "squad_std_penalty": 0.20,    # 阵容标准差惩罚系数 (0=关闭, 0.3=强)
        "squad_std_threshold": 0.50,  # 超过此 std/mean 比例开始惩罚
    },
    "possession": {
        "rank_tier1": 0.62,  # 1-4 名 持球率
        "rank_tier2": 0.58,  # 5-8 名
        "rank_tier3": 0.53,  # 9-16 名
        "rank_tier4": 0.48,  # 17-32 名
        "rank_tier5": 0.43,  # 33-48 名
    },
    "lambda_cap": 2.8,  # λ 上限 (v2.2.4 3.2→2.8, 修 4 场'身价压制全平局'偏差)
    "draw_boost": 1.35,  # 平局概率加成 (v2.2.4, 1.0=不加权, 1.35=+35%; 修'身价压制过度')
}

# 范围约束（防止用户拖极端值）
RANGES = {
    "position_top_n": {
        "FW": (1, 6), "MID": (1, 6), "DEF": (1, 8), "GK": (1, 3),
    },
    "status_weights": {
        "g_per_goal": (10, 200),
        "a_per_assist": (10, 200),
        "who_bonus_base": (3.0, 10.0),
        "who_bonus_denom": (1, 20),
    },
    "nat_intl": {
        "g_per_goal": (50, 1000),
        "a_per_assist": (50, 1000),
    },
    "def_gk_weights": {
        "base_factor": (0.5, 1.5),
        "honors_per_champ": (0, 100),
        "wc_per_ga": (10, 1000),
    },
    "player_to_total": {
        "player_share": (0.0, 1.0),
        "coach_share": (0.0, 1.0),
    },
    "smoothing": {
        "player_div": (500, 50000),
        "coach_div": (10, 1000),
        "rank_div": (100, 10000),
    },
    "venue_weights": {
        "altitude_threshold": (500, 4000),
        "altitude_penalty": (0.5, 1.0),
        "temp_threshold": (15, 50),
        "temp_penalty": (0.5, 1.0),
    },
    "venue_adaptation_weight": (0.0, 1.0),
    "depth": {
        "squad_std_penalty": (0.0, 0.5),     # 0=关闭, 0.5=强惩罚
        "squad_std_threshold": (0.2, 1.0),   # std/mean 比例阈值
    },
    "possession": {
        "rank_tier1": (0.55, 0.75),
        "rank_tier2": (0.50, 0.70),
        "rank_tier3": (0.45, 0.65),
        "rank_tier4": (0.40, 0.60),
        "rank_tier5": (0.35, 0.55),
    },
    "lambda_cap": (2.5, 5.0),
    "draw_boost": (1.0, 2.0),  # 平局加权 (1.0=不加, 2.0=翻倍)
}

# 预设（前端 6 个 preset 按钮）
PRESETS = {
    "default": {
        "label": "默认（均衡）",
        "weights": deepcopy(DEFAULT),
    },
    "high_value": {
        "label": "身价优先 💰",
        "weights": {
            **deepcopy(DEFAULT),
            "status_weights": {
                "g_per_goal": 80, "a_per_assist": 100,  # 状态权重下调
                "who_bonus_base": 6.5, "who_bonus_denom": 8,
            },
        },
    },
    "high_form": {
        "label": "状态优先 🔥",
        "weights": {
            **deepcopy(DEFAULT),
            "status_weights": {
                "g_per_goal": 20, "a_per_assist": 30,  # 进球/助攻权重大
                "who_bonus_base": 6.0, "who_bonus_denom": 2,
            },
            "def_gk_weights": {**DEFAULT["def_gk_weights"], "base_factor": 1.10},  # 防守加权
        },
    },
    "low_value": {
        "label": "低身价 📉",
        "weights": {
            **deepcopy(DEFAULT),
            "def_gk_weights": {**DEFAULT["def_gk_weights"], "base_factor": 0.50},  # 身价影响减半
            "status_weights": {**DEFAULT["status_weights"], "g_per_goal": 25},  # 状态/进球权重 ↑
        },
    },
    "coach_heavy": {
        "label": "教练为王 👔",
        "weights": {
            **deepcopy(DEFAULT),
            "player_to_total": {"player_share": 0.30, "coach_share": 0.70},
        },
    },
    "balance_343": {
        "label": "3-4-3 阵型 ⚔️",
        "weights": {
            **deepcopy(DEFAULT),
            "position_top_n": {"FW": 3, "MID": 4, "DEF": 3, "GK": 1},
        },
    },
}


def validate(weights: dict) -> tuple[bool, str]:
    """校验 weights 在合理范围内。返回 (ok, msg)

    支持两种 RANGES 条目:
    - 嵌套 dict: 校验 {group: {field: number, ...}}
    - tuple: 校验顶层 number (e.g. 'venue_adaptation_weight': (0.0, 1.0))
    """
    if not isinstance(weights, dict):
        return False, "weights must be a dict"
    for group_key, group in RANGES.items():
        if group_key not in weights:
            return False, f"missing group: {group_key}"
        # 顶层 scalar 字段: 校验 number in range
        if isinstance(group, tuple) and len(group) == 2:
            lo, hi = group
            v = weights[group_key]
            if not isinstance(v, (int, float)):
                return False, f"{group_key} must be number, got {type(v).__name__}"
            if not (lo <= v <= hi):
                return False, f"{group_key}={v} out of range [{lo}, {hi}]"
            continue
        # 嵌套 dict 字段
        if not isinstance(weights[group_key], dict):
            return False, f"{group_key} must be a dict"
        for k, (lo, hi) in group.items():
            if k not in weights[group_key]:
                return False, f"missing {group_key}.{k}"
            v = weights[group_key][k]
            if not isinstance(v, (int, float)):
                return False, f"{group_key}.{k} must be number, got {type(v).__name__}"
            if not (lo <= v <= hi):
                return False, f"{group_key}.{k}={v} out of range [{lo}, {hi}]"
    # 球员 + 教练占比应 = 1
    ps = weights["player_to_total"]["player_share"]
    cs = weights["player_to_total"]["coach_share"]
    if abs(ps + cs - 1.0) > 0.001:
        return False, f"player_share + coach_share must = 1, got {ps + cs}"
    return True, "ok"


def merge_with_default(weights: dict) -> dict:
    """补全缺失字段为默认值. 支持嵌套 dict + 顶层 scalar 字段"""
    result = deepcopy(DEFAULT)
    if not isinstance(weights, dict):
        return result
    for gk, group in result.items():
        if gk not in weights:
            continue
        # 顶层 scalar 字段: 直接覆盖
        if isinstance(group, (int, float)):
            result[gk] = weights[gk]
            continue
        # 嵌套 dict 字段: 字段级合并
        if isinstance(weights[gk], dict):
            for k in group:
                if k in weights[gk]:
                    result[gk][k] = weights[gk][k]
    return result
