"""
recruiting_vs_production.py

Analyzes the relationship between high-school recruiting star ratings and
CURRENT college production, for the top performers at each position group
(everything except Offensive Line), using the 2025 season as the production
snapshot (the same season already sitting in Roster_2024.csv /
player_stats_2024.csv per this project's naming convention).

For every player who lands in the top 25 at their position group (ranked by
a simple, traditional counting stat -- see GROUPS below), this script looks
up:

  - their high-school composite recruiting rating + stars. First choice is
    the recruitIds already attached to Roster_2024.csv, matched against a
    multi-year /recruiting/players pull (HS_YEARS below covers 2015-2026).
    BUT: roughly half of all roster rows have an empty recruitIds list (a
    CFBD linkage gap, not evidence the player was unrated), so when that ID
    lookup comes up empty this script falls back to (a) an exact
    first+last name match against the school the recruit originally
    committed to, then (b) a last-name + home-state match (only accepted
    if exactly one candidate has a matching first name, to avoid false
    positives on common surnames). match_method on each output row says
    which path found it ("id" / "name_school" / "name_state" / None).

  - IF they transferred at some point, the rating + stars they carried at
    the time they transferred to their CURRENT team, from a multi-year
    /player/portal pull (PORTAL_YEARS below, portal cycles 2018-2026).
    Matched by (first name, last name, destination team) since the portal
    payload doesn't expose a shared numeric id with roster data -- the same
    approach update_data.py already uses for the transfers_2025 files.

Raw API pulls are cached under data/analysis/_raw/ so re-running after a
matching-logic tweak doesn't require hitting the API again -- delete that
folder (or pass --refresh) to force a fresh pull.

USAGE (run locally -- needs internet + your existing CFBD_API_KEY on first
run; cached runs need no internet at all):
    python recruiting_vs_production.py [--refresh]

Outputs (written under data/analysis/):
    recruiting_vs_production_by_position.csv   - one row per top-25 player
    recruiting_vs_production_correlations.csv  - one row per position group
"""

import argparse
import ast
import json
import os
import sys
import time

import pandas as pd
import requests

BASE = "https://api.collegefootballdata.com"
REQUEST_DELAY = 0.35

SEASON = 2025
HS_YEARS = range(2015, 2027)
PORTAL_YEARS = range(2018, 2027)
TOP_N = 25
MIN_N_FOR_CORRELATION = 8  # below this, report the correlation as None (too noisy to mean anything)

RAW_DIR = "data/analysis/_raw"

GROUPS = {
    "QB":   {"tags": ["QB"],             "rank_stat": "passing_YDS",     "min_col": "passing_ATT",   "min_val": 100},
    "RB":   {"tags": ["RB"],             "rank_stat": "rushing_YDS",     "min_col": "rushing_CAR",   "min_val": 50},
    "WR":   {"tags": ["WR"],             "rank_stat": "receiving_YDS",   "min_col": "receiving_REC", "min_val": 15},
    "TE":   {"tags": ["TE"],             "rank_stat": "receiving_YDS",   "min_col": "receiving_REC", "min_val": 10},
    "DL":   {"tags": ["DL", "DT", "NT"], "rank_stat": "defensive_TFL",   "min_col": None,            "min_val": 0},
    "EDGE": {"tags": ["EDGE", "DE"],     "rank_stat": "defensive_SACKS", "min_col": None,            "min_val": 0},
    "LB":   {"tags": ["LB"],             "rank_stat": "defensive_TOT",   "min_col": None,            "min_val": 0},
    "DB":   {"tags": ["CB", "S", "DB"],  "rank_stat": "coverage_plays",  "min_col": None,            "min_val": 0},
    "K":    {"tags": ["PK"],             "rank_stat": "kicking_PTS",     "min_col": None,            "min_val": 0},
    "P":    {"tags": ["P"],              "rank_stat": "punting_YPP",     "min_col": "punting_NO",    "min_val": 20},
}


def section(title):
    print(f"\n=== {title} ===")


def s(v):
    """Stringify a pandas cell that might be NaN -- NaN is a float and is
    truthy, so `v or \"\"` does NOT catch it; this does."""
    return "" if pd.isna(v) else str(v).strip()


