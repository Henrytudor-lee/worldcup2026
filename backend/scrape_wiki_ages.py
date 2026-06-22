"""
Playwright 爬 Wikipedia 球员出生日期
"""
import json, csv, time, re, asyncio
from datetime import date

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))


def build_search_query(name_cn, team, club, position):
    """Build Wikipedia search query"""
    # Remove middle dot
    name = name_cn.replace('·', ' ')
    # Common patterns: "Name footballer" or "Name (footballer)"
    return f"{name} footballer {team}"


async def scrape_wiki(query):
    """Scrape Wikipedia for a player's birth date"""
    from playwright.async_api import async_playwright

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
        )
        page = await context.new_page()

        # Search Wikipedia
        search_url = f"https://en.wikipedia.org/w/index.php?search={query.replace(' ', '+')}&title=Special%3ASearch&go=Go"
        try:
            await page.goto(search_url, timeout=15000, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # Get page title
            title = await page.title()

            # Check if it's a search results page or direct article
            current_url = page.url
            if 'Special:Search' in current_url:
                # Click first result
                try:
                    first_link = page.locator('.mw-search-result-heading a').first
                    if await first_link.is_visible(timeout=3000):
                        href = await first_link.get_attribute('href')
                        await page.goto(f"https://en.wikipedia.org{href}", timeout=15000, wait_until='domcontentloaded')
                        await page.wait_for_timeout(1500)
                except:
                    pass

            # Extract birth date from page
            article_title = await page.title()

            # Try multiple selectors for birth date
            dob = None

            # Method 1: infobox birthplace section
            try:
                infobox = page.locator('.infobox').first
                if await infobox.is_visible(timeout=2000):
                    infobox_text = await infobox.inner_text()
                    # Look for patterns like "Born (1998-06-04) June 4, 1998"
                    m = re.search(r'Born.*?(\d{4})[–\-年](\d{1,2})[–\-月](\d{1,2})', infobox_text)
                    if m:
                        dob = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
            except:
                pass

            # Method 2: data in page
            if not dob:
                try:
                    page_text = await page.inner_text()
                    # Pattern: "Born (1998-06-04)" or "Born: June 4, 1998"
                    for pat in [
                        r'Born.*?\[(\d{4})[–\-年](\d{1,2})[–\-月](\d{1,2})',
                        r'Born.*?(\w+ \d{1,2}, \d{4})',
                    ]:
                        m = re.search(pat, page_text[:3000])
                        if m:
                            if len(m.groups()) == 3:
                                dob = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
                            break
                except:
                    pass

            # Method 3: span with date pattern
            if not dob:
                try:
                    born_span = page.locator('[data-date]').first
                    if await born_span.is_visible(timeout=1000):
                        dob = await born_span.get_attribute('data-date')
                except:
                    pass

            results.append({
                'query': query,
                'title': article_title,
                'dob': dob,
                'url': page.url,
            })

        except Exception as e:
            results.append({
                'query': query,
                'title': '',
                'dob': None,
                'url': '',
                'error': str(e),
            })

        await browser.close()

    return results


async def main():
    # Load unfixed players
    with open('1_数据基础/world_cup_2026_complete.csv', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    unfixed = []
    for i, r in enumerate(rows):
        a = r['年龄']
        if a == 'X待核实' or ('-' in a and a != 'X待核实') or (a.isdigit() and (int(a) < 16 or int(a) > 45)):
            unfixed.append({
                'row_idx': i,
                'team': r['国家'],
                'name_cn': r['球员'],
                'club': r['俱乐部'],
                'position': r['位置'],
                'current': a,
            })

    print(f'待爬: {len(unfixed)} 个')

    # Load existing results
    results_file = '1_数据基础/wiki_scrape_results.json'
    try:
        with open(results_file) as f:
            scraped = json.load(f)
    except:
        scraped = {}

    # Scrape in batches of 5
    batch_size = 5
    new_results = 0
    for batch_start in range(0, min(len(unfixed), 30), batch_size):
        batch = unfixed[batch_start:batch_start + batch_size]
        queries = [build_search_query(u['name_cn'], u['team'], u['club'], u['position']) for u in batch]

        print(f'\n=== 爬第 {batch_start+1}-{batch_start+len(batch)} 个 ===')
        tasks = [scrape_wiki(q) for q in queries]
        batch_results = await asyncio.gather(*tasks)

        for u, (result,) in zip(batch, batch_results):
            key = f"{u['team']}|{u['name_cn']}"
            scraped[key] = result
            if result.get('dob'):
                age = calc_age(result['dob'])
                print(f"  ✅ {u['team']:<6} {u['name_cn']:<20} → {result['dob']} (age={age}) [title={result.get('title','')}]")
                new_results += 1
            else:
                print(f"  ❌ {u['team']:<6} {u['name_cn']:<20} → 未找到 [title={result.get('title','')}]")
            await asyncio.sleep(1)

        # Save progress
        with open(results_file, 'w') as f:
            json.dump(scraped, f, ensure_ascii=False, indent=2)

        print(f'  本批次: {new_results} 个新结果, 保存进度')

    print(f'\n✅ 完成. 共 {new_results} 个新结果, 保存到 {results_file}')


if __name__ == '__main__':
    asyncio.run(main())
