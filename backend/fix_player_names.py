"""
球员主表名字规范化 v1
- P0: 去英文括号残留 (76 人: 哥伦比亚/巴拉圭/新西兰)
- P1: 知名球员简称 → 全称 (25 人: 德/西/比/荷/英)

用法: python3 backend/fix_player_names.py
"""
import csv
import re
from pathlib import Path

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
CSV = PROJECT / '1_数据基础' / 'world_cup_2026_complete.csv'

# === P0: 去括号 (用括号前的简体中文部分) ===
# 哥伦比亚队所有"X(English)" → "X" (简化中文)
# 例: "J罗(James Rodriguez)" → "J罗"
# 例: "路易斯·迪亚兹(Luis Diaz)" → "路易斯·迪亚兹"
# 例: "小阿隆索(Junior Alonso)" → "小阿隆索"

# 巴拉圭有"小X"结构, 保留"小"字
# 新西兰有"小X"也保留
# 注意: "罗德里戈·本坦库尔"已经在主表是全称, 不动

# === P1: 知名球员简称 → 全称 ===
P1_SHORT_TO_FULL = {
    # 德国
    '诺伊尔': '曼努埃尔·诺伊尔',
    '基米希': '约书亚·基米希',
    '穆西亚拉': '贾马尔·穆西亚拉',
    '维尔茨': '弗洛里安·维尔茨',
    '哈弗茨': '凯·哈弗茨',
    '萨内': '勒罗伊·萨内',
    '劳姆': '大卫·劳姆',
    # 西班牙
    '罗德里': '罗德里戈·埃尔南德斯',
    '佩德里': '佩德罗·冈萨雷斯·洛佩斯',
    '加维': '巴勃罗·帕冯·萨利纳斯',
    '库库雷利亚': '马克·库库雷利亚',
    '拉波尔特': '艾梅里克·拉波尔特',
    # 比利时
    '德布劳内': '凯文·德布劳内',
    '卢卡库': '罗梅卢·卢卡库',
    # 荷兰
    '范戴克': '维吉尔·范戴克',
    '邓弗里斯': '丹泽尔·邓弗里斯',
    '德容': '弗朗基·德容',
    '德佩': '孟菲斯·德佩',
    '加克波': '科迪·加克波',
    # 英格兰
    '斯通斯': '约翰·斯通斯',
    '格伊': '马克·格伊',
    '宽萨': '贾雷尔·宽萨',
    '孔萨': '埃兹里·孔萨',
    '贝林厄姆': '裘德·贝林厄姆',
    # 葡萄牙
    'C罗': '克里斯蒂亚诺·罗纳尔多',
}


def strip_english_paren(name: str) -> str:
    """去括号内的英文残留: 'J罗(James Rodriguez)' → 'J罗'"""
    # 处理半角 ( 和全角 （
    m = re.match(r'^(.+?)\s*[(\uff08].*$', name)
    if m:
        return m.group(1).strip()
    return name


def main():
    with open(CSV, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys())

    p0_changes = []
    p1_changes = []
    skipped = []

    for r in rows:
        original = r['球员']
        new_name = original

        # P0: 去括号 (仅当括号内是英文名, 简化中文保留)
        if '(' in new_name or '（' in new_name:
            stripped = strip_english_paren(new_name)
            if stripped != new_name:
                p0_changes.append((r['国家'], r['号码'], original, stripped))
                new_name = stripped

        # P1: 简称 → 全称 (全名匹配, 避免误伤)
        if new_name in P1_SHORT_TO_FULL:
            full = P1_SHORT_TO_FULL[new_name]
            p1_changes.append((r['国家'], r['号码'], new_name, full))
            new_name = full

        r['球员'] = new_name

    # === 输出变更摘要 ===
    print(f'=== 修改摘要 ===\n')
    print(f'P0 (去括号): {len(p0_changes)} 处')
    for c, n, old, new in p0_changes[:5]:
        print(f'  {c:<6} #{n:<3} "{old}" → "{new}"')
    if len(p0_changes) > 5:
        print(f'  ... 还有 {len(p0_changes)-5} 处\n')

    print(f'P1 (简称→全称): {len(p1_changes)} 处')
    for c, n, old, new in p1_changes:
        print(f'  {c:<6} #{n:<3} "{old}" → "{new}"')

    if not p0_changes and not p1_changes:
        print('✅ 无变更')
        return

    # === 写回 ===
    with open(CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f'\n✅ 写回 {CSV.name}: {len(rows)} 行')
    print(f'总计: P0 {len(p0_changes)} + P1 {len(p1_changes)} = {len(p0_changes)+len(p1_changes)} 处')


if __name__ == '__main__':
    main()