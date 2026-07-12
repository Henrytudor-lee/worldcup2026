#!/usr/bin/env python3
"""WS batch v3 - re-fetch matchCentreData, extract goals/assists/cards from events,
merge into existing match_*.json (keep ratings + add events).

Event type legend (Opta):
  16 = Goal
  17 = Card (Yellow/Red via qualifiers)
  1  = Pass (assists come from Goal's RelatedEventId -> preceding pass)
"""
import json
import time
import sys
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


def count_events(data: dict) -> dict:
    """Count per-player goals, assists, yellow cards, red cards from events array."""
    events = data.get('events', [])
    # Per-player counters
    goals = defaultdict(int)        # type.value=16
    yellow = defaultdict(int)
    red = defaultdict(int)
    # Goal -> RelatedEventId mapping
    goal_to_assist_event_id = {}
    for e in events:
        if e.get('type', {}).get('value') == 16:  # Goal
            player_id = e.get('playerId')
            if player_id:
                goals[player_id] += 1
            # find RelatedEventId
            for q in e.get('qualifiers', []):
                if q.get('type', {}).get('displayName') == 'RelatedEventId':
                    related_id = int(q.get('value', 0))
                    goal_to_assist_event_id[e['id']] = related_id
        elif e.get('type', {}).get('value') == 17:  # Card
            player_id = e.get('playerId')
            if not player_id:
                continue
            is_yellow = any(q.get('type', {}).get('displayName') == 'Yellow'
                          for q in e.get('qualifiers', []))
            is_red = any(q.get('type', {}).get('displayName') == 'Red'
                       for q in e.get('qualifiers', []))
            if is_yellow:
                yellow[player_id] += 1
            if is_red:
                red[player_id] += 1
    # Now find assist providers: look up events by Opta eventId (not WhoScored internal id)
    assists = defaultdict(int)
    events_by_eventId = {e['eventId']: e for e in events if 'eventId' in e}
    for goal_id, related_id in goal_to_assist_event_id.items():
        related_event = events_by_eventId.get(related_id)
        if related_event:
            assist_player = related_event.get('playerId')
            if assist_player:
                assists[assist_player] += 1
    return {'goals': dict(goals), 'assists': dict(assists),
            'yellow': dict(yellow), 'red': dict(red)}


def main():
    # Load all existing match data
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
            unique_matches.append({'match_id': mid, 'group': m.get('group', '?'),
                                    'text': m.get('text', ''), 'href': m['href']})

    # Only re-fetch existing matches
    to_do = [m for m in unique_matches if m['match_id'] in existing]
    print(f"Total matches: {len(unique_matches)}, Existing: {len(existing)}, To re-fetch: {len(to_do)}")

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
            print(f"[{i+1}/{len(to_do)}] Re-fetch {mid} - {m['text'][:50]}", end=' ... ')
            data = fetch_match_data(page, m['href'])
            if not data:
                print("FAILED")
                continue
            counters = count_events(data)
            # Merge into existing
            players = existing[mid]
            for r in players:
                pid = r['player_id']
                r['goals'] = counters['goals'].get(pid, 0)
                r['assists'] = counters['assists'].get(pid, 0)
                r['yellow_cards'] = counters['yellow'].get(pid, 0)
                r['red_cards'] = counters['red'].get(pid, 0)
            # Save back
            with open(OUTPUT_DIR / f"match_{mid}.json", 'w') as f:
                json.dump(players, f, indent=2, ensure_ascii=False)
            total_updated += 1
            g_total = sum(counters['goals'].values())
            a_total = sum(counters['assists'].values())
            print(f"OK (G={g_total} A={a_total} Y={sum(counters['yellow'].values())} R={sum(counters['red'].values())})")
            time.sleep(2)
        browser.close()

    # Rebuild combined CSV
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

    # Stats
    total_goals = sum(r.get('goals', 0) for r in combined)
    total_assists = sum(r.get('assists', 0) for r in combined)
    total_yellow = sum(r.get('yellow_cards', 0) for r in combined)
    total_red = sum(r.get('red_cards', 0) for r in combined)
    print(f"\n{'='*50}")
    print(f"Updated: {total_updated} matches")
    print(f"Total goals: {total_goals}")
    print(f"Total assists: {total_assists}")
    print(f"Total yellow cards: {total_yellow}")
    print(f"Total red cards: {total_red}")
    print(f"Output: {OUTPUT_DIR / 'all_player_ratings.csv'}")


if __name__ == "__main__":
    main()
