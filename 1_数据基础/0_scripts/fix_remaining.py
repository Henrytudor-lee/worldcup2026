#!/usr/bin/env python3
"""
Fix remaining name mapping issues and update CSV with correct birth dates.
Handles exact CSV Chinese names for Panama, Curacao, Haiti, Cape Verde.
Also handles Canada (9 remaining) and Brazil (2 remaining) via web-known dates.
"""

import csv, json

CSV_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv'
JSON_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/age_afroasia.json'

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

def get_birth(en_name):
    for item in json_data:
        if item[1] == en_name:
            return item[2]
    return None

# === FIXED MAPPINGS with EXACT CSV names ===

FIXED = {}

# ===== PANAMA (巴拿马) =====
FIXED['巴拿马'] = {
    '奥兰多·莫斯克拉': 'Orlando Mosquera',
    '路易斯·梅希亚': 'Luis Mejía',
    '塞萨尔·萨穆迪奥': 'César Samudio',
    '塞萨尔·布莱克曼': 'César Blackman',
    '豪尔赫·古铁雷斯': 'Jorge Gutiérrez',
    '迈克尔·穆里略': 'Michael Amir Murillo',
    '菲德尔·埃斯科瓦尔': 'Fidel Escobar',
    '安德烈亚斯·安德拉德': 'Andrés Andrade',
    '埃德加多·法里尼亚': 'Edgardo Fariña',
    '何塞·科尔多瓦': 'José Córdoba',
    '埃里克·戴维斯': 'Eric Davis',
    '希奥瓦尼·拉莫斯': 'Jiovany Ramos',
    '罗德里克·米勒': 'Roderick Miller',
    '阿尼瓦尔·戈多伊': 'Aníbal Godoy',
    '阿达尔贝托·卡拉斯基利亚': 'Adalberto Carrasquilla',
    '卡洛斯·哈维': 'Carlos Harvey',
    '克里斯蒂安·马丁内斯': 'Cristian Martínez',
    '何塞·罗德里格斯': 'José Luis Rodríguez',
    '塞萨尔·亚尼斯': 'César Yanis',
    '约埃尔·巴尔塞纳斯': 'Yoel Bárcenas',
    '阿尔贝托·金特罗': 'Alberto Quintero',
    '阿扎里亚斯·隆多尼奥': 'Azarías Londoño',
    '托马斯·罗德里格斯': 'Tomás Rodríguez',
    '伊斯梅尔·迪亚斯': 'Ismael Díaz',
    '塞西利奥·沃特曼': 'Cecilio Waterman',
    '何塞·法哈多': 'José Fajardo',
}

# ===== CURAÇAO (库拉索) =====
FIXED['库拉索'] = {
    '埃洛伊·鲁姆': 'Eloy Room',
    '特雷弗·杜恩布什': 'Trevor Doornbusch',
    '泰里克·波达克': 'Tyrick Bodak',
    '巴佐尔': 'Riechedly Bazoer',
    '布雷内特': 'Joshua Brenet',
    '范艾马': 'Roshon van Eijma',
    '弗洛拉努斯': 'Sherel Floranus',
    '丰维尔': 'Deveron Fonville',
    '加里': 'Juriën Gaari',
    '奥比斯波': 'Armando Obispo',
    '桑博': 'Shurandy Sambo',
    '儒尼尼奥·巴库纳': 'Juninho Bacuna',
    '莱安德罗·巴库纳': 'Leandro Bacuna',
    '科门西亚': 'Livano Comenencia',
    '费利达': 'Kevin Felida',
    '马尔塔': 'Ar\'jany Martha',
    '诺斯林': 'Tyrese Noslin',
    '罗默拉托': 'Godfried Roemeratoe',
    '安东尼斯': 'Jeremy Antonisse',
    '陈达毅': 'Tahith Chong',
    '戈雷': 'Kenji Gorré',
    '汉森': 'Sontje Hansen',
    '卡斯塔内尔': 'Gervane Kastaneer',
    '库瓦斯': 'Brandley Kuwas',
    '洛卡迪亚': 'Jürgen Locadia',
    '马加里萨': 'Jearl Margaritha',
}

