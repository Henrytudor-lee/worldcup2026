"""
用 ESPN Core API 查询 X待核实 球员的 DOB
不依赖 cache，直接查英文名
"""
import asyncio, aiohttp, json, csv, time
from datetime import date

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    d = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))

# =====================
# ESPN Core API (from save_player_ages.py)
# =====================
ESPN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://www.espn.com',
}

TEAM_ID_MAP = {
    '墨西哥': 846, '南非': 1385, '韩国': 221, '捷克': 1006, '加拿大': 111035,
    '波黑': 998, '美国': 804, '巴拉圭': 895, '卡塔尔': 20693,
    '瑞士': 780, '巴西': 754, '摩洛哥': 1357, '海地': 107,
    '苏格兰': 97, '澳大利亚': 508, '土耳其': 102, '德国': 759,
    '荷兰': 858, '日本': 931, '科特迪瓦': 1061, '厄瓜多尔': 897,
    '瑞典': 98, '突尼斯': 1358, '西班牙': 86, '佛得角': 20695,
    '比利时': 870, '埃及': 1356, '沙特': 1352, '乌拉圭': 858,
    '伊朗': 105, '新西兰': 113335, '法国': 660, '塞内加尔': 1062,
    '伊拉克': 105, '挪威': 95, '阿根廷': 71, '阿尔及利亚': 1350,
    '奥地利': 799, '约旦': 20853, '葡萄牙': 839, '民主刚果': 1351,
    '英格兰': 77, '克罗地亚': 1002, '加纳': 1059, '巴拿马': 111036,
    '乌兹别克斯坦': 20696, '哥伦比亚': 864,
}

async def fetch_roster(team_en, league_id=16):
    url = f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league_id}/teams/{team_en}/roster'
    async with aiohttp.ClientSession(headers=ESPN_HEADERS) as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
    return None

async def get_player_dob(team_en, player_en):
    roster = await fetch_roster(team_en)
    if not roster:
        return None, 'no_roster'
    for r in roster.get('athletes', []):
        for athlete in r.get('items', []):
            if athlete.get('displayName', '').lower() == player_en.lower():
                dob = athlete.get('dateOfBirth', '')
                if dob:
                    return dob[:10], 'found'
    return None, 'not_in_roster'

# =====================
# 生成英文名候选（从 manual_name_map + pinyin）
# =====================
from pypinyin import lazy_pinyin

def to_py(name):
    parts = name.split('·')
    return [''.join(lazy_pinyin(p, style=0)) for p in parts]

