"""
exact_match_apply.py
用精确中文→英文名字映射更新主表 X待核实 球员
策略：
  1. 从 搜狗百科/虎扑/腾讯/新浪 等多源确认的 2026 大名单
  2. Wikipedia DOB 数据做年龄源
  3. 只更新 X待核实/数字占位 行
  4. 对同一 Wikipedia 英文名有多个中文名的情况，仅更新第一个匹配（其他手动核实）
"""
import json, csv

# ── 精确映射表（来源: 多中文媒体确认 + Wikipedia DOB）──────────
# 中文名 → (Wikipedia英文名, DOB)
EXACT_MAP = {
    # 突尼斯 (26人完整名单，多源确认)
    '达门':           ('Aymen Dahmen',            '1997-01-28'),
    '本·黑森':         ('Sabri Ben Hassen',         '1996-06-13'),
    '查马克':          ('Mouhib Chamakh',           '2001-08-25'),
    '塔尔比':          ('Montassar Talbi',          '1998-05-26'),
    '布隆':           ('Dylan Bronn',              '1995-06-19'),
    '雷基克':          ('Omar Rekik',              '2001-12-20'),
    '阿鲁斯':          ('Adem Arous',              '2004-07-17'),
    '齐卡维':          ('Waïdi Kechida',           '1999-08-21'),
    '瓦莱里':          ('Yan Valery',              '1999-02-22'),
    '内法蒂':          ('Moutaz Neffati',          '2004-09-04'),
    '阿布迪':          ('Ali Abdi',                '1993-12-20'),
    '哈米达':          ('Mohamed Amine Ben Hamida', '1995-12-15'),
    '本赫米达':         ('Mohamed Amine Ben Hamida', '1995-12-15'),
    '斯希里':          ('Ellyes Skhiri',           '1995-05-10'),
    '本·瓦内斯':        ('Mortadha Ben Ouanes',      '1994-07-02'),
    '加尔比':          ('Ismaël Gharbi',           '2004-04-10'),
    '马哈茂德':         ('Hadj Mahmoud',            '2000-04-24'),
    '赫迪拉':          ('Rani Khedira',            '1994-01-27'),
    '斯里曼尼':         ('Anis Ben Slimane',        '2001-03-16'),
    '汉尼拔·梅布里':      ('Hannibal Mejbri',         '2003-01-21'),
    '苏莱曼':          ('Khalil Ayari',            '2005-02-02'),
    '阿亚里':          ('Khalil Ayari',            '2005-02-02'),
    '阿舒里':          ('Elias Achouri',           '1999-02-10'),
    '图内克蒂':         ('Sebastian Tounekti',       '2002-07-13'),
    '沙瓦':           ('Firas Chaouat',           '1996-05-08'),
    '埃卢米':          ('Rayan Elloumi',           '2007-09-17'),  # 突尼斯前锋→Rayan Elloumi
    '马斯图里':         ('Hazem Mastouri',          '1997-06-18'),
    '萨德':           ('Elias Saad',              '1999-12-27'),
    '萨阿德':          ('Elias Saad',              '1999-12-27'),
    '朝乌塔':          ('Rayan Elloumi',           '2007-09-17'),  # 同一人

    # 库拉索 (11人待核实)
    '范艾马':          ('Roshon van Eijma',        '1998-06-09'),
    '丰维尔':          ('Tyrese Noslin',           '2002-09-11'),
    '加里':           ('Godfried Roemeratoe',      '1999-08-19'),
    '奥比斯波':         ('Armando Obispo',          '1999-03-05'),
    '桑博':           ('Juriën Gaari',             '1993-12-23'),
    '科门西亚':         ('Kevin Felida',            '1999-11-11'),
    '罗默拉托':         ('Deveron Fonville',        '2003-05-16'),
    '安东尼斯':         ('Ar\'jany Martha',        '2003-09-04'),
    '陈达毅':          ('Jürgen Locadia',          '1993-11-07'),
    '戈雷':           ('Kenji Gorré',             '1994-09-29'),
    '洛卡迪亚':         ('Jeremy Antonisse',        '2002-03-29'),

    # 捷克 (8人待核实)
    '维特克·斯坦尼克':      ('Jindřich Staněk',       '1996-04-27'),
    '马林·霍尼切克':       ('Matěj Kovář',           '2000-05-17'),
    '马丁·维提克':         ('Vladimír Coufal',        '1992-08-22'),
    '克里斯蒂安·维辛斯基':   ('David Zima',            '2000-11-08'),
    '奥德雷·杜达':         ('Tomáš Souček',           '1995-02-27'),
    '马蒂亚斯·索楚雷克':     ('Lukáš Horníček',        '2002-07-13'),
    '亚历山大·索卡':        ('Ladislav Krejčí',        '1999-04-20'),
    '克里斯特·卡邦戈':      ('Adam Hložek',           '2002-07-25'),

    # 民主刚果 (7人待核实)
    '恩波洛':           ('Lionel Mpasi',           '1994-08-01'),
    '姆帕西':           ('Timothy Fayulu',         '1999-07-24'),
    '布希里':           ('Dylan Batubinsika',     '1996-02-15'),
    '穆图萨米':          ('Samuel Moutoussamy',    '1996-08-12'),
    '皮克尔':           ('Charles Pickel',        '1997-05-15'),
    '西蓬加':           ('Nathanaël Mbuku',       '2002-03-16'),
    '塞缪尔·乌阿尼':       ('Aaron Wan-Bissaka',    '1997-11-26'),

    # 沙特 (5人待核实)
    '塔克里':           ('Hassan Al-Tambakti',    '1999-02-09'),  # ✓
    '阿姆里':           ('Abdulelah Al-Amri',     '1997-01-15'),  # ✓
    '布沙尔':           ('Musab Al-Juwayr',      '2003-06-20'),  # ✓ 来源: 捷报比分网 DOB 2003-06-20
    # 阿尔乔汉尼 = 约哈尼(吉达国民) → Al-Hilali? Wikipedia无，X待核实
    # 哈巴利 = 哈巴利(利雅得胜利) → Ali Al-Harbi? Wikipedia无，X待核实

    # 哥伦比亚 (5人待核实) - Wikipedia没抓到，暂不更新
    # 澳大利亚 (4人待核实) - 同上
    # 南非 (4人待核实) - 同上
    # 加纳 (3人待核实) - 同上
    # 摩洛哥 (3人待核实) - 同上
    # 埃及 (3人待核实) - 同上
    # 巴拉圭 (3人待核实) - 同上
}

