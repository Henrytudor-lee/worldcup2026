"""生成 793 个无年龄球员的优先级队列, 按 FIFA 排名 + 身价排序"""
import csv

with open('/Users/garcia/Desktop/WorldCup2026/1_数据基础/world_cup_2026_complete.csv') as f:
    rows = list(csv.DictReader(f))

# FIFA 排名 Top 50
fifa_top = {
    '西班牙':1,'阿根廷':2,'法国':3,'英格兰':4,'巴西':5,'葡萄牙':6,'荷兰':7,'比利时':8,'德国':9,'意大利':10,
    '乌拉圭':11,'哥伦比亚':12,'克罗地亚':13,'摩洛哥':14,'墨西哥':15,'美国':16,'日本':17,'瑞士':18,'丹麦':19,'塞内加尔':20,
    '伊朗':21,'韩国':22,'厄瓜多尔':23,'奥地利':24,'乌克兰':25,'土耳其':26,'波兰':27,'澳大利亚':28,'沙特':29,'突尼斯':30,
    '捷克':31,'苏格兰':32,'加拿大':33,'加纳':34,'摩洛哥':34,'罗马尼亚':35,'巴拉圭':36,'巴拿马':37,'阿尔及利亚':38,'挪威':39,
    '瑞典':40,'日本':17,'威尔士':41,'北马其顿':42,'秘鲁':43,'南非':44,'新西兰':45,'佛得角':46,'民主刚果':47,'海地':48,
    '约旦':49,'乌兹别克斯坦':50,
}

no_age = []
for r in rows:
    if not r.get('年龄') or r['年龄'] == 'X待核实':
        no_age.append({
            '国家': r['国家'],
            '球员': r['球员'],
            '位置': r.get('位置', ''),
            '俱乐部': r.get('俱乐部', ''),
            '身价_万欧': float(r.get('身价_万欧', 0) or 0),
            'fifa': fifa_top.get(r['国家'], 99),
        })

# 排序: FIFA 排名 (1-50=Top, 99=Other), 然后身价降序
no_age.sort(key=lambda x: (x['fifa'], -x['身价_万欧']))

print(f'无年龄球员总数: {len(no_age)}')
print()
print('=== 优先级队列 (Top 50) ===')
for i, p in enumerate(no_age[:80]):
    star = '⭐' if p['fifa'] <= 20 else ('✓' if p['fifa'] <= 50 else ' ')
    print(f'{i+1:3d}. {star} [{p["fifa"]:2d}] {p["国家"]:<8} {p["球员"]:<14} ({p["位置"]:<6}) @ {p["俱乐部"]:<14} {p["身价_万欧"]:>6.0f}万欧')

# 保存队列
with open('/Users/garcia/Desktop/WorldCup2026/1_数据基础/age_queue.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['国家', '球员', '位置', '俱乐部', '身价_万欧', 'fifa'])
    writer.writeheader()
    writer.writerows(no_age)
print(f'\n✅ 队列已保存到 age_queue.csv ({len(no_age)} 条)')

# 按 FIFA 统计
from collections import Counter
c = Counter(p['fifa'] for p in no_age)
print('\n=== 按 FIFA 段统计 ===')
print(f'Top 20 强队缺: {sum(v for k, v in c.items() if k <= 20)}')
print(f'Top 21-50 强队缺: {sum(v for k, v in c.items() if 21 <= k <= 50)}')
print(f'Other (小国) 缺: {sum(v for k, v in c.items() if k > 50)}')
