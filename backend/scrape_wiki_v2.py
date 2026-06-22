"""
Playwright 批量爬 Wikipedia DOB
策略: 英文名直接访问 / 直接搜索
"""
import asyncio, json, csv, re
from datetime import date

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))

def slugify(name):
    """URL slug: 去掉 ·, 替换特殊字符"""
    return name.replace('·', ' ').replace('č', 'c').replace('ć', 'c').replace('š', 's').replace(
        'ž', 'z').replace('ř', 'r').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u').replace(
        'ş', 's').replace('ı', 'i').replace('ñ', 'n').replace('ø', 'o').replace(
        'æ', 'ae').replace('å', 'a').replace('é', 'e').replace('á', 'a').replace(
        'í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ý', 'y').replace(
        'ě', 'e').replace('ů', 'u').replace('ą', 'a').replace('ę', 'e').replace(
        'ł', 'l').replace('ń', 'n').replace('ś', 's').replace('ź', 'z').replace(
        'ż', 'z').replace('á', 'a').replace('à', 'a').replace('â', 'a').replace(
        'ã', 'a').replace('ä', 'a').replace('å', 'a').replace('ā', 'a').replace(
        'ă', 'a').replace('ȧ', 'a').replace('é', 'e').replace('è', 'e').replace(
        'ê', 'e').replace('ë', 'e').replace('ē', 'e').replace('ė', 'e').replace(
        'ę', 'e').replace('ě', 'e').replace('í', 'i').replace('ì', 'i').replace(
        'î', 'i').replace('ï', 'i').replace('ī', 'i').replace('į', 'i').replace(
        'ó', 'o').replace('ò', 'o').replace('ô', 'o').replace('õ', 'o').replace(
        'ö', 'o').replace('ō', 'o').replace('ő', 'o').replace('ú', 'u').replace(
        'ù', 'u').replace('û', 'u').replace('ü', 'u').replace('ū', 'u').replace(
        'ű', 'u').replace('ý', 'y').replace('ỳ', 'y').replace('ŷ', 'y').replace(
        'ÿ', 'y').replace('ȳ', 'y').replace('ć', 'c').replace('ģ', 'g').replace(
        'ķ', 'k').replace('ļ', 'l').replace('ń', 'n').replace('ņ', 'n').replace(
        'š', 's').replace('ž', 'z').replace('Œ', 'OE').replace('œ', 'oe').replace(
        'ß', 'ss').replace('&', 'and').replace("'", '').replace('`', '').replace("'", "'")


