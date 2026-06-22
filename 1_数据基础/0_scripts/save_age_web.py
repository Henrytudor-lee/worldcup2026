"""保存已搜年龄到 CSV
关键修复: CSV 球员名是 "全名(English Name)" 形式, JSON 是 "全名" 形式
两边都清洗: 去括号英文 + 去点 + 去空格 + 去横杠
"""
import csv, json, re
from collections import defaultdict

JSON_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/age_found_web.json'
CSV_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv'

def clean(s):
    """去括号英文, 去点去空去横杠"""
    if not s:
        return ''
    s = re.sub(r'\([^)]*\)', '', s)  # 去括号
    s = s.replace('·', '').replace(' ', '').replace('-', '').replace('　', '')
    return s

with open(JSON_PATH) as f:
    known = json.load(f)

# 去重
seen = set()
unique = []
for k in known:
    key = (k[0], k[1])
    if key not in seen:
        seen.add(key)
        unique.append(k)

with open(CSV_PATH) as f:
    rows = list(csv.DictReader(f))

def needs_fill(a):
    """需要填: 空 / X待核实 / 纯数字 (无日期精度) / 错误格式"""
    if not a or a in ('', 'X待核实'):
        return True
    # 纯数字 (如 '33') 是估算, 应该用精确日期覆盖
    if a.isdigit():
        return True
    # 有日期格式 (YYYY-MM-DD) 才保留
    if '-' in a and len(a) == 10:
        return False
    return True  # 其他异常值也算需要填

# 索引: 国家 -> [(i, csv_name_clean, csv_name_raw)]
csv_by_country = defaultdict(list)
for i, r in enumerate(rows):
    if needs_fill(r.get('年龄', '')):
        csv_by_country[r['国家']].append((i, clean(r['球员']), r['球员']))

by_country_json = defaultdict(list)
for entry in unique:
    c, n = entry[0], entry[1]
    a = entry[2]
    by_country_json[c].append((clean(n), a))

updated = 0
log = []

for country, csv_list in csv_by_country.items():
    json_list = by_country_json.get(country, [])
    for i, cn_clean, cn_raw in csv_list:
        if not cn_clean:
            continue
        for jn_clean, age in json_list:
            # EXACT (清洗后相等)
            if cn_clean == jn_clean and cn_clean:
                rows[i]['年龄'] = age
                updated += 1
                log.append(('EXACT', country, cn_raw, age))
                break
            # SUFFIX (CSV 简称 = JSON 全名后缀)
            if len(cn_clean) >= 2 and jn_clean.endswith(cn_clean) and cn_clean != jn_clean:
                rows[i]['年龄'] = age
                updated += 1
                log.append(('SUFFIX', country, cn_raw, age))
                break
            # PREFIX (CSV 简称 = JSON 全名前缀)
            if len(cn_clean) >= 2 and jn_clean.startswith(cn_clean) and cn_clean != jn_clean:
                rows[i]['年龄'] = age
                updated += 1
                log.append(('PREFIX', country, cn_raw, age))
                break

with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f'总计更新: {updated}')
print()
from collections import Counter
by_kind = Counter(k for k, *_ in log)
print('=== 按匹配类型 ===')
for k, n in by_kind.most_common():
    print(f'  {k}: {n}')

print()
print('=== 按国家 ===')
by_c = Counter(c for _, c, _, _ in log)
for c, n in by_c.most_common(15):
    print(f'  {c}: +{n}')

print()
print('=== 全部样本 ===')
for kind, c, n, a in log:
    print(f'  [{kind}] {c} {n} = {a}')

have_age = sum(1 for r in rows if r.get('年龄') and r['年龄'] not in ('', 'X待核实'))
total = len(rows)
print(f'\n当前年龄覆盖: {have_age}/{total} ({have_age/total*100:.1f}%)')
print(f'X待核实: {sum(1 for r in rows if r.get("年龄") == "X待核实")}')