def py_to_en_firstname(py):
    """pinyin -> 英文名首字（常用名库）"""
    MAP = {
        'ali': 'Ali', 'ahmed': 'Ahmed', 'mohammed': 'Mohammed', 'mohammad': 'Mohammad',
        'abdullah': 'Abdullah', 'ibrahim': 'Ibrahim', 'omar': 'Omar', 'youssef': 'Youssef',
        'zayn': 'Zain', 'tarek': 'Tarek', 'karim': 'Karim', 'samir': 'Samir',
        'nabil': 'Nabil', 'rashid': 'Rashid', 'fahd': 'Fahd', 'khaled': 'Khaled',
        'hassan': 'Hassan', 'hossam': 'Hossam', 'amr': 'Amr', 'salah': 'Salah',
        'mostafa': 'Mostafa', 'yousef': 'Yousef', 'abdel': 'Abdel', 'hamza': 'Hamza',
        'mourad': 'Mourad', 'ayman': 'Ayman', 'fares': 'Fares', 'walid': 'Walid',
        'saad': 'Saad', 'mounir': 'Mounir', 'noureddine': 'Noureddine', 'jalal': 'Jalal',
        'jaber': 'Jaber', 'bader': 'Bader', 'turki': 'Turki', 'abdullah': 'Abdullah',
        'sultan': 'Sultan', 'fahad': 'Fahad', 'hazim': 'Hazim', 'mahdi': 'Mahdi',
        'qasim': 'Qasim', 'hadi': 'Hadi', 'zaid': 'Zaid', 'murtadha': 'Murtadha',
        'mejia': 'Mejia', 'gonzalez': 'Gonzalez', 'rodriguez': 'Rodriguez', 'martinez': 'Martinez',
        'lopez': 'Lopez', 'garcia': 'Garcia', 'torres': 'Torres', 'ramirez': 'Ramirez',
        'flores': 'Flores', 'gutierrez': 'Gutierrez', 'chavez': 'Chavez', 'reyes': 'Reyes',
        'morales': 'Morales', 'cruz': 'Cruz', 'ortega': 'Ortega', 'castillo': 'Castillo',
        'herrera': 'Herrera', 'vasquez': 'Vasquez', 'dominguez': 'Dominguez', 'medina': 'Medina',
        'cervantes': 'Cervantes', 'aguilar': 'Aguilar', 'perez': 'Perez', 'sanchez': 'Sanchez',
        'carrasco': 'Carrasco', 'jimenez': 'Jimenez', 'fernandez': 'Fernandez', 'diaz': 'Diaz',
        'moreno': 'Moreno', 'ruiz': 'Ruiz', 'alvarez': 'Alvarez', 'romero': 'Romero',
        'suarez': 'Suarez', 'gomez': 'Gomez', 'vargas': 'Vargas', 'rios': 'Rios',
        'vega': 'Vega', 'carrillo': 'Carrillo', 'mendoza': 'Mendoza', 'estrada': 'Estrada',
        'cruz': 'Cruz', 'benitez': 'Benitez', 'galicia': 'Galicia', 'velazquez': 'Velazquez',
        'nunez': 'Nunez', 'ibarra': 'Ibarra', 'gonzales': 'Gonzales', 'espinosa': 'Espinosa',
        'peña': 'Peña', 'silva': 'Silva', 'dela': 'Dela', 'zambrano': 'Zambrano',
        'henry': 'Henry', 'jose': 'Jose', 'juan': 'Juan', 'carlos': 'Carlos', 'miguel': 'Miguel',
        'luis': 'Luis', 'angel': 'Angel', 'francisco': 'Francisco', 'david': 'David',
        'alex': 'Alex', 'cristian': 'Cristian', 'ricardo': 'Ricardo', 'enrique': 'Enrique',
        'ivan': 'Ivan', 'carlos': 'Carlos', 'oscar': 'Oscar', 'raul': 'Raul',
        'marco': 'Marco', 'daniel': 'Daniel', 'sebastian': 'Sebastian', 'andres': 'Andres',
        'german': 'German', 'marcos': 'Marcos', 'pablo': 'Pablo', 'alvaro': 'Alvaro',
        'sergio': 'Sergio', 'adrian': 'Adrian', 'jorge': 'Jorge', 'santiago': 'Santiago',
        'matias': 'Matias', 'nicolas': 'Nicolas', 'lautaro': 'Lautaro', 'lionel': 'Lionel',
        'gonzalo': 'Gonzalo', 'marcelo': 'Marcelo', 'thiago': 'Thiago', 'neymar': 'Neymar',
        'rodrigo': 'Rodrigo', 'bruno': 'Bruno', 'joao': 'João', 'pedro': 'Pedro',
        'bernardo': 'Bernardo', 'diogo': 'Diogo', 'tiago': 'Tiago', 'nuno': 'Nuno',
        'rafael': 'Rafael', 'fabio': 'Fabio', 'tiago': 'Tiago', 'paulo': 'Paulo',
        'carlos': 'Carlos', 'william': 'William', 'john': 'John', 'james': 'James',
        'mason': 'Mason', 'harry': 'Harry', 'cole': 'Cole', 'jack': 'Jack',
        'tyler': 'Tyler', 'jake': 'Jake', 'ethan': 'Ethan', 'noah': 'Noah',
        'oliver': 'Oliver', 'benjamin': 'Benjamin', 'elijah': 'Elijah', 'lucas': 'Lucas',
        'michael': 'Michael', 'mason': 'Mason', 'logan': 'Logan', 'alexander': 'Alexander',
        'jackson': 'Jackson', 'sebastian': 'Sebastian', 'aiden': 'Aiden', 'matthew': 'Matthew',
        'samuel': 'Samuel', 'david': 'David', 'joseph': 'Joseph', 'carter': 'Carter',
        'owen': 'Owen', 'wyatt': 'Wyatt', 'johnny': 'Johnny', 'luca': 'Luca',
        'toby': 'Toby', 'harvey': 'Harvey', 'callum': 'Callum', 'jamie': 'Jamie',
        'scott': 'Scott', 'mitchell': 'Mitchell', 'grant': 'Grant', 'campbell': 'Campbell',
        'ryan': 'Ryan', 'connor': 'Connor', 'kyle': 'Kyle', 'jordan': 'Jordan',
        'bradley': 'Bradley', 'jacob': 'Jacob', 'jacob': 'Jacob', 'jensen': 'Jensen',
        'thabo': 'Thabo', 'percy': 'Percy', 'zizzo': 'Zizzo', 'zithulele': 'Zithulele',
        'lukhanyo': 'Lukhanyo', 'amanda': 'Amanda', 'boal': 'Boal', 'makha': 'Makha',
        'tshimanga': 'Tshimanga', 'benni': 'Benni', 'evidence': 'Evidence', 'thapelo': 'Thapelo',
        'terry': 'Terry', 'siyabonga': 'Siyabonga', 'monde': 'Monde', 'ziko': 'Ziko',
        'petersen': 'Petersen', 'sandile': 'Sandile', 'nkosana': 'Nkosana', 'sibusiso': 'Sibusiso',
        'mpho': 'Mpho', 'kabelo': 'Kabelo', 'lungi': 'Lungi', 'tk': 'TK',
        'lucky': 'Lucky', 'moses': 'Moses', 'abel': 'Abel', 'abel': 'Abel',
        'emile': 'Emile', 'zaki': 'Zaki', 'youssef': 'Youssef', 'mido': 'Mido',
        'ahmed': 'Ahmed', 'mohamed': 'Mohamed', 'abdallah': 'Abdallah', 'salah': 'Salah',
        'triga': 'Triga', 'goran': 'Goran', 'milenko': 'Milenko', 'veljko': 'Veljko',
        'stevan': 'Stevan', 'uros': 'Uros', 'darko': 'Darko', 'nemanja': 'Nemanja',
        'petar': 'Petar', 'milad': 'Milad', 'saeid': 'Saeid', 'mehrdad': 'Mehrdad',
        'vahid': 'Vahid', 'arshia': 'Arshia', 'sadegh': 'Sadegh', 'meysam': 'Meysam',
        'ali': 'Ali', 'mohammad': 'Mohammad', 'amir': 'Amir', 'morteza': 'Morteza',
        'pour': 'Pour', 'hamed': 'Hamed', 'javad': 'Javad', 'behzad': 'Behzad',
        'mostafa': 'Mostafa', 'seyed': 'Seyed', 'sajjad': 'Sajjad', 'milad': 'Milad',
        'ali': 'Ali', 'hossein': 'Hossein', 'mehdi': 'Mehdi', 'peyman': 'Peyman',
        'alireza': 'Alireza', 'sheriff': 'Sheriff', 'ibraheem': 'Ibraheem', 'abdulla': 'Abdulla',
        'ali': 'Ali', 'yusuf': 'Yusuf', 'tah': 'Tah', 'jassim': 'Jassim',
        'akram': 'Akram', 'hassan': 'Hassan', 'al': 'Al', 'mubarak': 'Mubarak',
        'abdul': 'Abdul', 'rahman': 'Rahman', 'salam': 'Salam', 'fadel': 'Fadel',
        'rashid': 'Rashid', 'mahmoud': 'Mahmoud', 'issa': 'Issa', 'ibrahim': 'Ibrahim',
        'gylfi': 'Gylfi', 'sigurdsson': 'Sigurdsson', 'jon': 'Jon', 'daniel': 'Daniel',
        'aron': 'Aron', 'bjorn': 'Bjorn', 'freyr': 'Freyr', 'indriði': 'Indridi',
        'gustav': 'Gustav', 'erik': 'Erik', 'anton': 'Anton', 'oscar': 'Oscar',
        'wilhelm': 'Wilhelm', 'henrik': 'Henrik', 'tobias': 'Tobias', 'filip': 'Filip',
        'emil': 'Emil', 'lucas': 'Lucas', 'alex': 'Alex', 'olof': 'Olof',
        'niklas': 'Niklas', 'marcus': 'Marcus', 'kristoffer': 'Kristoffer', 'johan': 'Johan',
        'andreas': 'Andreas', 'sebastian': 'Sebastian', 'jonatan': 'Jonatan', 'isak': 'Isak',
        'jonte': 'Jonte', 'alex': 'Alex', 'william': 'William', 'felix': 'Felix',
        'oscar': 'Oscar', 'viktor': 'Viktor', 'jacob': 'Jacob', 'henrik': 'Henrik',
        'caleb': 'Caleb', 'isaac': 'Isaac', 'jude': 'Jude', 'john': 'John',
        'julio': 'Julio', 'alexander': 'Alexander', 'oriol': 'Oriol', 'dani': 'Dani',
        'marc': 'Marc', 'jordi': 'Jordi', 'sergi': 'Sergi', 'pau': 'Pau',
        'ximo': 'Ximo', 'alvaro': 'Alvaro', 'raul': 'Raul', 'carlos': 'Carlos',
        'fernando': 'Fernando', 'francisco': 'Francisco', 'manuel': 'Manuel', 'jose': 'Jose',
        'adrian': 'Adrian', 'david': 'David', 'sergio': 'Sergio', 'javi': 'Javi',
        'koke': 'Koke', 'thibaut': 'Thibaut', 'edouard': 'Edouard', 'romelu': 'Romelu',
        'kylian': 'Kylian', 'antoine': 'Antoine', 'paul': 'Paul', 'ngolo': 'Ngolo',
        'blaise': 'Blaise', 'randal': 'Randal', 'mason': 'Mason', 'declan': 'Declan',
        'bukayo': 'Bukayo', 'cole': 'Cole', 'phil': 'Phil', 'harry': 'Harry',
        'john': 'John', 'declan': 'Declan', 'jack': 'Jack', 'jordan': 'Jordan',
        'cole': 'Cole', 'bukayo': 'Bukayo', 'phil': 'Phil', 'harry': 'Harry',
        'declan': 'Declan', 'jack': 'Jack', 'jordan': 'Jordan', 'mark': 'Mark',
        'david': 'David', 'ben': 'Ben', 'tom': 'Tom', 'james': 'James',
        'ollie': 'Ollie', 'cole': 'Cole', 'mason': 'Mason', 'harry': 'Harry',
        'alex': 'Alex', 'tyler': 'Tyler', 'christian': 'Christian', 'weston': 'Weston',
        'yunus': 'Yunus', 'arda': 'Arda', 'kerem': 'Kerem', 'baris': 'Baris',
        'berat': 'Berat', 'altay': 'Altay', 'ugur': 'Ugur', 'merih': 'Merih',
        'samet': 'Samet', 'abdülkadir': 'Abdülkadir', 'hakan': 'Hakan', 'irfan': 'Irfan',
        'ogulcan': 'Ogulcan', 'umut': 'Umut', 'sertac': 'Sertac', 'siralp': 'Siralp',
        'enes': 'Enes', 'salih': 'Salih', 'zeki': 'Zeki', 'halil': 'Halil',
        'mehmet': 'Mehmet', 'firat': 'Firat', 'can': 'Can', 'bilal': 'Bilal',
        'altug': 'Altug', 'goktan': 'Goktan', 'goktug': 'Goktug', 'arda': 'Arda',
        'batuhan': 'Batuhan', 'oguz': 'Oguz', 'mert': 'Mert', 'efe': 'Efe',
        'yusuf': 'Yusuf', 'kadir': 'Kadir', 'semih': 'Semih', 'mert': 'Mert',
        'sait': 'Sait', 'erol': 'Erol', 'veysel': 'Veysel', 'gokay': 'Gokay',
        'ugur': 'Ugur', 'bayram': 'Bayram', 'alperen': 'Alperen', 'furkan': 'Furkan',
        'oguzhan': 'Oguzhan', 'ibrahim': 'Ibrahim', 'serdar': 'Serdar', 'hakan': 'Hakan',
        'selim': 'Selim', 'muharrem': 'Muharrem', 'batuhan': 'Batuhan', 'gokhan': 'Gokhan',
        'abdullah': 'Abdullah', 'omer': 'Omer', 'taha': 'Taha', 'furkan': 'Furkan',
        'deniz': 'Deniz', 'ugur': 'Ugur', 'yavuz': 'Yavuz', 'sener': 'Sener',
        'bilal': 'Bilal', 'berat': 'Berat', 'huseyin': 'Huseyin', 'alperen': 'Alperen',
        'cem': 'Cem', 'tayyip': 'Tayyip', 'efe': 'Efe', 'yigit': 'Yigit',
        'demiral': 'Demiral', 'sven': 'Sven', 'nuri': 'Nuri', 'cansu': 'Cansu',
        'milan': 'Milan', 'nikola': 'Nikola', 'luka': 'Luka', 'marco': 'Marco',
        'ivan': 'Ivan', 'ante': 'Ante', 'matej': 'Matej', 'milan': 'Milan',
        'stevan': 'Stevan', 'ujoš': 'Ujos', 'ondrej': 'Ondrej', 'milan': 'Milan',
        'jakub': 'Jakub', 'tomas': 'Tomas', 'petr': 'Petr', 'marek': 'Marek',
        'jan': 'Jan', 'vojtěch': 'Vojtech', 'lukas': 'Lukas', 'roman': 'Roman',
        'milan': 'Milan', 'stanislav': 'Stanislav', 'pavel': 'Pavel', 'zdenek': 'Zdenek',
        'david': 'David', 'ondrej': 'Ondrej', 'matej': 'Matej', 'vojtech': 'Vojtech',
        'oleksandr': 'Oleksandr', 'artem': 'Artem', 'vladyslav': 'Vladyslav', 'mykhailo': 'Mykhailo',
        'oleksandr': 'Oleksandr', 'ruslan': 'Ruslan', 'andriy': 'Andriy', 'yevhen': 'Yevhen',
        'taras': 'Taras', 'dmytro': 'Dmytro', 'igor': 'Igor', 'serhiy': 'Serhiy',
        'bohdan': 'Bohdan', 'roman': 'Roman', 'vitaliy': 'Vitaliy', 'pavlo': 'Pavlo',
        'volodymyr': 'Volodymyr', 'ivan': 'Ivan', 'oleksandr': 'Oleksandr', 'anton': 'Anton',
        'danylo': 'Danylo', 'kirill': 'Kirill', 'yaroslav': 'Yaroslav', 'maxim': 'Maxim',
        'artur': 'Artur', 'aziz': 'Aziz', 'azmoun': 'Azmoun', 'torabi': 'Torabi',
        'nourollah': 'Nourollah', ' Khalil': 'Khalil', 'jafar': 'Jafar', 'saeid': 'Saeid',
        'rashid': 'Rashid', 'salim': 'Salim', 'majid': 'Majid', 'hamed': 'Hamed',
        'sajad': 'Sajad', 'iman': 'Iman', 'morteza': 'Morteza', 'farid': 'Farid',
        'ali': 'Ali', 'behrouz': 'Behrouz', 'arman': 'Arman', 'soroush': 'Soroush',
        'alireza': 'Alireza', 'mehdi': 'Mehdi', 'arash': 'Arash', 'pooya': 'Pooya',
        'sheriff': 'Sheriff', 'ibraheem': 'Ibraheem', 'abdulla': 'Abdulla', 'mubarak': 'Mubarak',
        'abdul': 'Abdul', 'rahman': 'Rahman', 'jassim': 'Jassim', 'akram': 'Akram',
        'al': 'Al', 'issa': 'Issa', 'mahmoud': 'Mahmoud', 'fadel': 'Fadel',
        'rashid': 'Rashid', 'ali': 'Ali', 'hassan': 'Hassan', 'yusuf': 'Yusuf',
        'tah': 'Tah', 'nabil': 'Nabil', 'dj好不好': 'Dj好不好', 'bouna': 'Bouna',
        'sarr': 'Sarr', 'mane': 'Mane', 'bissouma': 'Bissouma', 'kouyate': 'Kouyate',
        'kone': 'Kone', 'doumbia': 'Doumbia', 'diakite': 'Diakite', 'samba': 'Samba',
        'moussa': 'Moussa', 'ibrahim': 'Ibrahim', 'ousmane': 'Ousmane', 'madamba': 'Madamba',
        'seck': 'Seck', 'papy': 'Papy', 'moris': 'Moris', 'honadia': 'Honadia',
        'bouri': 'Bouri', 'kane': 'Kane', 'djenepo': 'Djenepo', 'sarr': 'Sarr',
        'dj好不好': 'Dj好不好', 'binta': 'Binta', 'baba': 'Baba', 'issa': 'Issa',
        'gning': 'Gning', 'moussa': 'Moussa', 'baba': 'Baba', 'demba': 'Demba',
        'pape': 'Pape', 'papy': 'Papy', 'issa': 'Issa', 'aliou': 'Aliou',
        'abdoulaye': 'Abdoulaye', 'moussa': 'Moussa', 'bakary': 'Bakary', 'cheick': 'Cheick',
        'moussa': 'Moussa', 'el hadji': 'El Hadji', 'baba': 'Baba', 'issa': 'Issa',
        'papiss': 'Papiss', 'dade': 'Dade', 'mbaye': 'Mbaye', 'papis': 'Papis',
        'issa': 'Issa', 'sadio': 'Sadio', 'baba': 'Baba', 'cheikh': 'Cheikh',
        'issa': 'Issa', 'kalidou': 'Kalidou', 'youssouf': 'Youssouf', 'bouna': 'Bouna',
        'aliou': 'Aliou', 'issa': 'Issa', 'cheick': 'Cheick', 'ousmane': 'Ousmane',
        'abdoulaye': 'Abdoulaye', 'pape': 'Pape', 'moussa': 'Moussa', 'papy': 'Papy',
        'issa': 'Issa', 'ibrahim': 'Ibrahim', 'moussa': 'Moussa', 'ousmane': 'Ousmane',
        'kalidou': 'Kalidou', 'youssouf': 'Youssouf', 'bouna': 'Bouna', 'aliou': 'Aliou',
    }
    return MAP.get(py.lower(), py.capitalize())

