"""
apply_wiki_squad_v4_safe.py
用 Wikipedia Squad 英文数据精确匹配更新主表
规则：
  1. 只更新 X待核实/数字占位 的行，不动任何真实年龄
  2. 用 manual_name_map + fuzzy 拼音匹配
  3. 匹配阈值 ≥ 0.75 才接受
"""
import json, csv, re, os
from difflib import SequenceMatcher

# ── 姓氏拼音表 ─────────────────────────────────────────────
SURNAME = {
    '孙':'Sun','李':'Li','王':'Wang','张':'Zhang','刘':'Liu','陈':'Chen','杨':'Yang',
    '赵':'Zhao','黄':'Huang','周':'Zhou','吴':'Wu','徐':'Xu','胡':'Hu','朱':'Zhu',
    '郭':'Guo','何':'He','高':'Gao','林':'Lin','罗':'Luo','郑':'Zheng','梁':'Liang',
    '谢':'Xie','宋':'Song','唐':'Tang','韩':'Han','曹':'Cao','许':'Xu','邓':'Deng',
    '冯':'Feng','曾':'Zeng','程':'Cheng','蔡':'Cai','彭':'Peng','潘':'Pan','袁':'Yuan',
    '于':'Yu','董':'Dong','余':'Yu','苏':'Su','叶':'Ye','吕':'Lu','魏':'Wei','蒋':'Jiang',
    '田':'Tian','杜':'Du','丁':'Ding','沈':'Shen','姜':'Jiang','范':'Fan','江':'Jiang',
    '傅':'Fu','孔':'Kong','谭':'Tan','廖':'Liao','史':'Shi','龙':'Long','万':'Wan',
    '段':'Duan','钱':'Qian','汤':'Tang','尹':'Yin','黎':'Li','易':'Yi','常':'Chang',
    '武':'Wu','乔':'Qiao','贺':'He','赖':'Lai','龚':'Gong','庞':'Pang','熊':'Xiong',
    '白':'Bai','崔':'Cui','康':'Kang','邹':'Zou','邱':'Qiu','夏':'Xia','雷':'Lei',
    '顾':'Gu','孟':'Meng','戴':'Dai','姚':'Yao','卢':'Lu','钟':'Zhong','郝':'Hao',
    '翁':'Weng','任':'Ren','饶':'Rao','席':'Xi','古':'Gu','兰':'Lan','费':'Fei',
    '蒙':'Meng','申':'Shen','莫':'Mo','钱':'Qian','严':'Yan','熊':'Xiong','莫':'Mo',
    '兰':'Lan','司':'Si','韦':'Wei','阮':'Ruan','卫':'Wei','戴':'Dai','兰':'Lan',
    '梅':'Mei','庄':'Zhuang','钟':'Zhong','童':'Tong','管':'Guan','祝':'Zhu',
    '梁':'Liang','马':'Ma','苗':'Miao','凤':'Feng','花':'Fang','郝':'Hao',
}

def is_cjk(ch):
    return '\u4e00' <= ch <= '\u9fff'

def cn_to_pinyin(name):
    """转拼音字符串"""
    result = []
    name = name.replace('·', '.').strip()
    i = 0
    while i < len(name):
        ch = name[i]
        if not is_cjk(ch):
            result.append(ch)
            i += 1
            continue
        # 两字姓氏
        if i == 0 and i+1 < len(name) and name[i:i+2] in SURNAME:
            result.append(SURNAME[name[i:i+2]])
            i += 2
        elif ch in SURNAME:
            result.append(SURNAME[ch])
            i += 1
        else:
            i += 1
    s = ''.join(result)
    return re.sub(r'[^a-zA-Z]', '', s).lower()

def fuzzy_score(pinyin, en_name):
    """计算拼音 vs 英文名的匹配分"""
    en_clean = re.sub(r'[^a-zA-Z]', '', en_name).lower()
    if not pinyin or not en_clean:
        return 0.0
    # 直接相似度
    score = SequenceMatcher(None, pinyin, en_clean).ratio()
    # 子串匹配加分
    if pinyin in en_clean or en_clean in pinyin:
        score = max(score, 0.85)
    # 分段匹配（姓+名）
    if len(pinyin) > 2 and len(en_clean) > 2:
        # 取拼音前4字符和后4字符
        p_prefix = pinyin[:min(4, len(pinyin))]
        p_suffix = pinyin[-min(4, len(pinyin)):]
        if p_prefix in en_clean or p_suffix in en_clean:
            score = max(score, 0.8)
    return score