def get(path, **params):
    api_key = os.environ.get("CFBD_API_KEY")
    if not api_key:
        sys.exit(
            "No CFBD_API_KEY environment variable found (needed for a fresh pull).\n"
            "Set one before running this script (same one update_data.py uses).\n"
            "Get a free key at https://collegefootballdata.com/key"
        )
    resp = requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {api_key}"}, params=params, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"GET {path} params={params} -> HTTP {resp.status_code}: {resp.text[:300]}")
    time.sleep(REQUEST_DELAY)
    return resp.json()


def cached_fetch(cache_name, endpoint, years, refresh):
    path = os.path.join(RAW_DIR, cache_name)
    if not refresh and os.path.exists(path):
        section(f"Loading cached {cache_name}")
        with open(path) as f:
            return json.load(f)

    section(f"Fetching {endpoint} for {years.start}-{years.stop - 1}")
    all_records = []
    for year in years:
        try:
            recs = get(endpoint, year=year)
        except RuntimeError as e:
            print(f"  {year}: {e}")
            continue
        print(f"  {year}: {len(recs)} records")
        all_records.extend(recs)

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(path, "w") as f:
        json.dump(all_records, f)
    return all_records


def load_local_data():
    section("Loading local roster + player stats (2025 season)")
    roster = pd.read_csv("Roster_2024.csv")
    stats = pd.read_csv("player_stats_2024.csv")

    pd_col = stats["defensive_PD"].fillna(0) if "defensive_PD" in stats.columns else 0
    int_col = stats["interceptions_INT"].fillna(0) if "interceptions_INT" in stats.columns else 0
    stats["coverage_plays"] = pd_col + int_col

    df = roster.merge(stats, left_on="id", right_on="playerId", how="left", suffixes=("", "_stat"))
    print(f"  {len(df)} roster rows merged with production stats")
    return df


def build_recruiting_indices(records):
    by_id, by_name_school, by_lastname_state = {}, {}, {}
    for r in records:
        info = {
            "hs_stars": r.get("stars"),
            "hs_rating": r.get("rating"),
            "hs_year": r.get("year"),
            "hs_committedTo": r.get("committedTo"),
        }
        full_name = (r.get("name") or "").strip()
        parts = full_name.split()
        first = parts[0].lower() if parts else ""
        last = parts[-1].lower() if len(parts) > 1 else ""
        info["_first"] = first
        school = (r.get("committedTo") or "").strip().lower()
        state = (r.get("stateProvince") or "").strip().lower()

        by_id[str(r.get("id"))] = info
        by_name_school.setdefault((first, last, school), info)
        by_lastname_state.setdefault((last, state), []).append(info)
    return by_id, by_name_school, by_lastname_state


def build_portal_lookup(records):
    lookup = {}
    for r in records:
        key = (
            (r.get("firstName") or "").strip().lower(),
            (r.get("lastName") or "").strip().lower(),
            (r.get("destination") or "").strip().lower(),
        )
        lookup[key] = {
            "portal_stars": r.get("stars"),
            "portal_rating": r.get("rating"),
            "portal_year": r.get("season"),
            "portal_origin": r.get("origin"),
            "portal_transferDate": r.get("transferDate"),
        }
    return lookup


def get_hs_rating(row, by_id, by_name_school, by_lastname_state):
    try:
        ids = ast.literal_eval(row.get("recruitIds")) if isinstance(row.get("recruitIds"), str) else []
    except (ValueError, SyntaxError):
        ids = []
    for rid in ids:
        if str(rid) in by_id:
            return by_id[str(rid)], "id"

    first = s(row.get("firstName")).lower()
    last = s(row.get("lastName")).lower()
    team = s(row.get("team")).lower()
    key = (first, last, team)
    if key in by_name_school:
        return by_name_school[key], "name_school"

    state = s(row.get("homeState")).lower()
    candidates = by_lastname_state.get((last, state), [])
    name_matches = [c for c in candidates if c["_first"] == first]
    if len(name_matches) == 1:
        return name_matches[0], "name_state"

    return {"hs_stars": None, "hs_rating": None, "hs_year": None, "hs_committedTo": None}, None


def get_portal_rating(first, last, team, portal_lookup):
    key = (s(first).lower(), s(last).lower(), s(team).lower())
    return portal_lookup.get(key)


