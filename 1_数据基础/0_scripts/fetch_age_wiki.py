"""
批量从 Wikipedia 获取球员出生日期
使用 Wikipedia REST API (免费, 无需认证)
"""
import csv, json, time, re, urllib.request, urllib.parse, urllib.error
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
CSV_PATH = DATA_DIR / "world_cup_2026_complete.csv"
JSON_PATH = DATA_DIR / "age_found_web.json"
QUEUE_PATH = DATA_DIR / "age_queue.csv"

USER_AGENT = "WorldCup2026Project/1.0 (https://github.com/Henrytudor-lee/worldcup2026; tlee4014@gmail.com)"

def wiki_search(player_name, team=""):
    """Search Wikipedia for a player and extract birth date."""
    # Build search query
    query = f"{player_name} 足球"
    if team:
        query += f" {team}"

    url = "https://zh.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'format': 'json',
        'srlimit': 3,
    }
    encoded = urllib.parse.urlencode(params)
    full_url = f"{url}?{encoded}"

    req = urllib.request.Request(full_url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return None, f"Search error: {e}"

    results = data.get('query', {}).get('search', [])
    if not results:
        return None, "No results"

    # For each result, get page extract to find birth date
    for result in results[:2]:
        pageid = result['pageid']
        extract_url = "https://en.wikipedia.org/w/api.php"
        extract_params = {
            'action': 'query',
            'pageids': str(pageid),
            'prop': 'extracts',
            'exintro': 1,
            'explaintext': 1,
            'format': 'json',
        }
        encoded = urllib.parse.urlencode(extract_params)

        req2 = urllib.request.Request(f"{extract_url}?{encoded}", headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req2, timeout=10) as resp:
                edata = json.loads(resp.read().decode())
        except Exception:
            continue

        pages = edata.get('query', {}).get('pages', {})
        page = pages.get(str(pageid), {})
        extract = page.get('extract', '')

        if not extract:
            continue

        # Search for birth date patterns
        # Pattern: "born 15 May 1998" or "born May 15, 1998" or "(born 15 May 1998)"
        patterns = [
            r'\(born\s+(\d{1,2})\s+(\w+)\s+(\d{4})\)',
            r'born\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
            r'\(born\s+(\w+)\s+(\d{1,2}),?\s+(\d{4})\)',
        ]

        for pat in patterns:
            m = re.search(pat, extract, re.IGNORECASE)
            if m:
                groups = m.groups()
                # Parse month
                months = {
                    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
                    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12
                }
                try:
                    if groups[1].isdigit():
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        month_str = groups[1].lower()
                        if month_str in months:
                            day, month, year = int(groups[0]), months[month_str], int(groups[2])
                        else:
                            continue
                    return f"{year:04d}-{month:02d}-{day:02d}", f"Wikipedia:{page.get('title','')}"
                except (ValueError, IndexError):
                    continue

    return None, "No birth date found in extract"


def main():
    # Load current data
    with open(CSV_PATH, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # Load existing found ages
    found = []
    if JSON_PATH.exists():
        with open(JSON_PATH, encoding='utf-8') as f:
            found = json.load(f)

    # Build set of already-found keys
    found_keys = set()
    for item in found:
        found_keys.add((item[0], item[1]))

    # Players needing age (excluding those already found)
    need_age = []
    for r in rows:
        age = (r.get('年龄', '') or '').strip()
        if not age or age == 'X待核实' or age.isdigit():
            key = (r['国家'], r['球员'])
            if key not in found_keys:
                need_age.append(r)

    print(f"需要查找年龄: {len(need_age)} 人")

    # Sort by priority: FIFA rank (approximate by market value)
    need_age.sort(key=lambda r: -float(r.get('身价_万欧', 0) or 0))

    # Process in batches with rate limiting
    new_found = 0
    errors = 0

    for i, r in enumerate(need_age[:200]):  # Process top 200 first
        country = r['国家']
        name = r['球员']

        # Try search
        dob, source = wiki_search(name, country)

        if dob:
            found.append([country, name, dob, 'Wikipedia API', source or ''])
            found_keys.add((country, name))
            new_found += 1
            if new_found % 10 == 0:
                print(f"  已找到 {new_found} ...")
        else:
            errors += 1

        # Rate limit: 5 requests per second max
        time.sleep(0.3)

    print(f"\n本轮新找到: {new_found}, 未找到: {errors}")

    # Save progress
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(found, f, ensure_ascii=False, indent=2)
    print(f"已保存到 {JSON_PATH} (总计 {len(found)} 条)")

    # Now apply to CSV
    # Build lookup by clean name
    def clean_name(s):
        if not s: return ''
        s = re.sub(r'\([^)]*\)', '', s)
        s = s.replace('·', '').replace(' ', '').replace('-', '').replace('　', '')
        return s.lower()

    csv_by_key = {}
    for i, r in enumerate(rows):
        age = (r.get('年龄', '') or '').strip()
        if not age or age == 'X待核实' or age.isdigit():
            csv_by_key[(r['国家'], clean_name(r['球员']))] = i

    updated = 0
    for item in found:
        c, n, dob = item[0], item[1], item[2]
        cn = clean_name(n)
        key = (c, cn)
        if key in csv_by_key:
            rows[csv_by_key[key]]['年龄'] = dob
            updated += 1

    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    remaining = sum(1 for r in rows if (r.get('年龄','') or '').strip() in ('', 'X待核实') or (r.get('年龄','') or '').strip().isdigit())
    print(f'\nCSV更新: {updated} 条')
    print(f'年龄完整率: {len(rows)-remaining}/{len(rows)} ({(len(rows)-remaining)/len(rows)*100:.1f}%)')


if __name__ == '__main__':
    main()
