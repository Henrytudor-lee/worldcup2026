#!/usr/bin/env python3
"""
WhoScored batch player ratings scraper for 2026 World Cup.
Fetches all 94 matches (72 group + 22 KO), extracts per-player ratings from matchCentreData JSON.
"""
import json
import time
from playwright.sync_api import sync_playwright
from pathlib import Path

BASE_URL = "https://www.whoscored.com"
MATCHES_FILE = "/tmp/wc_matches.json"
OUTPUT_DIR = Path("/Users/garcia/Desktop/WorldCup2026/4_比赛预测/player_ratings")
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_match_data(page, match_url: str) -> dict:
    """Navigate to match page, extract matchCentreData JSON."""
    url = f"{BASE_URL}{match_url}" if match_url.startswith("/") else match_url
    match_id = match_url.split('/matches/')[1].split('/')[0] if '/matches/' in match_url else '?'
    for attempt in range(3):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Get matchCentreData from require.config
            raw = page.evaluate("""() => {
                try {
                    const args = require.config.params['args'];
                    if (!args || !args.matchCentreData) return null;
                    return JSON.stringify(args.matchCentreData);
                } catch(e) { return null; }
            }""")
            
            if raw:
                return json.loads(raw)
            else:
                print(f"  No matchCentreData found for match {match_id}, retrying...")
                time.sleep(3)
        except Exception as e:
            print(f"  Error fetching {match_id} (attempt {attempt+1}): {e}")
            time.sleep(8)
    return None


def extract_player_ratings(data: dict) -> list:
    """Extract player-level final ratings from matchCentreData."""
    results = []
    
    if not data:
        return results
    
    # Get team names + match metadata
    metadata = {
        'match_id': data.get('matchId'),
        'date': data.get('startDate', ''),
        'venue': data.get('venueName', ''),
        'referee': f"{data.get('referee', {}).get('firstName', '')} {data.get('referee', {}).get('lastName', '')}".strip(),
        'score': data.get('ftScore', data.get('score', '')),
        'home_team': data.get('home', {}).get('name', ''),
        'away_team': data.get('away', {}).get('name', ''),
        'home_team_id': data.get('home', {}).get('teamId', ''),
        'away_team_id': data.get('away', {}).get('teamId', ''),
    }
    
    player_names = data.get('playerIdNameDictionary', {})
    
    for team_field in ['home', 'away']:
        team_data = data.get(team_field, {})
        team_name = team_data.get('name', '')
        team_id = team_data.get('teamId', '')
        
        for p in team_data.get('players', []):
            stats = p.get('stats', {})
            ratings = stats.get('ratings', {})
            if not ratings:
                continue
            
            # Final rating = max minute value (last rating)
            max_min = max(ratings.keys(), key=int)
            final_rating = ratings[max_min]
            
            # Get the per-minute ratings trajectory (for sparkline)
            ratings_traj = {int(k): v for k, v in ratings.items()}
            
            # Get other key stats
            total_shots = sum(stats.get('totalScoringAttempt', {}).values())
            goals = sum(stats.get('goals', {}).values())
            assists = sum(stats.get('goalAssist', {}).values())
            yellow = sum(stats.get('yellowCard', {}).values())
            red = sum(stats.get('redCard', {}).values())
            
            results.append({
                'match_id': metadata['match_id'],
                'date': metadata['date'],
                'team': team_name,
                'team_id': team_id,
                'opponent': metadata['away_team'] if team_field == 'home' else metadata['home_team'],
                'home_away': team_field,
                'player_id': p.get('playerId'),
                'player_name': p.get('name'),
                'shirt_no': p.get('shirtNo'),
                'position': p.get('position'),
                'age': p.get('age'),
                'is_first_eleven': p.get('isFirstEleven', False),
                'is_man_of_match': p.get('isManOfTheMatch', False),
                'final_rating': final_rating,
                'max_minute': int(max_min),
                'goals': goals,
                'assists': assists,
                'total_shots': total_shots,
                'yellow_cards': yellow,
                'red_cards': red,
                'ratings_trajectory': ratings_traj,
                'venue': metadata['venue'],
                'referee': metadata['referee'],
                'score': metadata['score'],
            })
    
    return results


def main():
    # Load match URLs
    with open(MATCHES_FILE) as f:
        matches = json.load(f)
    
    print(f"Found {len(matches)} matches to scrape")
    
    # Extract match URLs (full path)
    match_urls = []
    for m in matches:
        match_urls.append({
            'href': m['href'],
            'group': m.get('group', '?'),
            'text': m.get('text', ''),
            'match_id': int(m['href'].split('/matches/')[1].split('/')[0]) if '/matches/' in m['href'] else None
        })
    
    # Dedupe by match_id
    seen = set()
    unique_matches = []
    for m in match_urls:
        if m['match_id'] not in seen:
            seen.add(m['match_id'])
            unique_matches.append(m)
    
    print(f"Unique match IDs: {len(unique_matches)}")
    
    all_player_ratings = []
    failed = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        
        for i, m in enumerate(unique_matches):
            mid = m['match_id']
            print(f"\n[{i+1}/{len(unique_matches)}] Group {m['group']}: Match {mid} - {m['text'][:50]}")
            
            data = fetch_match_data(page, m['href'])
            if data:
                ratings = extract_player_ratings(data)
                print(f"  Got {len(ratings)} player ratings")
                all_player_ratings.extend(ratings)
                # Save individual match file
                with open(OUTPUT_DIR / f"match_{mid}.json", 'w') as f:
                    json.dump(ratings, f, indent=2, ensure_ascii=False)
            else:
                failed.append(mid)
                print(f"  FAILED")
            
            time.sleep(2)  # Rate limiting
        
        browser.close()
    
    # Save combined CSV
    import csv
    with open(OUTPUT_DIR / "all_player_ratings.csv", 'w', newline='') as f:
        if all_player_ratings:
            writer = csv.DictWriter(f, fieldnames=[k for k in all_player_ratings[0].keys() if k != 'ratings_trajectory'])
            writer.writeheader()
            for r in all_player_ratings:
                row = {k: v for k, v in r.items() if k != 'ratings_trajectory'}
                writer.writerow(row)
    
    print(f"\n{'='*50}")
    print(f"Total player ratings collected: {len(all_player_ratings)}")
    print(f"Failed matches: {len(failed)} - {failed}")
    print(f"Output: {OUTPUT_DIR / 'all_player_ratings.csv'}")


if __name__ == "__main__":
    main()
