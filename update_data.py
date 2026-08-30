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

    Team season stats (offense + defense) and weekly schedule/spreads
        -> power the "Weekly Preview" page. Team stats default to the completed
           2025 season (last year's numbers, since 2026 hasn't kicked off);
           re-run with --season-stats-year 2026 once games start this season to
           switch the preview over to in-season numbers. The weekly schedule +
           opening spreads are pulled on demand with --week N.

File names are left exactly as the app already expects them (Roster_2024.csv,
Roster_2025.csv, etc.) so none of the Streamlit pages need to change -- only
the *contents* move forward a year. Comments below call out each mapping.

USAGE (run this locally -- it needs real internet access):
    pip install requests pandas
    python update_data.py                       # pulls everything except this week's schedule
    python update_data.py --week 1               # also pulls Week 1's schedule + opening spreads
                                                    # (FBS games only by default -- add
                                                    # --all-classifications for every NCAA game)
    python update_data.py --skip-qb               # skip the (slower) per-week QB pull
    python update_data.py --skip-plays             # skip the week-1 play-by-play pull
    python update_data.py --skip-lines              # skip full-season betting lines
    python update_data.py --skip-team-stats           # skip team season offense/defense stats
    python update_data.py --season-stats-year 2026      # once 2026 games exist, refresh
                                                           # team season stats from this season
                                                           # instead of the 2025 default

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
# 10) Team game & season stats (offense + defense splits) -- powers the
#     "Weekly Preview" page's stat comparison (yards/gm, points/gm, 3rd down
#     %, yards & points allowed, turnovers forced, turnover margin).
#
#     /games/teams returns two rows per game (one per team), each holding
#     that TEAM'S OWN offensive output for the game. There's no separate
#     "defense" endpoint -- a team's defensive numbers for a game are just
#     the opponent's offensive row for that same game, so
#     build_team_season_stats looks the opponent row up rather than fetching
#     anything extra.
# ---------------------------------------------------------------------------

def extract_team_game_row(game, team_obj, opponent_obj):
    stats = {s.get("category"): s.get("stat") for s in team_obj.get("stats", [])}

    def num(key, default=0.0):
        v = stats.get(key)
        if v in (None, "", "--"):
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def frac(key):
        """Parse a 'made-attempted' stat like thirdDownEff: '6-13' -> (6.0, 13.0)."""
        v = stats.get(key)
        if not v or "-" not in str(v):
            return 0.0, 0.0
        made, att = str(v).split("-", 1)
        try:
            return float(made), float(att)
        except ValueError:
            return 0.0, 0.0

    third_made, third_att = frac("thirdDownEff")

    return {
        "gameId": game.get("id"),
        "week": game.get("week"),
        "team": team_obj.get("team"),
        "conference": team_obj.get("conference"),
        "opponent": opponent_obj.get("team") if opponent_obj else None,
        "homeAway": team_obj.get("homeAway"),
        "points": team_obj.get("points") if team_obj.get("points") is not None else 0,
        "totalYards": num("totalYards"),
        "thirdDownMade": third_made,
        "thirdDownAtt": third_att,
        "turnovers": num("turnovers"),
    }


def fetch_team_game_stats(year, max_week=15):
    section(f"Team game stats ({year} full season, offense + allowed)")
    rows = []
    for week in range(1, max_week + 1):
        try:
            games_json = get("/games/teams", year=year, week=week, seasonType="regular")
        except RuntimeError as e:
            print(f"  week {week}: {e}")
            continue
        if not games_json:
            print(f"  week {week}: no data (season likely ended before this week)")
            continue
        week_rows = 0
        for game in games_json:
            teams = game.get("teams", [])
            if len(teams) != 2:
                continue
            a, b = teams
            rows.append(extract_team_game_row(game, a, b))
            rows.append(extract_team_game_row(game, b, a))
            week_rows += 2
        print(f"  week {week}: {week_rows} team-game rows")

    long_df = pd.DataFrame(rows)
    save(long_df, f"data/team_game_stats_{year}.csv")
    return long_df


