"""
主表年龄最终修复: 启发式匹配 + cache 拿年龄
"""
import csv, json, re, os
from datetime import date, datetime
from pathlib import Path
import urllib.request

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
CSV = PROJECT / '1_数据基础' / 'world_cup_2026_complete.csv'
CACHE = PROJECT / '1_数据基础' / 'age_found_web.json'

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

PINYIN = {
    '阿':'a','埃':'a','艾':'a','安':'a','巴':'b','鲍':'b','贝':'b','比':'b','伯':'b','波':'b',
    '查':'c','陈':'c','程':'c','达':'d','戴':'d','德':'d','迪':'d','丹':'d','多':'d',
    '恩':'e','弗':'f','费':'f','法':'f','范':'f','福':'f','格':'g','戈':'g','古':'g','瓜':'g',
    '哈':'h','海':'h','汉':'h','霍':'h','胡':'h','华':'h','伊':'i','亚':'y','雅':'y','加':'j',
    '杰':'j','吉':'j','卡':'k','科':'k','凯':'k','库':'k','拉':'l','罗':'l','卢':'l','洛':'l',
    '吕':'l','莱':'l','朗':'l','马':'m','麦':'m','梅':'m','米':'m','曼':'m','穆':'m','纳':'n',
    '尼':'n','诺':'n','帕':'p','佩':'p','普':'p','乔':'q','萨':'s','桑':'s','塞':'s','施':'s',
    '斯':'s','苏':'s','塔':'t','特':'t','托':'t','瓦':'w','维':'w','文':'w','西':'x','谢':'x',
    '雅':'y','杨':'y','尤':'y','扎':'z','詹':'z','张':'z','朱':'z',
}

TODAY = date(2026, 6, 15)


def cn_tokens(name):
    return [t for t in re.split(r'[·\s]', name) if t]


def cn_pinyin_init(token):
    return ''.join(PINYIN.get(ch, '') for ch in token)


def match_score(cn_name, en_name):
    cn_tokens_list = cn_tokens(cn_name)
    en_words = en_name.split()
    if len(cn_tokens_list) < 2 or len(en_words) < 2:
        return 0
    cn_last = cn_pinyin_init(cn_tokens_list[-1])
    cn_first = cn_pinyin_init(cn_tokens_list[0])
    en_last = en_words[-1].lower()
    en_first = en_words[0].lower()
    score = 0
    if cn_last and en_last.startswith(cn_last[:2].lower()):
        score += 3
    elif cn_last and en_last.startswith(cn_last[0].lower()):
        score += 1
    if cn_first and en_first.startswith(cn_first[:2].lower()):
        score += 2
    elif cn_first and en_first.startswith(cn_first[0].lower()):
        score += 1
    return score


def load_espn_by_team():
    from collections import defaultdict
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


def load_cache():
    if not CACHE.exists(): return {}
    with open(CACHE) as f:
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

    with open(CSV, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    if 'player_en' not in fieldnames:
        fieldnames.append('player_en')

    matched_count = 0
    aged_count = 0
    for r in rows:
        team = r['国家']
        cn_name = r['球员']
        if team not in espn:
            r['player_en'] = ''
            continue
        # 启发式找最佳匹配
        best = None
        best_score = 0
        for en in espn[team]:
            s = match_score(cn_name, en)
            if s > best_score:
                best_score = s
                best = en
        if best and best_score >= 3:
            r['player_en'] = best
            matched_count += 1
            # 用 cache 拿年龄
            key = (team, best)
            if key in cache:
                age = calc_age(cache[key])
                if 16 <= age <= 45:
                    r['年龄'] = str(age)
                    aged_count += 1
        else:
            r['player_en'] = ''

    print(f'启发式匹配 (player_en): {matched_count}/{len(rows)}')
    print(f'通过 cache 拿年龄: {aged_count}')

    # 写回
    with open(CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f'✅ 写回 {CSV.name}')


if __name__ == '__main__':
    main()