"""
Wikipedia Squad DOB 批量爬虫 v4
策略：从每个国家队 Wikipedia 页面直接提取球员名单和生日
不再依赖 manual_name_map.json（那里的英文名大量错误）
"""
import asyncio, json, csv, re, os, sys
from datetime import date, datetime

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    try:
        d = datetime.strptime(dob_str[:10], '%Y-%m-%d').date()
        return TODAY.year - d.year - ((TODAY.month, TODAY.day) < (d.month, d.day))
    except:
        return None

# 2026世界杯真实48强 Wikipedia 页面映射（62->48，清除非参赛队）
TEAM_PAGES = {
    # 欧洲 16队
    '英格兰': 'England_national_football_team',
    '法国': 'France_national_football_team',
    '德国': 'Germany_national_football_team',
    '西班牙': 'Spain_national_football_team',
    '葡萄牙': 'Portugal_national_football_team',
    '荷兰': 'Netherlands_national_football_team',
    '比利时': 'Belgium_national_football_team',
    '克罗地亚': 'Croatia_national_football_team',
    '瑞士': 'Switzerland_national_football_team',
    '奥地利': 'Austria_national_football_team',
    '苏格兰': 'Scotland_national_football_team',
    '挪威': 'Norway_national_football_team',
    '土耳其': 'Turkey_national_football_team',
    '瑞典': 'Sweden_men%27s_national_football_team',
    '捷克': 'Czech_Republic_national_football_team',
    '波黑': 'Bosnia_and_Herzegovina_national_football_team',
    # 亚洲 9队
    '日本': 'Japan_national_football_team',
    '伊朗': 'Iran_national_football_team',
    '韩国': 'South_Korea_national_football_team',
    '澳大利亚': 'Australia_men%27s_national_soccer_team',
    '沙特': 'Saudi_Arabia_national_football_team',
    '卡塔尔': 'Qatar_national_football_team',
    '乌兹别克斯坦': 'Uzbekistan_national_football_team',
    '约旦': 'Jordan_national_football_team',
    '伊拉克': 'Iraq_national_football_team',
    # 非洲 10队
    '摩洛哥': 'Morocco_national_football_team',
    '塞内加尔': 'Senegal_national_football_team',
    '埃及': 'Egypt_national_football_team',
    '科特迪瓦': 'Ivory_Coast_national_football_team',
    '加纳': 'Ghana_national_football_team',
    '突尼斯': 'Tunisia_national_football_team',
    '阿尔及利亚': 'Algeria_national_football_team',
    '南非': 'South_Africa_national_soccer_team',
    '佛得角': 'Cape_Verde_national_football_team',
    '民主刚果': 'DR_Congo_national_football_team',
    # 南美 6队
    '阿根廷': 'Argentina_national_football_team',
    '巴西': 'Brazil_national_football_team',
    '乌拉圭': 'Uruguay_national_football_team',
    '哥伦比亚': 'Colombia_national_football_team',
    '厄瓜多尔': 'Ecuador_national_football_team',
    '巴拉圭': 'Paraguay_national_football_team',
    # 中北美+加勒比 6队（含3东道主）
    '美国': 'United_States_men%27s_national_soccer_team',
    '加拿大': 'Canada_men%27s_national_soccer_team',
    '墨西哥': 'Mexico_national_football_team',
    '巴拿马': 'Panama_national_football_team',
    '海地': 'Haiti_national_football_team',
    '库拉索': 'Cura%C3%A7ao_national_football_team',
    # 大洋洲 1队
    '新西兰': 'New_Zealand_men%27s_national_football_team',
}

