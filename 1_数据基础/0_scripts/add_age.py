"""
批量补年龄：从 48 国 26 人名单中提取年龄/出生日期
"""
import json
import re
import os
import sys
from datetime import date

# 当前日期 (用于计算年龄)
TODAY = date(2026, 6, 17)

def parse_age_from_text(text, today=TODAY):
    """从文本中解析年龄: 优先数字+岁, 其次 (YYYY年MM月DD日)"""
    if not text:
        return None
    # 优先匹配 X岁 / X 岁
    m = re.search(r'(\d{1,2})\s*岁', text)
    if m:
        return int(m.group(1))
    # 匹配 (YYYY年MM月DD日) 或 (YYYY-MM-DD)
    m2 = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if m2:
        y, mo, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        bd = date(y, mo, d)
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        return age
    m3 = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if m3:
        y, mo, d = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
        bd = date(y, mo, d)
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        return age
    # 匹配 born YYYY 或 born on DD/MM/YYYY
    m4 = re.search(r'born\s*(\d{4})', text, re.I)
    if m4:
        return today.year - int(m4.group(1))
    return None

def load_csv_players(path):
    """读 CSV，返回 {国家: [球员名,...]}"""
    countries = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('国家,'):
                continue
            parts = line.split(',')
            if len(parts) < 4:
                continue
            country = parts[0].strip()
            player = parts[3].strip()
            countries.setdefault(country, []).append(player)
    return countries

def update_csv_with_ages(csv_path, age_data, output_path):
    """
    age_data: {国家: {球员名: 年龄或 None}}
    读 CSV，添加年龄列，输出到 output_path
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 找标题行
    header = lines[0].strip()
    if '年龄' not in header:
        new_header = header + ',年龄'
    else:
        new_header = header
    new_lines = [new_header + '\n']

    stats = {'updated': 0, 'missing': 0, 'not_in_data': 0}

    for line in lines[1:]:
        line = line.rstrip('\n')
        if not line:
            new_lines.append('\n')
            continue
        parts = line.split(',')
        if len(parts) < 4:
            new_lines.append(line + '\n')
            continue
        country = parts[0].strip()
        player = parts[3].strip()
        age_str = ''
        if country in age_data and player in age_data[country]:
            age = age_data[country][player]
            if age is not None:
                age_str = str(age)
                stats['updated'] += 1
            else:
                age_str = 'X待核实'
                stats['missing'] += 1
        else:
            age_str = 'X待核实'
            stats['not_in_data'] += 1
        new_lines.append(line + ',' + age_str + '\n')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    return stats

if __name__ == '__main__':
    import shutil
    csv_path = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv'
    bak_path = csv_path + '.bak20260617_age'

    # 总是从备份恢复 (避免重复添加 age 列)
    if os.path.exists(bak_path):
        shutil.copy2(bak_path, csv_path)
        print(f"[恢复] 从备份恢复: {bak_path}")
    else:
        shutil.copy2(csv_path, bak_path)
        print(f"[备份] 创建备份: {bak_path}")

    from age_all_data import AGE_DATA
    stats = update_csv_with_ages(csv_path, AGE_DATA, csv_path)
    print(f"\n[完成] 更新 {stats['updated']} 球员, 缺数据 {stats['missing']}, 未匹配 {stats['not_in_data']}")
    print(f"[汇总] {stats['updated']} 有年龄, {stats['missing'] + stats['not_in_data']} 缺年龄")
