"""
update_data.py

Refreshes every CSV that the College Football Analytics Hub (Main.py + pages/)
actually reads, pulling fresh data from the CollegeFootballData.com (CFBD) API.

WHY: the site tracks two different kinds of "current":

    "preseason" slots (rosters, recruiting class, transfer portal, incoming
    NFL draft departures) roll forward a year at a time and keep the legacy
    file names the app already expects:

        "prior season" slot   (files with 2024 in the name, e.g. Roster_2024.csv,
                                player_stats_2024.csv)
            -> filled with the FINAL 2025 season (now complete)

        "current/upcoming" slot (files with 2025 in the name, e.g. Roster_2025.csv,
                                  Recruits_2025.csv, Draft_Position.csv, transfers_2025*.csv)
            -> filled with 2026 preseason data (roster, recruiting class, transfer
               portal, incoming NFL draft departures)

    "in-season" slots (QB stats, betting lines, team offense/defense splits)
    are pulled for BOTH seasons and saved to explicitly year-named files, so
    last year's finished season and this year's in-progress season never
    overwrite each other:

        data/QB_Stats/2025_QBstats.csv         data/QB_Stats/2026_QBstats.csv
        data/all_qb_game_stats_2025.csv        data/all_qb_game_stats_2026.csv
        data/espnBetLines_2025.csv             data/espnBetLines_2026.csv
        data/team_game_stats_2025.csv          data/team_game_stats_2026.csv
        data/team_season_stats_2025.csv        data/team_season_stats_2026.csv
        data/advanced_game_stats_2025.csv      data/advanced_game_stats_2026.csv   (+ _nogt_ versions)
        data/returning_production_2025.csv     data/returning_production_2026.csv
        data/talent_2025.csv                   data/talent_2026.csv

    The pages that use these (QB Comparison, Betting Results, Weekly Preview)
    have a season picker and read whichever year's file the person selects.
    Every "in-season" pull walks week 1 upward and simply stops when a week
    comes back empty, so re-running this script partway through the 2026
    season automatically picks up whatever new games have been played since
    the last run -- no flags needed to say "we're on week N now".

USAGE (run this locally -- it needs real internet access):
    pip install requests pandas
    python update_data.py                       # pulls everything (both seasons' in-season
                                                    # stats, current preseason rosters, etc.)
    python update_data.py --week 1               # also pulls Week 1's 2026 schedule + opening
                                                    # spreads (FBS games only by default -- add
                                                    # --all-classifications for every NCAA game)
    python update_data.py --seasons 2026          # only refresh in-season stats (QB, betting
                                                    # lines, team stats) for 2026 -- skips
                                                    # re-pulling last year's already-final numbers
    python update_data.py --skip-qb               # skip the (slower) per-week QB pull
    python update_data.py --skip-lines            # skip betting lines
    python update_data.py --skip-team-stats       # skip team season offense/defense stats
    python update_data.py --only-model-inputs     # only pull advanced game stats, returning
                                                    # production and talent (for score_model.py)
    python update_data.py --skip-model-inputs     # skip those

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

PRIOR_SEASON = 2025      # last fully-completed season -> fills "*_2024"-named preseason slots
UPCOMING_SEASON = 2026   # season currently being played -> fills "*_2025"-named preseason slots

# In-season data (QB stats, betting lines, team stats) is pulled for each
# year in SEASONS, each saved to its own year-named file. Defaults to both
# years; overridden at the bottom of main() by --seasons if that's passed.
SEASONS = [PRIOR_SEASON, UPCOMING_SEASON]

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
# 7) QB stats -- a per-week/per-game log across every week, plus a season-
#    total snapshot used for the QB comparison radar chart. Pulled once per
#    season in SEASONS (2025 final + 2026 in-progress) and saved to files
#    named for that season, so the QB Comparison page can offer a season
#    picker without one year's numbers ever clobbering the other's.
#
#    For a season still in progress, weeks that haven't been played yet come
#    back empty and are skipped -- so this naturally pulls "every game played
#    so far" without needing to know which week the season is currently on.
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


def fetch_qb_stats_for_season(year, max_week=15):
    section(f"QB game-by-game stats ({year}, all conferences)")
    all_rows = []
    for week in range(1, max_week + 1):
        try:
            games_json = get("/games/players", year=year, week=week, category="passing")
        except RuntimeError as e:
            print(f"  week {week}: {e}")
            continue
        if not games_json:
            print(f"  week {week}: no data (not played yet, or season ended before this week)")
            continue
        week_rows = extract_qb_week(games_json, week)
        print(f"  week {week}: {len(week_rows)} QB performances")
        all_rows.extend(week_rows)

    weekly_df = pd.DataFrame(all_rows)
    if weekly_df.empty:
        print(f"  No QB data available yet for {year} -- skipping file writes for this season.")
        return

    weekly_df["completion_pct"] = weekly_df["comp"] / weekly_df["att"]
    save(weekly_df, f"data/all_qb_game_stats_{year}.csv")

    # Season snapshot: one row per QB, aggregated across all weeks played so far.
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
    save(season_df, f"data/QB_Stats/{year}_QBstats.csv")


def fetch_qb_stats():
    for year in SEASONS:
        fetch_qb_stats_for_season(year)


# ---------------------------------------------------------------------------
# 8) Betting lines -- ESPN Bet lines, pulled for each season in SEASONS and
#    saved to a year-named file so 2025's finished lines and 2026's
#    in-progress lines stay separate.
# ---------------------------------------------------------------------------

def fetch_lines_for_season(year):
    section(f"Betting lines ({year}, ESPN Bet preferred)")
    games = get("/lines", year=year, seasonType="regular")

    rows = []
    provider_counts = {}
    skipped_no_lines = 0
    for g in games:
        game_lines = g.get("lines", [])
        if not game_lines:
            skipped_no_lines += 1
            continue
        for line in game_lines:
            provider_counts[line.get("provider")] = provider_counts.get(line.get("provider"), 0) + 1
        # Prefer ESPN Bet when it's posted for this game, same as the weekly
        # schedule pull does -- but don't drop the game entirely just because
        # ESPN Bet specifically isn't listed for it (a provider going quiet
        # for a stretch of games, or CFBD renaming/rotating its primary book,
        # shouldn't zero out a whole season of betting data).
        chosen = next((l for l in game_lines if l.get("provider") == "ESPN Bet"), None)
        chosen = chosen or game_lines[0]
        row = {k: v for k, v in g.items() if k != "lines"}
        row.update(chosen)
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        print(f"  No lines available yet for {year} -- skipping file write for this season.")
        if skipped_no_lines:
            print(f"  ({skipped_no_lines} games had no lines posted at all for {year})")
        return
    save(df, f"data/espnBetLines_{year}.csv")
    espn_bet_rows = (df["provider"] == "ESPN Bet").sum()
    if espn_bet_rows < len(df):
        other = sorted(provider_counts.items(), key=lambda kv: -kv[1])
        print(
            f"  Note: only {espn_bet_rows}/{len(df)} games had an ESPN Bet line for {year} -- "
            f"the rest fell back to another provider. Providers seen: {other}"
        )


def fetch_lines():
    for year in SEASONS:
        fetch_lines_for_season(year)


# ---------------------------------------------------------------------------
# 9) Team game & season stats (offense + defense splits) -- powers the
#     "Weekly Preview" page's stat comparison (yards/gm, points/gm, 3rd down
#     %, yards & points allowed, turnovers forced, turnover margin). Pulled
#     for each season in SEASONS so the page can prefer in-season 2026
#     numbers once a team has played enough games, falling back to 2025.
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
            print(f"  week {week}: no data (not played yet, or season ended before this week)")
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


def fetch_team_stats_all_seasons():
    for year in SEASONS:
        try:
            long_df = fetch_team_game_stats(year)
            build_team_season_stats(long_df, year)
        except Exception as e:
            print(f"  Team season stats fetch failed for {year}: {e}")


# ---------------------------------------------------------------------------
# 9b) Model inputs for score_model.py -- per-game advanced stats (EPA/PPA,
#     success rate, explosiveness, havoc...), returning production and team
#     talent. Pulled for each season in SEASONS.
#
#     advanced_game_stats_{year}.csv        every play counted
#     advanced_game_stats_nogt_{year}.csv   garbage time removed (usually the
#                                           better signal for predicting)
#     returning_production_{year}.csv       % of last year's production back
#     talent_{year}.csv                     247 roster talent composite
# ---------------------------------------------------------------------------

def fetch_advanced_game_stats(year, max_week=16):
    for exclude_gt, suffix in ((False, ""), (True, "_nogt")):
        label = "garbage time removed" if exclude_gt else "all plays"
        section(f"Advanced game stats ({year}, {label})")
        frames = []
        for week in range(1, max_week + 1):
            try:
                rows = get("/stats/game/advanced", year=year, week=week, seasonType="regular",
                           excludeGarbageTime=str(exclude_gt).lower())
            except RuntimeError as e:
                print(f"  week {week}: {e}")
                continue
            if not rows:
                print(f"  week {week}: no data (not played yet, or no games that week)")
                continue
            df = pd.json_normalize(rows, sep="_")
            if "week" not in df.columns:
                df["week"] = week
            frames.append(df)
            print(f"  week {week}: {len(df)} team-game rows")
        if frames:
            save(pd.concat(frames, ignore_index=True), f"data/advanced_game_stats{suffix}_{year}.csv")
        else:
            print("  nothing returned -- skipping save")


def fetch_returning_and_talent(year):
    section(f"Returning production + team talent ({year})")
    try:
        ret = pd.json_normalize(get("/player/returning", year=year), sep="_")
        save(ret, f"data/returning_production_{year}.csv")
    except Exception as e:
        print(f"  returning production fetch failed: {e}")
    try:
        tal = pd.json_normalize(get("/talent", year=year), sep="_")
        save(tal, f"data/talent_{year}.csv")
    except Exception as e:
        print(f"  talent fetch failed: {e}")


def fetch_model_inputs():
    for year in SEASONS:
        try:
            fetch_advanced_game_stats(year)
        except Exception as e:
            print(f"  Advanced game stats fetch failed for {year}: {e}")
        fetch_returning_and_talent(year)


# ---------------------------------------------------------------------------
# 10) Weekly schedule + opening spreads -- one week at a time, on demand
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
    parser.add_argument("--skip-qb", action="store_true", help="skip per-week QB stats pull (both seasons)")
    parser.add_argument("--skip-lines", action="store_true", help="skip betting lines pull (both seasons)")
    parser.add_argument("--skip-team-stats", action="store_true", help="skip team season offense/defense stats pull (both seasons)")
    parser.add_argument("--skip-model-inputs", action="store_true",
                        help="skip advanced game stats / returning production / talent (used by score_model.py)")
    parser.add_argument("--only-model-inputs", action="store_true",
                        help="ONLY pull advanced game stats / returning production / talent, then stop")
    parser.add_argument(
        "--week", type=int, default=None,
        help="also pull the schedule + opening spreads for this week of the upcoming season "
             "(e.g. --week 5), used by the Weekly Preview page",
    )
    parser.add_argument(
        "--all-classifications", action="store_true",
        help="with --week, include every NCAA game (FCS/DII/DIII too) instead of the default "
             "FBS-only schedule (a game is kept if at least one team is FBS)",
    )
    parser.add_argument(
        "--seasons", type=int, nargs="+", default=None, metavar="YEAR",
        help="which season(s) to pull in-season stats (QB stats, betting lines, team season "
             f"stats) for. Defaults to both {PRIOR_SEASON} and {UPCOMING_SEASON}. Pass just the "
             f"current season to skip re-pulling last year's already-final numbers, "
             f"e.g. --seasons {UPCOMING_SEASON}",
    )
    args = parser.parse_args()

    global SEASONS
    if args.seasons:
        SEASONS = args.seasons

    if args.only_model_inputs:
        fetch_model_inputs()
        print("\nDone (model inputs only).")
        return

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

    if not args.skip_team_stats:
        fetch_team_stats_all_seasons()
    else:
        print("\nSkipping team season stats (--skip-team-stats)")

    if not args.skip_model_inputs:
        fetch_model_inputs()
    else:
        print("\nSkipping model inputs (--skip-model-inputs)")

    if args.week:
        try:
            fetch_week_games(args.week, fbs_only=not args.all_classifications)
        except Exception as e:
            print(f"  Week {args.week} schedule/lines fetch failed: {e}")
    else:
        print(
            "\nNo --week given -- skipping this-week schedule/lines pull. "
            "Run again with e.g. --week N once you know which week to preview."
        )

    print("\nAll done. Restart the Streamlit app to see the refreshed data:")
    print("    streamlit run Main.py")


if __name__ == "__main__":
    main()
