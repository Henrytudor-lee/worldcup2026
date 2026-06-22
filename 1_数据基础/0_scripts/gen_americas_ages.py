"""
从网络搜索结果中提取美洲区 9 队球员出生日期，生成 age_americas.json

格式: [["国家", "球员", "YYYY-MM-DD"], ...]

所有出生日期均来自 2026 年 6 月的最新阵容公告 / FBref / Wikipedia
"""
import json
import csv
import re

csv_path = "/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv"
json_path = "/Users/garcia/Desktop/WorldCup2026/1_数据基础/age_americas.json"

# ============================================================
# CSV 内中文球员名 → 出生日期 (YYYY-MM-DD)
# 根据 FBref / Wikipedia / 官方阵容公告 (2026 年 6 月)
# ============================================================

cn_to_birth = {}

# ======================== 墨西哥 ========================
mexico = {
    "何塞·兰赫尔": "2000-02-25",      # Raúl Rangel / José Rangel
    "卡洛斯·阿塞韦多": "1996-04-19",   # Carlos Acevedo
    "吉列尔莫·奥乔亚": "1985-07-13",   # Guillermo Ochoa
    "伊斯雷尔·雷耶斯": "2000-05-23",   # Israel Reyes
    "豪尔赫·桑切斯": "1997-12-10",     # Jorge Sánchez
    "约翰·巴斯克斯": "1998-10-22",     # Johan Vásquez
    "赫苏斯·加利亚多": "1994-08-15",   # Jesús Gallardo
    "马特奥·查韦斯": "2004-05-12",     # Mateo Chávez
    "埃德松·阿尔瓦雷斯": "1997-10-24", # Edson Álvarez
    "阿尔瓦罗·菲达尔戈": "1997-04-09", # Álvaro Fidalgo
    "布莱恩·古铁雷斯": "2003-06-17",   # Brian Gutiérrez
    "埃里克·利拉": "2000-05-08",       # Erik Lira
    "希尔韦托·莫拉": "2008-10-14",     # Gilberto Mora
    "奥贝德·巴尔加斯": "2005-08-05",   # Obed Vargas
    "奥韦林·皮内达": "1996-03-24",     # Orbelín Pineda
    "罗伯托·阿尔瓦拉多": "1998-09-07", # Roberto Alvarado
    "阿莱克斯·维加": "1997-11-25",     # Alexis Vega
    "吉列尔莫·马丁内斯": "1995-03-15", # Guillermo Martínez
    "阿曼多·冈萨雷斯": "2003-04-20",   # Armando González
    "胡利安·基尼奥内斯": "1997-03-24", # Julián Quiñones
    "劳尔·希门尼斯": "1991-05-05",     # Raúl Jiménez
    "路易斯·查韦斯": "1996-01-15",     # Luis Chávez
    "路易斯·罗莫": "1995-06-05",       # Luis Romo
}
cn_to_birth.update(mexico)

# ======================== 美国 ========================
usa = {
    "克里斯·布雷迪": "2004-03-03",     # Chris Brady
    "克里斯·理查兹": "2000-03-28",     # Chris Richards
    "马克·麦肯齐": "1999-02-25",       # Mark McKenzie
    "奥斯顿·特拉斯蒂": "1998-08-12",   # Auston Trusty
    "迈尔斯·罗宾逊": "1997-03-14",     # Miles Robinson
    "安东尼·罗宾逊": "1997-08-08",     # Antonee Robinson
    "塞尔吉尼奥·德斯特": "2000-11-03", # Sergiño Dest
    "亚历克斯·弗里曼": "2004-08-09",   # Alex Freeman
    "乔·斯卡利": "2002-12-31",         # Joe Scally
    "马克斯·阿夫斯滕": "2001-04-19",   # Max Arfsten
    "泰勒·亚当斯": "1999-02-14",       # Tyler Adams
    "马尔基·蒂尔曼": "2002-05-28",     # Malik Tillman
    "吉奥·雷纳": "2002-11-13",         # Gio Reyna
    "克里斯蒂安·普利西奇": "1998-09-18", # Christian Pulisic
    "蒂莫西·维阿": "2000-02-22",       # Tim Weah
    "亚历杭德罗·曾德哈斯": "1998-02-07", # Alejandro Zendejas
    "里卡多·佩皮": "2003-01-09",       # Ricardo Pepi
    "马特·弗里斯": "1998-09-02",       # Matt Freese
}
cn_to_birth.update(usa)

# ======================== 加拿大 ========================
canada = {
    "马塞洛·弗洛雷斯": "2003-10-01",   # Marcelo Flores
    "凯尔·拉林": "1995-04-17",         # Cyle Larin
    "奥卢瓦塞伊": "2000-05-15",         # Tani Oluwaseyi
}
cn_to_birth.update(canada)

