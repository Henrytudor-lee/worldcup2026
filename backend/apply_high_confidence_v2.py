"""
最终合并 v2: 用 (team, cn_name) 直接定位, 不用 row_idx
严格保护: 只改 X待核实 / 日期格式 / 离谱值, 不覆盖已有真实年龄
"""
import csv, json, re
from datetime import date, datetime


TODAY = date(2026, 6, 15)


def calc_age(dob_str):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))


def main():
    with open('1_数据基础/heuristic_confident.json') as f:
        confident = json.load(f)

    with open('1_数据基础/age_found_web.json') as f:
        raw = json.load(f)
    cache = {}
    for x in raw:
        if isinstance(x, list) and len(x) >= 3:
            c, n, dob = x[0], x[1], x[2]
            if isinstance(dob, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
                cache[(c, n)] = dob

    with open('1_数据基础/world_cup_2026_complete.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # 建索引: (team, cn_name) -> row
    idx = {}
    for i, r in enumerate(rows):
        idx[(r['国家'], r['球员'])] = i

    written = 0
    skipped_already_good = 0
    skipped_no_cache = 0
    skipped_bad_age = 0
    not_found = 0
    audit_log = []

    for m in confident:
        team = m['team']
        cn = m['cn_name']
        en = m['en_name']
        key_idx = (team, cn)
        if key_idx not in idx:
            not_found += 1
            continue
        r = rows[idx[key_idx]]
        current_age = r['年龄']

        if current_age.isdigit() and 16 <= int(current_age) <= 45:
            skipped_already_good += 1
            continue

        cache_key = (team, en)
        if cache_key not in cache:
            skipped_no_cache += 1
            continue
        dob = cache[cache_key]
        age = calc_age(dob)
        if not (16 <= age <= 45):
            skipped_bad_age += 1
            continue

        # 审计: 写之前 + 写之后
        audit_log.append({
            'team': team, 'cn': cn, 'en': en,
            'before': current_age, 'after': str(age),
            'dob': dob,
        })
        r['年龄'] = str(age)
        written += 1

    # 写回
    with open('1_数据基础/world_cup_2026_complete.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f'高置信度启发式映射: {len(confident)} 个')
    print(f'✅ 写入新年龄: {written}')
    print(f'⚠️ 跳过 (已有真实年龄): {skipped_already_good}')
    print(f'⚠️ 跳过 (cache 无 dob): {skipped_no_cache}')
    print(f'⚠️ 跳过 (年龄异常): {skipped_bad_age}')
    print(f'⚠️ 跳过 (主表找不到): {not_found}')

    # 审计日志
    with open('1_数据基础/age_audit_v2.json', 'w', encoding='utf-8') as f:
        json.dump(audit_log, f, ensure_ascii=False, indent=2)

    # 状态
    real = sum(1 for r in rows if r['年龄'].isdigit() and 16 <= int(r['年龄']) <= 45)
    x_unk = sum(1 for r in rows if r['年龄'] == 'X待核实')
    date_fmt = sum(1 for r in rows if '-' in r['年龄'] and r['年龄'] != 'X待核实')
    weird = sum(1 for r in rows if r['年龄'].isdigit() and (int(r['年龄']) < 16 or int(r['年龄']) > 45))
    total = len(rows)
    print(f'\n=== 主表新状态 ===')
    print(f'✅ 真实年龄: {real} ({real*100/total:.1f}%)')
    print(f'❌ X待核实: {x_unk}')
    print(f'⚠️ 日期格式: {date_fmt}')
    print(f'⚠️ 离谱值: {weird}')

    # 前 10 个审计
    print(f'\n=== 前 10 个审计 (样本) ===')
    for a in audit_log[:10]:
        print(f"  {a['team']:<6} {a['cn']:<18} ({a['before']!r:>14}) → {a['after']!r:<4} [dob={a['dob']}]")


if __name__ == '__main__':
    main()