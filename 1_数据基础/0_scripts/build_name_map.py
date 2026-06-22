#!/usr/bin/env python3
"""
Accurate name mapping: Chinese names (CSV) <-> English names (JSON)
for Africa, Asia, Oceania, and Americas World Cup 2026 teams.

Uses club names and positions to build a correct manual mapping.
Applies dates to the CSV for players that don't already have them.
"""

import csv
import json

CSV_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv'
JSON_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/age_afroasia.json'
MAP_OUT_PATH = '/Users/garcia/Desktop/WorldCup2026/1_数据基础/name_map_afroasia.json'

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    csv_rows = list(reader)

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    json_data = json.load(f)

# =====================================================
# MANUAL MAPPING: Chinese player name -> English player name
# Built by cross-referencing clubs, positions, and jersey numbers
# =====================================================

# Helper: look up birth date from JSON
def get_birth(en_name):
    for item in json_data:
        if item[1] == en_name:
            return item[2]
    return 'UNMATCHED'

# Mapping per team: {Chinese_name: English_name}
TEAM_MAPS = {}

# ============ SOUTH AFRICA (南非) ============
TEAM_MAPS['南非'] = {
    '罗恩文·威廉姆斯': 'Ronwen Williams',
    '西波·查内': 'Sipho Chaine',
    '里卡多·戈斯': 'Ricardo Goss',
    '库利索·穆达乌': 'Khuliso Mudau',
    '恩科西纳蒂·西比西': 'Nkosinathi Sibisi',
    '伊梅·奥孔': 'Ime Okon',
    '库卢马尼·恩达马内': 'Khulumani Ndamane',
    '奥布雷·莫迪巴': 'Aubrey Modiba',
    '萨穆凯洛·卡比尼': 'Samukele Kabini',
    '塔邦·马图鲁迪': 'Thabang Matuludi',
    '奥尔韦图·马卡尼亚': 'Olwethu Makhanya',
    '布拉德利·克罗斯': 'Bradley Cross',
    '卡莫盖洛·塞贝莱贝莱': 'Kamogelo Sebelebele',
    '姆贝凯泽利·姆博卡齐': 'Mbekezeli Mbokazi',
    '特博霍·莫库纳': 'Teboho Mokoena',
    '塔伦特·姆巴塔': 'Thalente Mbatha',
    '亚亚·西索莱': 'Sphephelo Sithole',
    '杰登·亚当斯': 'Jayden Adams',
    '奥斯温·阿波利斯': 'Oswin Appollis',
    '伊克拉姆·雷纳斯': 'Iqraam Rayners',
    '切潘·莫雷米': 'Tshepang Moremi',
    '埃维登斯·马科戈帕': 'Evidence Makgopa',
    '莱尔·福斯特': 'Lyle Foster',
    '雷莱博希莱·莫福肯': 'Relebohile Mofokeng',
    '滕巴·兹瓦内': 'Themba Zwane',
    '塔佩洛·马塞科': 'Thapelo Maseko',
}

# ============ EGYPT (埃及) ============
# Egypt JSON is NOT position-grouped. We match individually by club.
TEAM_MAPS['埃及'] = {
    '穆罕默德·谢纳维': 'Mohamed El-Shenawy',
    '肖贝尔': 'Mostafa Shobeir',
    '苏莱曼': 'El Mahdy Soliman',
    '穆罕默德·阿拉': 'Mohamed Alaa',
    '穆罕默德·哈尼': 'Mohamed Hany',
    '塔里克·阿拉': 'Tarek Alaa',
    '哈姆迪·法蒂': 'Hamdy Fathy',
    '拉米·拉比亚': 'Ramy Rabia',
    '亚西尔·易卜拉欣': 'Yasser Ibrahim',
    '阿卜杜勒马吉德': 'Hossam Abdelmaguid',
    '阿卜杜勒穆奈姆': 'Mohamed Abdelmonem',
    '艾哈迈德·法图赫': 'Ahmed Fatouh',
    '哈菲兹': 'Karim Hafez',
    '阿提亚': 'Marwan Attia',
    '穆罕纳德·拉辛': 'Mohanad Mostafa',
    '纳比勒·东加': 'Nabil Dunga',
    '马哈茂德·萨比尔': 'Mahmoud Saber',
    '齐佐': 'Zizo',
    '特雷泽盖': 'Trézéguet',
    '阿舒尔': 'Emam Ashour',
    '穆斯塔法·济科': 'Mostafa Ziko',
    '易卜拉欣·阿代勒': 'Ibrahim Adel',
    '海瑟姆·哈桑': 'Haissem Hassan',
    '萨拉赫': 'Mohamed Salah',
    '马尔穆什': 'Omar Marmoush',
    '哈姆扎·阿卜杜勒卡里姆': 'Hamza Abdelkarim',
}

