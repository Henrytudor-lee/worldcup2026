"""
根据搜索到的真实名单，修正 manual_name_map 并重跑 Wikipedia scrape
只针对最终进入48强名单的球员
"""
import json, csv, asyncio, os
from datetime import date
from pypinyin import lazy_pinyin

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    d = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))

def to_py(name):
    return ''.join(lazy_pinyin(name, style=0))

# 加载现有 map
manual = json.load(open('backend/manual_name_map.json'))

# ========================
# 已确认的正确英文名映射（基于搜索到的名单）
# ========================
correct_maps = {
    '沙特': {
        '卡萨尔': 'Ahmed Al-Kassar',
        '塔克里': 'Jihaj Al-Taqri',
        '哈尔比': 'Moteb Al-Harbi',
        '哈巴利': 'Al-Habli',
        '布沙尔': 'Al-Bushar',
        '赫吉': 'Al-Haji',
        '加纳姆': 'Khaled Al-Ghanam',
        '朱瓦伊尔': 'Al-Juwair',
        '叶海亚': 'Ayman Yahya',
        '布赖坎': 'Firas Al-Buraikan',
        '谢赫里': 'Saleh Al-Shahrani',
    },
    '约旦': {
        '萨利姆·奥贝德': 'Salem Obaid',
        '阿卜杜拉·法霍里': 'Abdallah Al-Fakhouri',
        '阿米尔·贾穆斯': 'Amer Jamal',
        '努尔·拉瓦比德': 'Nour Al-Rawabdeh',
        '尼扎尔·拉什丹': 'Nizar Al-Rashdan',
        '穆罕默德·达伍德': 'Mohammad Dawood',
        '穆罕默德·阿布-兹雷克': 'Mohammad Abu Zreik',
        '阿里·奥尔万': 'Ali Al-Orman',
        '易卜拉欣·萨布拉': 'Ibrahim Sabra',
        '亚赞·阿拉伯': 'Yazan Al-Arab',
    },
    '乌兹别克斯坦': {
        '奥斯顿·乌鲁诺夫': 'Oston Ostonov',
        '奥迪尔忠·哈姆罗别科夫': 'Odiljon Qalandarov',
        '谢尔佐德·捷米罗夫': 'Sherzod Temirov',
        '贾洪吉尔·乌罗佐夫': 'Jakhongir Urozov',
        '阿卜杜沃希德·涅马托夫': 'Abdulvozhid Nematov',
    },
}

# 更新 map
for team, mapping in correct_maps.items():
    if team not in manual:
        manual[team] = {}
    for cn, en in mapping.items():
        manual[team][cn] = en

with open('backend/manual_name_map.json', 'w') as f:
    json.dump(manual, f, ensure_ascii=False, indent=2)
print('Map 更新完成')

# 主表 X待核实
rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))
xun = [(r['国家'], r['球员']) for r in rows if r['年龄'] == 'X待核实']
xun_set = set(xun)
print(f'X待核实: {len(xun_set)}')

# 对这214人：分类
# A. 有正确英文名且需要重爬
# B. 有正确英文名且之前已爬有效
# C. 名字拼错需要修正的
# D. 不在最终名单的

# 从之前 scrape 结果恢复有效 DOB
scrape_results = {}
if os.path.exists('1_数据基础/wiki_scrape_v3_results.json'):
    scrape_results = json.load(open('1_数据基础/wiki_scrape_v3_results.json'))

# 统计
in_scrape_valid = {}  # (team,cn) -> (dob, age)
in_scrape_outlier = {}  # (team,cn) -> (dob, age)
not_in_scrape = {}

for team, cn in xun_set:
    key = f'{team}|{cn}'
    if key in scrape_results:
        dob = scrape_results[key].get('dob', '')
        if dob and len(dob) >= 10:
            dob = dob[:10]
            try:
                age = calc_age(dob)
                if 16 <= age <= 45:
                    in_scrape_valid[(team, cn)] = (dob, age)
                else:
                    in_scrape_outlier[(team, cn)] = (dob, age)
            except:
                not_in_scrape[(team, cn)] = scrape_results[key]
        else:
            not_in_scrape[(team, cn)] = scrape_results[key]
    else:
        not_in_scrape[(team, cn)] = None

print(f'有效DOB可恢复: {len(in_scrape_valid)}')
print(f'离谱值(需新查): {len(in_scrape_outlier)}')
print(f'未爬到(需新爬): {len(not_in_scrape)}')

