"""
球员主表年龄修复 v2 - Step 1
- 用 age_found_web.json cache 修日期格式行 + 离谱值
- 输出 cache 修复结果
"""
import csv, json, re
from datetime import date, datetime
from pathlib import Path

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
CSV = PROJECT / '1_数据基础' / 'world_cup_2026_complete.csv'
CACHE = PROJECT / '1_数据基础' / 'age_found_web.json'

TODAY = date(2026, 6, 15)


def load_cache():
    if not CACHE.exists():
        return {}
    with open(CACHE) as f:
        raw = json.load(f)
    out = {}
    for item in raw:
        if isinstance(item, list) and len(item) >= 3:
            c, n, dob = item[0], item[1], item[2]
            if isinstance(dob, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
                out[(c, n)] = dob
    return out


def calc_age(dob_str):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))


def main():
    cache = load_cache()
    print(f'Cache 大小: {len(cache)}')

    with open(CSV, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    # 修日期格式 + 离谱值
    fixed = []
    for r in rows:
        a = r.get('年龄', '').strip()
        if not a or a == 'X待核实':
            continue
        key = (r['国家'], r['球员'])
        if key not in cache:
            continue
        try:
            new_age = calc_age(cache[key])
        except Exception:
            continue
        is_date_fmt = bool(re.match(r'^\d{4}-\d{2}-\d{2}$', a))
        is_weird = a.isdigit() and (int(a) < 16 or int(a) > 45)
        if is_date_fmt or is_weird:
            fixed.append((r['国家'], r['号码'], r['球员'], a, new_age))
            r['年龄'] = str(new_age)

    print(f'\n=== 修复详情 ===')
    print(f'  日期格式 → 年龄: {sum(1 for x in fixed if re.match(r"^\\d{4}-\\d{2}-\\d{2}$", x[3]))}')
    print(f'  离谱值 → 真实年龄: {sum(1 for x in fixed if x[3].isdigit())}')
    print(f'  总计: {len(fixed)} 处')
    print()
    print('=== 前 15 条 ===')
    for c, n, name, old, new in fixed[:15]:
        print(f'  {c:<6} #{n:<3} {name}: {old} → {new}')
    if len(fixed) > 15:
        print(f'  ... 还有 {len(fixed)-15} 处')

    # 写回
    if fixed:
        with open(CSV, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f'\n✅ 写回 {CSV.name}')

    # 检查剩多少异常
    print(f'\n=== 修复后状态 ===')
    new_weird = sum(1 for r in rows if r['年龄'].isdigit() and (int(r['年龄']) < 16 or int(r['年龄']) > 45))
    new_date = sum(1 for r in rows if re.match(r'^\d{4}-\d{2}-\d{2}$', r.get('年龄','')))
    new_x = sum(1 for r in rows if r['年龄'] == 'X待核实')
    new_real = sum(1 for r in rows if r['年龄'].isdigit() and 16 <= int(r['年龄']) <= 45)
    total = len(rows)
    print(f'  总球员: {total}')
    print(f'  ✅ 真实年龄: {new_real} ({new_real*100/total:.1f}%)')
    print(f'  ❌ X待核实: {new_x} ({new_x*100/total:.1f}%)')
    print(f'  ⚠️ 仍异常: {new_weird + new_date}')


if __name__ == '__main__':
    main()