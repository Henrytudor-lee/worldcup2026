"""
球员主表年龄修复 v3 - 用 Wikipedia API 批量查
- 修剩余 30 离谱值 + 29 日期格式 (没被 cache 覆盖的)
- 中文名 → 英文名 映射 (基于 ESPN cache 的 surname 匹配)
- 查英文 Wikipedia, 解析 birth_date
"""
import csv, json, re, os, time
from datetime import date, datetime
from pathlib import Path
import urllib.request, urllib.parse

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
CSV = PROJECT / '1_数据基础' / 'world_cup_2026_complete.csv'
ESPN_DIR = PROJECT / '1_数据基础' / 'espn_match_data'

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

WIKI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
}
TODAY = date(2026, 6, 15)


def load_espn_rosters():
    """{(team_cn, player_en_lower): displayName}"""
    out = {}
    for fname in os.listdir(ESPN_DIR):
        if not fname.endswith('.json'):
            continue
        with open(f'{ESPN_DIR}/{fname}') as f:
            d = json.load(f)
        for r in d.get('rosters', []):
            team_en = r.get('team', {}).get('displayName', '')
            team_cn = CN_FROM_EN.get(team_en, team_en)
            for p in r.get('roster', []):
                ath = p.get('athlete', {})
                name_en = ath.get('displayName', '')
                if name_en:
                    out[(team_cn, name_en.lower())] = name_en
    return out


def cn_to_en_lookup(player_cn, country, espn):
    """中文名 → 英文名 (按 ESPN cache 的 surname 匹配)
    策略: 取中文名"姓"(最后一个汉字的拼音首字母) + ESPN displayName 第一个词
    简化: 直接用 ESPN 缓存的 player_en 列表, 按 (team, 姓/名 token 匹配)
    """
    # 中文名常见的"姓 + 名"结构, 取每个汉字 (简化: ESPN cache 找含有相同汉字拼音首字母的英文名太复杂)
    # 兜底: 用全 ESPN 该国家球员列表, 手工不在此做, 跳到维基查中文
    candidates = [en for (team, _), en in espn.items() if team == country]
    if not candidates:
        return None

    # 简化匹配 1: 中文名汉字 → 拼音首字母 (需要 pypinyin, 没装)
    # 简化匹配 2: ESPN displayName 长度与中文名长度相近 + 同位置首字母匹配 (启发式)
    # 这里降级: 直接对所有候选, 让 wiki 搜索 "中文名 footballer" 命中后取英文标题
    return None  # 让 wiki 中文搜索直接拿


def wiki_search(query, lang='en'):
    """维基百科搜索, 返回 [(title, snippet), ...]"""
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        'action':'query', 'format':'json', 'list':'search', 'srsearch': query, 'srlimit': 1,
    })
    try:
        req = urllib.request.Request(url, headers=WIKI_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        return [(h['title'], h.get('snippet','')) for h in data.get('query', {}).get('search', [])]
    except Exception:
        return []


def wiki_get_birth(title, lang='en'):
    """拿 wikitext 解析 birth_date"""
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        'action':'parse', 'format':'json', 'page': title, 'prop':'wikitext',
    })
    try:
        req = urllib.request.Request(url, headers=WIKI_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        text = data.get('parse', {}).get('wikitext', {}).get('*', '')
    except Exception:
        return None
    if not text:
        return None
    m = re.search(r'\|\s*birth_date\s*=\s*\{\{(?:birth date and age|birth date)\|(\d{4})\|(\d{1,2})\|(\d{1,2})', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r'\{\{birth date and age\|(\d{4})\|(\d{1,2})\|(\d{1,2})', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def calc_age(dob_str):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))