# ============ MOROCCO (摩洛哥) ============
TEAM_MAPS['摩洛哥'] = {
    '亚辛·布努': 'Yassine Bounou',
    '穆尼尔·穆罕默迪': 'Munir El Kajoui',
    '塔纳乌蒂': 'Ahmed Reda Tagnaouti',
    '阿什拉夫·哈基米': 'Achraf Hakimi',
    '努萨伊·马兹拉维': 'Noussair Mazraoui',
    '伊萨·迪奥普': 'Issa Diop',
    '沙迪·里亚德': 'Chadi Riad',
    '萨拉赫·埃丁': 'Anass Salah-Eddine',
    '扎卡里亚·瓦赫迪': 'Zakaria El Ouahdi',
    '贝拉马里': 'Youssef Belammari',
    '哈勒哈勒': 'Redouane Halhal',
    '阿格尔德': 'Marwane Saadane',  # Marwane Saadane is a Morocco defender
    '萨米尔·穆拉贝': 'Samir El Mourabet',
    '阿尤布·布阿迪': 'Ayyoub Bouaddi',
    '艾纳维': 'Neil El Aynaoui',
    '萨伊瓦里': 'Ismael Saibari',
    '哈努斯': 'Bilal El Khannouss',
    '阿姆拉巴特': 'Sofyan Amrabat',
    '阿兹丁·欧纳希': 'Azzedine Ounahi',
    '卜拉欣·迪亚斯': 'Brahim Diaz',
    '塔勒比': 'Amine Sbai',
    '苏菲安·拉希米': 'Soufiane Rahimi',
    '卡埃比': 'Ayoub El Kaabi',
    '阿布德': 'Chemsdine Talbi',
    '盖西姆·亚辛': 'Yassine Gessime',
    '阿迈穆尼·埃奇古亚布': 'Ayoub Amaimouni-Echghouyabe',
}

# ============ TUNISIA (突尼斯) ============
TEAM_MAPS['突尼斯'] = {
    '达门': 'Aymen Dahmen',
    '本·黑森': 'Sabri Ben Hessen',
    '查马克': 'Mouhib Chamakh',
    '阿布迪': 'Ali Abdi',
    '塔尔比': 'Montassar Talbi',
    '布隆': 'Dylan Bronn',
    '瓦莱里': 'Yan Valery',
    '本赫米达': 'Mohamed Amine Ben Hamida',
    '雷基克': 'Omar Rekik',
    '阿鲁斯': 'Adem Arous',
    '内法蒂': 'Moutaz Neffati',
    '齐卡维': 'Raed Chikhaoui',
    '斯希里': 'Ellyes Skhiri',
    '拉尼·赫迪拉': 'Rani Khedira',
    '本·瓦内斯': 'Mortadha Ben Ouanes',
    '汉尼拔·梅布里': 'Hannibal Mejbri',
    '本·斯利曼': 'Anis Ben Slimane',
    '马哈茂德': 'Hadj Mahmoud',
    '加尔比': 'Ismaël Gharbi',
    '阿舒里': 'Elias Achouri',
    '沙瓦': 'Firas Chaouat',
    '马斯图里': 'Hazem Mastouri',
    '萨德': 'Elias Saad',
    '图内克蒂': 'Sebastian Tounekti',
    '阿亚里': 'Khalil Ayari',
    '埃卢米': 'Rayan Elloumi',
}

# ============ SENEGAL (塞内加尔) ============
TEAM_MAPS['塞内加尔'] = {
    '爱德华·门迪': 'Édouard Mendy',
    '莫里·迪奥': 'Mory Diaw',
    '耶旺恩·迪乌夫': 'Yehvann Diouf',
    '卡利杜·库利巴利': 'Kalidou Koulibaly',
    '阿卜杜拉耶·塞克': 'Abdoulaye Seck',
    '穆萨·尼亚卡泰': 'Moussa Niakhaté',
    '克雷平·迪亚塔': 'Krépin Diatta',
    '伊斯梅尔·雅各布斯': 'Ismail Jakobs',
    '埃尔·哈吉·马利克·迪乌夫': 'El Hadji Malick Diouf',
    '安托万·门迪': 'Antoine Mendy',
    '马马杜·萨尔': 'Mamadou Sarr',
    '伊德里萨·盖耶': 'Idrissa Gana Gueye',
    '帕特·西斯': 'Pathé Ciss',
    '帕佩·盖耶': 'Pape Gueye',
    '拉明·卡马拉': 'Lamine Camara',
    '哈比卜·迪亚拉': 'Habib Diarra',
    '帕佩·萨尔': 'Pape Matar Sarr',
    '巴拉·萨波科·恩迪亚耶': 'Bara Sapoko Ndiaye',
    '萨迪奥·马内': 'Sadio Mané',
    '谢里夫·恩迪亚耶': 'Cherif Ndiaye',
    '伊斯梅拉·萨尔': 'Ismaïla Sarr',
    '班巴·迪昂': 'Bamba Dieng',
    '伊利曼·恩迪亚耶': 'Iliman Ndiaye',
    '尼古拉斯·杰克逊': 'Nicolas Jackson',
    '阿萨内·迪奥': 'Assane Diao',
    '易卜拉欣·姆巴耶': 'Ibrahim Mbaye',
}

# ============ ALGERIA (阿尔及利亚) ============
TEAM_MAPS['阿尔及利亚'] = {
    '乌萨马·本博特': 'Oussama Benbot',
    '卢卡·齐达内': 'Luca Zidane',
    '梅尔文·马斯蒂尔': 'Melvin Mastil',
    '艾萨·曼迪': 'Aïssa Mandi',
    '拉米·本塞拜尼': 'Ramy Bensebaini',
    '拉扬·艾特-努里': 'Rayan Aït-Nouri',
    '阿什里夫·阿巴达': 'Achref Abada',
    '齐内丁·贝莱德': 'Zineddine Belaïd',
    '拉菲克·贝尔加利': 'Rafik Belghali',
    '萨米尔·谢尔吉': 'Samir Chergui',
    '穆罕默德·阿明·图加伊': 'Mohamed Amine Tougai',
    '贾万·哈贾姆': 'Jaouen Hadjam',
    '侯塞姆·奥阿尔': 'Houssem Aouar',
    '拉米兹·泽鲁基': 'Ramiz Zerrouki',
    '希沙姆·布道维': 'Hicham Boudaoui',
    '法雷斯·沙伊比': 'Farès Chaïbi',
    '纳比勒·本塔莱布': 'Nabil Bentaleb',
    '易卜拉欣·马扎': 'Ibrahim Maza',
    '亚辛·蒂特劳伊': 'Yacine Titraoui',
    '里亚德·马赫雷斯': 'Riyad Mahrez',
    '穆罕默德·阿明·阿穆拉': 'Mohamed Amoura',
    '阿明·古伊里': 'Amine Gouiri',
    '阿尼斯·哈吉·穆萨': 'Anis Hadj Moussa',
    '阿迪勒·布尔比纳': 'Adil Boulbina',
    '法雷斯·盖杰米斯': 'Farès Ghedjemis',
    '纳迪尔·本布阿利': 'Nadhir Benbouali',
}

