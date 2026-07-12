#!/usr/bin/env python3
"""WS batch v4 - add stats fields (passesKey, shotsOnTarget, tackles, dribbles, aerials)
and penalty goal counts to existing match_*.json files.

Preserves: ratings, goals, assists, yellow, red, etc.
Adds:
  - passesKey (key passes / 关键传球)
  - shotsOnTarget (射正)
  - tacklesTotal / tackleSuccessful (铲断)
  - dribblesAttempted (过人尝试)
  - aerialsWon (争顶成功)
  - penalty_goals (点球破门)
  - penalty_missed (点球未进)
"""
import json
import time
from playwright.sync_api import sync_playwright
from pathlib import Path
from collections import defaultdict

BASE_URL = "https://www.whoscored.com"
MATCHES_FILE = "/tmp/wc_matches.json"
OUTPUT_DIR = Path("/Users/garcia/Desktop/WorldCup2026/4_比赛预测/player_ratings")


def fetch_match_data(page, match_url: str) -> dict:
    url = f"{BASE_URL}{match_url}" if match_url.startswith("/") else match_url
    match_id = match_url.split('/matches/')[1].split('/')[0] if '/matches/' in match_url else '?'
    for attempt in range(3):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3500)
            raw = page.evaluate("""() => {
                try {
                    const args = require.config.params['args'];
                    if (!args || !args.matchCentreData) return null;
                    return JSON.stringify(args.matchCentreData);
                } catch(e) { return null; }
            }""")
            if raw:
                return json.loads(raw)
            print(f"  No data for {match_id}, retry {attempt+1}")
            time.sleep(3)
        except Exception as e:
            print(f"  Error {match_id} attempt {attempt+1}: {e}")
            time.sleep(8)
    return None


def collect_player_stats(data: dict) -> dict:
    """For each player_id, return {passesKey, shotsOnTarget, tacklesTotal, tackleSuccessful,
    dribblesAttempted, aerialsWon, penalty_goals, penalty_missed}."""
    result = {}
    events = data.get('events', [])
    for p in data.get('home', {}).get('players', []) + data.get('away', {}).get('players', []):
        pid = p.get('playerId')
        if not pid:
            continue
        stats = p.get('stats', {})
        result[pid] = {
            'passes_key': sum(stats.get('passesKey', {}).values()),
            'shots_on_target': sum(stats.get('shotsOnTarget', {}).values()),
            'tackles_total': sum(stats.get('tacklesTotal', {}).values()),
            'tackle_successful': sum(stats.get('tackleSuccessful', {}).values()),
            'dribbles_attempted': sum(stats.get('dribblesAttempted', {}).values()),
            'aerials_won': sum(stats.get('aerialsWon', {}).values()),
            'penalty_goals': 0,
            'penalty_missed': 0,
        }
    # Count penalty goals/missed from events
    for e in events:
        if e.get('type', {}).get('value') != 16:  # only Goal
            continue
        pid = e.get('playerId')
        if not pid or pid not in result:
            continue
        is_penalty = any(q.get('type', {}).get('displayName') == 'Penalty'
                          for q in e.get('qualifiers', []))
        if is_penalty:
            result[pid]['penalty_goals'] += 1
    # Missed penalties: type=13 (MissedShots) with Penalty qualifier
    for e in events:
        if e.get('type', {}).get('value') != 13:
            continue
        pid = e.get('playerId')
        if not pid or pid not in result:
            continue
        is_penalty = any(q.get('type', {}).get('displayName') == 'Penalty'
                          for q in e.get('qualifiers', []))
        if is_penalty:
            result[pid]['penalty_missed'] += 1
    return result


def main():
    # Load existing
    existing = {}
    for f in OUTPUT_DIR.glob("match_*.json"):
        mid = int(f.stem.split('_')[1])
        with open(f) as fh:
            existing[mid] = json.load(fh)
    print(f"Existing match files: {len(existing)}")

    # Load match list
    with open(MATCHES_FILE) as f:
        matches = json.load(f)
    seen = set()
    unique_matches = []
    for m in matches:
        mid = int(m['href'].split('/matches/')[1].split('/')[0]) if '/matches/' in m['href'] else None
        if mid and mid not in seen:
            seen.add(mid)
            unique_matches.append({'match_id': mid, 'href': m['href'], 'text': m.get('text', '')})
    to_do = [m for m in unique_matches if m['match_id'] in existing]
    print(f"To re-fetch: {len(to_do)}")

    total_updated = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()

        for i, m in enumerate(to_do):
            mid = m['match_id']
            data = fetch_match_data(page, m['href'])
            if not data:
                print(f"[{i+1}/{len(to_do)}] {mid} FAILED")
                continue
            stats_map = collect_player_stats(data)
            players = existing[mid]
            for r in players:
                pid = r['player_id']
                s = stats_map.get(pid, {})
                r['passes_key'] = s.get('passes_key', 0)
                r['shots_on_target'] = s.get('shots_on_target', 0)
                r['tackles_total'] = s.get('tackles_total', 0)
                r['tackle_successful'] = s.get('tackle_successful', 0)
                r['dribbles_attempted'] = s.get('dribbles_attempted', 0)
                r['aerials_won'] = s.get('aerials_won', 0)
                r['penalty_goals'] = s.get('penalty_goals', 0)
                r['penalty_missed'] = s.get('penalty_missed', 0)
            with open(OUTPUT_DIR / f"match_{mid}.json", 'w') as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            total_updated += 1
            if (i + 1) % 10 == 0 or i == len(to_do) - 1:
                print(f"[{i+1}/{len(to_do)}] {mid} OK")
        browser.close()

    # Rebuild CSV
    import csv
    combined = []
    for f in sorted(OUTPUT_DIR.glob("match_*.json")):
        with open(f) as fh:
            combined.extend(json.load(fh))
    if combined:
        with open(OUTPUT_DIR / "all_player_ratings.csv", 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[k for k in combined[0].keys() if k != 'ratings_trajectory'])
            writer.writeheader()
            for r in combined:
                row = {k: v for k, v in r.items() if k != 'ratings_trajectory'}
                writer.writerow(row)

    # Stats summary
    print(f"\n{'='*50}")
    print(f"Updated: {total_updated} matches")
    total_passes_key = sum(r.get('passes_key', 0) for r in combined)
    total_sot = sum(r.get('shots_on_target', 0) for r in combined)
    total_pen_goals = sum(r.get('penalty_goals', 0) for r in combined)
    total_pen_missed = sum(r.get('penalty_missed', 0) for r in combined)
    print(f"Total key passes: {total_passes_key}")
    print(f"Total shots on target: {total_sot}")
    print(f"Total penalty goals: {total_pen_goals}")
    print(f"Total penalty missed: {total_pen_missed}")


if __name__ == "__main__":
    main()