def pinyin_to_approx(name):
    """把中文名转近似拼音，用于匹配"""
    import unicodedata
    # 移除 Unicode 变音符号
    s = unicodedata.normalize('NFD', name)
    # 常见姓氏拼音映射
    mapping = {
        '孙': 'Son', '李': 'Li', '王': 'Wang', '张': 'Zhang', '刘': 'Liu',
        '陈': 'Chen', '杨': 'Yang', '赵': 'Zhao', '黄': 'Huang', '周': 'Zhou',
        '吴': 'Wu', '徐': 'Xu', '孙': 'Sun', '胡': 'Hu', '朱': 'Zhu',
        '郭': 'Guo', '何': 'He', '高': 'Gao', '林': 'Lin', '罗': 'Luo',
        '郑': 'Zheng', '梁': 'Liang', '谢': 'Xie', '宋': 'Song', '唐': 'Tang',
        '韩': 'Han', '曹': 'Cao', '许': 'Xu', '邓': 'Deng', '萧': 'Xiao',
        '冯': 'Feng', '曾': 'Zeng', '程': 'Cheng', '蔡': 'Cai', '彭': 'Peng',
        '潘': 'Pan', '袁': 'Yuan', '于': 'Yu', '董': 'Dong', '余': 'Yu',
        '苏': 'Su', '叶': 'Ye', '吕': 'Lu', '魏': 'Wei', '蒋': 'Jiang',
        '田': 'Tian', '杜': 'Du', '丁': 'Ding', '沈': 'Shen', '姜': 'Jiang',
        '范': 'Fan', '江': 'Jiang', '傅': 'Fu', '孔': 'Kong', '谭': 'Tan',
        '廖': 'Liao', '庚': 'Geng', '史': 'Shi', '龙': 'Long', '万': 'Wan',
        '段': 'Duan', '漕': 'Cao', '钱': 'Qian', '汤': 'Tang', '尹': 'Yin',
        '黎': 'Li', '易': 'Yi', '常': 'Chang', '武': 'Wu', '乔': 'Qiao',
        '贺': 'He', '赖': 'Lai', '龚': 'Gong', '文': 'Wen', '庞': 'Pang',
    }
    result = []
    for ch in name:
        if ch in mapping:
            result.append(mapping[ch])
        elif '\u4e00' <= ch <= '\u9fff':
            result.append(ch)  # 保留生僻字
        else:
            result.append(ch)
    return ' '.join(result)