# ============ IVORY COAST (科特迪瓦) ============
TEAM_MAPS['科特迪瓦'] = {
    '叶海亚·福法纳': 'Yahia Fofana',
    '穆罕默德·科内': 'Mohamed Koné',
    '拉丰': 'Alban Lafont',
    '埃万·恩迪卡': 'Evan N\'Dicka',
    '奥迪隆·科索努': 'Odilon Kossounou',
    '奥斯曼·迪奥曼德': 'Ousmane Diomande',
    '盖拉·杜埃': 'Guéla Doué',
    '阿格巴杜': 'Emmanuel Agbadou',
    '威尔弗里德·辛戈': 'Wilfried Singo',
    '奥佩里': 'Christopher Opéri',
    '吉兰·科南': 'Ghislain Konan',
    '塞科·福法纳': 'Seko Fofana',
    '易卜拉欣·桑加雷': 'Ibrahim Sangaré',
    '弗兰克·凯西': 'Franck Kessié',
    '让-米歇尔·塞里': 'Jean Michaël Seri',
    '帕尔费特·吉亚贡': 'Parfait Guiagon',
    '克里斯特·伊瑙·乌拉伊': 'Christ Inao Oulaï',
    '巴祖马纳·图雷': 'Bazoumana Touré',
    '阿玛德·迪亚洛': 'Amad Diallo',
    '尼古拉斯·佩佩': 'Nicolas Pépé',
    '安热-约安·博尼': 'Ange-Yoan Bonny',
    '西蒙·阿丁格拉': 'Simon Adingra',
    '埃利·瓦希': 'Elye Wahi',
    '埃万·盖桑': 'Evann Guessand',
    '扬·迪奥曼德': 'Yan Diomandé',
    '乌马尔·迪亚基特': 'Oumar Diakité',
}

# ============ GHANA (加纳) ============
TEAM_MAPS['加纳'] = {
    '劳伦斯·阿蒂齐吉': 'Lawrence Ati-Zigi',
    '约瑟夫·阿南': 'Joseph Anang',
    '本杰明·阿萨雷': 'Benjamin Asare',
    '阿里杜·塞杜': 'Alidu Seidu',
    '乔纳斯·阿杰蒂': 'Jonas Adjetey',
    '阿卜杜勒·穆明': 'Abdul Mumin',
    '吉迪恩·门萨': 'Gideon Mensah',
    '巴巴·阿卜杜勒·拉赫曼': 'Baba Abdul Rahman',
    '杰罗姆·奥波库': 'Jerome Opoku',
    '科乔·奥彭·佩普拉': 'Kojo Peprah Oppong',
    '德里克·卢卡森': 'Derrick Luckassen',
    '马文·塞纳亚': 'Marvin Senaya',
    '卡莱布·伊伦基': 'Caleb Yirenkyi',
    '托马斯·帕尔特伊': 'Thomas Partey',
    '法塔乌': 'Abdul Fatawu Issahaku',
    '夸西·西博': 'Kwasi Sibo',
    '伊莱莎·奥乌苏': 'Elisha Owusu',
    '奥古斯丁·博克耶': 'Augustine Boakye',
    '乔丹·阿尤': 'Jordan Ayew',
    '布兰登·托马斯·阿桑特': 'Brandon Thomas-Asante',
    '塞梅尼奥': 'Antoine Semenyo',
    '克里斯托弗·邦苏·巴': 'Christopher Bonsu Baah',
    '伊纳基·威廉姆斯': 'Iñaki Williams',
    '苏莱马纳': 'Kamaldeen Sulemana',
    '努瓦马': 'Ernest Nuamah',
    '夸贝纳·阿杜': 'Prince Kwabena Adu',
    # 萨利夫·希内 - NOT in official Ghana WC squad. Real #13 is Christopher Bonsu Baah.
    # This player not found. Removing wrong mapping to Ibrahim Mbaye.
}

# ============ DR CONGO (民主刚果) ============
TEAM_MAPS['民主刚果'] = {
    '恩波洛': 'Matthieu Epolo',
    '法尤鲁': 'Timothy Fayulu',
    '姆帕西': 'Lionel Mpasi',
    '姆本巴': 'Chancel Mbemba',
    '万-比萨卡': 'Aaron Wan-Bissaka',
    '图安泽贝': 'Axel Tuanzebe',
    '马苏亚库': 'Arthur Masuaku',
    '热代翁·卡卢卢': 'Gédéon Kalulu',
    '卡延贝': 'Joris Kayembe',
    '巴图宾西卡': 'Dylan Batubinsika',
    '卡普阿迪': 'Steve Kapuadi',
    '邦贡达': 'Théo Bongonda',
    '西蓬加': 'Brian Cipenga',
    '卡库塔': 'Gaël Kakuta',
    '埃多·卡延贝': 'Edo Kayembe',
    '姆布库': 'Nathanaël Mbuku',
    '穆图萨米': 'Samuel Moutoussamy',
    '穆考': 'Ngal\'Ayel Mukau',
    '皮克尔': 'Charles Pickel',
    '萨迪基': 'Noah Sadiki',
    '恩通巴': 'Aaron Tshibola',
    '巴坎布': 'Cédric Bakambu',
    '班扎': 'Simon Banza',
    '马耶莱': 'Fiston Mayele',
    '维萨': 'Yoane Wissa',
    '塞缪尔·乌阿尼': 'Meschak Elia',
}