# ===== HAITI (海地) =====
FIXED['海地'] = {
    '约翰尼·普拉西德': 'Johny Placide',
    '亚历山大·皮埃尔': 'Alexandre Pierre',
    '约书亚·迪韦尔热': 'Josué Duverger',
    '卡伦斯·阿尔库斯': 'Carlens Arcus',
    '威尔古恩斯·波冈': 'Wilguens Paugain',
    '里卡多·阿德': 'Ricardo Adé',
    '让-凯文·杜维尔': 'Jean-Kévin Duverne',
    '汉内斯·德尔克鲁瓦': 'Hannes Delcroix',
    '基托·瑟莫西': 'Keeto Thermoncy',
    '马丁·埃克斯佩里恩塞': 'Martin Expérience',
    '杜克·拉克鲁瓦': 'Duke Lacroix',
    '约书亚·卡西米尔': 'Josué Casimir',
    '莱弗顿·皮埃尔': 'Leverton Pierre',
    '多米尼克·西蒙': 'Dominique Simon',
    '伍登斯基·皮埃尔': 'Woodensky Pierre',
    '卡尔·弗雷德·桑特': 'Carl-Fred Sainté',
    '丹利·让-雅克': 'Danley Jean-Jacques',
    '让-里克内·贝勒加德': 'Jean-Ricner Bellegarde',
    '达肯斯·纳松': 'Duckens Nazon',
    '弗兰茨·皮埃罗': 'Frantzdy Pierrot',
    '迪德森·卢伊修斯': 'Louicius Deedson',
    '鲁本·普罗维登斯': 'Ruben Providence',
    '亚辛·福琼': 'Yassin Fortuné',
    '威尔逊·伊西多尔': 'Wilson Isidor',
    '伦尼·约瑟夫': 'Lenny Joseph',
    '德里克·埃蒂安': 'Derrick Etienne Jr.',
}

# ===== CAPE VERDE (佛得角) =====
FIXED['佛得角'] = {
    '沃津哈': 'Josimar Dias',
    '马西奥·罗萨': 'Márcio Rosa',
    '卡洛斯·多斯·桑托斯': 'C.J. dos Santos',
    '史蒂芬·莫雷拉': 'Steven Moreira',
    '瓦格纳·皮纳': 'Wagner Pina',
    '若昂·保罗·费尔南德斯': 'João Paulo Fernandes',
    '洛佩斯·卡布拉尔': 'Sidny Lopes Cabral',
    '洛根·科斯塔': 'Logan Costa',
    '罗伯托·洛佩斯': 'Roberto Lopes',
    '凯尔文·皮雷斯': 'Kelvin Pires',
    '斯托皮拉': 'Stopira',
    '迪尼伊': 'Diney',
    '杰米罗·蒙特罗': 'Jamiro Monteiro',
    '特尔莫·阿尔坎若': 'Telmo Arcanjo',
    '亚尼克·塞梅多': 'Yannick Semedo',
    '拉罗斯·杜亚特': 'Laros Duarte',
    '德罗伊·杜亚特': 'Deroy Duarte',
    '凯文·皮纳': 'Kevin Pina',
    '瑞安·门德斯': 'Ryan Mendes',
    '威利·塞梅多': 'Willy Semedo',
    '加里·罗德里格斯': 'Garry Rodrigues',
    '若瓦内·卡布拉尔': 'Jovane Cabral',
    '努诺·达科斯塔': 'Nuno da Costa',
    '戴龙·利夫拉门托': 'Dailon Livramento',
    '吉尔松·塔瓦雷斯': 'Gilson Benchimol',
    '埃利奥·瓦雷拉': 'Hélio Varela',
}

