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


# 2026 世界杯 48 强英文→中文映射 (完整版)
TEAM_ALIASES = {
    # Group A
    'Mexico': '墨西哥', 'South Africa': '南非',
    'South Korea': '韩国', 'Korea Republic': '韩国',
    'Czechia': '捷克', 'Czech Republic': '捷克',
    # Group B
    'Canada': '加拿大', 'Bosnia-Herzegovina': '波黑', 'Bosnia': '波黑',
    'Qatar': '卡塔尔', 'Switzerland': '瑞士',
    # Group C
    'Brazil': '巴西', 'Morocco': '摩洛哥',
    'Haiti': '海地', 'Scotland': '苏格兰',
    # Group D
    'United States': '美国', 'USA': '美国', 'Paraguay': '巴拉圭',
    'Australia': '澳大利亚', 'Turkey': '土耳其', 'Türkiye': '土耳其',
    # Group E
    'Germany': '德国',
    'Curacao': '库拉索', 'Curaçao': '库拉索', 'Curaçao': '库拉索',
    'Ivory Coast': '科特迪瓦', "Côte d'Ivoire": '科特迪瓦', "Cote d'Ivoire": '科特迪瓦',
    'Ecuador': '厄瓜多尔',
    # Group F
    'Netherlands': '荷兰', 'Japan': '日本',
    'Sweden': '瑞典', 'Tunisia': '突尼斯',
    # Group G
    'Iran': '伊朗', 'New Zealand': '新西兰',
    'Belgium': '比利时', 'Egypt': '埃及',
    # Group H
    'Spain': '西班牙', 'Cape Verde': '佛得角',
    'Saudi Arabia': '沙特', 'Uruguay': '乌拉圭',
    # Group I
    'France': '法国', 'Senegal': '塞内加尔',
    'Norway': '挪威', 'Iraq': '伊拉克',
    # Group J
    'Argentina': '阿根廷', 'Algeria': '阿尔及利亚',
    'Austria': '奥地利', 'Jordan': '约旦',
    # Group K
    'Portugal': '葡萄牙', 'Colombia': '哥伦比亚',
    'Uzbekistan': '乌兹别克斯坦',
    'DR Congo': '民主刚果', 'Congo DR': '民主刚果', 'Democratic Republic of the Congo': '民主刚果',
    # Group L
    'England': '英格兰', 'Croatia': '克罗地亚',
    'Ghana': '加纳', 'Panama': '巴拿马',
}


def to_zh(team_en):
    return TEAM_ALIASES.get(team_en, team_en)


def fetch_espn_scoreboard(date_str):
    """抓 ESPN 某日 scoreboard, 返回 FIFA 已完赛比赛

    ⚠️ ESPN 按**美东 (ET) 日期**归类, 不是用户本地时区!
    美东 6/11 晚 8:00 = 北京 6/12 上午 8:00, 归在 6/11.
    用户说"昨天 2 场", 可能漏了"前天美东 0:00-23:59"那批.

    date_str: '2026-06-12' (美东日期)
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
        # Always include match, even if team not in mapping (warn about unmapped)
        if h_team_en not in TEAM_ALIASES:
            print(f"  [warn] unmapped home team: {h_team_en}")
        if a_team_en not in TEAM_ALIASES:
            print(f"  [warn] unmapped away team: {a_team_en}")
        games.append((h_team, a_team, int(h_score), int(a_score), ""))

    # Filter to only World Cup teams (ignore club/youth matches)
    wc_teams = set()
    try:
        schedule_path = DATA_DIR / 'world_cup_2026_group_schedule.csv'
        if schedule_path.exists():
            with open(schedule_path, encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    wc_teams.add(row['主队'])
                    wc_teams.add(row['客队'])
    except Exception:
        pass  # If schedule not available, don't filter
    
    wc_games = []
    if wc_teams:
        wc_games = [g for g in games if g[0] in wc_teams and g[1] in wc_teams]
    else:
        wc_games = games
    
    return wc_games


def collect_results(start_date='2026-06-11', end_date='2026-07-19', overwrite=False):
    """收集世界杯期间全部比赛结果, 写入 match_results.csv

    overwrite=False (默认) 时, 保留已有数据, 只追加新比赛
    overwrite=True 时, 备份后重新全量抓取
    """
    if overwrite and CSV_RESULTS.exists():
        import shutil
        backup = CSV_RESULTS.with_suffix('.csv.bak')
        shutil.copy(CSV_RESULTS, backup)
        print(f"  [info] 备份到 {backup.name}, 重新写入")

    # 加载已有结果 (始终加载, 不对已有做覆盖)
    existing = {}
    if CSV_RESULTS.exists():
        with open(CSV_RESULTS, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                key = (row['date'], row['home'], row['away'])
                existing[key] = row

    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    # v2.2.3 修: 硬编码 today=6/13 永远抓不到 6/14+ 的数据
    # today 改成动态 = 当前美东时间 (但不用时区, 简化起见用 UTC+0 略偏, 反正 cron 12:00 跑会自然覆盖)
    today = datetime.now() + timedelta(days=1)  # +1 防边界 (美东比 UTC-5, 偏早一点没坏处)

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
    # v2.2.4 修: 兼容 stage/note 字段 (manual_ko_update 标 R16/QF 晋级用)
    fieldnames = ['date', 'home', 'away', 'home_score', 'away_score', 'key_events', 'source', 'collected_at', 'stage', 'note']
    with open(CSV_RESULTS, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
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