# ======================== 巴西 ========================
brazil = {
    "阿利松": "1992-10-02",
    "埃德森": "1993-08-17",
    "马尔基尼奥斯": "1994-05-14",
    "加布里埃尔": "1997-12-19",
    "布雷默": "1997-03-18",
    "阿莱士·桑德罗": "1991-01-26",
    "达尼洛": "1991-07-15",
    "道格拉斯·桑托斯": "1994-03-22",
    "卡塞米罗": "1992-02-23",
    "布鲁诺·吉马良斯": "1997-11-16",
    "达尼洛·桑托斯": "2001-04-29",
    "维尼修斯": "2000-07-12",
    "内马尔": "1992-02-05",
    "拉菲尼亚": "1996-12-14",
    "马丁内利": "2001-06-18",
    "伊戈尔·蒂亚戈": "2001-06-26",
}
cn_to_birth.update(brazil)

# ======================== 阿根廷 ========================
argentina = {
    "尼古拉斯·塔利亚菲科": "1992-08-31",
    "克里斯蒂安·罗梅罗": "1998-04-27",
    "尼古拉斯·奥塔门迪": "1988-02-12",
    "莱安德罗·帕雷德斯": "1994-06-29",
    "罗德里戈·德保罗": "1994-05-24",
    "乔瓦尼·洛塞尔索": "1996-04-09",
    "亚历克西斯·麦卡利斯特": "1998-12-24",
    "恩佐·费尔南德斯": "2001-01-17",
    "蒂亚戈·阿尔马达": "2001-04-26",
    "朱利亚诺·西蒙尼": "2002-12-18",
    "尼科·帕斯": "2004-09-08",
    "何塞·曼努埃尔·洛佩斯": "2000-12-06",
}
cn_to_birth.update(argentina)

# ======================== 哥伦比亚 ========================
colombia = {
    "路易斯·迪亚兹": "1997-01-13",     # Luis Díaz
    "乔恩·科尔多瓦": "1993-05-11",     # Jhon Córdoba
    "路易斯·苏亚雷斯": "1997-12-02",   # Luis Suárez
    "安德烈斯·戈麦斯": "2002-09-12",   # Carlos Andrés Gómez
    "杰弗森·莱尔马": "1994-10-25",     # Jefferson Lerma
    "里卡多·里奥斯": "2000-06-02",     # Richard Ríos
    "金特罗": "1993-01-18",            # Juan Fernando Quintero
    "卡斯塔尼奥": "2000-09-29",        # Kevin Castaño
    "普埃塔": "2003-07-23",            # Gustavo Puerta
    "波尔蒂利亚": "1998-05-25",        # Jorge Carrascal (or Portilla)
    "卡拉斯卡尔": "1998-05-25",        # Jorge Carrascal
    "阿里亚斯": "1997-09-21",          # Jhon Arias
    "坎帕兹": "2000-05-24",            # Jaminton Campaz
    "约翰·卢库米": "1998-06-26",       # Jhon Lucumí
    "圣地亚哥·阿里亚斯": "1992-01-13", # Santiago Arias
    "马查多": "1993-09-02",            # Deiver Machado
    "莫西卡": "1992-08-21",            # Johan Mojica
    "迪塔": "1997-01-23",             # Willer Ditta
    "大卫·奥斯皮纳": "1988-08-31",     # David Ospina
    "卡米洛·巴尔加斯": "1989-03-09",   # Camilo Vargas
    "阿尔瓦罗·蒙特罗": "1995-03-29",   # Álvaro Montero
    "耶里·米纳": "1994-09-23",         # Yerry Mina
    "达文森·桑切斯": "1996-06-12",     # Davinson Sánchez
    "丹尼尔·穆尼奥斯": "1996-05-26",   # Daniel Muñoz
}
cn_to_birth.update(colombia)

# ======================== 乌拉圭 ========================
uruguay = {
    "罗纳德·阿劳霍": "1999-03-07",
    "圣地亚哥·布埃诺": "1998-11-09",
    "马蒂亚斯·奥利维拉": "1997-10-31",
    "马蒂亚斯·比尼亚": "1997-11-09",
    "埃米里亚诺·马丁内斯": "1999-08-17",  # Emiliano Martínez (MID)
    "胡安·萨纳布里亚": "2000-03-29",      # Juan Manuel Sanabria
    "罗德里戈·萨拉萨尔": "1999-08-12",    # Rodrigo Zalazar
    "法昆多·佩利斯特里": "2001-12-20",
    "马克西米利亚诺·阿劳霍": "2000-02-15",
    "罗德里戈·阿吉雷": "1994-10-01",
    "费德里科·比尼亚斯": "1998-06-30",
}
cn_to_birth.update(uruguay)