async def fetch_squad_page(team_cn, wiki_slug):
    """用 Playwright 抓取国家队 Wikipedia 页面，提取球员名单"""
    from playwright.async_api import async_playwright

    url = f'https://en.wikipedia.org/wiki/{wiki_slug}'
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

            tables = await page.query_selector_all('table')
            
            # 找包含 'No.' 和 'Pos' 和 'Caps' 的球员名单表格
            squad_table = None
            for t in tables:
                txt = await t.inner_text()
                if 'No.' in txt and 'Pos' in txt and 'Caps' in txt:
                    squad_table = t
                    break

            if not squad_table:
                await browser.close()
                return {'team': team_cn, 'url': url, 'players': [], 'count': 0, 'error': 'no squad table'}

            rows = await squad_table.query_selector_all('tr')
            print(f' (表格{len(rows)}行)', end='')

            # Wikipedia 球员名单格式：
            # | No. | Pos | Player | Date of birth (age) | Caps | Goals | Club |
            # 球员名在 <th> 或第一个 <td>，DOB 在第4个单元格
            for row in rows[1:]:  # 跳过表头行
                cells = await row.query_selector_all('th, td')
                if len(cells) < 4:
                    continue

                # 取球员名（找第一个有 /wiki/ 链接且链接文本非位置的）
                # 位置关键词：GK/DF/MF/FW 以及对应全称
                pos_keywords = {'GK','DF','MF','FW','Goalkeeper','Defender','Midfielder','Forward',
                               'goalkeeper','defender','midfielder','forward'}
                name = ''
                for ci, cell in enumerate(cells):
                    # 在此单元格找 wiki 链接
                    link = await cell.query_selector('a[href^="/wiki/"]')
                    if not link:
                        continue
                    link_text = (await link.inner_text()).strip()
                    # 跳过链接文本为位置的（如 "GK" 或 "Forward"）
                    if link_text in pos_keywords:
                        continue
                    # 排除其他非球员链接
                    skip_kw = {'Coach', 'Manager', 'Federation', 'Association',
                               'Captain', 'Statistics', 'Record', 'List'}
                    if any(kw in link_text for kw in skip_kw):
                        continue
                    if len(link_text) > 1:
                        name = link_text
                        break

                if not name or len(name) < 2:
                    continue

                # 取 DOB（第4个单元格）
                dob_text = await cells[3].inner_text() if len(cells) > 3 else ''
                
                # 格式: "6 February 1989 (age 37)" 或 "June 24, 1994 (age 31)"
                # 同时支持 "24 June 1998" 和 "June 24, 1994"
                m = re.search(r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})', dob_text)
                if not m:
                    continue
                
                dob_str = m.group(1)
                # 支持两种格式：
                # "9 June 1998" → "1998-06-09"
                # "June 24, 1994" → "1994-06-24"
                month_map = {'January':'01','February':'02','March':'03','April':'04',
                             'May':'05','June':'06','July':'07','August':'08',
                             'September':'09','October':'10','November':'11','December':'12',
                             'Jan':'01','Feb':'02','Mar':'03','Apr':'04',
                             'Jun':'06','Jul':'07','Aug':'08',
                             'Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
                try:
                    dob_str_clean = re.sub(r'[,]+', '', dob_str.strip())
                    parts = dob_str_clean.split()
                    # 判断是哪种格式
                    if parts[0].isdigit():  # "9 June 1998"
                        day = parts[0].zfill(2)
                        month = month_map.get(parts[1], '01')
                        year = parts[2]
                    else:  # "June 24 1994" 或 "June 24, 1994"
                        month = month_map.get(parts[0], '01')
                        day = parts[1].zfill(2)
                        year = parts[2]
                    dob_iso = f'{year}-{month}-{day}'
                except:
                    continue

                # 取位置
                pos_text = await cells[1].inner_text() if len(cells) > 1 else ''
                pos = pos_text.strip()

                # 取俱乐部（最后一个单元格）
                club_text = await cells[-1].inner_text() if cells else ''
                club = club_text.strip()

                age = calc_age(dob_iso)
                if age and 15 <= age <= 50:
                    players.append({
                        'en': name,
                        'dob': dob_iso,
                        'age': age,
                        'pos': pos,
                        'club': club
                    })

            await browser.close()
            return {'team': team_cn, 'url': url, 'players': players, 'count': len(players)}

    except Exception as e:
        return {'team': team_cn, 'url': url, 'players': [], 'count': 0, 'error': str(e)}


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        # 检查模式：只看有多少队能抓到
        print('检查 Wikipedia 页面可访问性...')
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            ok_teams = []
            bad_teams = []
            for team_cn, slug in TEAM_PAGES.items():
                url = f'https://en.wikipedia.org/wiki/{slug}'
                try:
                    r = await page.goto(url, timeout=10000)
                    if r and r.status == 200:
                        title = await page.title()
                        ok_teams.append((team_cn, slug, title[:40]))
                    else:
                        bad_teams.append((team_cn, slug, r.status if r else 'no_response'))
                except Exception as e:
                    bad_teams.append((team_cn, slug, str(e)[:30]))
                await page.wait_for_timeout(500)

            await browser.close()
            print(f'\n✅ 可访问: {len(ok_teams)}/48')
            for t, s, title in ok_teams:
                print(f'  {t}: {title}')
            print(f'\n❌ 失败: {len(bad_teams)}/48')
            for t, s, err in bad_teams:
                print(f'  {t}: {err}')
            return

    print(f'抓取 48 队 Wikipedia 页面...')
    results_file = '1_数据基础/wiki_squad_v4_results.json'
    cache = {}
    if os.path.exists(results_file):
        cache = json.load(open(results_file))
        print(f'已有缓存: {len(cache)} 队')

    # 逐队抓取（避免并发过多）
    for i, (team_cn, slug) in enumerate(TEAM_PAGES.items()):
        if team_cn in cache and cache[team_cn].get('count', 0) > 0:
            cached_cnt = cache[team_cn]['count']
            print(f'  [{i+1}/48] {team_cn}: 已缓存 {cached_cnt} 人')
            continue

        print(f'  [{i+1}/48] {team_cn}: 抓取中...', end='', flush=True)
        r = await fetch_squad_page(team_cn, slug)
        cache[team_cn] = r
        cnt = r.get('count', 0)
        err = r.get('error', '')
        print(' → ' + str(cnt) + ' 人' + (' [错误: ' + err + ']' if err else ''))

        # 每5队保存一次
        if (i + 1) % 5 == 0:
            with open(results_file, 'w') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

        await asyncio.sleep(1.5)

    with open(results_file, 'w') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    total_players = sum(r.get('count', 0) for r in cache.values())
    print(f'\n=== 完成 ===')
    print(f'抓取队数: {len(cache)}/48')
    print(f'总球员: {total_players}')
    for team, data in cache.items():
        print(f'  {team}: {data.get("count", 0)} 人')

if __name__ == '__main__':
    asyncio.run(main())
