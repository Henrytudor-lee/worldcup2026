"""
Wikipedia DOB 爬虫 v3
只爬 371 个 X待核实球员，全部用已知英文名
"""
import asyncio, json, csv, re, os
from datetime import date

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    d = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))

def slugify(name):
    """URL slug: 特殊字符 → ASCII"""
    s = name.replace('·', ' ').replace('č', 'c').replace('ć', 'c').replace('š', 's').replace(
        'ž', 'z').replace('ř', 'r').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u').replace(
        'ş', 's').replace('ı', 'i').replace('ñ', 'n').replace('ø', 'o').replace(
        'æ', 'ae').replace('å', 'a').replace('é', 'e').replace('á', 'a').replace(
        'í', 'i').replace('ó', 'o').replace('ú', 'u').replace('ý', 'y').replace(
        'ě', 'e').replace('ů', 'u').replace('ą', 'a').replace('ę', 'e').replace(
        'ł', 'l').replace('ń', 'n').replace('ś', 's').replace('ź', 'z').replace(
        'ż', 'z').replace('â', 'a').replace('ã', 'a').replace('ä', 'a').replace(
        'ā', 'a').replace('ă', 'a').replace('ė', 'e').replace('ė', 'e').replace(
        'ę', 'e').replace('ë', 'e').replace('ê', 'e').replace('è', 'e').replace(
        'î', 'i').replace('ï', 'i').replace('ī', 'i').replace('į', 'i').replace(
        'ô', 'o').replace('õ', 'o').replace('ō', 'o').replace('ő', 'o').replace(
        'û', 'u').replace('ű', 'u').replace('ÿ', 'y').replace('ȳ', 'y').replace(
        'ć', 'c').replace('ģ', 'g').replace('ķ', 'k').replace('ļ', 'l').replace(
        'ń', 'n').replace('ņ', 'n').replace('Œ', 'OE').replace('œ', 'oe').replace(
        'ß', 'ss').replace('&', 'and').replace("'", '').replace('`', '').replace("'", "'")
    return s

async def scrape_player(en_name, cn_name, team):
    """访问 Wikipedia 球员页面, 提取 DOB"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        )
        page = await context.new_page()

        # 策略1: 直接访问
        dob = None
        title_used = ''
        url_used = ''
        try:
            slug = slugify(en_name).replace(' ', '_')
            url = f'https://en.wikipedia.org/wiki/{slug}'
            response = await page.goto(url, timeout=12000)
            if response and response.status == 200:
                dob = await page.evaluate('''() => {
                    const bday = document.querySelector('.bday');
                    if (bday) return bday.textContent.trim();
                    const t = document.querySelector('time[itemprop=birthDate]');
                    if (t) return t.getAttribute('datetime');
                    const t2 = document.querySelector('time[datetime]');
                    if (t2) return t2.getAttribute('datetime');
                    return null;
                }''')
                if dob:
                    title_used = await page.title()
                    url_used = page.url
                    await browser.close()
                    return {'en': en_name, 'cn': cn_name, 'team': team, 'dob': dob, 'title': title_used, 'url': url_used}
            await page.wait_for_timeout(500)
        except:
            pass

        # 策略2: 搜索
        try:
            search_url = f'https://en.wikipedia.org/w/index.php?search={slugify(en_name).replace(" ", "+")}&title=Special%3ASearch'
            await page.goto(search_url, timeout=12000, wait_until='domcontentloaded')
            await page.wait_for_timeout(1500)
            try:
                first_link = page.locator('.mw-search-result-heading a').first
                if await first_link.is_visible(timeout=3000):
                    href = await first_link.get_attribute('href')
                    direct_url = f'https://en.wikipedia.org{href}'
                    await page.goto(direct_url, timeout=12000, wait_until='domcontentloaded')
                    dob2 = await page.evaluate('''() => {
                        const bday = document.querySelector('.bday');
                        if (bday) return bday.textContent.trim();
                        const t = document.querySelector('time[itemprop=birthDate]');
                        if (t) return t.getAttribute('datetime');
                        const t2 = document.querySelector('time[datetime]');
                        if (t2) return t2.getAttribute('datetime');
                        return null;
                    }''')
                    if dob2:
                        dob = dob2
                        title_used = await page.title()
                        url_used = page.url
            except:
                pass
        except:
            pass

        await browser.close()
        return {'en': en_name, 'cn': cn_name, 'team': team, 'dob': dob, 'title': title_used or 'no_result', 'url': url_used or 'no_result'}

async def main():
    # 加载 manual map
    manual = json.load(open('backend/manual_name_map.json'))

    # 主表 X待核实
    rows = list(csv.DictReader(open('1_数据基础/world_cup_2026_complete.csv')))
    xun = [x for x in rows if x['年龄'] == 'X待核实']
    xun_set = {(x['国家'], x['球员']) for x in xun}
    print(f'X待核实: {len(xun_set)}')

    # 从 manual map 找这些人的英文名
    candidates = []
    for x in xun:
        team, cn = x['国家'], x['球员']
        if team in manual and cn in manual[team]:
            en = manual[team].get(cn, '')
            if en:
                candidates.append((en, cn, team))
            else:
                print(f'  ⚠️  无英文名: ({team}, {cn})')
        else:
            print(f'  ⚠️  未在 manual map: ({team}, {cn})')

    print(f'有英文名候选: {len(candidates)}')

    # 加载已有结果（断点续传）
    results = {}
    results_file = '1_数据基础/wiki_scrape_v3_results.json'
    if os.path.exists(results_file):
        results = json.load(open(results_file))
        print(f'已有结果: {len(results)} 条 (续传)')

    # 分批爬
    batch_size = 8
    found = 0
    total = len(candidates)

    for i in range(0, total, batch_size):
        batch = candidates[i:i+batch_size]
        batch_i = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f'\n批次 {batch_i}/{total_batches}: 爬 {len(batch)} 个', flush=True)

        tasks = [scrape_player(en, cn, team) for en, cn, team in batch]
        batch_results = await asyncio.gather(*tasks)

        for r in batch_results:
            key = f"{r['team']}|{r['cn']}"
            results[key] = r
            dob = r.get('dob') or ''
            if dob and len(dob) >= 10:
                dob = dob[:10]
                age = calc_age(dob)
                if 16 <= age <= 45:
                    print(f"  ✅ {r['team']:<6} {r['cn']:<20} → {r['en']:<25} {dob} age={age}")
                    found += 1
                else:
                    print(f"  ⚠️  {r['team']:<6} {r['cn']:<20} → {r['en']:<25} {dob} age={age} (离谱)")
            else:
                print(f"  ❌ {r['team']:<6} {r['cn']:<20} → {r['en']:<25} [未找到 DOB] [{r['title'][:40]}]")
            await asyncio.sleep(1.0)

        # 每批保存断点
        with open(results_file, 'w') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    # 最终统计
    valid = {k: v for k, v in results.items() if v.get('dob') and len(v.get('dob','')) >= 10}
    print(f'\n=== 完成 ===')
    print(f'总爬取: {len(results)}  有效DOB: {len(valid)}  离谱: {len(results)-len(valid)}')

    # 覆盖 X待核实情况
    covered = sum(1 for k in valid if tuple(k.split('|')) in xun_set)
    print(f'覆盖X待核实: {covered}/{len(xun_set)}')

if __name__ == '__main__':
    asyncio.run(main())