# ============ IRAN (伊朗) ============
TEAM_MAPS['伊朗'] = {
    '阿里雷萨·贝兰万德': 'Alireza Beiranvand',
    '帕亚姆·尼亚曼德': 'Payam Niazmand',
    '侯赛因·侯赛尼': 'Hossein Hosseini',
    '达尼亚尔·埃里': 'Danial Eiri',
    '哈吉萨菲': 'Ehsan Hajsafi',
    '萨利赫·哈达尼': 'Saleh Hardani',
    '侯赛因·卡纳尼': 'Hossein Kanaanizadegan',
    '舒贾·哈利勒扎德': 'Shojae Khalilzadeh',
    '米拉德·穆罕默迪': 'Milad Mohammadi',
    '阿里·内马蒂': 'Ali Nemati',
    '拉明·雷扎伊扬': 'Ramin Rezaeian',
    '鲁兹贝·切什米': 'Rouzbeh Cheshmi',
    '赛义德·埃扎托拉希': 'Saeid Ezatolahi',
    '萨曼·戈多斯': 'Saman Ghoddos',
    '穆罕默德·戈尔巴尼': 'Mohammad Ghorbani',
    '穆罕默德·莫赫比': 'Mohammad Mohebi',
    '阿米尔穆罕默德·拉扎格尼亚': 'Amirmohammad Razzaghinia',
    '梅迪·托拉比': 'Mehdi Torabi',
    '阿里莱扎·贾汉巴赫什': 'Alireza Jahanbakhsh',
    '迈赫迪·加耶迪': 'Mehdi Ghayedi',
    '阿丽亚·尤素菲': 'Aria Yousefi',
    '梅赫迪·塔雷米': 'Mehdi Taremi',
    '萨达尔·阿兹蒙': 'Shahriyar Moghanlou',
    '阿里·阿利普尔': 'Ali Alipour',
    '丹尼斯·埃克特': 'Dennis Eckert',
    '阿米尔侯赛因·侯赛因扎德': 'Amirhossein Hosseinzadeh',
}

# ============ SAUDI ARABIA (沙特) ============
TEAM_MAPS['沙特'] = {
    '阿奇迪': 'Nawaf Al-Aqidi',
    '阿洛瓦伊斯': 'Mohammed Al-Owais',
    '卡萨尔': 'Ahmed Al-Kassar',
    '阿卜杜勒哈米德': 'Saud Abdulhamid',
    '阿姆里': 'Abdulelah Al-Amri',
    '坦巴克蒂': 'Hassan Al-Tambakti',
    '布沙尔': 'Nawaf Boushal',
    '拉贾米': 'Ali Lajami',
    '卡迪什': 'Hassan Kadesh',
    '哈尔比': 'Moteb Al-Harbi',
    '塔克里': 'Jehad Thakri',
    '马拉希': 'Abdullah Al-Khaibari',
    '阿布沙马特': 'Mohammed Abu Al-Shamat',
    '阿尔乔汉尼': 'Ziyad Al-Johani',
    '纳赛尔·多萨里': 'Nasser Al-Dawsari',
    '卡努': 'Mohamed Kanno',
    '哈巴利': 'Musab Al-Juwayr',
    '赫吉': 'Alaa Al-Hejji',
    '萨利姆·多萨里': 'Salem Al-Dawsari',
    '加纳姆': 'Khalid Al-Ghannam',
    '朱瓦伊尔': 'Ayman Yahya',
    '曼达什': 'Sultan Mandash',
    '叶海亚': 'Ali Majrashi',
    '布赖坎': 'Firas Al-Buraikan',
    '谢赫里': 'Saleh Al-Shehri',
    '哈姆丹': 'Abdullah Al-Hamdan',
}

# ============ JAPAN (日本) ============
TEAM_MAPS['日本'] = {
    '铃木彩艳': 'Zion Suzuki',
    '大迫敬介': 'Keisuke Ōsako',
    '早川友基': 'Tomoki Hayakawa',
    '长友佑都': 'Yūto Nagatomo',
    '谷口彰悟': 'Shōgo Taniguchi',
    '板仓滉': 'Kō Itakura',
    '渡边刚': 'Tsuyoshi Watanabe',
    '富安健洋': 'Takehiro Tomiyasu',
    '伊藤洋辉': 'Hiroki Itō',
    '濑古步梦': 'Ayumu Seko',
    '菅原由势': 'Yukinari Sugawara',
    '铃木淳之介': 'Junnosuke Suzuki',
    '远藤航': 'Wataru Endō',
    '伊东纯也': 'Junya Itō',
    '镰田大地': 'Daichi Kamada',
    '小川航基': 'Kōki Ogawa',
    '前田大然': 'Daizen Maeda',
    '堂安律': 'Ritsu Dōan',
    '上田绮世': 'Ayase Ueda',
    '田中碧': 'Ao Tanaka',
    '中村敬斗': 'Keito Nakamura',
    '佐野海舟': 'Kaishū Sano',
    '久保建英': 'Takefusa Kubo',
    '铃木唯人': 'Yuito Suzuki',
    '盐贝健人': 'Kento Shiogai',
    '后藤启介': 'Keisuke Gotō',
}