def build_team_season_stats(long_df, year):
    """Aggregate the per-game long table into one row per team: offensive
    per-game averages plus 'allowed'/'forced' defensive numbers pulled from
    the opponent's row in the same game."""
    section(f"Team season stats ({year}, offense + defense splits)")
    if long_df.empty:
        print("  No team game stats available -- skipping.")
        return pd.DataFrame()

    df = long_df.copy()
    opp_index = df.set_index(["gameId", "team"])

    def opponent_row(row):
        try:
            return opp_index.loc[(row["gameId"], row["opponent"])]
        except KeyError:
            return None

    points_allowed, yards_allowed, turnovers_forced = [], [], []
    def_third_made, def_third_att = [], []
    for _, row in df.iterrows():
        orow = opponent_row(row)
        if orow is None:
            points_allowed.append(None)
            yards_allowed.append(None)
            turnovers_forced.append(None)
            def_third_made.append(None)
            def_third_att.append(None)
        else:
            points_allowed.append(orow["points"])
            yards_allowed.append(orow["totalYards"])
            turnovers_forced.append(orow["turnovers"])  # opponent's own turnovers = ones this team forced
            def_third_made.append(orow["thirdDownMade"])
            def_third_att.append(orow["thirdDownAtt"])

    df["points_allowed"] = points_allowed
    df["yards_allowed"] = yards_allowed
    df["turnovers_forced"] = turnovers_forced
    df["def_third_made"] = def_third_made
    df["def_third_att"] = def_third_att

    agg = df.groupby("team").agg(
        games=("gameId", "nunique"),
        off_points_total=("points", "sum"),
        off_yards_total=("totalYards", "sum"),
        off_third_made=("thirdDownMade", "sum"),
        off_third_att=("thirdDownAtt", "sum"),
        turnovers_committed_total=("turnovers", "sum"),
        def_points_total=("points_allowed", "sum"),
        def_yards_total=("yards_allowed", "sum"),
        turnovers_forced_total=("turnovers_forced", "sum"),
        def_third_made_total=("def_third_made", "sum"),
        def_third_att_total=("def_third_att", "sum"),
    ).reset_index()

    g = agg["games"].replace(0, pd.NA)
    season = pd.DataFrame({
        "team": agg["team"],
        "games": agg["games"],
        "off_points_pg": agg["off_points_total"] / g,
        "off_yards_pg": agg["off_yards_total"] / g,
        "off_third_down_pct": (agg["off_third_made"] / agg["off_third_att"].replace(0, pd.NA) * 100).fillna(0),
        "def_points_pg": agg["def_points_total"] / g,
        "def_yards_pg": agg["def_yards_total"] / g,
        "def_third_down_pct": (agg["def_third_made_total"] / agg["def_third_att_total"].replace(0, pd.NA) * 100).fillna(0),
        "turnovers_committed_pg": agg["turnovers_committed_total"] / g,
        "turnovers_forced_pg": agg["turnovers_forced_total"] / g,
    })
    season["turnover_margin_pg"] = season["turnovers_forced_pg"] - season["turnovers_committed_pg"]
    season = season.round(2)

    save(season, f"data/team_season_stats_{year}.csv")
    return season


# ---------------------------------------------------------------------------
# 11) Weekly schedule + opening spreads -- one week at a time, on demand
#     (pass --week N). Powers the matchup list on the "Weekly Preview" page.
# ---------------------------------------------------------------------------

def load_fbs_teams():
    """FBS team names, for filtering the weekly schedule down to FBS games.
    Reads data/teams.csv, which fetch_teams() always refreshes earlier in
    main() -- so this is normally guaranteed fresh. Returns None (meaning
    "don't filter") if that file isn't available for some reason, rather
    than failing the whole schedule pull."""
    try:
        teams = pd.read_csv("data/teams.csv")
        return set(teams.loc[teams["classification"].str.lower() == "fbs", "school"])
    except Exception as e:
        print(f"  Could not load FBS team list from data/teams.csv ({e}) -- schedule will include all classifications.")
        return None


