"""
apply_wiki_squad_v4.py
用 Wikipedia Squad 数据更新主表年龄
策略：中文名 → 拼音近似 → Wikipedia 英文名模糊匹配
"""
import json, csv, re, os
from difflib import SequenceMatcher

# ── pinyin 转换 ──────────────────────────────────────────────
CN_CHARS = set('\u4e00-\u9fff')

def is_cjk(ch):
    return '\u4e00' <= ch <= '\u9fff'

def cn_to_pinyin(name):
    """把中文名转成近似拼音字符串（用于匹配）"""
    # 常用姓氏拼音
    surname_map = {
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
        '顾':'Gu','孟':'Meng','戴':'Dai','姚':'Yao','卢':'Lu','姜':'Jiang','钟':'Zhong',
        '郝':'Hao','翁':'Weng','傅':'Fu','任':'Ren','饶':'Rao','孟':'Meng','席':'Xi',
        '古':'Gu','兰':'Lan','奥':'Ao','贝':'Bei','贝':'Bei','马':'Ma','苗':'Miao',
        '凤':'Feng','花':'Hua','芳':'Fang','佘':'She','沙':'Sha','党':'Dang','翟':'Zhai',
        '齐':'Qi','康':'Kang','伍':'Wu','余':'Yu','元':'Yuan','顾':'Gu','佟':'Tong',
        '费':'Fei','蒙':'Meng','申':'Shen','莫':'Mo','西':'Xi','蒙':'Meng','德':'De',
    }
    parts = []
    i = 0
    name = name.strip()
    while i < len(name):
        ch = name[i]
        if is_cjk(ch):
            # 尝试两字姓氏
            if i == 0 and i+1 < len(name) and name[i:i+2] in surname_map:
                parts.append(surname_map[name[i:i+2]])
                i += 2
            elif ch in surname_map:
                parts.append(surname_map[ch])
                i += 1
            else:
                parts.append(ch)
                i += 1
        elif ch == '·' or ch == '.':
            i += 1  # 跳过间隔号
        else:
            # 非中文字符（可能已是拼音或英文）
            parts.append(ch)
            i += 1
    s = ''.join(parts)
    # 提取拼音部分（去掉数字和特殊字符）
    s = re.sub(r'[^a-zA-Z]', '', s)
    return s.lower()


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ── 加载数据 ──────────────────────────────────────────────────
wiki_data = json.load(open('1_数据基础/wiki_squad_v4_results.json'))
rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))

# 建立 Wikipedia 数据索引：{国家: [(英文名, DOB, age), ...]}
wiki_index = {}
for team, info in wiki_data.items():
    wiki_index[team] = []
    for p in info.get('players', []):
        en = p['en'].strip()
        dob = p['dob']
        age = p['age']
        if en and dob and age:
            wiki_index[team].append({'en': en, 'dob': dob, 'age': age})

print(f'主表球员: {len(rows)}  维基索引队: {len(wiki_index)}')

# ── 匹配并更新 ──────────────────────────────────────────────
updated = []    # 成功更新的
unmatched = []  # 未匹配的
replaced = []   # 有旧数据的（年龄被新数据覆盖）
already_real = [] # 原本就是真实年龄的

for row in rows:
    team = row['国家']
    cn_name = row['球员']  # 中文名（主表）
    old_age = row['年龄']

    if team not in wiki_index:
        unmatched.append(row)
        continue

    candidates = wiki_index[team]

    # 策略1：中文名全等匹配（用 cn_name 直接找）
    matched_en = None
    matched_dob = None
    matched_age = None
    best_score = 0

    for c in candidates:
        en = c['en']

        # 完全匹配：英文名包含中文名拼音
        cn_pinyin = cn_to_pinyin(cn_name)
        en_clean = re.sub(r'[^a-zA-Z]', '', en).lower()

        # 中文名拼音 vs 英文名
        score1 = similarity(cn_pinyin, en_clean)

        # 中文名拼音分段 vs 英文名（姓+名）
        score2 = 0.0
        if ' ' in en_clean or '-' in en_clean:
            en_parts = re.split(r'[\s\-]+', en_clean)
            cn_parts = []
            # 尝试拆分中文名
            i = 0
            temp = ''
            for ch in cn_name:
                if is_cjk(ch):
                    p = cn_to_pinyin(ch)
                    if p:
                        cn_parts.append(p)
                elif ch == '·':
                    continue
                else:
                    temp += ch
            if len(cn_parts) >= 2:
                # 比较相邻组合
                for i in range(len(cn_parts)-1):
                    pair = cn_parts[i] + cn_parts[i+1]
                    for ep in en_parts:
                        sc = similarity(pair, ep)
                        if sc > score2:
                            score2 = sc

        score = max(score1, score2 * 1.2)  # 分段匹配加权

        # 同时检查：如果英文名部分匹配中文名
        if cn_pinyin and len(cn_pinyin) > 2:
            if cn_pinyin in en_clean or en_clean in cn_pinyin:
                score = max(score, 0.85)

        if score > best_score:
            best_score = score
            matched_en = en
            matched_dob = c['dob']
            matched_age = c['age']

    # 阈值：相似度 > 0.55 才接受
    if best_score >= 0.55 and matched_dob:
        # 检查是否替换了旧数据
        is_new = (old_age == 'X待核实' or old_age == '数字占位')
        if old_age.isdigit():
            replaced.append({'name': cn_name, 'team': team, 'old': old_age, 'new': str(matched_age), 'en': matched_en})
        elif old_age == 'X待核实':
            updated.append({'name': cn_name, 'team': team, 'age': matched_age, 'dob': matched_dob, 'en': matched_en, 'score': round(best_score, 2)})
        else:
            updated.append({'name': cn_name, 'team': team, 'age': matched_age, 'dob': matched_dob, 'en': matched_en, 'score': round(best_score, 2)})

        row['年龄'] = str(matched_age)
        row['数据来源'] = 'wikipedia_squad_v4'
    else:
        unmatched.append(row)

print(f'\\n=== 匹配结果 ===')
print(f'成功更新: {len(updated)} + 替换旧数据: {len(replaced)} = {len(updated)+len(replaced)}')
print(f'未匹配: {len(unmatched)}')
if replaced:
    print('\n替换旧数据 (前10):')
    for r in replaced[:10]:
        t = r['team'].ljust(10); n = r['name'].ljust(20)
        print(f'  {t}{n}{str(r["old"]).ljust(4)}→{str(r["new"]).ljust(4)} ({r["en"]})')

if updated:
    print('\n更新样本 (前10):')
    for r in updated[:10]:
        t = r['team'].ljust(10); n = r['name'].ljust(20)
        print(f'  {t}{n} age={str(r["age"]).ljust(3)} score={r["score"]} ({r["en"]})')

# ── 写回主表 ──────────────────────────────────────────────
with open('1_数据基础/world_cup_2026_complete.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

# 写更新记录
update_log = {
    'strategy': 'wikipedia_squad_v4_fuzzy_match',
    'total_updated': len(updated) + len(replaced),
    'unmatched': len(unmatched),
    'replaced': replaced,
    'updated': updated[:50],  # 最多写50条
}
with open('1_数据基础/wiki_squad_v4_updates.json', 'w', encoding='utf-8') as f:
    json.dump(update_log, f, ensure_ascii=False, indent=2)

print(f'\\n✅ 主表已更新: world_cup_2026_complete.csv')
print(f'   更新日志: wiki_squad_v4_updates.json')
