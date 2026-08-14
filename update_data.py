"""
update_data.py

Refreshes every CSV that the College Football Analytics Hub (Main.py + pages/)
actually reads, pulling fresh data from the CollegeFootballData.com (CFBD) API.

WHY: the site's data was frozen around the 2024/2025 seasons. This script
rolls everything forward for the 2026 season:

    "prior season" slot   (files with 2024 in the name, e.g. Roster_2024.csv,
                            player_stats_2024.csv)
        -> filled with the FINAL 2025 season (now complete)

    "current/upcoming" slot (files with 2025 in the name, e.g. Roster_2025.csv,
                              Recruits_2025.csv, Draft_Position.csv, transfers_2025*.csv)
        -> filled with 2026 preseason data (roster, recruiting class, transfer
           portal, incoming NFL draft departures)

    QB game-by-game / season stats
        -> finalized for the complete 2025 season (2026 games haven't happened yet,
           so there's nothing to pull there until the season kicks off)

File names are left exactly as the app already expects them (Roster_2024.csv,
Roster_2025.csv, etc.) so none of the Streamlit pages need to change -- only
the *contents* move forward a year. Comments below call out each mapping.

USAGE (run this locally -- it needs real internet access):
    pip install requests pandas
    python update_data.py                 # pulls everything
    python update_data.py --skip-qb       # skip the (slower) per-week QB pull
    python update_data.py --skip-plays    # skip the week-1 play-by-play pull
    python update_data.py --skip-lines    # skip betting lines

A CFBD API key is required, set via an environment variable (never hardcoded
in source, so it's safe to put this project on GitHub):
    setx CFBD_API_KEY "your-key-here"      (Windows, new terminal after)
    export CFBD_API_KEY="your-key-here"    (Mac/Linux)
Get a free key at https://collegefootballdata.com/key
"""

import argparse
import os
import sys
import time

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("CFBD_API_KEY")
if not API_KEY:
    sys.exit(
        "No CFBD_API_KEY environment variable found.\n"
        "Set one before running this script, e.g. on Windows (in a new terminal after running this):\n"
        '    setx CFBD_API_KEY "your-key-here"\n'
        "Get a free key at https://collegefootballdata.com/key"
    )
BASE = "https://api.collegefootballdata.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PRIOR_SEASON = 2025     # last fully-completed season -> fills "*_2024"-named slots
UPCOMING_SEASON = 2026  # season about to start -> fills "*_2025"-named slots

REQUEST_DELAY = 0.35    # be polite to the API between calls


