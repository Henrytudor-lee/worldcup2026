"""
抓取中文维基百科 48队球员名单（含中文名）
用于：主表中文名 ↔ Wikipedia DOB 精确匹配
"""
import asyncio, json, re, os

# 48队中文维基百科 slug
ZH_TEAMS = {
    '英格兰': '英格兰国家足球队',
    '法国': '法国国家足球队',
    '德国': '德国国家足球队',
    '西班牙': '西班牙国家足球队',
    '葡萄牙': '葡萄牙国家足球队',
    '荷兰': '荷兰国家足球队',
    '比利时': '比利时国家足球队',
    '克罗地亚': '克罗地亚国家足球队',
    '瑞士': '瑞士国家足球队',
    '奥地利': '奥地利国家足球队',
    '苏格兰': '苏格兰足球代表队',
    '挪威': '挪威国家足球队',
    '土耳其': '土耳其国家足球队',
    '瑞典': '瑞典国家足球队',
    '捷克': '捷克国家足球队',
    '波黑': '波斯尼亚和黑塞哥维那国家足球队',
    '日本': '日本国家足球队',
    '伊朗': '伊朗国家足球队',
    '韩国': '韩国国家足球队',
    '澳大利亚': '澳大利亚国家足球队',
    '沙特': '沙特阿拉伯国家足球队',
    '卡塔尔': '卡塔尔国家足球队',
    '乌兹别克斯坦': '乌兹别克斯坦国家足球队',
    '约旦': '约旦国家足球队',
    '伊拉克': '伊拉克国家足球队',
    '摩洛哥': '摩洛哥国家足球队',
    '塞内加尔': '塞内加尔国家足球队',
    '埃及': '埃及国家足球队',
    '科特迪瓦': '科特迪瓦国家足球队',
    '加纳': '加纳国家足球队',
    '突尼斯': '突尼斯国家足球队',
    '阿尔及利亚': '阿尔及利亚国家足球队',
    '南非': '南非国家足球队',
    '佛得角': '佛得角国家足球队',
    '民主刚果': '民主刚果国家足球队',
    '阿根廷': '阿根廷国家足球队',
    '巴西': '巴西国家足球队',
    '乌拉圭': '乌拉圭国家足球队',
    '哥伦比亚': '哥伦比亚国家足球队',
    '厄瓜多尔': '厄瓜多尔国家足球队',
    '巴拉圭': '巴拉圭国家足球队',
    '美国': '美国国家男子足球队',
    '加拿大': '加拿大国家男子足球队',
    '墨西哥': '墨西哥国家足球队',
    '巴拿马': '巴拿马国家足球队',
    '海地': '海地国家足球队',
    '库拉索': '库拉索国家足球队',
    '新西兰': '新西兰国家足球队',
}

async def fetch_zh_squad(team_cn, slug):
    """抓取中文维基百科球员名单"""
    from playwright.async_api import async_playwright

    url = f'https://zh.wikipedia.org/wiki/{slug}'
    players = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            )
            page = await context.new_page()
            await page.goto(url, timeout=20000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # 找球员名单表格（有 "号码" 或 "位置" 列）
            tables = await page.query_selector_all('table')
            squad_table = None
            for t in tables:
                txt = await t.inner_text()
                if ('号码' in txt and '出生' in txt) or ('No.' in txt and 'Pos' in txt and 'Caps' in txt):
                    squad_table = t
                    break

            if not squad_table:
                await browser.close()
                return {'team': team_cn, 'url': url, 'players': [], 'count': 0, 'error': 'no squad table'}

            rows = await squad_table.query_selector_all('tr')
            print(f' ({len(rows)}行)', end='')

            # 中文维基百科格式：| 号码 | 位置 | 球员 | 出生日期 | ... |
            # 或: | No. | Pos | Player | Date of birth | ... |
            for row in rows[1:]:  # 跳过表头
                cells = await row.query_selector_all('th, td')
                if len(cells) < 4:
                    continue

                # 提取中文名（球员列，通常是第3个单元格）
                name_cell_idx = 2  # 默认：号码(0) 位置(1) 球员(2) 出生(3)
                name = ''
                dob_text = ''

                for ci, cell in enumerate(cells):
                    txt = await cell.inner_text()
                    # 跳过位置单元格
                    if txt.strip() in {'GK', 'DF', 'MF', 'FW', '门将', '后卫', '中场', '前锋', '守门员'}:
                        continue
                    # 找第一个有链接的非位置单元格
                    link = await cell.query_selector('a[href^="/wiki/"]')
                    if link and not name:
                        link_text = (await link.inner_text()).strip()
                        # 排除非球员链接
                        skip = {'教练', '主教练', '经理', '队长', '门将', '后卫', '中场', '前锋',
                               'GK', 'DF', 'MF', 'FW', '世界杯', '欧洲杯', '国家', '联赛'}
                        if link_text and link_text not in skip and len(link_text) > 1:
                            name = link_text
                            name_cell_idx = ci
                            break

                if not name:
                    continue

                # 找 DOB（第4个单元格或包含日期的单元格）
                dob = ''
                for ci, cell in enumerate(cells):
                    if ci == name_cell_idx:
                        continue
                    txt = await cell.inner_text()
                    # 匹配日期格式：YYYY-MM-DD 或 YYYY年M月D日
                    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', txt)
                    if m:
                        dob = f'{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}'
                        break
                    # 中文格式：YYYY年M月D日
                    m2 = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', txt)
                    if m2:
                        dob = f'{m2.group(1)}-{m2.group(2).zfill(2)}-{m2.group(3).zfill(2)}'
                        break

                if name and dob:
                    from datetime import date
                    try:
                        parts = dob.split('-')
                        d = date(int(parts[0]), int(parts[1]), int(parts[2]))
                        age = (date(2026, 6, 15) - d).days // 365
                        if 16 <= age <= 45:
                            players.append({'cn': name, 'dob': dob, 'age': age})
                    except:
                        pass

            await browser.close()
            return {'team': team_cn, 'url': url, 'players': players, 'count': len(players)}

    except Exception as e:
        return {'team': team_cn, 'url': url, 'players': [], 'count': 0, 'error': str(e)}


async def main():
    results_file = '1_数据基础/wiki_zh_squad_results.json'
    cache = {}
    if os.path.exists(results_file):
        cache = json.load(open(results_file))
        print(f'已有缓存: {len(cache)} 队')

    for i, (team_cn, slug) in enumerate(ZH_TEAMS.items()):
        if team_cn in cache and cache[team_cn].get('count', 0) > 0:
            print(f'  [{i+1}/{len(ZH_TEAMS)}] {team_cn}: 已缓存 {cache[team_cn]["count"]} 人')
            continue

        print(f'  [{i+1}/{len(ZH_TEAMS)}] {team_cn}: 抓取中', end='', flush=True)
        r = await fetch_zh_squad(team_cn, slug)
        cache[team_cn] = r
        cnt = r.get('count', 0)
        err = r.get('error', '')
        print(f' → {cnt} 人' + (' [错误: ' + err + ']' if err else ''))

        if (i + 1) % 5 == 0:
            with open(results_file, 'w') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        await asyncio.sleep(1)

    with open(results_file, 'w') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    total = sum(r.get('count', 0) for r in cache.values())
    print(f'\n=== 完成 ===')
    print(f'抓取队数: {len(cache)}/{len(ZH_TEAMS)}')
    print(f'总球员: {total}')
    for team, data in cache.items():
        print(f'  {team}: {data.get("count", 0)} 人')

if __name__ == '__main__':
    asyncio.run(main())