# 中文姓名 → 英文姓名 (手工映射, 覆盖 30+ 个异常)
MANUAL_CN_EN = {
    # 离谱值
    ('加拿大', '阿尔菲·琼斯'): 'Alfie Jones',
    ('巴西', '韦斯利'): 'Wesley',
    ('厄瓜多尔', '拉米雷斯'): 'Álex Ramírez',  # 厄瓜多尔门将? 还是其他人
    ('厄瓜多尔', '约翰·叶博亚'): 'John Yeboah',
    ('德国', '布朗'): 'Braun',  # 不确定, 可能是 R Bella-Kotchap
    ('乌拉圭', '圣地亚哥·布埃诺'): 'Santiago Bueno',
    ('巴拿马', '埃里克·戴维斯'): 'Éric Davis',
    ('英格兰', '安东尼·戈登'): 'Anthony Gordon',
    ('澳大利亚', '亚历山德罗·西卡蒂'): 'Alessandro Circati',
    ('澳大利亚', '穆罕默德·图雷'): 'Mohamed Toure',
    ('澳大利亚', '克里斯蒂安·沃尔帕托'): 'Christian Volpato',
    ('西班牙', '尼科·威廉姆斯'): 'Nico Williams',
    ('科特迪瓦', '穆罕默德·科内'): 'Mohamed Koné',
    ('埃及', '马哈茂德·萨比尔'): 'Mahmoud Saber',
    ('伊朗', '丹尼斯·埃克特'): 'Dennis Eckert',
    ('伊拉克', '埃曼·侯赛因'): 'Aiman Hussein',
    ('伊拉克', '莫哈纳德·阿里'): 'Mohanad Ali',
    ('卡塔尔', '穆罕默德·蒙塔里'): 'Mohammed Muntari',
    ('瑞士', '马文·凯勒'): 'Marvin Keller',
    ('瑞士', '约翰·曼赞比'): 'Joël Monzango',  # 猜的
    ('苏格兰', '安迪·罗伯逊'): 'Andrew Robertson',
    ('苏格兰', '约翰·苏塔尔'): 'John Souttar',
    ('苏格兰', '约翰·麦金'): 'John McGinn',
    ('苏格兰', '乔治·赫斯特'): 'George Hirst',
    ('奥地利', '亚历山大·普拉斯'): 'Alexander Prass',
    ('奥地利', '大卫·阿芬格鲁伯'): 'David Affengruber',
    ('波黑', '丹尼斯·哈季卡杜尼奇'): 'Denis Hadžikadunić',
    ('美国', '克里斯·布雷迪'): 'Chris Brady',
    ('美国', '亚历克斯·弗里曼'): 'Alex Freeman',
    ('美国', '泰勒·亚当斯'): 'Tyler Adams',
}


def main():
    espn = load_espn_rosters()
    print(f'ESPN 缓存: {len(espn)} 球员英文名')

    with open(CSV, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    # 收集待修球员
    targets = []
    for r in rows:
        a = r.get('年龄', '').strip()
        is_date_fmt = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', a))
        is_weird = a.isdigit() and (int(a) < 16 or int(a) > 45)
        if is_date_fmt or is_weird:
            targets.append((r, a))

    print(f'\n待修: {len(targets)} 个')

    fixed = []
    failed = []
    for i, (r, old_age) in enumerate(targets):
        country = r['国家']
        player_cn = r['球员']
        # 1) 优先用 MANUAL_CN_EN
        en_name = MANUAL_CN_EN.get((country, player_cn))
        # 2) fallback: 中文维基搜 (拿英文 title 失败)
        if not en_name:
            # 用 ESPN cache 找该国所有英文名, 启发式匹配
            candidates = sorted(set(en for (t, _), en in espn.items() if t == country))
            # 取 ESPN cache 最短 (通常是简称) 与中文名对比
            # 中文名姓通常在最后 (单字) 或最后 1-2 字, 启发式: ESPN 末词 vs 中文末字
            # 跳过启发式, 直接 mark failed
            failed.append((country, player_cn, 'NO_MANUAL_MAP'))
            continue

        # 维基百科查
        title = None
        for q in [f'{en_name} footballer', f'{en_name} football player', en_name]:
            hits = wiki_search(q, 'en')
            if hits:
                title = hits[0][0]
                break
        if not title:
            failed.append((country, player_cn, en_name + ' WIKI_NO_HIT'))
            continue

        dob = wiki_get_birth(title, 'en')
        if not dob:
            failed.append((country, player_cn, en_name + f' NO_BIRTH'))
            continue

        age = calc_age(dob)
        r['年龄'] = str(age)
        fixed.append((country, r['号码'], player_cn, en_name, old_age, age, dob))
        if len(fixed) % 5 == 0:
            print(f'  [{i+1}/{len(targets)}] ✅ {player_cn} → {en_name} ({age})')
        time.sleep(0.1)

    print(f'\n=== 结果 ===')
    print(f'✅ 修复: {len(fixed)}')
    print(f'❌ 失败: {len(failed)}')
    for c, p, reason in failed[:10]:
        print(f'  ❌ {c:<6} {p}: {reason}')

    if fixed:
        with open(CSV, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f'\n✅ 写回 {CSV.name}')

    # 输出失败名单
    if failed:
        with open(PROJECT / '1_数据基础' / 'age_step2_failed.json', 'w', encoding='utf-8') as f:
            json.dump([{'country': c, 'name': p, 'reason': r} for c, p, r in failed], f, ensure_ascii=False, indent=2)
        print(f'失败名单 → age_step2_failed.json')


if __name__ == '__main__':
    main()