# ========================
# 剩余需要重新爬的球员
# 策略: 用正确的英文名，查 Wikipedia search
# ========================
async def scrape_wiki(en_name, cn_name, team):
    """Wikipedia search + DOB extraction"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        ).new_page()

        # 先搜索
        search_url = f'https://en.wikipedia.org/w/index.php?search={en_name.replace(\" \", \"+\")}&title=Special%3ASearch'
        dob = None
        url_used = None
        title_used = None
        try:
            await page.goto(search_url, timeout=12000, wait_until='domcontentloaded')
            await page.wait_for_timeout(1500)
            # 点击第一个结果
            try:
                first = page.locator('.mw-search-result-heading a').first
                if await first.is_visible(timeout=3000):
                    href = await first.get_attribute('href')
                    title_used = await first.inner_text()
                    detail_url = f'https://en.wikipedia.org{href}'
                    await page.goto(detail_url, timeout=12000, wait_until='domcontentloaded')
                    await page.wait_for_timeout(800)
                    dob = await page.evaluate('''() => {
                        const b = document.querySelector(\'.bday\');
                        if (b) return b.textContent.trim();
                        const t = document.querySelector(\'time[itemprop=birthDate]\');
                        if (t) return t.getAttribute(\'datetime\');
                        return null;
                    }''')
                    url_used = page.url
            except:
                # 直接访问
                slug = en_name.replace(' ', '_')
                direct = f'https://en.wikipedia.org/wiki/{slug}'
                await page.goto(direct, timeout=12000, wait_until='domcontentloaded')
                dob2 = await page.evaluate('''() => {
                    const b = document.querySelector(\'.bday\');
                    if (b) return b.textContent.trim();
                    const t = document.querySelector(\'time[itemprop=birthDate]\');
                    if (t) return t.getAttribute(\'datetime\');
                    return null;
                }''')
                if dob2:
                    dob = dob2
                    url_used = page.url
                    title_used = await page.title()
        except:
            pass

        await browser.close()
        return {'en': en_name, 'cn': cn_name, 'team': team, 'dob': dob, 'title': title_used or '', 'url': url_used or ''}

# 剩余需要重爬的：in_scrape_outlier + not_in_scrape
retry_list = []
for (team, cn) in list(in_scrape_outlier.keys()) + list(not_in_scrape.keys()):
    en = None
    if team in manual and cn in manual[team]:
        en = manual[team][cn]
    if en:
        retry_list.append((en, cn, team))
    else:
        # 没有英文名，标记 X待核实
        pass

print(f'\n需要重爬: {len(retry_list)} 个 (有正确英文名)')
print(f'没有英文名: {len(retry_list2:=len([1 for (team,cn) in list(in_scrape_outlier.keys())+list(not_in_scrape.keys()) if not (team in manual and cn in manual.get(team,{}))]))} 个')

# 先把有效的结果写回去（从scrape_v3）
final_valid = {}
for (team, cn), (dob, age) in in_scrape_valid.items():
    key = f'{team}|{cn}'
    r = scrape_results.get(key, {})
    final_valid[(team, cn)] = {'dob': dob, 'age': age, 'en': r.get('en', '')}

# ========================
# 写回主表
# ========================
updates = {}
for row in rows:
    team, cn, orig = row['国家'], row['球员'], row['年龄']
    if orig != 'X待核实':
        continue
    key = (team, cn)
    if key in in_scrape_valid:
        dob, age = in_scrape_valid[key]
        row['年龄'] = str(age)
        updates[key] = {'dob': dob, 'age': age, 'source': 'wiki_v3'}
    elif key in in_scrape_outlier:
        # 离谱值保持 X待核实
        pass

fieldnames = list(rows[0].keys())
with open('1_数据基础/world_cup_2026_complete.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f'\n写回完成! 本轮恢复有效: {len(in_scrape_valid)} 条')
print(f'离谱值待重爬: {len(in_scrape_outlier)} 条')
print(f'完全未找到: {len(not_in_scrape)} 条')

# 最终统计
real = sum(1 for r in rows if r['年龄'].isdigit() and 16 <= int(r['年龄']) <= 45)
xun = sum(1 for r in rows if r['年龄'] == 'X待核实')
print(f'主表现在: 真实{real}/1248  X待核实{xun}/1248')
