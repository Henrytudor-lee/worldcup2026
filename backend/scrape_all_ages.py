"""
Playwright 批量爬 Wikipedia 球员 DOB
用法: python3 backend/scrape_all_ages.py
"""
import asyncio, json, csv, re, time, os
from datetime import date

TODAY = date(2026, 6, 15)

def calc_age(dob_str):
    from datetime import datetime
    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
    return TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))

RESULTS_FILE = '1_数据基础/wiki_scrape_results.json'


async def scrape_one(query, name_cn, team):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            extra_http_headers={'Accept-Language': 'en-US,en;q=0.9'},
        )
        page = await context.new_page()
        search_url = f"https://en.wikipedia.org/w/index.php?search={query.replace(' ', '+')}&title=Special%3ASearch&go=Go"
        try:
            await page.goto(search_url, timeout=15000, wait_until='domcontentloaded')
            await page.wait_for_timeout(1500)

            # Click first search result
            try:
                first_link = page.locator('.mw-search-result-heading a').first
                if await first_link.is_visible(timeout=3000):
                    href = await first_link.get_attribute('href')
                    await page.goto(f"https://en.wikipedia.org{href}", timeout=15000, wait_until='domcontentloaded')
                    await page.wait_for_timeout(1200)
            except:
                pass

            # Extract DOB via JS
            dob = await page.evaluate('''() => {
                const bday = document.querySelector('.bday');
                if (bday) return bday.textContent.trim();
                const time = document.querySelector('time[itemprop="birthDate"]');
                if (time) return time.getAttribute('datetime');
                // Infobox Born row
                const rows = document.querySelectorAll('.infobox tr');
                for (const row of rows) {
                    const th = row.querySelector('th');
                    if (th && /Born/i.test(th.textContent)) {
                        const td = row.querySelector('td');
                        if (!td) continue;
                        const time = td.querySelector('time');
                        if (time) return time.getAttribute('datetime');
                    }
                }
                return null;
            }''')

            title = await page.title()
            return {
                'query': query,
                'name_cn': name_cn,
                'team': team,
                'title': title,
                'dob': dob if dob else None,
                'url': page.url,
            }
        except Exception as e:
            return {
                'query': query,
                'name_cn': name_cn,
                'team': team,
                'title': '',
                'dob': None,
                'url': '',
                'error': str(e),
            }
        finally:
            await browser.close()


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
    try:
        with open(RESULTS_FILE) as f:
            scraped = json.load(f)
    except:
        scraped = {}

    def build_query(name_cn, team, club, position):
        name = name_cn.replace('·', ' ')
        return f"{name} footballer {team}"

    # Filter unfixed that haven't been scraped
    pending = [
        u for u in unfixed
        if f"{u['team']}|{u['name_cn']}" not in scraped
    ]
    print(f'待爬 (未处理): {len(pending)} 个')

    # Scrape all pending, 5 at a time
    batch_size = 5
    found_count = 0
    for i in range(0, len(pending), batch_size):
        batch = pending[i:i+batch_size]
        queries = [build_query(u['name_cn'], u['team'], u['club'], u['position']) for u in batch]
        print(f'\n=== 批次 {i//batch_size+1}: 爬 {len(batch)} 个 ===')

        tasks = [scrape_one(q, u['name_cn'], u['team']) for q, u in zip(queries, batch)]
        batch_results = await asyncio.gather(*tasks)

        for u, result in zip(batch, batch_results):
            key = f"{u['team']}|{u['name_cn']}"
            scraped[key] = result
            if result.get('dob'):
                age = calc_age(result['dob'])
                if 16 <= age <= 45:
                    print(f"  ✅ {u['team']:<6} {u['name_cn']:<20} → {result['dob']} (age={age})")
                    found_count += 1
                else:
                    print(f"  ⚠️  {u['team']:<6} {u['name_cn']:<20} → {result['dob']} (age={age} 离谱!)")
            else:
                print(f"  ❌ {u['team']:<6} {u['name_cn']:<20} [{result.get('title','')}]")
            await asyncio.sleep(1.2)

        # Save progress every batch
        with open(RESULTS_FILE, 'w') as f:
            json.dump(scraped, f, ensure_ascii=False, indent=2)
        print(f'  保存进度 ({len(scraped)} 条)')

    print(f'\n✅ 全部完成! 共 {found_count} 个找到 DOB')
    print(f'结果: {RESULTS_FILE}')


if __name__ == '__main__':
    asyncio.run(main())