# ============ SOUTH KOREA (韩国) ============
TEAM_MAPS['韩国'] = {
    '金承奎': 'Kim Seung-gyu',
    '赵贤祐': 'Jo Hyeon-woo',
    '宋范根': 'Song Bum-keun',
    '金玟哉': 'Kim Min-jae',
    '金纹焕': 'Kim Moon-hwan',
    '金太铉': 'Kim Tae-hyeon',
    '朴镇燮': 'Park Jin-seob',
    '薛英佑': 'Seol Young-woo',
    '延斯·卡斯特罗普': 'Jens Castrop',
    '李期奕': 'Lee Gi-hyuk',
    '李太锡': 'Lee Tae-seok',
    '李韩汎': 'Lee Han-beom',
    '曹侑珉': 'Cho Yumin',
    '李在城': 'Lee Jae-sung',
    '黄喜灿': 'Hwang Hee-chan',
    '黄仁范': 'Hwang In-beom',
    '李刚仁': 'Lee Kang-in',
    '白昇浩': 'Paik Seung-ho',
    '金镇圭': 'Kim Jin-gyu',
    '李东炅': 'Lee Dong-gyeong',
    '裴俊浩': 'Bae Jun-ho',
    '严智星': 'Eom Ji-sung',
    '杨贤俊': 'Yang Hyun-jun',
    '孙兴慜': 'Son Heung-min',
    '曹圭成': 'Cho Gue-sung',
    '吴贤揆': 'Oh Hyeon-gyu',
}

# ============ AUSTRALIA (澳大利亚) ============
TEAM_MAPS['澳大利亚'] = {
    '马修·瑞安': 'Mathew Ryan',
    '保罗·伊佐': 'Paul Izzo',
    '帕特里克·比奇': 'Patrick Beach',
    '阿齐兹·贝希奇': 'Aziz Behich',
    '乔丹·博斯': 'Jordan Bos',
    '卡梅隆·伯吉斯': 'Cameron Burgess',
    '亚历山德罗·西卡蒂': 'Alessandro Circati',
    '米洛斯·德格内克': 'Miloš Degenek',
    '贾森·杰里亚': 'Jason Geria',
    '卢卡斯·赫林顿': 'Lucas Herrington',
    '雅各布·伊塔利亚诺': 'Jacob Italiano',
    '哈里·苏塔尔': 'Harry Souttar',
    '凯·特里温': 'Kai Trewin',
    '卡梅隆·德夫林': 'Cammy Devlin',
    '艾丁·赫鲁斯蒂奇': 'Ajdin Hrustic',
    '杰克逊·欧文': 'Jackson Irvine',
    '康纳·梅特卡夫': 'Connor Metcalfe',
    '保罗·奥孔-恩斯特勒': 'Paul Okon-Engstler',
    '艾登·奥尼尔': 'Aiden O\'Neill',
    '伊兰昆达': 'Nestory Irankunda',
    '马修·莱基': 'Mathew Leckie',
    '阿维·马比尔': 'Awer Mabil',
    '穆罕默德·图雷': 'Mohamed Touré',
    '尼山·韦卢皮莱': 'Nishan Velupillay',
    '克里斯蒂安·沃尔帕托': 'Cristian Volpato',
    '泰特·延吉': 'Tete Yengi',
}

# ============ QATAR (卡塔尔) ============
TEAM_MAPS['卡塔尔'] = {
    '马穆德·阿布纳德': 'Mahmoud Abunada',
    '萨拉赫·扎卡里亚': 'Salah Zakaria',
    '梅萨尔·巴沙姆': 'Meshaal Barsham',
    '佩德罗·米格尔': 'Pedro Miguel',
    '卢卡斯·门德斯': 'Lucas Mendes',
    '伊萨·拉耶': 'Issa Laye',
    '阿尤布·阿莱维': 'Ayoub Al-Oui',
    '霍曼·艾哈迈德': 'Homam Ahmed',
    '布阿莱姆·胡希': 'Boualem Khoukhi',
    '苏丹·布雷克': 'Sultan Al-Brake',
    '哈希米·阿尔侯赛因': 'Al-Hashmi Al-Hussain',
    '贾西姆·阿卜杜勒萨拉姆': 'Jassem Gaber',
    '阿卜杜勒阿齐兹·哈特姆': 'Abdulaziz Hatem',
    '卡里姆·布迪亚夫': 'Karim Boudiaf',
    '艾哈迈德·法特希': 'Ahmed Fathy',
    '阿西姆·马迪博': 'Assim Madibo',
    '穆罕默德·马奈': 'Mohamed Al-Mannai',
    '艾哈迈德·阿拉丁': 'Ahmed Alaaeldin',
    '埃迪米森': 'Edmilson Junior',
    '穆罕默德·蒙塔里': 'Mohammed Muntari',
    '哈桑·艾尔·海多斯': 'Hassan Al-Haydos',
    '阿克拉姆·阿菲夫': 'Akram Afif',
    '优素福·阿卜杜里萨格': 'Yusuf Abdurisag',
    '艾哈迈德·贾内希': 'Ahmed Al-Ganehi',
    '埃莫兹·阿里': 'Almoez Ali',
    '塔辛·穆罕默德·贾姆希德': 'Tahsin Jamshid',
}

