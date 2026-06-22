"""
球员主表年龄全面修复 - 多渠道, 慢速, 稳错误处理
"""
import csv, json, re, os, time, sys
from datetime import date, datetime
from pathlib import Path
import urllib.request, urllib.parse

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
CSV = PROJECT / '1_数据基础' / 'world_cup_2026_complete.csv'
CACHE = PROJECT / '1_数据基础' / 'age_found_web.json'
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
    'Accept': 'application/json',
}
TODAY = date(2026, 6, 15)


def load_espn():
    """{(team_cn, player_en_lower): displayName}"""
    out = {}
    for fname in os.listdir(ESPN_DIR):
        if not fname.endswith('.json'): continue
        with open(f'{ESPN_DIR}/{fname}') as f:
            d = json.load(f)
        for r in d.get('rosters', []):
            team_en = r.get('team', {}).get('displayName', '')
            team_cn = CN_FROM_EN.get(team_en, team_en)
            for p in r.get('roster', []):
                ath = p.get('athlete', {})
                n = ath.get('displayName', '')
                if n: out[(team_cn, n.lower())] = n
    return out


def load_cache():
    if not CACHE.exists(): return {}
    with open(CACHE) as f:
        raw = json.load(f)
    out = {}
    for item in raw:
        if isinstance(item, list) and len(item) >= 3:
            c, n, dob = item[0], item[1], item[2]
            if isinstance(dob, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
                out[(c, n)] = dob
    return out


def http_get(url, timeout=10, retries=2):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=WIKI_HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                wait = 5 * (attempt + 1)
                print(f'    ⚠️ 429, wait {wait}s', flush=True)
                time.sleep(wait)
                continue
            return None
        except Exception as e:
            return None
    return None


def wiki_search(query, lang='en'):
    try:
        encoded = urllib.parse.urlencode({
            'action':'query', 'format':'json', 'list':'search',
            'srsearch': query, 'srlimit': 1,
        })
    except UnicodeEncodeError:
        return []
    url = f"https://{lang}.wikipedia.org/w/api.php?{encoded}"
    text = http_get(url, timeout=8)
    if not text: return []
    try:
        data = json.loads(text)
        return [(h['title'], h.get('snippet','')) for h in data.get('query', {}).get('search', [])]
    except Exception: return []


def wiki_get_birth(title, lang='en'):
    try:
        encoded = urllib.parse.urlencode({
            'action':'parse', 'format':'json', 'page': title, 'prop':'wikitext',
        })
    except UnicodeEncodeError:
        return None
    url = f"https://{lang}.wikipedia.org/w/api.php?{encoded}"
    text = http_get(url, timeout=10)
    if not text: return None
    try:
        text = json.loads(text).get('parse', {}).get('wikitext', {}).get('*', '')
    except Exception: return None
    if not text: return None
    patterns = [
        r'(?i)\|\s*birth_date\s*=\s*\{\{(?:birth date and age|birth date)\|(\d{4})\|(\d{1,2})\|(\d{1,2})',
        r'(?i)\{\{birth date and age\|(\d{4})\|(\d{1,2})\|(\d{1,2})',
        r'(?i)\|\s*birth_date\s*=\s*(\d{4})-(\d{2})-(\d{2})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def baike_search(name):
    """百度百科"""
    try:
        encoded = urllib.parse.urlencode({
            'scope': '103', 'format': 'json', 'appid': '379020',
            'bk_key': name, 'bk_length': 600,
        })
    except UnicodeEncodeError: return None
    url = f"https://baike.baidu.com/api/openapi/BaikeLemmaCardApi?{encoded}"
    text = http_get(url, timeout=8)
    if not text: return None
    try:
        data = json.loads(text)
        abstract = data.get('abstract', '')
        m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', abstract)
        if m: return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    except Exception: return None
    return None


def find_birth(name, country=None):
    """多渠道: en wiki → zh wiki → 百度"""
    for q in [f'{name} footballer', f'{name} (footballer)', name]:
        hits = wiki_search(q, 'en')
        if hits:
            title = hits[0][0]
            b = wiki_get_birth(title, 'en')
            if b: return b, f'en:{title}'
        time.sleep(0.3)

    if country:
        for q in [f'{name} 足球运动员', f'{name} 球员']:
            hits = wiki_search(q, 'zh')
            if hits:
                title = hits[0][0]
                b = wiki_get_birth(title, 'zh')
                if b: return b, f'zh:{title}'
            time.sleep(0.3)
        b = baike_search(name)
        if b: return b, 'baike'

    return None, None


def main():
    print('=== 多渠道查年龄 (慢速稳版) ===\n', flush=True)
    espn = load_espn()
    cache = load_cache()
    print(f'ESPN 缓存: {len(espn)}', flush=True)
    print(f'已有 cache: {len(cache)}', flush=True)

    en_names = sorted(set(name for (_, _), name in espn.items()))
    print(f'去重后英文名: {len(en_names)}', flush=True)
    print('-' * 50, flush=True)

    new_found = {}
    failed = []
    start = time.time()

    for i, name in enumerate(en_names):
        # 跳过 cache 已有的
        if any(name == n for (_, n) in cache.keys()):
            continue
        country = next((t for (t, low), _ in espn.items() if low == name.lower()), None)

        # 每 10 个强制刷盘
        if len(new_found) > 0 and len(new_found) % 20 == 0:
            elapsed = time.time() - start
            print(f'  [{i}/{len(en_names)}] ✅{len(new_found)} ❌{len(failed)} {elapsed:.0f}s', flush=True)
            with open(CACHE) as f:
                old = json.load(f)
            merged = old + [[c, n, d] for (c, n), d in new_found.items()]
            with open(CACHE, 'w') as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            new_found = {}

        birth, src = find_birth(name, country)
        if birth:
            new_found[(country, name)] = birth
            if len(new_found) % 5 == 0:
                print(f'  ✅ {name}: {birth} ({src})', flush=True)
        else:
            failed.append((country, name))

        time.sleep(0.5)  # 慢速避免 429

    # 最后刷盘
    if new_found:
        with open(CACHE) as f:
            old = json.load(f)
        merged = old + [[c, n, d] for (c, n), d in new_found.items()]
        with open(CACHE, 'w') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f'\n=== 完成 ===', flush=True)
    print(f'  新增: {len(new_found)}', flush=True)
    print(f'  失败: {len(failed)}', flush=True)
    print(f'  耗时: {time.time()-start:.0f}s', flush=True)


if __name__ == '__main__':
    main()