"""
球员主表年龄全面修复 - ESPN Core API
- 1241 个 ESPN 球员 → sports.core.api.espn.com/v2/sports/soccer/athletes/{id}
- 直接拿 dateOfBirth 算年龄
- 不受维基百科限流影响
"""
import csv, json, re, os, time
from datetime import date, datetime
from pathlib import Path
import urllib.request

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

HEADERS = {'User-Agent': 'Mozilla/5.0'}
TODAY = date(2026, 6, 15)


def load_espn_athletes():
    """{(team_cn, player_en, ath_id): {jersey, position}}"""
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
                name_en = ath.get('displayName', '')
                ath_id = ath.get('id', '')
                if name_en and ath_id:
                    out[(team_cn, name_en, ath_id)] = {
                        'jersey': p.get('jersey'),
                        'position': p.get('position', {}).get('abbreviation'),
                    }
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


def espn_get_dob(ath_id):
    """ESPN Core API 查 dateOfBirth"""
    url = f'https://sports.core.api.espn.com/v2/sports/soccer/athletes/{ath_id}'
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        dob = data.get('dateOfBirth')
        if dob:
            return dob[:10]  # YYYY-MM-DD
    except Exception:
        return None
    return None


def main():
    print('=== ESPN Core API 批量查出生日期 ===\n', flush=True)
    athletes = load_espn_athletes()
    cache = load_cache()
    print(f'ESPN 球员 (含 ath_id): {len(athletes)}', flush=True)
    print(f'已有 cache: {len(cache)}', flush=True)
    print('-' * 50, flush=True)

    new_found = {}
    failed = []
    start = time.time()

    items = list(athletes.items())
    for i, ((team_cn, name_en, ath_id), meta) in enumerate(items):
        # 跳过 cache 已有的
        if any(name_en == n for (_, n) in cache.keys()):
            continue

        dob = espn_get_dob(ath_id)
        if dob:
            new_found[(team_cn, name_en)] = dob
            if len(new_found) % 20 == 0:
                elapsed = time.time() - start
                print(f'  [{i}/{len(items)}] ✅{len(new_found)} ❌{len(failed)} {elapsed:.0f}s (last: {name_en}={dob})', flush=True)
                # 刷盘
                with open(CACHE) as f:
                    old = json.load(f)
                merged = old + [[c, n, d] for (c, n), d in new_found.items()]
                with open(CACHE, 'w') as f:
                    json.dump(merged, f, ensure_ascii=False, indent=2)
                new_found = {}
        else:
            failed.append((team_cn, name_en, ath_id))

        # 限流
        time.sleep(0.05)

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

    if failed:
        with open(PROJECT / '1_数据基础' / 'age_espn_failed.json', 'w', encoding='utf-8') as f:
            json.dump([{'team': t, 'name': n, 'id': i} for t, n, i in failed], f, ensure_ascii=False, indent=2)
        print(f'  失败名单 → age_espn_failed.json', flush=True)


if __name__ == '__main__':
    main()