async def scrape_player(en_name, cn_name, team):
    """访问 Wikipedia 球员页面, 提取 DOB"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        )
        page = await context.new_page()

        # 策略1: 直接访问 /wiki/Name
        direct_url = None
        try:
            slug = slugify(en_name).replace(' ', '_')
            url = f'https://en.wikipedia.org/wiki/{slug}'
            response = await page.goto(url, timeout=12000)
            if response and response.status == 200:
                title = await page.title()
                if 'football' in title.lower() or 'footballer' in title.lower() or 'soccer' in title.lower() or any(k in title.lower() for k in team.lower().split()):
                    direct_url = url
                await page.wait_for_timeout(800)
        except:
            pass

        # 策略2: 搜索
        if not direct_url:
            try:
                search_url = f'https://en.wikipedia.org/w/index.php?search={slugify(en_name).replace(" ", "+")}&title=Special%3ASearch&go=Go'
                await page.goto(search_url, timeout=12000, wait_until='domcontentloaded')
                await page.wait_for_timeout(1500)
                # 点击第一个结果
                try:
                    first_link = page.locator('.mw-search-result-heading a').first
                    if await first_link.is_visible(timeout=3000):
                        href = await first_link.get_attribute('href')
                        direct_url = f'https://en.wikipedia.org{href}'
                        await page.goto(direct_url, timeout=12000, wait_until='domcontentloaded')
                        await page.wait_for_timeout(800)
                except:
                    pass
            except:
                pass

        # 提取 DOB
        dob = await page.evaluate('''() => {
            const bday = document.querySelector('.bday');
            if (bday) return bday.textContent.trim();
            const time = document.querySelector('time[itemprop=birthDate]');
            if (time) return time.getAttribute('datetime');
            const time2 = document.querySelector('time[datetime]');
            if (time2) return time2.getAttribute('datetime');
            return null;
        }''')

        title = await page.title()
        url = page.url

        await browser.close()
        return {'en': en_name, 'cn': cn_name, 'team': team, 'dob': dob, 'title': title, 'url': url}


async def main():
    # 加载所有已知英文名
    with open('backend/manual_name_map.json') as f:
        manual = json.load(f)

    # ESPN cache 有英文名
    import os
    CN_FROM_EN = {
        'Mexico': '墨西哥', 'South Africa': '南非', 'South Korea': '韩国', 'Czechia': '捷克',
        'Canada': '加拿大', 'Bosnia-Herzegovina': '波黑', 'United States': '美国', 'Paraguay': '巴拉圭',
        'Qatar': '卡塔尔', 'Switzerland': '瑞士', 'Brazil': '巴西', 'Morocco': '摩洛哥',
        'Haiti': '海地', 'Scotland': '苏格兰', 'Australia': '澳大利亚', 'Türkiye': '土耳其',
        'Germany': '德国', 'Curaçao': '库拉索', 'Netherlands': '荷兰', 'Japan': '日本',
        'Ivory Coast': '科特迪瓦', 'Ecuador': '厄瓜多尔', 'Sweden': '瑞典', 'Tunisia': '突尼斯',
        'Spain': '西班牙', 'Cape Verde': '佛得角', 'Belgium': '比利时', 'Egypt': '埃及',
        'Saudi Arabia': '沙特', 'Uruguay': '乌拉圭', 'Iran': '伊朗', 'New Zealand': '新西兰',
        'France': '法国', 'Senegal': '塞内加尔', 'Iraq': '伊拉克', 'Norway': '挪威',
        'Argentina': '阿根廷', 'Algeria': '阿尔及利亚', 'Austria': '奥地利', 'Jordan': '约旦',
        'Portugal': '葡萄牙', 'Congo DR': '民主刚果', 'England': '英格兰', 'Croatia': '克罗地亚',
        'Ghana': '加纳', 'Panama': '巴拿马', 'Uzbekistan': '乌兹别克斯坦', 'Colombia': '哥伦比亚',
    }
    EN_FROM_CN = {v: k for k, v in CN_FROM_EN.items()}

    # 收集所有需要爬的球员: (en_name, cn_name, team)
    to_scrape = []

    # 1. 手工映射有英文名的
    for team, mapping in manual.items():
        if team == '_comment': continue
        for cn, en in mapping.items():
            if en and cn:  # 有英文名
                to_scrape.append((en, cn, team))

    # 2. 从 ESPN cache 英文名里找候选 (pypinyin 匹配)
    from pypinyin import lazy_pinyin
    espn_by_team = {}
    for fname in os.listdir('1_数据基础/espn_match_data'):
        if not fname.endswith('.json'): continue
        with open(f'1_数据基础/espn_match_data/{fname}') as f:
            d = json.load(f)
        for r in d.get('rosters', []):
            team_en = r.get('team', {}).get('displayName', '')
            team_cn = CN_FROM_EN.get(team_en, team_en)
            for p in r.get('roster', []):
                n = p.get('athlete', {}).get('displayName', '')
                if n and team_cn not in espn_by_team:
                    espn_by_team[team_cn] = []
                if n:
                    espn_by_team.setdefault(team_cn, []).append(n)

    def cn_to_py(name):
        parts = name.split('·')
        def to_py(s):
            return ''.join(lazy_pinyin(s, style=0))
        if len(parts) < 2:
            return to_py(parts[0]), to_py(parts[0])
        py0, py1 = to_py(parts[0]), to_py(parts[1])
        return (py0, py1) if len(parts[0]) >= len(parts[1]) else (py1, py0)

    # 加载主表未修
    with open('1_数据基础/world_cup_2026_complete.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    unfixed_names = set()
    for r in rows:
        a = r['年龄']
        if a == 'X待核实' or ('-' in a and a != 'X待核实') or (a.isdigit() and (int(a) < 16 or int(a) > 45)):
            unfixed_names.add((r['国家'], r['球员']))

    # 对于未修球员, 找 ESPN 英文名候选
    existing_en = set(e for e, _, _ in to_scrape)
    for team, cn in unfixed_names:
        if team not in espn_by_team: continue
        cn_first, cn_last = cn_to_py(cn)
        for en in espn_by_team.get(team, []):
            if en in existing_en: continue
            en_words = en.lower().split()
            if len(en_words) < 2: continue
            en_last = en_words[-1]
            # 宽松匹配: lastName 前3字符
            if cn_last[:3] and en_last.startswith(cn_last[:3].lower()):
                to_scrape.append((en, cn, team))
                existing_en.add(en)
                break

    # 去重
    seen = set()
    unique = []
    for en, cn, team in to_scrape:
        key = (en, cn, team)
        if key not in seen:
            seen.add(key)
            unique.append((en, cn, team))

    print(f'待爬: {len(unique)} 个 (去重后)')

    # 分批爬 (5个一批)
    results = {}
    batch_size = 5
    found = 0
    for i in range(0, min(len(unique), 200), batch_size):
        batch = unique[i:i+batch_size]
        print(f'\n批次 {i//batch_size+1}: 爬 {len(batch)} 个', flush=True)
        tasks = [scrape_player(en, cn, team) for en, cn, team in batch]
        batch_results = await asyncio.gather(*tasks)
        for r in batch_results:
            key = f"{r['team']}|{r['cn']}"
            results[key] = r
            if r['dob'] and len(r['dob']) >= 10:
                dob = r['dob'][:10]
                age = calc_age(dob)
                if 16 <= age <= 45:
                    print(f"  ✅ {r['team']:<6} {r['cn']:<20} → {r['en']:<25} {dob} age={age}")
                    found += 1
                else:
                    print(f"  ⚠️  {r['team']:<6} {r['cn']:<20} → {r['en']:<25} {dob} age={age} (离谱)")
            else:
                print(f"  ❌ {r['team']:<6} {r['cn']:<20} → {r['en']:<25} [{r['title'][:40]}]")
            await asyncio.sleep(0.8)

    # 保存
    with open('1_数据基础/wiki_scrape_results.json', 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'\n✅ 完成! 找到 {found} 个 DOB')
    # 统计
    ok = sum(1 for r in results.values() if r.get('dob') and len(r.get('dob','')) >= 10)
    print(f'总: {ok}/{len(results)}')


if __name__ == '__main__':
    asyncio.run(main())