# 从中文名生成英文名候选
def gen_en_candidates(cn_name, team_cn):
    pys = to_py(cn_name)
    candidates = []
    if len(pys) == 1:
        py = pys[0]
        fn = py_to_en_firstname(py)
        candidates.append(fn)  # Single name assumption
        if len(py) > 2:
            candidates.append(fn + ' ' + py.capitalize())
    elif len(pys) >= 2:
        last = pys[-1]
        for i in range(len(pys)-1):
            first = pys[i]
            fn = py_to_en_firstname(first)
            ln = last.capitalize()
            # 常见格式: FirstName LastName
            candidates.append(f'{fn} {ln}')
            # 也试 last-first
            candidates.append(f'{ln} {fn}')
            # 全小写
            candidates.append(f'{fn.lower()} {ln.lower()}')
            # 单名
            candidates.append(fn)
            candidates.append(ln)
    return candidates

# =====================
# 主逻辑
# =====================
async def main():
    # 加载 X待核实 列表
    rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))
    xun = [x for x in rows if x['年龄'] == 'X待核实']
    print(f'X待核实: {len(xun)}')

    # 已知英文名 (manual map) → 从头构建
    manual = json.load(open('backend/manual_name_map.json'))
    en_map = {}  # (team, cn) -> en_name
    for team, mapping in manual.items():
        if team == '_comment': continue
        for cn, en in mapping.items():
            if en and cn:
                en_map[(team, cn)] = en

    # ESPN team ID map (中文 -> 英文名)
    TEAM_EN = {
        '墨西哥': 'mexico', '南非': 'south-africa', '韩国': 'south-korea', '捷克': 'czech-republic',
        '加拿大': 'canada', '波黑': 'bosnia-herzegovina', '美国': 'united-states', '巴拉圭': 'paraguay',
        '卡塔尔': 'qatar', '瑞士': 'switzerland', '巴西': 'brazil', '摩洛哥': 'morocco',
        '海地': 'haiti', '苏格兰': 'scotland', '澳大利亚': 'australia', '土耳其': 'turkey',
        '德国': 'germany', '荷兰': 'netherlands', '日本': 'japan', '科特迪瓦': 'ivory-coast',
        '厄瓜多尔': 'ecuador', '瑞典': 'sweden', '突尼斯': 'tunisia', '西班牙': 'spain',
        '佛得角': 'cape-verde', '比利时': 'belgium', '埃及': 'egypt', '沙特': 'saudi-arabia',
        '乌拉圭': 'uruguay', '伊朗': 'iran', '新西兰': 'new-zealand', '法国': 'france',
        '塞内加尔': 'senegal', '伊拉克': 'iraq', '挪威': 'norway', '阿根廷': 'argentina',
        '阿尔及利亚': 'algeria', '奥地利': 'austria', '约旦': 'jordan', '葡萄牙': 'portugal',
        '民主刚果': 'dr-congo', '英格兰': 'england', '克罗地亚': 'croatia', '加纳': 'ghana',
        '巴拿马': 'panama', '乌兹别克斯坦': 'uzbekistan', '哥伦比亚': 'colombia', '库拉索': 'curacao',
    }

    results = {}  # (team, cn) -> dob

    # 先用已知英文名查 ESPN
    print('=== 阶段1: ESPN已知英文名 ===')
    tasks = []
    for x in xun:
        key = (x['国家'], x['球员'])
        if key in en_map:
            team_en = TEAM_EN.get(x['国家'], '')
            if team_en:
                tasks.append(get_player_dob(team_en, en_map[key]))
            else:
                tasks.append(asyncio.sleep(0))
        else:
            tasks.append(asyncio.sleep(0))

    coro_results = await asyncio.gather(*tasks)
    found1 = 0
    for i, x in enumerate(xun):
        key = (x['国家'], x['球员'])
        if key in en_map:
            team_en = TEAM_EN.get(x['国家'], '')
            dob, status = coro_results[i]
            if dob:
                age = calc_age(dob)
                if 16 <= age <= 45:
                    results[key] = dob
                    found1 += 1
                    print(f'  ✅ {x["国家"]:<6} {x["球员"]:<20} → {en_map[key]:<25} {dob} age={age}')
                else:
                    print(f'  ⚠️  {x["国家"]:<6} {x["球员"]:<20} → {en_map[key]:<25} {dob} age={age} (离谱)')
            else:
                print(f'  ❌ ESPN not found: {x["国家"]:<6} {x["球员"]:<20} → {en_map[key]} [{status}]')

    print(f'阶段1 ESPN已知: {found1}/{sum(1 for x in xun if (x["国家"],x["球员"]) in en_map)}')

    # 阶段2: 生成英文名候选 查 ESPN
    print('\n=== 阶段2: ESPN生成英文名 ===')
    no_en = [(x['国家'], x['球员']) for x in xun if (x['国家'], x['球员']) not in en_map]
    found2 = 0

    for (team, cn), x in [(k, next(xx for xx in xun if xx['国家']==k[0] and xx['球员']==k[1])) for k in no_en]:
        team_en = TEAM_EN.get(team, '')
        if not team_en:
            continue
        cands = gen_en_candidates(cn, team)
        dob_found = None
        en_used = None
        for en in cands[:6]:  # 最多试6个
            dob, status = await get_player_dob(team_en, en)
            if dob:
                age = calc_age(dob)
                if 16 <= age <= 45:
                    dob_found = dob
                    en_used = en
                    break
            await asyncio.sleep(0.3)
        if dob_found:
            results[(team, cn)] = dob_found
            found2 += 1
            print(f'  ✅ {team:<6} {cn:<20} → {en_used:<25} {dob_found} age={calc_age(dob_found)}')
        else:
            print(f'  ❌ {team:<6} {cn:<20} 生成候选: {cands[:3]}')
        await asyncio.sleep(0.5)

    print(f'\n阶段2 ESPN生成: {found2}')
    print(f'总计 ESPN DOB: {len(results)}')

    # 保存
    with open('1_数据基础/espn_retry_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 统计还剩多少
    xun_keys = {(x['国家'], x['球员']) for x in xun}
    still_need = xun_keys - set(results.keys())
    print(f'还剩未找到DOB: {len(still_need)}')

if __name__ == '__main__':
    asyncio.run(main())