def fetch_week_games(week, year=None, fbs_only=True):
    """fbs_only=True (default) keeps games where at least one team is FBS --
    i.e. the normal "FBS schedule" for the week, including week-1 buy games
    against an FCS/DII opponent. Set False to pull every NCAA game (FBS
    through DIII), or filter further yourself afterward for FBS-vs-FBS only."""
    year = year or UPCOMING_SEASON
    section(f"Week {week} schedule & opening lines ({year})")
    try:
        games = get("/games", year=year, week=week, seasonType="regular")
    except RuntimeError as e:
        print(f"  games fetch failed: {e}")
        return pd.DataFrame()

    sched = pd.json_normalize(games)
    keep = [c for c in [
        "id", "week", "startDate", "startTimeTBD", "homeTeam", "homeConference",
        "awayTeam", "awayConference", "venue", "neutralSite",
    ] if c in sched.columns]
    sched = sched[keep].rename(columns={"id": "gameId"})

    if fbs_only:
        fbs_teams = load_fbs_teams()
        if fbs_teams:
            before = len(sched)
            sched = sched[sched["homeTeam"].isin(fbs_teams) | sched["awayTeam"].isin(fbs_teams)].copy()
            print(f"  filtered to FBS games: {len(sched)} of {before} (at least one team is FBS)")

    try:
        lines = get("/lines", year=year, week=week, seasonType="regular")
    except RuntimeError as e:
        print(f"  lines fetch failed: {e}")
        lines = []

    line_rows = []
    for g in lines:
        game_lines = g.get("lines", [])
        chosen = next((l for l in game_lines if l.get("provider") == "ESPN Bet"), None)
        chosen = chosen or (game_lines[0] if game_lines else None)
        if not chosen:
            continue
        line_rows.append({
            "gameId": g.get("id"),
            "spread": chosen.get("spread"),
            "formattedSpread": chosen.get("formattedSpread"),
            "overUnder": chosen.get("overUnder"),
            "homeMoneyline": chosen.get("homeMoneyline"),
            "awayMoneyline": chosen.get("awayMoneyline"),
        })
    line_df = pd.DataFrame(line_rows)

    merged = sched.merge(line_df, on="gameId", how="left") if not line_df.empty else sched
    save(merged, f"data/schedule/week_{week}_games_{year}.csv")
    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Refresh CFB Analytics Hub data")
    parser.add_argument("--skip-qb", action="store_true", help="skip per-week QB stats pull")
    parser.add_argument("--skip-plays", action="store_true", help="skip week-1 play-by-play pull")
    parser.add_argument("--skip-lines", action="store_true", help="skip full-season betting lines pull")
    parser.add_argument("--skip-team-stats", action="store_true", help="skip team season offense/defense stats pull")
    parser.add_argument(
        "--season-stats-year", type=int, default=None,
        help="pull team season stats for this year instead of the default prior season "
             "(e.g. --season-stats-year 2026 once games have been played this season)",
    )
    parser.add_argument(
        "--week", type=int, default=None,
        help="also pull the schedule + opening spreads for this week of the upcoming season "
             "(e.g. --week 1), used by the Weekly Preview page",
    )
    parser.add_argument(
        "--all-classifications", action="store_true",
        help="with --week, include every NCAA game (FCS/DII/DIII too) instead of the default "
             "FBS-only schedule (a game is kept if at least one team is FBS)",
    )
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

    if not args.skip_team_stats:
        try:
            stats_year = args.season_stats_year or PRIOR_SEASON
            team_game_stats = fetch_team_game_stats(stats_year)
            build_team_season_stats(team_game_stats, stats_year)
        except Exception as e:
            print(f"  Team season stats fetch failed: {e}")
    else:
        print("\nSkipping team season stats (--skip-team-stats)")

    if args.week:
        try:
            fetch_week_games(args.week, fbs_only=not args.all_classifications)
        except Exception as e:
            print(f"  Week {args.week} schedule/lines fetch failed: {e}")
    else:
        print(
            "\nNo --week given -- skipping this-week schedule/lines pull. "
            "Run again with e.g. --week 1 once you know which week to preview."
        )

    print("\nAll done. Restart the Streamlit app to see the refreshed data:")
    print("    streamlit run Main.py")


if __name__ == "__main__":
    main()
