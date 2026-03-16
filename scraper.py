"""
Roblox Game Stats Scraper
Pulls live player counts, visits, likes, and favorites from top Roblox games.
Saves data to CSV and generates charts.

Usage:
    python scraper.py          # Scrape once, save CSV + charts
    python scraper.py --track  # Scrape every 30 min and log over time
"""

import requests
import csv
import os
import sys
import time
from datetime import datetime

# ============================================================
# CONFIGURATION — Universe IDs mapped to game names
# To add a new game:
#   1. Get the Place ID from the game URL: roblox.com/games/PLACE_ID/...
#   2. Visit: https://apis.roblox.com/universes/v1/places/PLACE_ID/universe
#   3. Copy the universeId and add it below
# ============================================================

GAMES = {
    383310974:  "Adopt Me!",
    994732206:  "Blox Fruits",
    703124385:  "Tower of Hell",
    66654135:   "Murder Mystery 2",
    1686885941: "Brookhaven RP",
    2316994223: "Pet Simulator 99",
    140239261:  "MeepCity",
    65241:      "Natural Disaster Survival",
    321778215:  "Royale High",
    2440500124: "Doors",
    113491250:  "Phantom Forces",
    4335335911: "Dress to Impress",
    6035872082: "Rivals",
    2177157737: "Military Roleplay",
}

GAMES_API = "https://games.roblox.com/v1/games"
VOTES_API = "https://games.roblox.com/v1/games/votes"
DATA_DIR = "data"
CHARTS_DIR = "charts"


def fetch_game_details(universe_ids: list[int]) -> dict:
    """Fetch game details from Roblox API for a list of universe IDs."""
    ids_str = ",".join(str(uid) for uid in universe_ids)
    response = requests.get(GAMES_API, params={"universeIds": ids_str})
    response.raise_for_status()
    data = response.json().get("data", [])
    return {game["id"]: game for game in data}


def fetch_votes(universe_ids: list[int]) -> dict:
    """Fetch vote (like/dislike) data for games."""
    ids_str = ",".join(str(uid) for uid in universe_ids)
    response = requests.get(VOTES_API, params={"universeIds": ids_str})
    response.raise_for_status()
    data = response.json().get("data", [])
    return {item["id"]: item for item in data}


def scrape_all() -> list[dict]:
    """Scrape stats for all configured games. Returns a list of dicts."""
    universe_ids = list(GAMES.keys())

    print(f"[*] Fetching stats for {len(universe_ids)} games...")
    details = fetch_game_details(universe_ids)
    votes = fetch_votes(universe_ids)

    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for uid in universe_ids:
        game = details.get(uid, {})
        vote = votes.get(uid, {})

        row = {
            "timestamp": timestamp,
            "universe_id": uid,
            "name": GAMES[uid],
            "playing": game.get("playing", 0),
            "visits": game.get("visits", 0),
            "favorites": game.get("favoritedCount", 0),
            "likes": vote.get("upVotes", 0),
            "dislikes": vote.get("downVotes", 0),
            "like_pct": 0,
        }

        total_votes = row["likes"] + row["dislikes"]
        if total_votes > 0:
            row["like_pct"] = round(row["likes"] / total_votes * 100, 1)

        results.append(row)

    return results


def save_csv(results: list[dict], filename: str = "roblox_stats.csv"):
    """Save results to CSV. Appends if file exists (for tracking over time)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)

    file_exists = os.path.exists(filepath)

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(results)

    print(f"[+] Saved {len(results)} rows to {filepath}")
    return filepath


def print_table(results: list[dict]):
    """Print a clean table to the terminal."""
    sorted_results = sorted(results, key=lambda x: x["playing"], reverse=True)

    print("\n" + "=" * 85)
    print(f"  {'Game':<30} {'Playing':>10} {'Visits':>14} {'Favorites':>12} {'Like %':>8}")
    print("=" * 85)

    for r in sorted_results:
        print(f"  {r['name']:<30} {r['playing']:>10,} {r['visits']:>14,} {r['favorites']:>12,} {r['like_pct']:>7}%")

    print("=" * 85)
    total_playing = sum(r["playing"] for r in results)
    print(f"  Total players across tracked games: {total_playing:,}")
    print(f"  Scraped at: {results[0]['timestamp']}\n")


def format_number(n: int) -> str:
    """Format large numbers: 1.2B, 345M, 12.3K, or raw number."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    elif n >= 1_000_000:
        return f"{n / 1_000_000:.0f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    else:
        return str(n)