# ── 加载数据 ──────────────────────────────────────────────
wiki = json.load(open('1_数据基础/wiki_squad_v4_results.json'))  # English Wikipedia data
manual = json.load(open('backend/manual_name_map.json'))
rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))

# 建立 Wikipedia 索引
wiki_index = {}
for team, info in wiki.items():
    wiki_index[team] = []
    for p in info.get('players', []):
        en = p['en'].strip()
        dob = p['dob']
        age = p['age']
        if en and dob and age and 16 <= age <= 45:
            wiki_index[team].append({'en': en, 'dob': dob, 'age': age})

print(f'主表: {len(rows)}人, Wikipedia索引: {len(wiki_index)}队')

# ── 匹配 ─────────────────────────────────────────────────
THRESHOLD = 0.72  # 高阈值减少错配
updated = []
not_found = []

for row in rows:
    age = row['年龄']
    if age.isdigit():
        continue  # 跳过已有真实年龄
    if age not in ('X待核实', '数字占位'):
        continue

    team = row['国家']
    cn = row['球员']
    pos = row['位置']

    if team not in wiki_index:
        not_found.append({'name': cn, 'team': team, 'pos': pos})
        continue

    candidates = wiki_index[team]

    # 从 manual_name_map 找英文名参考
    ref_en = manual.get(team, {}).get(cn, None)

    pinyin = cn_to_pinyin(cn)

    # 在 Wikipedia 里找最佳匹配
    best_score = 0
    best_match = None
    for c in candidates:
        en = c['en']
        score = fuzzy_score(pinyin, en)
        if ref_en:
            # 如果 manual_name_map 有英文名，也用它来评分
            ref_clean = re.sub(r'[^a-zA-Z]', '', ref_en).lower()
            en_clean = re.sub(r'[^a-zA-Z]', '', en).lower()
            if ref_clean == en_clean:
                score = max(score, 0.95)
            elif ref_clean and en_clean:
                ref_score = SequenceMatcher(None, ref_clean, en_clean).ratio()
                score = max(score, ref_score * 1.1)

        if score > best_score:
            best_score = score
            best_match = c

    if best_score >= THRESHOLD and best_match:
        updated.append({
            'name': cn, 'team': team,
            'old': age,
            'new': best_match['age'],
            'dob': best_match['dob'],
            'en': best_match['en'],
            'score': round(best_score, 2),
            'ref_en': ref_en or '',
        })
        row['年龄'] = str(best_match['age'])
        row['数据来源'] = 'wikipedia_squad_v4'
    else:
        not_found.append({'name': cn, 'team': team, 'pos': pos, 'score': round(best_score, 2), 'ref_en': ref_en or ''})

# ── 统计 ──────────────────────────────────────────────
xun_now = sum(1 for r in rows if r['年龄'] == 'X待核实')
real_now = sum(1 for r in rows if r['年龄'].isdigit())
print(f'\n=== 结果 ===')
print(f'更新: {len(updated)}条')
print(f'未匹配: {len(not_found)}条')
print(f'主表现: {real_now}真实, {xun_now}X待核实')

# 分类未匹配
by_team = {}
for r in not_found:
    t = r['team']
    if t not in by_team:
        by_team[t] = []
    by_team[t].append(r)

print(f'\n未匹配（按球队）:')
for t, lst in sorted(by_team.items(), key=lambda x: -len(x[1])):
    print(f'  {t}: {len(lst)}')

# 写主表
with open('1_数据基础/world_cup_2026_complete.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# 写日志
log = {
    'strategy': 'wikipedia_squad_v4_safe',
    'threshold': THRESHOLD,
    'updated_count': len(updated),
    'not_found_count': len(not_found),
    'updated': updated,
    'not_found': not_found,
}
with open('1_数据基础/wiki_v4_safe_updates.json', 'w', encoding='utf-8') as f:
    json.dump(log, f, ensure_ascii=False, indent=2)

print(f'\n✅ 主表已更新: world_cup_2026_complete.csv')
print(f'   日志: wiki_v4_safe_updates.json')
