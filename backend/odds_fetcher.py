"""
竞彩实时赔率抓取器
==================
优先从 Playwright 抓取的 lottery_odds_live.json 读取真实数据
备选：竞彩官方 API (sporttery.cn)
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ODDS_CACHE = PROJECT_ROOT / "1_数据基础" / "odds_cache.json"
LIVE_ODDS_FILE = PROJECT_ROOT / "1_数据基础" / "lottery_odds_live.json"
SCRAPER_SCRIPT = Path(__file__).resolve().parent / "scrape_lottery_odds.js"

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'


def _load_scraped_odds():
    """从 Playwright 抓取的 JSON 文件读取真实赔率"""
    if not LIVE_ODDS_FILE.exists():
        return None
    try:
        with open(LIVE_ODDS_FILE, encoding='utf-8') as f:
            data = json.load(f)
        scraped_at = data.get('scraped_at', '')
        if scraped_at:
            ct = datetime.fromisoformat(scraped_at)
            # 统一成 aware UTC
            if ct.tzinfo is None:
                ct = ct.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            # 超过3小时的抓取数据视为过期
            if abs((now - ct).total_seconds()) > 3 * 3600:
                print(f"  [warn] 抓取数据已过期 ({scraped_at}), 跳过")
                return None
        matches = data.get('matches', [])
        if not matches:
            return None
        odds_map = {}
        for m in matches:
            home = m.get('home', '')
            away = m.get('away', '')
            if not home or not away:
                continue
            key = f"{home}_vs_{away}"
            entry = {'_source': 'lottery_gov_cn'}
            # 只加入已开售的胜平负
            if m.get('had_available') and m.get('had'):
                entry['home'] = m['had']['home']
                entry['draw'] = m['had']['draw']
                entry['away'] = m['had']['away']
            # 让球胜平负
            if m.get('hhad'):
                entry['hhad_handicap'] = m.get('hhad_handicap', 0)
                entry['hhad_home'] = m['hhad']['home']
                entry['hhad_draw'] = m['hhad']['draw']
                entry['hhad_away'] = m['hhad']['away']
            odds_map[key] = entry
        odds_map['_fetched_at'] = scraped_at
        odds_map['_source'] = 'lottery_gov_cn'
        return odds_map
    except Exception as e:
        print(f"  [warn] 读取抓取数据失败: {e}")
        return None


def _team_en_to_cn(name):
    """英文队名 → 中文"""
    mapping = {
        'Mexico': '墨西哥', 'South Africa': '南非', 'Korea Republic': '韩国', 'Czech Republic': '捷克',
        'Canada': '加拿大', 'Bosnia and Herzegovina': '波黑', 'United States': '美国', 'Paraguay': '巴拉圭',
        'Qatar': '卡塔尔', 'Switzerland': '瑞士', 'Brazil': '巴西', 'Morocco': '摩洛哥',
        'Haiti': '海地', 'Scotland': '苏格兰', 'Australia': '澳大利亚', 'Turkey': '土耳其',
        'Germany': '德国', 'Curacao': '库拉索', 'Netherlands': '荷兰', 'Japan': '日本',
        'Cote d\'Ivoire': '科特迪瓦', 'Ecuador': '厄瓜多尔', 'Sweden': '瑞典', 'Tunisia': '突尼斯',
        'Spain': '西班牙', 'Cape Verde': '佛得角', 'Belgium': '比利时', 'Egypt': '埃及',
        'Saudi Arabia': '沙特', 'Uruguay': '乌拉圭', 'Iran': '伊朗', 'New Zealand': '新西兰',
        'France': '法国', 'Senegal': '塞内加尔', 'Iraq': '伊拉克', 'Norway': '挪威',
        'Argentina': '阿根廷', 'Algeria': '阿尔及利亚', 'Austria': '奥地利', 'Jordan': '约旦',
        'Portugal': '葡萄牙', 'Congo DR': '民主刚果', 'England': '英格兰', 'Croatia': '克罗地亚',
        'Ghana': '加纳', 'Panama': '巴拿马', 'Uzbekistan': '乌兹别克斯坦', 'Colombia': '哥伦比亚',
        'Italy': '意大利', 'Denmark': '丹麦', 'Poland': '波兰', 'Romania': '罗马尼亚',
        'Cameroon': '喀麦隆', 'Nigeria': '尼日利亚', 'Chile': '智利', 'Peru': '秘鲁',
        'Slovakia': '斯洛伐克', 'Slovenia': '斯洛文尼亚', 'Ukraine': '乌克兰',
        'Costa Rica': '哥斯达黎加', 'Bolivia': '玻利维亚', 'Kosovo': '科索沃',
        'Albania': '阿尔巴尼亚', 'Venezuela': '委内瑞拉',
    }
    return mapping.get(name, name)


def fetch_live_odds():
    """从竞彩官方 API 抓取赔率（已弃用，改为读取 lottery_odds_live.json）"""
    # 1. 优先读取 Playwright 抓取的实时数据
    scraped = _load_scraped_odds()
    if scraped:
        had_count = sum(1 for k, v in scraped.items() if not k.startswith('_') and v.get('home'))
        print(f"  ✅ 来自体彩网真实数据: {had_count} 场胜平负赔率")
        scraped['_fetched_at'] = datetime.now(timezone.utc).isoformat()
        return scraped

    # 2. 尝试 API（已弃用，保持向后兼容）
    url = "https://webapi.sporttery.cn/gateway/uniform/football/getUniformMatchResultV1.qry"
    params = {
        'matchPage': '1', 'matchBeginDate': '2026-06-11', 'matchEndDate': '2026-07-20',
        'leagueId': '', 'pageSize': '200', 'pageNo': '1', 'isFix': '0',
    }
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{query}", headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  [warn] Sporttery API failed: {e}, using static fallback")
        return _fallback_static_odds()

    if not data.get('success') or not data.get('value'):
        print("  [warn] API returned no data, using static fallback")
        return _fallback_static_odds()

    odds_map = {}
    for m in data['value'].get('matchResultList', data['value'].get('matchList', [])):
        home = _team_en_to_cn(m.get('homeTeam', ''))
        away = _team_en_to_cn(m.get('awayTeam', ''))
        if not home or not away:
            continue
        key = f"{home}_vs_{away}"
        spf = m.get('had', {}) or m.get('spfOdds', {}) or {}
        odds = {
            'home': float(spf.get('h', 0) or 0),
            'draw': float(spf.get('d', 0) or 0),
            'away': float(spf.get('a', 0) or 0),
        }
        if odds['home'] > 1:
            odds_map[key] = odds

    odds_map['_fetched_at'] = datetime.utcnow().isoformat()
    odds_map['_source'] = 'sporttery_api'
    print(f"  ✅ 来自竞彩API: {len(odds_map)-1} 场比赛")
    return odds_map


def _fallback_static_odds():
    """终极兜底：读取 lottery_odds_live.json（不检查时间）"""
    if LIVE_ODDS_FILE.exists():
        try:
            with open(LIVE_ODDS_FILE, encoding='utf-8') as f:
                data = json.load(f)
            matches = data.get('matches', [])
            odds_map = {}
            for m in matches:
                home, away = m.get('home', ''), m.get('away', '')
                if not home or not away:
                    continue
                key = f"{home}_vs_{away}"
                entry = {'_source': 'lottery_gov_cn'}
                if m.get('had_available') and m.get('had'):
                    entry['home'] = m['had']['home']
                    entry['draw'] = m['had']['draw']
                    entry['away'] = m['had']['away']
                if m.get('hhad'):
                    entry['hhad_handicap'] = m.get('hhad_handicap', 0)
                    entry['hhad_home'] = m['hhad']['home']
                    entry['hhad_draw'] = m['hhad']['draw']
                    entry['hhad_away'] = m['hhad']['away']
                odds_map[key] = entry
            if odds_map:
                print(f"  ⚠️ 使用过期抓取数据: {sum(1 for v in odds_map.values() if v.get('home'))} 场")
                odds_map['_fetched_at'] = datetime.utcnow().isoformat()
                odds_map['_source'] = 'lottery_gov_cn_expired'
                return odds_map
        except Exception as e:
            print(f"  [warn] 读取过期数据失败: {e}")
    print("  [ERROR] 无可用数据来源！")
    return {'_fetched_at': datetime.utcnow().isoformat(), '_source': 'none'}


def get_odds():
    """获取赔率"""
    if ODDS_CACHE.exists():
        try:
            with open(ODDS_CACHE, encoding='utf-8') as f:
                cached = json.load(f)
            if cached.get('_fetched_at'):
                ct = datetime.fromisoformat(cached['_fetched_at'])
                if ct.tzinfo is None:
                    ct = ct.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - ct).total_seconds() < 3600:
                    return cached
        except Exception:
            pass
    return fetch_live_odds()


if __name__ == '__main__':
    odds = fetch_live_odds()
    count = len(odds) - (1 if '_fetched_at' in odds else 0)
    print(f"\n获取到 {count} 场比赛赔率 (source: {odds.get('_source', 'unknown')})")
    for k, v in list(odds.items())[:5]:
        if not k.startswith('_'):
            print(f"  {k}: had={v.get('home')}/{v.get('draw')}/{v.get('away')}")