def get(path, **params):
    """GET a CFBD endpoint and return parsed JSON, raising on HTTP errors."""
    resp = requests.get(f"{BASE}{path}", headers=HEADERS, params=params, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(
            f"GET {path} params={params} -> HTTP {resp.status_code}: {resp.text[:300]}"
        )
    time.sleep(REQUEST_DELAY)
    return resp.json()


def save(df, *paths):
    """Write the same dataframe to one or more paths (some files are read
    from more than one location by different pages)."""
    for p in paths:
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
        df.to_csv(p, index=False)
        print(f"  wrote {p}  ({len(df):,} rows, {len(df.columns)} cols)")


def section(title):
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# 1) Rosters
# ---------------------------------------------------------------------------

def fetch_rosters():
    section(f"Rosters ({PRIOR_SEASON} final, {UPCOMING_SEASON} preseason)")
    roster_prior = pd.json_normalize(get("/roster", year=PRIOR_SEASON))
    save(roster_prior, "data/Roster_2024.csv", "Roster_2024.csv")

    roster_upcoming = pd.json_normalize(get("/roster", year=UPCOMING_SEASON))
    save(roster_upcoming, "data/Roster_2025.csv", "Roster_2025.csv")

    return roster_prior, roster_upcoming


# ---------------------------------------------------------------------------
# 2) NFL Draft picks -- players who left after PRIOR_SEASON get drafted the
#    following spring, i.e. the UPCOMING_SEASON-numbered draft (2026 draft
#    already happened by the time this runs in August 2026).
# ---------------------------------------------------------------------------

def fetch_draft():
    section(f"Draft picks ({UPCOMING_SEASON} draft class)")
    draft_raw = pd.json_normalize(get("/draft/picks", year=UPCOMING_SEASON))
    cols = [c for c in ["collegeAthleteId", "collegeTeam", "overall", "position"] if c in draft_raw.columns]
    draft_position = draft_raw[cols].copy()
    save(draft_position, "data/Draft_Position.csv", "Draft_Position.csv")
    return draft_position


# ---------------------------------------------------------------------------
# 3) Recruiting class joining for the upcoming season
# ---------------------------------------------------------------------------

def fetch_recruits():
    section(f"Recruiting class ({UPCOMING_SEASON})")
    recruits = pd.json_normalize(get("/recruiting/players", year=UPCOMING_SEASON))
    save(recruits, "data/Recruits_2025.csv", "Recruits_2025.csv")
    return recruits


# ---------------------------------------------------------------------------
# 4) Player season stats for the final PRIOR_SEASON, pivoted into the wide
#    "category_statType" format the app's production-impact math expects
#    (e.g. passing_YDS, rushing_TD, defensive_SACKS ...).
# ---------------------------------------------------------------------------

def fetch_player_stats():
    section(f"Player season stats ({PRIOR_SEASON} final, wide format)")
    long_df = pd.json_normalize(get("/stats/player/season", year=PRIOR_SEASON))

    wide = long_df.pivot_table(
        index="playerId", columns=["category", "statType"], values="stat", aggfunc="sum"
    )
    wide.columns = [f"{cat}_{stat}" for cat, stat in wide.columns]
    wide = wide.reset_index()

    # Both locations are read by different pages -- keep them identical.
    save(wide, "player_stats_2024.csv", "data/player_stats_2024.csv")
    return wide


# ---------------------------------------------------------------------------
# 5) Teams / team_info (refresh so conference realignment is current)
# ---------------------------------------------------------------------------

def fetch_teams():
    section(f"Teams ({UPCOMING_SEASON} alignment)")
    teams = pd.json_normalize(get("/teams", year=UPCOMING_SEASON))

    # The API returns "logos" as a list of URLs (multiple sizes/themes). Left
    # as a list, it round-trips through CSV as a stringified list (e.g.
    # "['url1', 'url2']"), which breaks every st.image(...) call downstream.
    # Flatten to a single usable URL before saving.
    if "logos" in teams.columns:
        teams["logos"] = teams["logos"].apply(
            lambda x: x[0] if isinstance(x, list) and x else x
        )

    save(teams, "data/teams.csv")

    cols = [c for c in ["school", "id", "logos", "mascot", "conference"] if c in teams.columns]
    team_info = teams[cols].copy()
    save(team_info, "data/team_info.csv")
    return teams, team_info


# ---------------------------------------------------------------------------
# 6) Transfer portal for the upcoming cycle, matched against the prior
#    season's roster (to know each player's most recent team/position), then
#    merged again with player stats to show production gained/lost.
# ---------------------------------------------------------------------------

def fetch_transfers(roster_prior, player_stats_wide):
    section(f"Transfer portal ({UPCOMING_SEASON} cycle)")
    portal = pd.json_normalize(get("/player/portal", year=UPCOMING_SEASON))

    roster_small = roster_prior[["id", "firstName", "lastName", "position", "team"]].copy()
    roster_small["name_school"] = (
        roster_small["firstName"].fillna("") + roster_small["lastName"].fillna("") + roster_small["team"].fillna("")
    )
    portal["name_school"] = (
        portal["firstName"].fillna("") + portal["lastName"].fillna("") + portal["origin"].fillna("")
    )

    transfers = pd.merge(
        roster_small, portal, on="name_school", how="inner", suffixes=("_x", "_y")
    )
    transfers = transfers.rename(columns={"id": "playerId"})
    save(transfers, "data/Transfers_2025.csv", "data/transfers_2025.csv")

    # Attach each transfer's production from their last season on the wide stats table
    transfers_stats = transfers.copy()
    transfers_stats["playerId"] = pd.to_numeric(transfers_stats["playerId"], errors="coerce")
    stats = player_stats_wide.copy()
    stats["playerId"] = pd.to_numeric(stats["playerId"], errors="coerce")
    transfers_stats = transfers_stats.merge(stats, how="left", on="playerId").fillna(0)
    save(transfers_stats, "data/transfers_2025_stats.csv")

    return transfers, transfers_stats


# ---------------------------------------------------------------------------
# 7) QB stats -- since 2026 games haven't been played, this finalizes the
#    complete PRIOR_SEASON (2025): a per-week/per-game log across every week,
#    plus a season-total snapshot used for the QB comparison radar chart.
#    (The original notebook only ever pulled SEC, weeks 1-3; this pulls every
#    FBS conference across the whole season.)
# ---------------------------------------------------------------------------

def extract_qb_week(games_json, week):
    def extract_stat(types, stat_name):
        for t in types:
            if t["name"] == stat_name:
                return {a["id"]: a for a in t["athletes"]}
        return {}

    rows = []
    for game in games_json:
        for team in game.get("teams", []):
            team_name = team.get("team")
            others = [t for t in game["teams"] if t.get("team") != team_name]
            opponent = others[0]["team"] if others else None
            passing = next((c for c in team.get("categories", []) if c["name"] == "passing"), None)
            if not passing:
                continue

            c_att = extract_stat(passing["types"], "C/ATT")
            yds = extract_stat(passing["types"], "YDS")
            avg = extract_stat(passing["types"], "AVG")
            td = extract_stat(passing["types"], "TD")
            inte = extract_stat(passing["types"], "INT")
            qbr = extract_stat(passing["types"], "QBR")

            for pid, player in c_att.items():
                try:
                    comp, att = map(int, player["stat"].split("/"))
                except (ValueError, AttributeError):
                    continue
                if att < 5:
                    continue
                rows.append({
                    "player_id": pid,
                    "player_name": player.get("name"),
                    "team": team_name,
                    "conference": team.get("conference"),
                    "opponent": opponent,
                    "comp": comp,
                    "att": att,
                    "yds": int(yds[pid]["stat"]) if pid in yds and yds[pid]["stat"] not in (None, "--") else None,
                    "avg": float(avg[pid]["stat"]) if pid in avg and avg[pid]["stat"] not in (None, "--") else None,
                    "td": int(td[pid]["stat"]) if pid in td and td[pid]["stat"] not in (None, "--") else 0,
                    "int": int(inte[pid]["stat"]) if pid in inte and inte[pid]["stat"] not in (None, "--") else 0,
                    "qbr": None if qbr.get(pid, {}).get("stat") in (None, "--") else float(qbr[pid]["stat"]),
                    "week": week,
                })
    return rows


def fetch_qb_stats(max_week=15):
    section(f"QB game-by-game stats ({PRIOR_SEASON} full season, all conferences)")
    all_rows = []
    for week in range(1, max_week + 1):
        try:
            games_json = get("/games/players", year=PRIOR_SEASON, week=week, category="passing")
        except RuntimeError as e:
            print(f"  week {week}: {e}")
            continue
        if not games_json:
            print(f"  week {week}: no data (season likely ended before this week)")
            continue
        week_rows = extract_qb_week(games_json, week)
        print(f"  week {week}: {len(week_rows)} QB performances")
        all_rows.extend(week_rows)

    weekly_df = pd.DataFrame(all_rows)
    if weekly_df.empty:
        print("  No QB data collected -- skipping QB file writes.")
        return

    weekly_df["completion_pct"] = weekly_df["comp"] / weekly_df["att"]
    save(weekly_df, "data/all_qb_game_stats_2024.csv")

    # Season snapshot: one row per QB, aggregated across all weeks played.
    def agg_group(g):
        comp, att = g["comp"].sum(), g["att"].sum()
        return pd.Series({
            "player_id": g["player_id"].iloc[-1],
            "team": g["team"].iloc[-1],
            "conference": g["conference"].iloc[-1],
            "opponent": "Season",
            "comp": comp,
            "att": att,
            "yds": g["yds"].sum(),
            "avg": (g["yds"].sum() / att) if att else 0,
            "td": g["td"].sum(),
            "int": g["int"].sum(),
            "qbr": (g["qbr"] * g["att"]).sum() / att if att and g["qbr"].notna().any() else None,
            "week": g["week"].max(),
            "completion_pct": (comp / att) if att else 0,
        })

    season_df = weekly_df.groupby("player_name").apply(agg_group).reset_index()
    season_df = season_df[season_df["att"] >= 20]
    save(season_df, "data/QB_Stats/2025_QBstats.csv")


# ---------------------------------------------------------------------------
# 8) Betting lines -- ESPN Bet lines for the full (now-complete) PRIOR_SEASON
# ---------------------------------------------------------------------------

def fetch_lines():
    section(f"Betting lines ({PRIOR_SEASON} full season, ESPN Bet)")
    games = get("/lines", year=PRIOR_SEASON, seasonType="regular")

    rows = []
    for g in games:
        for line in g.get("lines", []):
            if line.get("provider") != "ESPN Bet":
                continue
            row = {k: v for k, v in g.items() if k != "lines"}
            row.update(line)
            rows.append(row)

    df = pd.DataFrame(rows)
    save(df, "data/espnBetLines.csv")


# ---------------------------------------------------------------------------
# 9) Week 1 play-by-play (finalized, since the season is over)
# ---------------------------------------------------------------------------

def fetch_week1_plays():
    section(f"Week 1 play-by-play ({PRIOR_SEASON})")
    plays = pd.json_normalize(get("/plays", year=PRIOR_SEASON, week=1, seasonType="regular"))
    save(plays, "data/Drives/week_1_plays_2025.csv")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Refresh CFB Analytics Hub data")
    parser.add_argument("--skip-qb", action="store_true", help="skip per-week QB stats pull")
    parser.add_argument("--skip-plays", action="store_true", help="skip week-1 play-by-play pull")
    parser.add_argument("--skip-lines", action="store_true", help="skip betting lines pull")
    args = parser.parse_args()

    roster_prior, roster_upcoming = fetch_rosters()
    fetch_draft()
    fetch_recruits()
    player_stats_wide = fetch_player_stats()
    fetch_teams()
    fetch_transfers(roster_prior, player_stats_wide)

    if not args.skip_qb:
        fetch_qb_stats()
    else:
        print("\nSkipping QB stats (--skip-qb)")

    if not args.skip_lines:
        try:
            fetch_lines()
        except Exception as e:
            print(f"  Betting lines fetch failed: {e}")
    else:
        print("\nSkipping betting lines (--skip-lines)")

    if not args.skip_plays:
        try:
            fetch_week1_plays()
        except Exception as e:
            print(f"  Play-by-play fetch failed: {e}")
    else:
        print("\nSkipping play-by-play (--skip-plays)")

    print("\nAll done. Restart the Streamlit app to see the refreshed data:")
    print("    streamlit run Main.py")


if __name__ == "__main__":
    main()