def generate_charts(results: list[dict]):
    """Generate bar charts from the scraped data."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[!] matplotlib not installed. Run: pip install matplotlib")
        return

    os.makedirs(CHARTS_DIR, exist_ok=True)
    sorted_results = sorted(results, key=lambda x: x["playing"], reverse=True)

    names = [r["name"] for r in sorted_results]
    playing = [r["playing"] for r in sorted_results]
    visits = [r["visits"] for r in sorted_results]
    like_pcts = [r["like_pct"] for r in sorted_results]

    # --- Chart 1: Current Players ---
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(names[::-1], playing[::-1], color="#5865F2", edgecolor="none")
    ax.set_xlabel("Players Online Right Now", fontsize=12)
    ax.set_title("Roblox Games \u2014 Live Player Count", fontsize=14, fontweight="bold")

    max_playing = max(playing) if max(playing) > 0 else 1
    for bar in bars:
        width = bar.get_width()
        ax.text(width + max_playing * 0.01, bar.get_y() + bar.get_height() / 2,
                format_number(int(width)), va="center", fontsize=9, color="#444")

    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "player_count.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("[+] Chart saved: charts/player_count.png")

    # --- Chart 2: Like Percentage ---
    colors = ["#57F287" if pct >= 80 else "#FEE75C" if pct >= 60 else "#ED4245" for pct in like_pcts]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(names[::-1], like_pcts[::-1], color=colors[::-1], edgecolor="none")
    ax.set_xlabel("Like Percentage (%)", fontsize=12)
    ax.set_title("Roblox Games \u2014 Community Rating", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 105)

    for bar, pct in zip(bars, like_pcts[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{pct}%", va="center", fontsize=9, color="#444")

    plt.tight_layout()
    plt.savefig(os.path.join(CHARTS_DIR, "like_percentage.png"), dpi=150, bbox_inches="tight")
    plt.close()
    print("[+] Chart saved: charts/like_percentage.png")

    # --- Chart 3: Total Visits ---
    # Only include games with visits > 0 for clean log scale
    visit_data = [(n, v) for n, v in zip(names, visits) if v > 0]

    if visit_data:
        visit_data.sort(key=lambda x: x[1])
        v_names, v_visits = zip(*visit_data)

        fig, ax = plt.subplots(figsize=(12, 7))
        bars = ax.barh(list(v_names), list(v_visits), color="#EB459E", edgecolor="none")
        ax.set_xlabel("Total Visits (log scale)", fontsize=12)
        ax.set_title("Roblox Games \u2014 All-Time Visits", fontsize=14, fontweight="bold")
        ax.set_xscale("log")

        for bar in bars:
            width = bar.get_width()
            if width > 0:
                ax.text(width * 1.3, bar.get_y() + bar.get_height() / 2,
                        format_number(int(width)), va="center", fontsize=9, color="#444")

        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, "total_visits.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("[+] Chart saved: charts/total_visits.png")
    else:
        print("[!] No visit data to chart.")


def track_mode(interval_minutes: int = 30):
    """Run the scraper on a loop, appending data each time."""
    print(f"[*] Tracking mode \u2014 scraping every {interval_minutes} min. Press Ctrl+C to stop.\n")

    while True:
        try:
            results = scrape_all()
            if results:
                save_csv(results)
                print_table(results)
                generate_charts(results)
            print(f"[*] Next scrape in {interval_minutes} min...\n")
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n[*] Stopped tracking.")
            break
        except Exception as e:
            print(f"[!] Error: {e}. Retrying in 60s...")
            time.sleep(60)


def main():
    if "--track" in sys.argv:
        track_mode()
    else:
        results = scrape_all()
        if results:
            save_csv(results)
            print_table(results)
            generate_charts(results)
            print("[*] Done! Check the 'data' and 'charts' folders.")
        else:
            print("[!] No data scraped. Check your connection and try again.")


if __name__ == "__main__":
    main()