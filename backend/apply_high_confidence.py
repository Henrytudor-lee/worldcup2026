"""
最终合并: 把高置信度启发式映射 (67 个) 写入主表
严格保护: 只改 X待核实 / 日期格式 / 离谱值, 不覆盖已有真实年龄
"""
import csv, json, re
from datetime import date, datetime


TODAY = date(2026, 6, 15)


def calc_age(dob_str):
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))


def main():
    # 加载启发式映射
    with open('1_数据基础/heuristic_confident.json') as f:
        confident = json.load(f)

    # 加载 cache
    with open('1_数据基础/age_found_web.json') as f:
        raw = json.load(f)
    cache = {}
    for x in raw:
        if isinstance(x, list) and len(x) >= 3:
            c, n, dob = x[0], x[1], x[2]
            if isinstance(dob, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
                cache[(c, n)] = dob

    # 加载主表
    with open('1_数据基础/world_cup_2026_complete.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    # 统计: 哪些 (team, cn_name) 没真实年龄, 可写
    written = 0
    skipped_already_good = 0
    skipped_no_cache = 0
    skipped_bad_age = 0

    for m in confident:
        idx = m['row_idx']
        r = rows[idx]
        team = m['team']
        cn = m['cn_name']
        en = m['en_name']
        current_age = r['年龄']

        # 保护: 真实年龄 (16-45) 不动
        if current_age.isdigit() and 16 <= int(current_age) <= 45:
            skipped_already_good += 1
            continue

        # 查 cache 拿年龄
        key = (team, en)
        if key not in cache:
            skipped_no_cache += 1
            continue
        dob = cache[key]
        age = calc_age(dob)
        if not (16 <= age <= 45):
            skipped_bad_age += 1
            continue

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

    # 统计最终状态
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


if __name__ == '__main__':
    main()