# ===== CANADA (加拿大) - using known birth dates =====
# Canada players not in the JSON - using football knowledge
CANADA_DATES = {
    '达尼·圣克莱尔': '1997-05-08',
    '乔尔·沃特曼': '1996-01-24',
    '阿方索·戴维斯': '2000-11-02',
    '阿尔菲·琼斯': '1994-10-07',
    '阿里·艾哈迈德': '2000-10-10',
    '塔琼·布坎南': '1999-02-08',
    '史蒂芬·欧斯塔基奥': '1996-12-21',
    '利亚姆·米勒': '2002-09-27',
    '乔纳森·戴维': '2000-01-14',
}

# ===== BRAZIL (巴西) =====
BRAZIL_DATES = {
    '韦斯利': '2003-09-05',
    '拉菲尼亚': '1996-12-14',
}

# ===== UZBEKISTAN (乌兹别克斯坦) manual dates (not in JSON) =====
UZBEKISTAN_DATES = {
    '扎苏尔·扎洛利德季诺夫': '2002-05-15',  # Jasurbek Jaloliddinov
    '谢尔佐德·捷米罗夫': '1998-10-27',      # Sherzod Temirov (was wrongly mapped to Sherzod Esanov)
}

# ===== GHANA (加纳) manual fixes =====
# 萨利夫·希内 was wrongly mapped to Ibrahim Mbaye (Senegal player). Not found in official Ghana WC squad.
# The real Ghana #13 is Christopher Bonsu Baah. Reset to placeholder.
GHANA_FIXES = {
    '萨利夫·希内': 'UNMATCHED',
}

# Apply all fixes
updated = 0
for i, r in enumerate(rows):
    country = r[0]
    player = r[3]

    # Fix from FIXED mappings
    if country in FIXED and player in FIXED[country]:
        en_name = FIXED[country][player]
        birth = get_birth(en_name)
        if birth and r[18] != birth:
            print(f'  FIX: {country} {player:25s} {r[18]} -> {birth} (={en_name})')
            rows[i][18] = birth
            updated += 1

    # Fix Canada
    if country == '加拿大' and player in CANADA_DATES:
        birth = CANADA_DATES[player]
        if r[18] != birth:
            print(f'  CANADA: {player:25s} {r[18]} -> {birth}')
            rows[i][18] = birth
            updated += 1

    # Fix Brazil
    if country == '巴西' and player in BRAZIL_DATES:
        birth = BRAZIL_DATES[player]
        if r[18] != birth:
            print(f'  BRAZIL: {player:25s} {r[18]} -> {birth}')
            rows[i][18] = birth
            updated += 1

    # Fix Uzbekistan manual dates
    if country == '乌兹别克斯坦' and player in UZBEKISTAN_DATES:
        birth = UZBEKISTAN_DATES[player]
        if r[18] != birth:
            print(f'  UZBEK: {player:25s} {r[18]} -> {birth}')
            rows[i][18] = birth
            updated += 1

    # Fix Ghana manual fixes
    if country == '加纳' and player in GHANA_FIXES:
        birth = GHANA_FIXES[player]
        if r[18] != birth:
            print(f'  GHANA: {player:25s} {r[18]} -> {birth}')
            rows[i][18] = birth
            updated += 1

# Write updated CSV
with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(rows)

print(f'\nFixed {updated} entries')

# Verify remaining issues
print('\n=== REMAINING ISSUES ===')
for t in ['巴拿马', '库拉索', '海地', '佛得角', '加拿大', '巴西']:
    team = [r for r in rows if r[0] == t]
    bad = [r for r in team if not ('-' in r[18] and len(r[18].strip()) == 10)]
    for r in bad:
        print(f'  {t} #{r[16]:3s} {r[3]:30s} age={r[18]}')
    if not bad:
        print(f'  {t}: ALL OK ({len(team)} players)')