def build_analysis(df, by_id, by_name_school, by_lastname_state, portal_lookup):
    section(f"Building top-{TOP_N} tables per position group")
    all_rows = []
    corr_rows = []

    for group, cfg in GROUPS.items():
        sub = df[df["position"].isin(cfg["tags"])].copy()
        if cfg["min_col"] and cfg["min_col"] in sub.columns:
            sub = sub[sub[cfg["min_col"]].fillna(0) >= cfg["min_val"]]
        if cfg["rank_stat"] not in sub.columns:
            print(f"  {group}: rank stat {cfg['rank_stat']} missing from data -- skipping")
            continue
        sub = sub.dropna(subset=[cfg["rank_stat"]])
        sub = sub.sort_values(cfg["rank_stat"], ascending=False).head(TOP_N)
        print(f"  {group}: {len(sub)} players (ranked by {cfg['rank_stat']})")

        for rank, (_, row) in enumerate(sub.iterrows(), start=1):
            hs, method = get_hs_rating(row, by_id, by_name_school, by_lastname_state)
            portal = get_portal_rating(row.get("firstName"), row.get("lastName"), row.get("team"), portal_lookup)

            all_rows.append({
                "position_group": group,
                "rank": rank,
                "name": f"{s(row.get('firstName'))} {s(row.get('lastName'))}".strip(),
                "team": row.get("team"),
                "position_tag": row.get("position"),
                "rank_stat": cfg["rank_stat"],
                "rank_stat_value": row.get(cfg["rank_stat"]),
                "hs_stars": hs["hs_stars"],
                "hs_rating": hs["hs_rating"],
                "hs_class_year": hs["hs_year"],
                "hs_match_method": method,
                "is_transfer": portal is not None,
                "portal_stars": portal["portal_stars"] if portal else None,
                "portal_rating": portal["portal_rating"] if portal else None,
                "portal_year": portal["portal_year"] if portal else None,
                "portal_origin_team": portal["portal_origin"] if portal else None,
            })

        group_df = pd.DataFrame(all_rows)
        group_df = group_df[group_df["position_group"] == group]
        n_with_stars = group_df["hs_stars"].notna().sum()
        pearson = spearman = None
        if n_with_stars >= MIN_N_FOR_CORRELATION:
            paired = group_df[["hs_stars", "rank_stat_value"]].dropna()
            pearson = paired.corr(method="pearson").iloc[0, 1]
            spearman = paired.corr(method="spearman").iloc[0, 1]

        corr_rows.append({
            "position_group": group,
            "rank_stat": cfg["rank_stat"],
            "n_players": len(group_df),
            "n_with_hs_stars": int(n_with_stars),
            "n_transfers": int(group_df["is_transfer"].sum()),
            "pearson_r_stars_vs_production": pearson,
            "spearman_r_stars_vs_production": spearman,
        })

    return pd.DataFrame(all_rows), pd.DataFrame(corr_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="ignore cached raw pulls and re-fetch from CFBD")
    args = parser.parse_args()

    df = load_local_data()
    recruiting_records = cached_fetch("hs_recruiting.json", "/recruiting/players", HS_YEARS, args.refresh)
    portal_records = cached_fetch("portal.json", "/player/portal", PORTAL_YEARS, args.refresh)

    by_id, by_name_school, by_lastname_state = build_recruiting_indices(recruiting_records)
    portal_lookup = build_portal_lookup(portal_records)

    by_position, correlations = build_analysis(df, by_id, by_name_school, by_lastname_state, portal_lookup)

    os.makedirs("data/analysis", exist_ok=True)
    by_position.to_csv("data/analysis/recruiting_vs_production_by_position.csv", index=False)
    correlations.to_csv("data/analysis/recruiting_vs_production_correlations.csv", index=False)

    section("Done")
    print(f"  wrote data/analysis/recruiting_vs_production_by_position.csv  ({len(by_position)} rows)")
    print(f"  wrote data/analysis/recruiting_vs_production_correlations.csv ({len(correlations)} rows)")
    print("\nMatch-rate summary:")
    print(by_position.groupby("position_group")["hs_match_method"].value_counts(dropna=False).to_string())
    print("\nCorrelation summary:")
    print(correlations.to_string(index=False))


if __name__ == "__main__":
    main()
