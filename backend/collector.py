"""
Mavis PDP 数据收集器 (v2.2.1)

抓取真实比赛结果，写入 match_results.csv
数据源: ESPN scoreboard
设计: 幂等, 增量写入

ESPN HTML 结构 (验证于 2026-06-12):
  每场 = 2 个 <li class="ScoreboardScoreCell__Item ..."> 块
  每个块 = 1 个 <div class="ScoreCell__TeamName ..."> (队名)
         + 1 个 <div class="ScoreCell__Score ..."> (比分)
  顺序: home team + home score + away team + away score (每个 li 独立)

⚠️ 关键修复: 用 (?:(?!</li>).)*? 替代 .*?, 防止 1MB+ HTML 跨多块
  catastrophic backtracking
"""
import csv
import re
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "1_数据基础"
CSV_RESULTS = DATA_DIR / "match_results.csv"


# 48 强英文→中文映射 (48 队)
TEAM_ALIASES = {
    'Canada': '加拿大', 'Bosnia-Herzegovina': '波黑', 'Bosnia': '波黑',
    'United States': '美国', 'USA': '美国', 'Paraguay': '巴拉圭',
    'Qatar': '卡塔尔', 'Switzerland': '瑞士',
    'Brazil': '巴西', 'Morocco': '摩洛哥',
    'Haiti': '海地', 'Scotland': '苏格兰',
    'Mexico': '墨西哥', 'South Africa': '南非',
    'South Korea': '韩国', 'Korea Republic': '韩国',
    'Germany': '德国', 'Curacao': '库拉索', 'Curaçao': '库拉索',
    'Netherlands': '荷兰', 'Japan': '日本',
    'Spain': '西班牙', 'Cape Verde': '佛得角',
    'Ivory Coast': '科特迪瓦', "Côte d'Ivoire": '科特迪瓦',
    'Iran': '伊朗', 'New Zealand': '新西兰',
    'Portugal': '葡萄牙', 'Norway': '挪威',
    'France': '法国', 'Senegal': '塞内加尔',
    'Argentina': '阿根廷', 'Algeria': '阿尔及利亚',
    'England': '英格兰', 'Croatia': '克罗地亚',
    'Tunisia': '突尼斯',
    'Belgium': '比利时', 'Egypt': '埃及',
    'Italy': '意大利', 'Uzbekistan': '乌兹别克斯坦',
    'Poland': '波兰',
    'Uruguay': '乌拉圭', 'Ghana': '加纳', 'Panama': '巴拿马',
    'Saudi Arabia': '沙特', 'Australia': '澳大利亚',
    'Colombia': '哥伦比亚', 'Ecuador': '厄瓜多尔',
    'Cameroon': '喀麦隆', 'Costa Rica': '哥斯达黎加',
    'Denmark': '丹麦', 'Turkey': '土耳其', 'Austria': '奥地利',
    'Jordan': '约旦', 'Albania': '阿尔巴尼亚',
    'Czechia': '捷克', 'Czech Republic': '捷克',
    'Sweden': '瑞典', 'Ukraine': '乌克兰', 'Kosovo': '科索沃',
    'Romania': '罗马尼亚', 'Slovakia': '斯洛伐克', 'Slovenia': '斯洛文尼亚',
    'Nigeria': '尼日利亚', 'Chile': '智利', 'Peru': '秘鲁', 'Bolivia': '玻利维亚',
}


def to_zh(team_en):
    return TEAM_ALIASES.get(team_en, team_en)


