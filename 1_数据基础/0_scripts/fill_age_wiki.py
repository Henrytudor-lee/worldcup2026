"""
用 Wikipedia API 批量补球员年龄
"""
import csv
import re
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import sys
import os
from datetime import date

TODAY = date(2026, 6, 17)
CSV_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv'

def http_get_json(url, headers=None, timeout=10, max_retry=3):
    """带 429 重试的 HTTP GET"""
    headers = headers or {}
    headers.setdefault('User-Agent', 'MavisAgent/1.0 (sports data; contact: user@gmail.com)')
    for attempt in range(max_retry):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 8
                print(f"  [429] 等 {wait}s", flush=True)
                time.sleep(wait)
            else:
                return None
        except Exception:
            return None
    return None

def search_wiki(query, lang='en'):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {'action': 'query', 'format': 'json', 'list': 'search', 'srsearch': query, 'srlimit': 3}
    return http_get_json(url + '?' + urllib.parse.urlencode(params))

def get_page_wikitext(title, lang='en'):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {'action': 'parse', 'format': 'json', 'page': title, 'prop': 'wikitext'}
    data = http_get_json(url + '?' + urllib.parse.urlencode(params))
    if data:
        return data.get('parse', {}).get('wikitext', {}).get('*', '')
    return None

def parse_birth_from_text(text):
    """从 wikitext 提取出生日"""
    if not text:
        return None
    # 模式 1: | birth_date = {{birth date and age|YYYY|M|D}}
    m = re.search(r'\|\s*birth_date\s*=\s*\{\{(?:birth date and age|birth date)\|(\d{4})\|(\d{1,2})\|(\d{1,2})', text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 模式 2: {{birth date and age|YYYY|M|D}}
    m = re.search(r'\{\{birth date and age\|(\d{4})\|(\d{1,2})\|(\d{1,2})', text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # 模式 3: 仅年 (birth year and age|YYYY)
    m = re.search(r'\|\s*birth_date\s*=\s*\{\{birth year and age\|(\d{4})', text)
    if m:
        return date(int(m.group(1)), 1, 1)
    # 模式 4: 仅年 (birth year|YYYY)
    m = re.search(r'\|\s*birth_date\s*=\s*\{\{birth year\|(\d{4})', text)
    if m:
        return date(int(m.group(1)), 1, 1)
    # 模式 5: born DD Month YYYY 自由文本
    m = re.search(r'born\s+(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', text[:5000])
    if m:
        months = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
        return date(int(m.group(3)), months[m.group(2)], int(m.group(1)))
    return None

def calc_age(birth):
    if not birth:
        return None
    return TODAY.year - birth.year - ((TODAY.month, TODAY.day) < (birth.month, birth.day))

def name_similarity(query, title):
    def tokens(s):
        return set(re.findall(r'[A-Za-z\u4e00-\u9fa5]+', s.lower()))
    q, t = tokens(query), tokens(title)
    if not q or not t:
        return 0
    return len(q & t) / max(len(q), len(t))

def find_age(player_name, country, position, club=None):
    """用 Wikipedia API 找球员年龄"""
    clean_name = player_name.replace('·', ' ').replace('•', ' ').strip()
    eng_part = ' '.join(re.findall(r'[A-Za-z\s\.\-]+', clean_name)).strip()
    if not eng_part:
        eng_part = clean_name
    is_chinese_only = bool(re.fullmatch(r'[\u4e00-\u9fa5·•]+', clean_name))

    queries = []
    if is_chinese_only:
        queries.append((f"{clean_name} 足球运动员", 'zh'))
        queries.append((f"{clean_name} 球员", 'zh'))
        # 同时搜英文 Wiki (可能用不同英文名)
        queries.append((f"{clean_name} footballer", 'en'))
    else:
        queries.append((f"{clean_name} footballer {country}", 'en'))
        queries.append((f"{clean_name} 足球运动员", 'zh'))
        queries.append((f"{clean_name} football player", 'en'))
        queries.append((f"{clean_name} (footballer)", 'en'))

    # 用 club 辅助
    if club:
        simple_club = re.sub(r'[^A-Za-z\u4e00-\u9fa5]', '', club)[:15]
        if simple_club:
            queries.append((f"{clean_name} {simple_club} footballer", 'en'))
            queries.append((f"{clean_name} {simple_club} 足球", 'zh'))

    for query, lang in queries:
        result = search_wiki(query, lang)
        if not result or 'query' not in result:
            continue
        hits = result['query'].get('search', [])
        if not hits:
            continue
        for h in hits[:5]:
            title = h['title']
            sim = max(name_similarity(clean_name, title), name_similarity(eng_part, title))
            threshold = 0.2 if (is_chinese_only and lang == 'zh') else 0.3
            if sim < threshold:
                continue
            text = get_page_wikitext(title, lang)
            birth = parse_birth_from_text(text)
            if birth:
                return calc_age(birth)
        time.sleep(0.1)
    return None

def main():
    print(f"开始批量用 Wikipedia 补年龄", flush=True)
    print(f"今天: {TODAY}", flush=True)

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    if '年龄' not in fieldnames:
        fieldnames.append('年龄')
        for r in rows:
            r['年龄'] = ''

    total = len(rows)
    skip_count = sum(1 for r in rows if r.get('年龄', '').strip() and r.get('年龄', '').strip() != 'X待核实')
    todo = total - skip_count
    print(f"总: {total}, 已有: {skip_count}, 待查: {todo}", flush=True)

    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    else:
        limit = todo
    limit = min(limit, todo)

    updated = 0
    failed = 0
    processed = 0
    save_every = 30
    for i, row in enumerate(rows):
        if updated + failed >= limit:
            break
        if row.get('年龄', '').strip() and row.get('年龄', '').strip() != 'X待核实':
            continue

        country = row['国家']
        player = row['球员']
        position = row['位置']
        club = row.get('俱乐部', '')

        age = find_age(player, country, position, club=club)
        if age:
            row['年龄'] = str(age)
            updated += 1
            if updated % 5 == 0:
                print(f"  [{i+1}/{total}] ✅ {player:25s} ({country:6s}) = {age}岁 [✅{updated} ❌{failed}]", flush=True)
        else:
            row['年龄'] = 'X待核实'
            failed += 1
            if failed % 10 == 0:
                print(f"  [{i+1}/{total}] ❌ {player:25s} ({country:6s}) 未找到 [✅{updated} ❌{failed}]", flush=True)

        processed += 1
        if processed % save_every == 0:
            with open(CSV_PATH, 'w', encoding='utf-8', newline='') as wf:
                writer = csv.DictWriter(wf, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  [已刷盘] 处理 {processed} 条", flush=True)
        time.sleep(0.1)

    # 最终保存
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as wf:
        writer = csv.DictWriter(wf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[完成] 找到 {updated} 球员年龄, {failed} 失败 (X待核实)", flush=True)
    print(f"[总计] 已有 {skip_count + updated} 球员有年龄, {(total - skip_count - updated)} 仍 X待核实", flush=True)

if __name__ == '__main__':
    main()