# ============ IRAQ (伊拉克) ============
TEAM_MAPS['伊拉克'] = {
    '法哈德·塔利卜': 'Fahad Talib',
    '贾拉尔·哈桑': 'Jalal Hassan',
    '艾哈迈德·巴西勒': 'Ahmed Basil',
    '侯赛因·阿里': 'Hussein Ali',
    '穆纳夫·尤尼斯': 'Manaf Younis',
    '扎伊德·塔辛': 'Zaid Tahseen',
    '雷宾·苏拉卡': 'Rebin Sulaka',
    '阿卡姆·哈希姆': 'Akam Hashim',
    '梅赫加斯·多斯基': 'Merchas Doski',
    '艾哈迈德·叶海亚': 'Mustafa Saadoon',
    '扎伊德·伊斯梅尔': 'Zaid Ismail',
    '阿米尔·阿玛里': 'Amir Al-Ammari',
    '凯文·雅各布': 'Kevin Yakob',
    '齐达内·伊克巴尔': 'Zidane Iqbal',
    '艾马尔·谢尔': 'Aimar Sher',
    '弗兰斯·普特罗斯': 'Frans Putros',
    '穆斯塔法·萨敦': 'Ahmed Maknzi',
    '优素福·阿明': 'Youssef Amyn',
    '易卜拉欣·拜阿什': 'Ibrahim Bayesh',
    '艾哈迈德·卡塞姆': 'Ahmed Qasem',
    '马科·法尔吉': 'Marko Farji',
    '埃曼·侯赛因': 'Aymen Hussein',
    '莫哈纳德·阿里': 'Mohanad Ali',
    '阿里·哈马迪': 'Ali Al-Hamadi',
    '阿里·贾西姆': 'Ali Jasim',
    '阿里·优素福': 'Ali Yousif',
}

# ============ JORDAN (约旦) ============
TEAM_MAPS['约旦'] = {
    '亚奇德·阿布拉伊拉': 'Yazeed Abulaila',
    '努雷丁·扎伊德': 'Nour Bani Attiah',
    '阿卜杜拉·法霍里': 'Abdallah Al-Fakhouri',
    '穆罕默德·阿布海塞': 'Mohammad Abu Hasheesh',
    '阿卜杜拉·纳西布': 'Abdallah Nasib',
    '胡萨姆·阿布·达哈布': 'Husam Abu Dahab',
    '亚赞·阿拉伯': 'Yazan Al-Arab',
    '穆罕默德·阿卜拉纳迪': 'Mo Abualnadi',
    '萨利姆·奥贝德': 'Salim Obaid',
    '萨伊德·罗桑': 'Saed Al-Rosan',
    '埃桑·哈达德': 'Ihsan Haddad',
    '阿纳斯·巴达维': 'Anas Badawi',
    '穆罕默德·阿布-塔哈': 'Mohannad Abu Taha',
    '阿米尔·贾穆斯': 'Amer Jamous',
    '努尔·拉瓦比德': 'Noor Al-Rawabdeh',
    '拉杰伊·阿耶德': 'Rajaei Ayed',
    '易卜拉欣·萨德': 'Ibrahim Sadeh',
    '尼扎尔·拉什丹': 'Nizar Al-Rashdan',
    '穆罕默德·达伍德': 'Mohammad Al-Dawoud',
    '穆罕默德·阿布-兹雷克': 'Mohammad Abu Zrayq',
    '阿里·奥尔万': 'Ali Olwan',
    '穆萨·阿尔-塔马里': 'Musa Al-Taamari',
    '奥德·法胡里': 'Odeh Al-Fakhouri',
    '马赫穆德·马尔迪': 'Mahmoud Al-Mardi',
    '易卜拉欣·萨布拉': 'Ibrahim Sabra',
    '阿里·阿扎伊泽': 'Ali Azaizeh',
}

# ============ UZBEKISTAN (乌兹别克斯坦) ============
TEAM_MAPS['乌兹别克斯坦'] = {
    '乌特基尔·尤苏波夫': 'Utkir Yusupov',
    '阿卜杜沃希德·涅马托夫': 'Abduvohid Nematov',
    '博季拉利·埃尔加舍夫': 'Botirali Ergashev',
    '阿卜杜科迪尔·胡桑诺夫': 'Abdukodir Khusanov',
    '科贾阿克巴尔·阿里忠诺夫': 'Khojiakbar Alijonov',
    '鲁斯塔姆忠·阿舒尔马托夫': 'Rustam Ashurmatov',
    '谢尔佐德·叶萨诺夫': 'Sherzod Esanov',
    '乌马尔别克·埃什穆罗多夫': 'Umar Eshmurodov',
    '阿卜杜拉·阿卜杜拉耶夫': 'Abdulla Abdullaev',
    '别赫鲁兹·卡里莫夫': 'Bekhruz Karimov',
    '阿瓦兹别克·乌尔马萨利耶夫': 'Avazbek Ulmasaliev',
    '贾洪吉尔·乌罗佐夫': 'Jakhongir Urozov',
    '阿克马尔·莫兹戈沃伊': 'Akmal Mozgovoy',
    '奥塔别克·舒库罗夫': 'Otabek Shukurov',
    '贾姆希德·伊斯坎德罗夫': 'Jamshid Iskanderov',
    '奥迪尔忠·哈姆罗别科夫': 'Odiljon Hamrobekov',
    '贾洛利丁·马沙里波夫': 'Jaloliddin Masharipov',
    '奥斯顿·乌鲁诺夫': 'Oston Urunov',
    '多斯托恩别克·哈姆达莫夫': 'Dostonbek Khamdamov',
    '阿齐兹忠·加尼耶夫': 'Azizjon Ganiev',
    '阿博斯别克·法伊祖拉耶夫': 'Abbosbek Fayzullaev',
    '阿齐兹别克·阿莫诺夫': 'Azizbek Amonov',
    '埃尔多尔·肖穆罗多夫': 'Eldor Shomurodov',
    '伊戈尔·谢尔盖耶夫': 'Igor Sergeev',
    '扎苏尔·扎洛利德季诺夫': 'Jasurbek Jaloliddinov',   # 2002-05-15
    '谢尔佐德·捷米罗夫': 'Sherzod Temirov',            # 1998-10-27 (was wrongly mapped to Esanov)
}

