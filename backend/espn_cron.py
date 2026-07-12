"""
ESPN 定时抓取脚本 (mavis cron 调用)
- 拉 N 天前至今的 ESPN scoreboard 找已完赛
- 新场次拉 summary 存 espn_match_data/{id}.json
- 跑 ETL 写入 3 张 CSV
- 输出: 新增场次 / 总场次 / 抓取成功率 / 失败列表

用法: python3 espn_cron.py
"""
import json
import time
import urllib.request
import csv
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

PROJECT = Path('/Users/garcia/Desktop/WorldCup2026')
BACKEND = PROJECT / 'backend'
DATA = PROJECT / '1_数据基础'
RAW = DATA / 'espn_match_data'
RAW.mkdir(exist_ok=True)

# 中英文球队名映射
EN2CN = {
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

ESPN_BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world'


def fetch_scoreboard(d: date):
    """按日期拉 scoreboard"""
    ds = d.strftime('%Y%m%d')
    url = f'{ESPN_BASE}/scoreboard?dates={ds}'
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.load(r).get('events', [])
    except Exception as ex:
        print(f'  ❌ scoreboard {ds} 失败: {ex}', file=sys.stderr)
        return []


def fetch_summary(event_id: str):
    """拉单场 summary, 存到 espn_match_data/{id}.json

    v3.0.1 修 (2026-07-07): 兜底重抓
    - 旧逻辑: 已缓存就跳过 → 7/5 760502/503 抓的是 Scheduled 状态 (比赛还没踢), 永远卡死
    - 新逻辑: 如果缓存文件 status='Scheduled' 但比赛日期已过 (≥2 天), 自动重抓
    """
    out = RAW / f'{event_id}.json'
    need_refetch = False
    if out.exists():
        try:
            with open(out, encoding='utf-8') as f:
                cached = json.load(f)
            status_state = cached.get('header', {}).get('competitions', [{}])[0].get('status', {}).get('type', {}).get('state', '')
            status_desc = cached.get('header', {}).get('competitions', [{}])[0].get('status', {}).get('type', {}).get('description', '')
            # v3.0.1: 兜底 — Scheduled 状态缓存, 但比赛日期已过 (≥2 天), 强制重抓
            if status_state == 'pre' and status_desc == 'Scheduled':
                # 看 scoreboard 哪天发现这场比赛 (data 里的日期可能没, 用文件 mtime 兜底)
                import datetime as _dt
                mtime = _dt.datetime.fromtimestamp(out.stat().st_mtime)
                age_days = (_dt.datetime.now() - mtime).days
                if age_days >= 2:
                    need_refetch = True
                    print(f'  🔄 {event_id} 缓存是 Scheduled 状态 (mtime {age_days} 天前), 强制重抓')
        except Exception:
            pass
        if not need_refetch:
            return None  # 已缓存
    url = f'{ESPN_BASE}/summary?event={event_id}'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.load(r)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        return 'ok'
    except Exception as ex:
        print(f'  ❌ summary {event_id} 失败: {ex}', file=sys.stderr)
        return 'fail'


def main():
    """主流程: 拉近 7 天 scoreboard + 抓新完赛 summary + 跑 ETL"""
    print(f'=== ESPN 定时抓取 - {date.today().isoformat()} ===\n')

    # 1) 拉近 7 天 scoreboard (覆盖完赛延迟 + 24h buffer)
    finished = []  # [(event_id, date, home_en, away_en, home_score, away_score)]
    for offset in range(7):
        d = date.today() - timedelta(days=offset)
        events = fetch_scoreboard(d)
        for e in events:
            comps = e.get('competitions', [{}])[0].get('competitors', [])
            if len(comps) < 2:
                continue
            # v2.3.7 修: status 过滤必须包含加时/点球大战 (Final Score - After Extra Time / After Penalties)
            # 之前只过滤 "Full Time" 会漏掉加时赛和点球大战的比赛 (760499 澳大利亚 1-1 埃及 / 760500 阿根廷 3-2 佛得角)
            status_obj = e.get('status', {}).get('type', {})
            status_desc = status_obj.get('description', '')
            status_state = status_obj.get('state', '')
            status_completed = status_obj.get('completed', False)
            # state='post' + completed=True 是统一的"比赛已踢完"标记, 覆盖 Full Time / AET / PK
            if not (status_state == 'post' and status_completed):
                continue
            h_en = comps[0].get('team', {}).get('displayName', '')
            a_en = comps[1].get('team', {}).get('displayName', '')
            h_score = comps[0].get('score', 0)
            a_score = comps[1].get('score', 0)
            finished.append((e['id'], d.isoformat(), h_en, a_en, h_score, a_score))

    print(f'近 7 天已完赛: {len(finished)} 场')

    # 2) 抓新 summary (idempotent: 已缓存跳过)
    new_count, fail_count, skip_count = 0, 0, 0
    failed_ids = []
    for eid, d, h, a, hs, as_ in finished:
        out = RAW / f'{eid}.json'
        if out.exists():
            skip_count += 1
            continue
        r = fetch_summary(eid)
        if r == 'ok':
            new_count += 1
            print(f'  ✅ {eid} {h} vs {a} ({hs}-{as_})')
            time.sleep(0.3)
        elif r == 'fail':
            fail_count += 1
            failed_ids.append(eid)
        time.sleep(0.1)

    print(f'\n抓取: 新增 {new_count} 场, 跳过(已缓存) {skip_count} 场, 失败 {fail_count} 场')
    if failed_ids:
        print(f'失败 IDs: {failed_ids}')

    # 3) 跑 ETL
    print(f'\n=== 跑 ETL (etl_espn.py) ===')
    result = subprocess.run(
        [sys.executable, str(BACKEND / 'etl_espn.py')],
        capture_output=True, text=True, cwd=str(BACKEND)
    )
    etl_output = result.stdout + result.stderr
    print(etl_output[-800:])  # 末尾几行

    # 4) 读最终统计
    team_csv = DATA / 'match_team_stats.csv'
    player_csv = DATA / 'match_player_stats.csv'
    event_csv = DATA / 'match_events.csv'

    def count_rows(p):
        if not p.exists(): return 0
        with open(p) as f:
            return sum(1 for _ in f) - 1  # -1 表头

    n_team = count_rows(team_csv)
    n_player = count_rows(player_csv)
    n_event = count_rows(event_csv)

    # v3.0.1 加 (2026-07-07): 历史持久化 (cron_history.jsonl)
    # 旧版 espn_cron_report.json 是覆盖式, 没法看趋势
    # 新版: 每次跑追加一行 (json lines), 供 trend_chart.py 生成趋势图
    history_path = DATA / 'cron_history.jsonl'
    history_record = {
        'date': date.today().isoformat(),
        'new_matches': new_count,
        'skipped_matches': skip_count,
        'failed_matches': fail_count,
        'team_rows': n_team,
        'player_rows': n_player,
        'event_rows': n_event,
    }
    with open(history_path, 'a', encoding='utf-8') as hf:
        hf.write(json.dumps(history_record, ensure_ascii=False) + '\n')
    print(f'  📈 历史已追加: {history_path}')

    # 5) 输出报告 (cron 会用这个给用户)
    print(f'\n=== 报告 ===')
    print(f'今日新增 ESPN 场次: {new_count}')
    print(f'抓取失败: {fail_count} 场 ({", ".join(failed_ids) if failed_ids else "无"})')
    print(f'数据库统计:')
    print(f'  match_team_stats.csv:   {n_team} 行')
    print(f'  match_player_stats.csv: {n_player} 行')
    print(f'  match_events.csv:       {n_event} 行')

    # 6) 单独写一个 report JSON 给 cron
    report = {
        'date': date.today().isoformat(),
        'new_matches': new_count,
        'skipped_matches': skip_count,
        'failed_matches': fail_count,
        'failed_ids': failed_ids,
        'db_stats': {
            'match_team_stats': n_team,
            'match_player_stats': n_player,
            'match_events': n_event,
        },
        'etl_ok': result.returncode == 0,
    }
    with open(DATA / 'espn_cron_report.json', 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # v3.0.1 加 (2026-07-07): cron 跑完自动生成趋势图
    # 0_scripts/trend_chart.py 读 cron_history.jsonl 输出 HTML
    # 明天的 cron 报告就会自动附带最新趋势
    try:
        trend_script = PROJECT / '0_scripts' / 'trend_chart.py'
        if trend_script.exists():
            subprocess.run(
                [sys.executable, str(trend_script)],
                capture_output=True, text=True, cwd=str(PROJECT),
                timeout=15,
            )
            print(f'  📈 趋势图已自动生成: 4_可视化/cron_trend_chart.html')
    except Exception as ex:
        print(f'  ⚠️  趋势图生成失败: {ex}', file=sys.stderr)

    sys.exit(0 if result.returncode == 0 and fail_count == 0 else 1)


if __name__ == '__main__':
    main()