def fetch_espn_scoreboard(date_str):
    """抓 ESPN 某日 scoreboard, 返回 FIFA 已完赛比赛

    date_str: '2026-06-12'
    返回 [(home_zh, away_zh, home_score, away_score, key_events), ...]
    """
    yyyy, mm, dd = date_str.split('-')
    url = f"https://www.espn.com/soccer/scoreboard/_/date/{yyyy}{mm}{dd}"
    # ESPN 反爬: 简单 User-Agent 最稳, 复杂 Chrome 头会触发 SSL 断连
    user_agents = [
        'Mozilla/5.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    ]
    html = None
    last_err = None
    for ua in user_agents:
        req = urllib.request.Request(url, headers={'User-Agent': ua})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            break
        except Exception as e:
            last_err = e
            time.sleep(0.3)
    if html is None:
        print(f"  [warn] {date_str} ESPN fetch failed: {last_err}")
        return []

    # HTML 实体解码
    html = html.replace('&#x27;', "'")

    # 关键修复: 用 (?:(?!</li>).)*? 防止 catastrophic backtracking
    item_pattern = re.compile(
        r'class="ScoreboardScoreCell__Item[^"]*"'
        r'(?:(?!</li>).)*?'
        r'ScoreCell__TeamName[^"]*">([^<]+)<'
        r'(?:(?!</li>).)*?'
        r'ScoreCell__Score[^"]*">(\d+)<',
        re.DOTALL
    )
    items = item_pattern.findall(html)

    if len(items) < 2:
        return []

    # 配对: 2 item = 1 场
    games = []
    for i in range(0, len(items) - 1, 2):
        h_team_en, h_score = items[i]
        a_team_en, a_score = items[i + 1]
        h_team = to_zh(h_team_en)
        a_team = to_zh(a_team_en)
        if h_team_en in TEAM_ALIASES and a_team_en in TEAM_ALIASES:
            games.append((h_team, a_team, int(h_score), int(a_score), ''))

    return games


def collect_results(start_date='2026-06-11', end_date='2026-07-19', overwrite=True):
    """收集世界杯期间全部比赛结果, 写入 match_results.csv

    overwrite=True 时, 用 collector 数据完全覆盖手写种子数据
              (避免手动种子和抓取结果不一致)
    overwrite=False 时, 保留已有, 只追加新的
    """
    if overwrite and CSV_RESULTS.exists():
        # 备份后清空, 重新写入 (避免重复)
        import shutil
        backup = CSV_RESULTS.with_suffix('.csv.bak')
        shutil.copy(CSV_RESULTS, backup)
        print(f"  [info] 备份到 {backup.name}, 重新写入")

    # 加载已有结果
    existing = {}
    if not overwrite and CSV_RESULTS.exists():
        with open(CSV_RESULTS, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                key = (row['date'], row['home'], row['away'])
                existing[key] = row

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    today = datetime(2026, 6, 13)

    new_count = 0
    skip_count = 0
    cur = start
    while cur <= min(end, today):
        date_str = cur.strftime('%Y-%m-%d')
        games = fetch_espn_scoreboard(date_str)
        for h, a, hs, as_, events in games:
            key = (date_str, h, a)
            if not overwrite and key in existing:
                skip_count += 1
                continue
            row = {
                'date': date_str,
                'home': h,
                'away': a,
                'home_score': hs,
                'away_score': as_,
                'key_events': events,
                'source': f'espn_{date_str.replace("-", "")}',
                'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            existing[key] = row
            new_count += 1
            print(f"  [new] {date_str} {h} {hs}-{as_} {a}")
        cur += timedelta(days=1)
        time.sleep(0.3)

    # 写回 CSV (按日期 + 队名排序)
    fieldnames = ['date', 'home', 'away', 'home_score', 'away_score', 'key_events', 'source', 'collected_at']
    with open(CSV_RESULTS, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for key in sorted(existing.keys()):
            w.writerow(existing[key])

    print(f"\n=== 收集完成 ===")
    print(f"  新增: {new_count} 场")
    print(f"  跳过 (已存在): {skip_count} 场")
    print(f"  CSV: {CSV_RESULTS}")
    return new_count


if __name__ == '__main__':
    # 验证单天
    for date in ['2026-06-12', '2026-06-13']:
        print(f"\n=== {date} ===")
        games = fetch_espn_scoreboard(date)
        print(f"  FIFA 已完赛: {len(games)} 场")
        for g in games:
            print(f"    {g[0]} {g[2]}-{g[3]} {g[1]}")

    print("\n=== 全量收集 6/11-7/19 (覆盖模式) ===")
    collect_results('2026-06-11', '2026-07-19', overwrite=True)