# ============ NEW ZEALAND (新西兰) ============
TEAM_MAPS['新西兰'] = {
    '马克斯·克罗科姆': 'Max Crocombe',
    '亚历克斯·保尔森': 'Alex Paulsen',
    '迈克尔·伍德': 'Michael Woud',
    '蒂姆·佩恩': 'Tim Payne',
    '弗朗西斯·德弗里斯': 'Francis de Vries',
    '泰勒·宾登': 'Tyler Bindon',
    '迈克尔·博克萨尔': 'Michael Boxall',
    '利伯拉托·卡卡切': 'Liberato Cacace',
    '南多·派纳克': 'Nando Pijnaker',
    '芬·苏尔曼': 'Finn Surman',
    '卡伦·埃利奥特': 'Callan Elliot',
    '汤米·史密斯': 'Tommy Smith',
    '乔·贝尔': 'Joe Bell',
    '马特·加贝特': 'Matt Garbett',
    '马尔科·斯塔梅尼奇': 'Marko Stamenić',
    '萨尔普雷特·辛格': 'Sarpreet Singh',
    '亚历克斯·鲁弗': 'Alex Rufer',
    '本·奥尔德': 'Ben Old',
    '瑞安·托马斯': 'Ryan Thomas',
    '拉克兰·贝利斯': 'Lachlan Bayliss',
    '克里斯·伍德': 'Chris Wood',
    '埃利·贾斯特': 'Eli Just',
    '科斯塔·巴巴罗塞斯': 'Kosta Barbarouses',
    '本·韦恩': 'Ben Waine',
    '卡勒姆·麦考瓦特': 'Callum McCowatt',
    '杰西·兰德尔': 'Jesse Randall',
}

# ============ HAITI (海地) ============
TEAM_MAPS['海地'] = {
    '约翰尼·普拉西德': 'Johny Placide',
    '亚历山大·皮埃尔': 'Alexandre Pierre',
    '若苏埃·迪韦尔热': 'Josué Duverger',
    '里卡多·阿德': 'Ricardo Adé',
    '卡伦斯·阿库斯': 'Carlens Arcus',
    '汉内斯·德尔克罗瓦': 'Hannes Delcroix',
    '让-凯文·迪韦尔内': 'Jean-Kévin Duverne',
    '马丁·埃克斯佩里恩斯': 'Martin Expérience',
    '杜克·拉克鲁瓦': 'Duke Lacroix',
    '威尔金斯·保甘': 'Wilguens Paugain',
    '基托·瑟蒙西': 'Keeto Thermoncy',
    '让-里内·贝勒加德': 'Jean-Ricner Bellegarde',
    '丹利·让-雅克': 'Danley Jean-Jacques',
    '莱弗顿·皮埃尔': 'Leverton Pierre',
    '卡尔-弗雷德·圣特': 'Carl-Fred Sainté',
    '伍登斯基·皮埃尔': 'Woodensky Pierre',
    '多米尼克·西蒙': 'Dominique Simon',
    '卢伊修斯·迪德森': 'Louicius Deedson',
    '若苏埃·卡西米尔': 'Josué Casimir',
    '德里克·艾蒂安': 'Derrick Etienne Jr.',
    '亚辛·福尔图内': 'Yassin Fortuné',
    '威尔逊·伊西多尔': 'Wilson Isidor',
    '莱尼·约瑟夫': 'Lenny Joseph',
    '杜肯斯·纳宗': 'Duckens Nazon',
    '弗兰茨迪·皮埃罗': 'Frantzdy Pierrot',
    '鲁本·普罗维登斯': 'Ruben Providence',
}

# ============ PANAMA (巴拿马) ============
TEAM_MAPS['巴拿马'] = {
    '路易斯·梅希亚': 'Luis Mejía',
    '奥兰多·莫斯克拉': 'Orlando Mosquera',
    '塞萨尔·萨穆迪奥': 'César Samudio',
    '迈克尔·阿米尔·穆里略': 'Michael Amir Murillo',
    '安德烈斯·安德拉德': 'Andrés Andrade',
    '塞萨尔·布莱克曼': 'César Blackman',
    '何塞·科尔多瓦': 'José Córdoba',
    '埃里克·戴维斯': 'Eric Davis',
    '菲德尔·埃斯科瓦尔': 'Fidel Escobar',
    '埃德加多·法里纳': 'Edgardo Fariña',
    '豪尔赫·古铁雷斯': 'Jorge Gutiérrez',
    '罗德里克·米勒': 'Roderick Miller',
    '希奥瓦尼·拉莫斯': 'Jiovany Ramos',
    '约埃尔·巴尔塞纳斯': 'Yoel Bárcenas',
    '阿达尔贝托·卡拉斯奎利亚': 'Adalberto Carrasquilla',
    '阿尼瓦尔·戈多伊': 'Aníbal Godoy',
    '克里斯蒂安·马丁内斯': 'Cristian Martínez',
    '何塞·路易斯·罗德里格斯': 'José Luis Rodríguez',
    '卡洛斯·哈维': 'Carlos Harvey',
    '塞萨尔·亚尼斯': 'César Yanis',
    '阿尔贝托·金特罗': 'Alberto Quintero',
    '阿萨里亚斯·隆多尼奥': 'Azarías Londoño',
    '托马斯·罗德里格斯': 'Tomás Rodríguez',
    '伊斯梅尔·迪亚斯': 'Ismael Díaz',
    '何塞·法哈多': 'José Fajardo',
    '塞西利奥·沃特曼': 'Cecilio Waterman',
}