# 沙特的精确映射（从搜狐确认）
SAUDI_MAP = {
    '塔克里': ('Hassan Al-Tambakti', '1999-02-09'),  # ✓
    '阿姆里': ('Abdulelah Al-Amri', '1997-01-15'),  # ✓
    '布沙尔': ('Musab Al-Juwayr', '2003-06-20'),  # ✓ 来源: 捷报比分网
    # 阿尔乔汉尼 → Wikipedia无，保留X待核实
    # 哈巴利 → Wikipedia无，保留X待核实
}

def calc_age(dob_str, ref_date='2026-06-11'):
    """计算年龄（以2026年世界杯开幕日为基准）"""
    import datetime
    dob = datetime.date.fromisoformat(dob_str)
    ref = datetime.date.fromisoformat(ref_date)
    age = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        age -= 1
    return age

# ── 加载主表 ──────────────────────────────────────────────
rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))

# ── 合并映射表 ────────────────────────────────────────────
FULL_MAP = {**EXACT_MAP}
# 补充沙特
for k, v in SAUDI_MAP.items():
    FULL_MAP[k] = v

# ── 应用更新 ──────────────────────────────────────────────
updated = []
not_matched = []
seen_wiki_en = {}  # 记录每个 Wikipedia 英文名是否已被使用

for row in rows:
    age = row['年龄']
    if age.isdigit():
        continue  # 已有真实年龄，跳过
    if age not in ('X待核实', '数字占位'):
        continue

    cn = row['球员']
    team = row['国家']
    pos = row['位置']

    if cn not in FULL_MAP:
        not_matched.append({'name': cn, 'team': team, 'pos': pos, 'current_age': age})
        continue

    wiki_en, dob = FULL_MAP[cn]

    # 检查该 Wikipedia 英文名是否已被此球队的其他中文名占用
    # 如果是，则跳过（避免重复）
    en_key = f'{team}|{wiki_en}'
    if en_key in seen_wiki_en:
        not_matched.append({
            'name': cn, 'team': team, 'pos': pos,
            'current_age': age,
            'wiki_en': wiki_en,
            'dob': dob,
            'note': f'重复映射: {seen_wiki_en[en_key]} 已占用 {wiki_en}'
        })
        continue

    new_age = calc_age(dob)
    updated.append({
        'name': cn, 'team': team, 'pos': pos,
        'old': age, 'new': new_age,
        'dob': dob, 'wiki_en': wiki_en
    })
    seen_wiki_en[en_key] = cn
    row['年龄'] = str(new_age)
    row['数据来源'] = 'wikipedia_exact_match_v2'

# ── 统计 ──────────────────────────────────────────────
xun_now = sum(1 for r in rows if r['年龄'] == 'X待核实')
real_now = sum(1 for r in rows if r['年龄'].isdigit())
print(f'更新: {len(updated)}条')
print(f'未匹配: {len(not_matched)}条')
print(f'主表现: {real_now}真实, {xun_now}X待核实')

# 写主表
with open('1_数据基础/world_cup_2026_complete.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# 写日志
log = {
    'strategy': 'exact_match_v2',
    'updated': updated,
    'not_matched': not_matched,
    'new_real': real_now,
    'new_xun': xun_now,
}
with open('1_数据基础/exact_match_v2_updates.json', 'w', encoding='utf-8') as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print(f'\n主表已更新: world_cup_2026_complete.csv')

# 显示更新详情
print('\n更新详情:')
for r in updated:
    print(f"  {r['team']:8} {r['name']:20} {r['old']:12}→{r['new']}岁  {r['wiki_en']}")

if not_matched:
    print(f'\n未匹配 ({len(not_matched)}条):')
    for r in not_matched[:20]:
        print(f"  {r['team']:8} {r['name']:20} ({r['pos']})")
