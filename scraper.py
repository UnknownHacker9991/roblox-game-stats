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
# CONFIGURATION — edit this list to track whatever games you want
# Format: (Universe ID, Game Name)
# To find a game's Universe ID:
#   1. Go to the game page on roblox.com
#   2. Copy the number from the URL (that's the Place ID)
#   3. Use: https://apis.roblox.com/universes/v1/places/PLACE_ID/universe
# ============================================================

GAMES = [
    (286090429,  "Adopt Me!"),
    (2753915549, "Blox Fruits"),
    (1962086868, "Tower of Hell"),
    (2474168535, "Murder Mystery 2"),
    (292439477,  "Brookhaven RP"),
    (3260590327, "Pet Simulator X"),
    (65241, "MeepCity"),
    (189707, "Natural Disaster Survival"),
    (301549746, "Royale High"),
    (4252370517, "Doors"),
    (13822889, "Phantom Forces"),
    (1224212277, "MM2"),
    (3110005891, "The Strongest Battlegrounds"),
    (6284583030, "Dress to Impress"),
    (5765085099, "Rivals"),
    (2177157737, "Military Roleplay"),
]

API_URL = "https://games.roblox.com/v1/games"
VOTES_URL = "https://games.roblox.com/v1/games/votes"
DATA_DIR = "data"
CHARTS_DIR = "charts"


def fetch_game_details(universe_ids: list[int]) -> dict:
    """Fetch game details from Roblox API for a list of universe IDs."""
    # API accepts up to 100 universe IDs at once
    ids_str = ",".join(str(uid) for uid in universe_ids)
    
    response = requests.get(API_URL, params={"universeIds": ids_str})
    response.raise_for_status()
    
    data = response.json().get("data", [])
    return {game["id"]: game for game in data}


def fetch_votes(universe_ids: list[int]) -> dict:
    """Fetch vote (like/dislike) data for games."""
    ids_str = ",".join(str(uid) for uid in universe_ids)
    
    response = requests.get(VOTES_URL, params={"universeIds": ids_str})
    response.raise_for_status()
    
    data = response.json().get("data", [])
    return {item["id"]: item for item in data}


def scrape_all() -> list[dict]:
    """Scrape stats for all configured games. Returns a list of dicts."""
    universe_ids = [uid for uid, _ in GAMES]
    name_map = {uid: name for uid, name in GAMES}
    
    print(f"[*] Fetching data for {len(universe_ids)} games...")
    
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
            "name": name_map.get(uid, game.get("name", "Unknown")),
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
    # Sort by current players (highest first)
    sorted_results = sorted(results, key=lambda x: x["playing"], reverse=True)
    
    print("\n" + "=" * 85)
    print(f"  {'Game':<30} {'Playing':>10} {'Visits':>14} {'Favorites':>12} {'Like %':>8}")
    print("=" * 85)
    
    for r in sorted_results:
        visits_str = f"{r['visits']:,}"
        favs_str = f"{r['favorites']:,}"
        playing_str = f"{r['playing']:,}"
        
        print(f"  {r['name']:<30} {playing_str:>10} {visits_str:>14} {favs_str:>12} {r['like_pct']:>7}%")
    
    print("=" * 85)
    
    total_playing = sum(r["playing"] for r in results)
    print(f"  Total players across tracked games: {total_playing:,}")
    print(f"  Scraped at: {results[0]['timestamp']}\n")


def generate_charts(results: list[dict]):
    """Generate bar charts from the scraped data."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive backend
        import matplotlib.pyplot as plt
    except ImportError:
        print("[!] matplotlib not installed. Run: pip install matplotlib")
        print("    Skipping chart generation.")
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
    ax.set_title("Roblox Games — Live Player Count", fontsize=14, fontweight="bold")
    ax.tick_params(axis="y", labelsize=10)
    
    # Add value labels on bars
    for bar in bars:
        width = bar.get_width()
        label = f"{width:,.0f}"
        ax.text(width + max(playing) * 0.01, bar.get_y() + bar.get_height() / 2,
                label, va="center", fontsize=9, color="#444")
    
    plt.tight_layout()
    path1 = os.path.join(CHARTS_DIR, "player_count.png")
    plt.savefig(path1, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[+] Chart saved: {path1}")
    
    # --- Chart 2: Like Percentage ---
    colors = ["#57F287" if pct >= 80 else "#FEE75C" if pct >= 60 else "#ED4245" for pct in like_pcts]
    
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(names[::-1], like_pcts[::-1],
                   color=colors[::-1], edgecolor="none")
    ax.set_xlabel("Like Percentage (%)", fontsize=12)
    ax.set_title("Roblox Games — Community Rating", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 105)
    ax.tick_params(axis="y", labelsize=10)
    
    for bar, pct in zip(bars, like_pcts[::-1]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{pct}%", va="center", fontsize=9, color="#444")
    
    plt.tight_layout()
    path2 = os.path.join(CHARTS_DIR, "like_percentage.png")
    plt.savefig(path2, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[+] Chart saved: {path2}")
    
    # --- Chart 3: Total Visits (log scale) ---
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(names[::-1], visits[::-1], color="#EB459E", edgecolor="none")
    ax.set_xlabel("Total Visits (log scale)", fontsize=12)
    ax.set_title("Roblox Games — All-Time Visits", fontsize=14, fontweight="bold")
    ax.set_xscale("log")
    ax.tick_params(axis="y", labelsize=10)
    
    for bar in bars:
        width = bar.get_width()
        if width > 0:
            label = f"{width / 1_000_000_000:.1f}B" if width >= 1_000_000_000 else f"{width / 1_000_000:.0f}M"
            ax.text(width * 1.3, bar.get_y() + bar.get_height() / 2,
                    label, va="center", fontsize=9, color="#444")
    
    plt.tight_layout()
    path3 = os.path.join(CHARTS_DIR, "total_visits.png")
    plt.savefig(path3, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[+] Chart saved: {path3}")


def track_mode(interval_minutes: int = 30):
    """Run the scraper on a loop, appending data each time."""
    print(f"[*] Tracking mode — scraping every {interval_minutes} min. Press Ctrl+C to stop.\n")
    
    while True:
        try:
            results = scrape_all()
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
        save_csv(results)
        print_table(results)
        generate_charts(results)
        print("[*] Done! Check the 'data' and 'charts' folders.")


if __name__ == "__main__":
    main()
