"""
启发式匹配 v3: 输出 (team, cn_name, en_name, score) 映射建议表
不动主表, 只生成候选清单让人工审核.
"""
import csv, json, os, re
from collections import defaultdict
from pypinyin import lazy_pinyin, Style


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


def load_espn_by_team():
    out = defaultdict(set)
    for fname in os.listdir('1_数据基础/espn_match_data'):
        if not fname.endswith('.json'): continue
        with open(f'1_数据基础/espn_match_data/{fname}') as f:
            d = json.load(f)
        for r in d.get('rosters', []):
            team_en = r.get('team', {}).get('displayName', '')
            team_cn = CN_FROM_EN.get(team_en, team_en)
            for p in r.get('roster', []):
                n = p.get('athlete', {}).get('displayName', '')
                if n: out[team_cn].add(n)
    return {k: sorted(v) for k, v in out.items()}


def get_cn_pinyin_parts(name):
    """梅西·内马尔 → ('meixi', 'neimaer')
       穆罕默德·萨拉赫 → ('muhamode', 'salahe')
       阿利松 → ('alisong', 'alisong')"""
    parts = re.split(r'[·]', name)
    def to_py(s):
        return ''.join(lazy_pinyin(s, style=Style.NORMAL))
    if len(parts) < 2:
        py = to_py(parts[0])
        return py, py
    py0 = to_py(parts[0])
    py1 = to_py(parts[1])
    return py0, py1


def score_match(cn_first_py, cn_last_py, en_name):
    """打分: 越高越匹配. 0 = 完全不像"""
    en_words = en_name.lower().split()
    if len(en_words) < 2: return 0
    en_first = en_words[0]
    en_last = en_words[-1]

    score = 0
    # 1) last name 拼音前缀 vs en last 前缀 (3 字符)
    if cn_last_py and en_last:
        # 完全包含?
        if en_last.startswith(cn_last_py[:3]) or cn_last_py.startswith(en_last[:3]):
            score += 5
        elif en_last[:2] == cn_last_py[:2]:
            score += 3
        elif en_last[0] == cn_last_py[0]:
            score += 1

    # 2) first name 拼音 vs en first
    if cn_first_py and en_first:
        if en_first.startswith(cn_first_py[:3]) or cn_first_py.startswith(en_first[:3]):
            score += 3
        elif en_first[:2] == cn_first_py[:2]:
            score += 2
        elif en_first[0] == cn_first_py[0]:
            score += 1

    # 3) 单字 first name (如 "西" → "si") 比对英文
    cn_first_chars = re.findall(r'[\u4e00-\u9fff]', cn_first_py if len(cn_first_py) < 6 else '')
    # skip this bonus

    # 4) 长度差惩罚
    if score >= 5:
        cn_last_len = len(cn_last_py)
        en_last_len = len(en_last)
        if abs(cn_last_len - en_last_len) > 5:
            score -= 1

    return score


def main():
    espn = load_espn_by_team()

    with open('1_数据基础/world_cup_2026_complete.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # 主表按 (team, cn_name) 索引
    main_by_team = defaultdict(list)
    for i, r in enumerate(rows):
        main_by_team[r['国家']].append((i, r['球员']))

    # 启发式匹配
    all_matches = []
    no_match = []
    for team, candidates in main_by_team.items():
        if team not in espn:
            no_match.extend([(team, cn) for _, cn in candidates])
            continue
        for i, cn_name in candidates:
            cn_first_py, cn_last_py = get_cn_pinyin_parts(cn_name)
            best_score = 0
            best_en = None
            second_best = 0
            for en in espn[team]:
                s = score_match(cn_first_py, cn_last_py, en)
                if s > best_score:
                    second_best = best_score
                    best_score = s
                    best_en = en
                elif s > second_best:
                    second_best = s

            if best_en and best_score >= 5 and best_score > second_best:
                # 唯一候选
                all_matches.append({
                    'team': team,
                    'cn_name': cn_name,
                    'en_name': best_en,
                    'score': best_score,
                    'second_best': second_best,
                    'row_idx': i,
                })
            else:
                no_match.append((team, cn_name))

    print(f'启发式匹配候选: {len(all_matches)}/{sum(len(v) for v in main_by_team.values())}')
    print(f'  无匹配: {len(no_match)}')

    # 按分数分组
    by_score = defaultdict(list)
    for m in all_matches:
        by_score[m['score']].append(m)

    for s in sorted(by_score.keys(), reverse=True):
        print(f'\n=== score={s}: {len(by_score[s])} 个 ===')
        for m in by_score[s][:10]:
            print(f"  {m['team']:<6} {m['cn_name']:<20} → {m['en_name']:<25} (2nd={m['second_best']})")
        if len(by_score[s]) > 10:
            print(f'  ... 共 {len(by_score[s])} 个')

    # 输出 JSON 给用户审
    with open('1_数据基础/heuristic_matches.json', 'w', encoding='utf-8') as f:
        json.dump({
            'matches': all_matches,
            'no_match': [{'team': t, 'cn_name': n} for t, n in no_match],
        }, f, ensure_ascii=False, indent=2)
    print(f'\n✅ 写入 1_数据基础/heuristic_matches.json')

    # 写"高置信度"子集 (score >= 7, second_best < 5)
    confident = [m for m in all_matches if m['score'] >= 7 and m['second_best'] < 5]
    print(f'\n⭐ 高置信度 (score>=7, 2nd<5): {len(confident)} 个')
    with open('1_数据基础/heuristic_confident.json', 'w', encoding='utf-8') as f:
        json.dump(confident, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()