"""
增强版: 用 Wikipedia + ESPN 多源查年龄
"""
import csv
import re
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import sys
from datetime import date

TODAY = date(2026, 6, 17)
CSV_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv'

def http_get_json(url, headers=None, timeout=8):
    headers = headers or {}
    headers.setdefault('User-Agent', 'MavisAgent/1.0')
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return 'RATE_LIMIT'
        return None
    except Exception:
        return None

def search_wiki(query, lang='en'):
    url = f"https://{lang}.wikipedia.org/w/api.php?{urllib.parse.urlencode({'action':'query','format':'json','list':'search','srsearch':query,'srlimit':3})}"
    return http_get_json(url)

def get_summary(title, lang='en'):
    """用 summary API 拿 wikitext 前 500 字符"""
    url = f"https://{lang}.wikipedia.org/w/api.php?{urllib.parse.urlencode({'action':'query','format':'json','prop':'extracts','exintro':1,'explaintext':1,'titles':title})}"
    data = http_get_json(url)
    if data and 'query' in data:
        pages = data['query'].get('pages', {})
        for pid, p in pages.items():
            if 'extract' in p:
                return p['extract'][:1500]
    return None

def get_full_wikitext(title, lang='en'):
    url = f"https://{lang}.wikipedia.org/w/api.php?{urllib.parse.urlencode({'action':'parse','format':'json','page':title,'prop':'wikitext'})}"
    data = http_get_json(url)
    if data and 'parse' in data:
        return data['parse']['wikitext']['*']
    return None

def parse_birth(text):
    if not text:
        return None
    # 模式 1: | birth_date = {{birth date and age|YYYY|M|D}}
    m = re.search(r'\|\s*birth_date\s*=\s*\{\{(?:birth date and age|birth date)\|(\d{4})\|(\d{1,2})\|(\d{1,2})', text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 模式 2: 任意位置 {{birth date and age|YYYY|M|D}}
    m = re.search(r'\{\{birth date and age\|(\d{4})\|(\d{1,2})\|(\d{1,2})', text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 模式 3: 仅年
    m = re.search(r'\|\s*birth_date\s*=\s*\{\{birth year(?: and age)?\|(\d{4})', text)
    if m:
        return date(int(m.group(1)), 1, 1)
    # 模式 4: 自由文本 born DD Month YYYY
    m = re.search(r'born[^\d]{0,30}(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', text[:3000])
    if m:
        months = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
        try:
            return date(int(m.group(3)), months[m.group(2)], int(m.group(1)))
        except:
            return None
    return None

def calc_age(birth):
    if not birth:
        return None
    return TODAY.year - birth.year - ((TODAY.month, TODAY.day) < (birth.month, birth.day))

def name_tokens(s):
    return set(re.findall(r'[A-Za-z\u4e00-\u9fa5]+', s.lower()))

def similarity(a, b):
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0
    return len(ta & tb) / max(len(ta), len(tb))

def find_age_v2(player_name, country, club=None):
    """多策略: 中文 Wiki → 英文 Wiki → 球员全名+俱乐部 → 仅名"""
    clean = player_name.replace('·', ' ').replace('•', ' ').strip()
    eng = ' '.join(re.findall(r'[A-Za-z\s\.\-]+', clean)).strip() or clean
    is_zh = bool(re.fullmatch(r'[\u4e00-\u9fa5·•\s]+', clean))
    simple_club = re.sub(r'[^A-Za-z\u4e00-\u9fa5]', '', club or '')[:10] if club else ''

    queries = []
    if is_zh:
        queries.append((f'{clean} 足球运动员', 'zh'))
        queries.append((f'{clean} 球员', 'zh'))
        queries.append((f'{clean} footballer', 'en'))
        if simple_club:
            queries.append((f'{clean} {simple_club}', 'zh'))
    else:
        queries.append((f'{clean} footballer {country}', 'en'))
        queries.append((f'{clean} football player', 'en'))
        queries.append((f'{clean} (footballer)', 'en'))
        if simple_club:
            queries.append((f'{clean} {simple_club}', 'en'))
        queries.append((f'{clean} 足球运动员', 'zh'))

    for query, lang in queries:
        if lang == 'zh':
            time.sleep(0.05)
        result = search_wiki(query, lang)
        if result == 'RATE_LIMIT':
            time.sleep(8)
            continue
        if not result or 'query' not in result:
            continue
        hits = result['query'].get('search', [])
        for h in hits[:5]:
            title = h['title']
            sim = max(similarity(clean, title), similarity(eng, title))
            threshold = 0.2 if (is_zh and lang == 'zh') else 0.3
            if sim < threshold:
                continue
            # 先试 summary (快)
            text = get_summary(title, lang)
            birth = parse_birth(text)
            if birth:
                return calc_age(birth)
            # 失败试 full wikitext
            text = get_full_wikitext(title, lang)
            birth = parse_birth(text)
            if birth:
                return calc_age(birth)
        time.sleep(0.05)
    return None

def main():
    print(f"增强版: Wikipedia 批量补年龄 v2", flush=True)
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())
    if '年龄' not in fieldnames:
        fieldnames.append('年龄')
        for r in rows:
            r['年龄'] = ''

    total = len(rows)
    skip = sum(1 for r in rows if r.get('年龄','').strip() and r.get('年龄','').strip() != 'X待核实')
    todo = total - skip
    print(f"总 {total}, 已有 {skip}, 待查 {todo}", flush=True)

    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit')+1])
    else:
        limit = todo
    limit = min(limit, todo)

    updated, failed = 0, 0
    save_every = 30
    processed = 0
    for i, row in enumerate(rows):
        if updated + failed >= limit:
            break
        if row.get('年龄','').strip() and row.get('年龄','').strip() != 'X待核实':
            continue
        age = find_age_v2(row['球员'], row['国家'], club=row.get('俱乐部',''))
        if age:
            row['年龄'] = str(age)
            updated += 1
            if updated % 5 == 0:
                print(f"  [{i+1}/{total}] ✅ {row['球员']:25s} ({row['国家']}) = {age}岁 [✅{updated} ❌{failed}]", flush=True)
        else:
            row['年龄'] = 'X待核实'
            failed += 1
            if failed % 10 == 0:
                print(f"  [{i+1}/{total}] ❌ {row['球员']:25s} ({row['国家']}) [✅{updated} ❌{failed}]", flush=True)
        processed += 1
        if processed % save_every == 0:
            with open(CSV_PATH, 'w', encoding='utf-8', newline='') as wf:
                writer = csv.DictWriter(wf, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  [已刷盘] 处理 {processed}", flush=True)
        time.sleep(0.05)

    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as wf:
        writer = csv.DictWriter(wf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[完成] 找到 {updated}, 失败 {failed}", flush=True)
    print(f"[总] 已有 {skip+updated}/{total} ({(skip+updated)*100/total:.1f}%)", flush=True)

if __name__ == '__main__':
    main()