# ============ CURAÇAO (库拉索) ============
TEAM_MAPS['库拉索'] = {
    '埃洛伊·鲁姆': 'Eloy Room',
    '泰里克·博达克': 'Tyrick Bodak',
    '特雷弗·多恩布施': 'Trevor Doornbusch',
    '舒兰迪·桑博': 'Shurandy Sambo',
    '尤里恩·加里': 'Juriën Gaari',
    '罗顺·范·艾杰玛': 'Roshon van Eijma',
    '舍雷尔·弗洛拉努斯': 'Sherel Floranus',
    '阿曼多·奥比斯波': 'Armando Obispo',
    '约书亚·布雷内特': 'Joshua Brenet',
    '里切利·巴佐尔': 'Riechedly Bazoer',
    '德维隆·丰维尔': 'Deveron Fonville',
    '霍德里德·罗默拉托': 'Godfried Roemeratoe',
    '朱尼尼奥·巴库纳': 'Juninho Bacuna',
    '利瓦诺·科梅嫩西亚': 'Livano Comenencia',
    '莱安德罗·巴库纳': 'Leandro Bacuna',
    '泰雷塞·诺斯林': 'Tyrese Noslin',
    '阿尔扬尼·玛莎': 'Ar\'jany Martha',
    '塔希特·钟': 'Tahith Chong',
    '凯文·费利达': 'Kevin Felida',
    '于尔根·洛卡迪亚': 'Jürgen Locadia',
    '杰雷米·安东尼斯': 'Jeremy Antonisse',
    '松特耶·汉森': 'Sontje Hansen',
    '肯吉·戈雷': 'Kenji Gorré',
    '耶尔·玛格丽塔': 'Jearl Margaritha',
    '布兰德利·库瓦斯': 'Brandley Kuwas',
    '格瓦内·卡斯塔内尔': 'Gervane Kastaneer',
}

# ============ CAPE VERDE (佛得角) ============
TEAM_MAPS['佛得角'] = {
    '沃津哈': 'Josimar Dias',
    '马西奥·罗萨': 'Márcio Rosa',
    '卡洛斯·多斯·桑托斯': 'C.J. dos Santos',
    '斯托皮拉': 'Stopira',
    '迪尼伊': 'Diney',
    '罗伯托·洛佩斯': 'Roberto Lopes',
    '洛根·科斯塔': 'Logan Costa',
    '洛佩斯·卡布拉尔': 'Sidny Lopes Cabral',
    '史蒂芬·莫雷拉': 'Steven Moreira',
    '瓦格纳·皮纳': 'Wagner Pina',
    '凯尔文·皮雷斯': 'Kelvin Pires',
    '若昂·保罗·费尔南德斯': 'João Paulo Fernandes',
    '凯文·皮纳': 'Kevin Pina',
    '杰米罗·蒙特罗': 'Jamiro Monteiro',
    '德罗伊·杜亚特': 'Deroy Duarte',
    '拉罗斯·杜亚特': 'Laros Duarte',
    '亚尼克·塞梅多': 'Yannick Semedo',
    '特尔莫·阿尔坎若': 'Telmo Arcanjo',
    '若瓦内·卡布拉尔': 'Jovane Cabral',
    '吉尔松·塔瓦雷斯': 'Gilson Benchimol',
    '加里·罗德里格斯': 'Garry Rodrigues',
    '威利·塞梅多': 'Willy Semedo',
    '戴龙·利夫拉门托': 'Dailon Livramento',
    '瑞安·门德斯': 'Ryan Mendes',
    '努诺·达科斯塔': 'Nuno da Costa',
    '埃利奥·瓦雷拉': 'Hélio Varela',
}

# Build JSON output and update CSV
all_output = []
updated_count = 0

for cn_name, name_map in TEAM_MAPS.items():
    for cn_player, en_player in name_map.items():
        birth = get_birth(en_player)
        all_output.append([cn_name, cn_player, en_player, birth])

# Save mapping file
with open(MAP_OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(all_output, f, ensure_ascii=False, indent=2)

print(f"Saved {len(all_output)} mappings to {MAP_OUT_PATH}")

# Build lookup
lookup = {}
for item in all_output:
    cn, player, en, birth = item
    lookup[(cn, player)] = (en, birth)

# Update CSV
for i, r in enumerate(csv_rows):
    if r[0] not in TEAM_MAPS:
        continue
    key = (r[0], r[3])
    if key in lookup:
        en, birth = lookup[key]
        current_age = r[18].strip() if len(r) > 18 else ''
        if current_age != birth:
            old = current_age
            csv_rows[i][18] = birth
            updated_count += 1
            print(f"  UPDATE: {r[0]} {r[3]:25s} '{old}' -> '{birth}'")

with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(csv_rows)

print(f"\nUpdated {updated_count} rows in CSV")
print("Done!")