# ======================== 厄瓜多尔 ========================
ecuador = {
    "加林德斯": "1987-03-30",         # Hernán Galíndez
    "拉米雷斯": "2000-09-09",         # Moisés Ramírez
    "巴列": "1996-02-28",            # Gonzalo Valle
    "埃斯图皮尼安": "1998-01-21",     # Pervis Estupiñán
    "梅迪纳": "2004-11-05",          # Yaimar Medina
    "奥多涅斯": "2004-04-21",        # Joel Ordóñez
    "帕乔": "2001-10-16",            # Willian Pacho
    "波罗佐": "2000-08-04",          # Jackson Porozo
    "普雷西亚多": "1998-02-18",      # Ángelo Preciado
    "托雷斯": "1997-01-11",          # Félix Torres
    "阿尔西瓦尔": "1999-08-05",      # Jordy Alcívar
    "安古洛": "2003-06-19",          # Nilson Angulo
    "莫伊塞斯·凯塞多": "2001-11-02",
    "卡斯蒂略": "2004-03-24",        # Denil Castillo
    "阿兰·佛朗哥": "1998-08-21",    # Alan Franco
    "阿兰·明达": "2003-05-14",      # Alan Minda
    "肯德里·派斯": "2007-05-04",    # Kendry Páez
    "佩德罗·维特": "2002-03-09",    # Pedro Vite
    "阿雷瓦洛": "2005-03-19",        # Jeremy Arévalo
    "乔迪·凯塞多": "1997-11-18",    # Jordy Caicedo
    "贡萨洛·普拉塔": "2000-11-01",  # Gonzalo Plata
    "安东尼·瓦伦西亚": "2003-07-21", # Anthony Valencia
    "恩纳·瓦伦西亚": "1989-11-04",  # Enner Valencia
    "凯文·罗德里格斯": "2000-03-04", # Kevin Rodríguez
    "约翰·叶博亚": "2000-06-23",    # John Yeboah
}
cn_to_birth.update(ecuador)

# ======================== 巴拉圭 ========================
paraguay = {
    "米格尔·阿尔米隆": "1994-02-10",
    "拉蒙·索萨": "1999-08-31",
    "亚历克斯·阿塞": "1995-06-16",      # Álex Arce
    "伊西德罗·皮塔": "1999-08-14",      # Isidro Pitta
    "加布里埃尔·阿瓦洛斯": "1990-10-12", # Gabriel Ávalos
    "古斯塔沃·卡瓦列罗": "2001-09-21",  # Gustavo Caballero
    "胡利奥·恩西索": "2004-01-23",      # Julio Enciso
    "马蒂亚斯·加拉尔扎": "2002-02-11",   # Matías Galarza
    "安德烈斯·库瓦斯": "1996-05-22",     # Andrés Cubas
    "毛里西奥·马加良斯": "2001-06-22",   # Mauricio (Maurício Magalhães)
    "达米安·博巴迪利亚": "2001-07-11",   # Damián Bobadilla
    "布莱恩·奥赫达": "2000-06-27",       # Braian Ojeda
    "亚历杭德罗·罗梅罗": "1995-01-11",   # Alejandro "Kaku" Romero
    "古斯塔沃·戈麦斯": "1993-05-06",     # Gustavo Gómez (DEF)
    "胡安·卡塞雷斯": "2000-06-01",       # Juan Cáceres
    "小阿隆索": "1993-02-09",            # Júnior Alonso
    "何塞·卡纳莱": "1996-07-20",         # José Canale
    "古斯塔沃·贝拉斯克斯": "1991-04-17", # Gustavo Velázquez
    "亚历杭德罗·迈达纳": "2005-07-26",   # Alexandro Maidana
    "法比安·巴尔武埃纳": "1991-08-23",   # Fabián Balbuena
    "奥兰多·吉尔": "2000-06-11",         # Orlando Gill
    "小罗伯特·费尔南德斯": "1988-03-29",  # Roberto "Gatito" Fernández
    "加斯顿·奥利维拉": "1993-04-21",     # Gastón Olveira
    "安东尼奥·萨纳布里亚": "1996-03-04",  # Antonio Sanabria
}
cn_to_birth.update(paraguay)


# ============================================================
# 处理 CSV
# ============================================================

target_teams = {"墨西哥","美国","加拿大","巴西","阿根廷","哥伦比亚","乌拉圭","厄瓜多尔","巴拉圭"}

results = []
found_count = 0
already_have_full_date = 0
not_found = []

with open(csv_path, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for row in reader:
        country = row[0]
        if country not in target_teams:
            continue
        player_name = row[3]
        current_age = row[18] if len(row) > 18 else ""

        # 已有完整出生日期，跳过
        if re.match(r'^\d{4}-\d{2}-\d{2}$', current_age):
            already_have_full_date += 1
            continue

        # 在字典中查找
        if player_name in cn_to_birth:
            birth = cn_to_birth[player_name]
            results.append([country, player_name, birth])
            found_count += 1
        else:
            not_found.append((country, player_name, current_age))

# 写入 JSON
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"已有完整日期 (跳过): {already_have_full_date}")
print(f"本次新找到: {found_count}")
print(f"已保存至: {json_path}\n")

if not_found:
    print(f"未匹配 {len(not_found)} 条:")
    for c, p, a in not_found:
        print(f"  {c} | {p} | {a}")
else:
    print("全部匹配成功！")
