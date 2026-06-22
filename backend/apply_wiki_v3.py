"""
将 Wikipedia scrape v3 结果写回主表
"""
import csv, json
from datetime import date

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    d = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))

# 加载 scrape 结果
results = json.load(open('1_数据基础/wiki_scrape_v3_results.json'))

# 主表
rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))

valid_count = 0
outlier_count = 0
still_xun = 0

updated = []

for row in rows:
    team = row['国家']
    cn = row['球员']
    key = f"{team}|{cn}"
    r = results.get(key)
    orig_age = row['年龄']
    new_age = orig_age

    if r:
        dob = r.get('dob', '')
        if dob and len(dob) >= 10:
            dob = dob[:10]
            try:
                age = calc_age(dob)
                if 16 <= age <= 45:
                    new_age = str(age)
                    valid_count += 1
                    updated.append({
                        'team': team, 'cn': cn,
                        'en': r.get('en', ''),
                        'dob': dob, 'age': age,
                        'source': 'wikipedia_v3'
                    })
                else:
                    new_age = 'X待核实'
                    outlier_count += 1
                    updated.append({
                        'team': team, 'cn': cn,
                        'en': r.get('en', ''),
                        'dob': dob, 'age': age,
                        'source': 'wikipedia_v3_outlier'
                    })
            except:
                new_age = 'X待核实'
    else:
        if orig_age == 'X待核实':
            still_xun += 1

    row['年龄'] = new_age

# 写回 CSV
fieldnames = list(rows[0].keys())
with open('1_数据基础/world_cup_2026_complete.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f'写回完成!')
print(f'  有效DOB更新: {valid_count}')
print(f'  离谱值→X待核实: {outlier_count}')
print(f'  scrape未覆盖的X待核实: {still_xun}')
print(f'  更新记录: {len(updated)} 条')

with open('1_数据基础/wiki_v3_updates.json', 'w') as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)

# 最终统计
real_age = 0
xun = 0
for r in rows:
    a = r['年龄']
    if a not in ('X待核实', '年龄') and a.isdigit():
        age_int = int(a)
        if 16 <= age_int <= 45:
            real_age += 1
        else:
            xun += 1
    elif a == 'X待核实':
        xun += 1

print(f'\n主表现在: 真实年龄 {real_age}/1248  X待核实 {xun}')
