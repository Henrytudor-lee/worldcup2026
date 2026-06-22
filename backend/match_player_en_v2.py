"""
严格匹配: 中文名 → ESPN 英文名 (用 pypinyin + 编辑距离)
不用启发式打分, 用严格编辑距离阈值.
"""
import csv, json, os, re
from collections import defaultdict
from pypinyin import lazy_pinyin, Style
from datetime import date, datetime


CN_FROM_EN = {
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

TODAY = date(2026, 6, 15)


def edit_distance(s1, s2, max_dist=99):
    """Levenshtein distance, early exit if > max_dist"""
    if abs(len(s1) - len(s2)) > max_dist:
        return max_dist + 1
    if len(s1) == 0: return len(s2)
    if len(s2) == 0: return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[-1] + 1, prev[j + 1] + 1, prev[j] + cost))
            if curr[-1] > max_dist:
                return max_dist + 1
        prev = curr
    return prev[-1]


def cn_to_pinyin(name):
    """梅西·内马尔 → ['mei', 'xi', '·', 'na', 'er', 'ma', 'er'] → 处理后返回 token 数组"""
    tokens = re.split(r'([·\s])', name)
    result = []
    for t in tokens:
        if not t or t == '·' or t.isspace():
            if t == '·': result.append('·')
            continue
        # 中文部分 → 拼音
        if re.match(r'[\u4e00-\u9fff]', t):
            py = lazy_pinyin(t, style=Style.NORMAL)
            result.extend(py)
        else:
            # 已有英文/特殊 → 直接保留
            result.append(t)
    return result


def get_cn_tokens(name):
    """返回 (first_pinyin_str, last_pinyin_str) 或 (None, None)"""
    parts = re.split(r'[·]', name)
    if len(parts) < 2:
        # 单 part, last = 整个, first = 整个 (按欧洲格式 firstName lastName)
        last = ''.join(lazy_pinyin(parts[0], style=Style.NORMAL))
        first = last
        return first, last
    # 中文是 [姓][名] 结构, 但欧洲人反过来
    # 通用判断: 较短的部分是姓, 较长的部分是名
    # 例: "梅西" → "梅" = 姓, "西" = 名 → 但这是单字双字
    # 例: "穆罕默德·萨拉赫" → "穆罕默德" 4字 = 名, "萨拉赫" 3字 = 姓
    # 例: "拉斐尔·莱昂" → "拉斐尔" 3字 = 名, "莱昂" 2字 = 姓
    if len(parts[0]) >= len(parts[1]):
        first = ''.join(lazy_pinyin(parts[0], style=Style.NORMAL))
        last = ''.join(lazy_pinyin(parts[1], style=Style.NORMAL))
    else:
        first = ''.join(lazy_pinyin(parts[1], style=Style.NORMAL))
        last = ''.join(lazy_pinyin(parts[0], style=Style.NORMAL))
    return first, last


def load_espn_by_team():
    out = defaultdict(list)
    for fname in os.listdir('1_数据基础/espn_match_data'):
        if not fname.endswith('.json'): continue
        with open(f'1_数据基础/espn_match_data/{fname}') as f:
            d = json.load(f)
        for r in d.get('rosters', []):
            team_en = r.get('team', {}).get('displayName', '')
            team_cn = CN_FROM_EN.get(team_en, team_en)
            for p in r.get('roster', []):
                n = p.get('athlete', {}).get('displayName', '')
                if n: out[team_cn].append(n)
    # 去重保序
    for k in out:
        out[k] = list(dict.fromkeys(out[k]))
    return dict(out)


def load_cache():
    if not os.path.exists('1_数据基础/age_found_web.json'): return {}
    with open('1_数据基础/age_found_web.json') as f:
        raw = json.load(f)
    out = {}
    for x in raw:
        if isinstance(x, list) and len(x) >= 3:
            c, n, dob = x[0], x[1], x[2]
            if isinstance(dob, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
                out[(c, n)] = dob
    return out


def calc_age(dob_str):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))


def main():
    espn = load_espn_by_team()
    cache = load_cache()

    with open('1_数据基础/world_cup_2026_complete.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    matched_count = 0
    aged_count = 0
    ambiguous = []
    no_match = []

    # 记录每个主表行匹配到的英文名
    matches = {}

    for r in rows:
        team = r['国家']
        cn_name = r['球员']
        if team not in espn or not espn[team]:
            continue
        cn_first, cn_last = get_cn_tokens(cn_name)
        if not cn_first or not cn_last:
            continue

        # 找 lastName 编辑距离 ≤ 2 的所有候选
        candidates = []
        for en in espn[team]:
            en_words = en.split()
            if len(en_words) < 2: continue
            en_last = en_words[-1].lower()
            d = edit_distance(cn_last, en_last, max_dist=2)
            if d <= 2:
                candidates.append((d, en, en_words))

        if not candidates:
            no_match.append((team, cn_name))
            continue

        # 按 last 距离排序, 二次用 first name
        candidates.sort(key=lambda x: x[0])
        # 如果有多个候选且 first 距离都小, 用 first 二次过滤
        if len(candidates) > 1:
            best_first_d = 99
            best_en = None
            for d_last, en, en_words in candidates:
                en_first = en_words[0].lower()
                d_first = edit_distance(cn_first, en_first, max_dist=3)
                if d_first < best_first_d:
                    best_first_d = d_first
                    best_en = en
            if best_en and best_first_d <= 3:
                candidates = [(d, e, w) for d, e, w in candidates if e == best_en]
            else:
                # first name 也无法判断 → 跳过 (ambiguous)
                ambiguous.append((team, cn_name, [c[1] for c in candidates]))
                continue

        # 只剩 1 个候选
        if len(candidates) == 1:
            _, best_en, _ = candidates[0]
            matches[(team, cn_name)] = best_en
            matched_count += 1
            # 查 cache
            key = (team, best_en)
            if key in cache:
                age = calc_age(cache[key])
                if 16 <= age <= 45:
                    r['年龄'] = str(age)
                    aged_count += 1

    print(f'主表 1248 个球员:')
    print(f'  启发式匹配成功: {matched_count}')
    print(f'  通过 cache 拿年龄: {aged_count}')
    print(f'  无匹配 (跳过): {len(no_match)}')
    print(f'  歧义 (跳过): {len(ambiguous)}')

    # 写回 (不改 player_en 字段, 因为上一轮已回滚)
    # 但要在缓存里追加主表 → 英文映射关系, 供后续手工/查维基用
    print(f'\n=== 歧义样本 (前 15) ===')
    for team, cn, candidates in ambiguous[:15]:
        print(f'  {team:<6} {cn:<18} 候选={candidates}')

    print(f'\n=== 无匹配样本 (前 15) ===')
    for team, cn in no_match[:15]:
        print(f'  {team:<6} {cn}')


if __name__ == '__main__':
    main()