"""
export_web_data.py -- turns the CSVs in data/ into the JSON files the website reads.

Run it after your normal weekly update:
    python update_data.py
    python score_model.py
    python export_web_data.py

It writes everything to web/public/data/. Commit and push that folder (GitHub
Desktop picks it up like any other change) and Vercel rebuilds the site.

All the number-crunching that used to happen inside the Streamlit pages lives
here now, so the website itself only displays results. The formulas are the
same ones the Streamlit pages used, with three fixes noted inline (search for
"FIX:").
"""
import glob
import json
import math
import os
import re
import shutil
from datetime import datetime, timezone

import numpy as np
import pandas as pd

SEASON = 2026            # current season
PRIOR_SEASON = 2025      # last completed season
ROSTER_PRIOR = "data/Roster_2024.csv"     # final roster of last season
ROSTER_CURRENT = "data/Roster_2025.csv"   # roster for the current season
RECRUITS = "data/Recruits_2025.csv"
DRAFT = "data/Draft_Position.csv"
PLAYER_STATS = "data/player_stats_2024.csv"   # last season's player stats
TRANSFERS = "data/transfers_2025.csv"
TRANSFER_STATS = "data/transfers_2025_stats.csv"
PRED = "data/predictions"
OUT = os.environ.get("CFB_WEB_OUT", "web/public/data")
BREAK_EVEN = 52.4
TEAM_PAGE_LEVELS = ("fbs", "fcs")         # which schools get their own team page


# ----------------------------------------------------------------------------- helpers
def clean(o):
    """Make pandas/numpy values JSON-safe (NaN -> null, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if math.isnan(f) or math.isinf(f) else round(f, 4)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    if o is pd.NA or o is pd.NaT:
        return None
    return o


def write(path, obj):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(clean(obj), f, separators=(",", ":"), ensure_ascii=False)


def slugify(name):
    s = str(name).lower().replace("&", "").replace("'", "").replace(".", "")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def num(x, default=None):
    try:
        f = float(x)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def read(path, **kw):
    return pd.read_csv(path, **kw) if os.path.exists(path) else None


# ----------------------------------------------------------------------------- positions & scoring
POSITION_MAP = {
    "QB": "QB", "RB": "RB", "TB": "RB", "HB": "RB", "FB": "RB",
    "WR": "WR", "TE": "TE",
    "OL": "OL", "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL", "OT": "OL", "G": "OL",
    "DL": "DL", "DE": "DL", "DT": "DL", "NT": "DL", "EDGE": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB",
    "DB": "DB", "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "SAF": "DB",
    "K": "K", "PK": "K", "P": "P", "KR": "KR", "PR": "PR", "LS": "LS",
}


def pos_group(pos):
    if not isinstance(pos, str) or not pos.strip():
        return "OTHER"
    p = pos.strip().upper()
    return POSITION_MAP.get(p, p)


def g(row, col):
    v = row.get(col, 0)
    return 0 if v is None or (isinstance(v, float) and math.isnan(v)) else v


def impact_score(row):
    """Usage-weighted impact score (Team Comparison / Weekly Preview pages)."""
    grp = pos_group(row.get("position", ""))
    if grp == "QB":
        return (g(row, "passing_YDS") + 20 * g(row, "passing_TD") - 45 * g(row, "passing_INT")
                + g(row, "rushing_YDS") + 20 * g(row, "rushing_TD") + 5 * g(row, "passing_YPA"))
    if grp == "RB":
        return g(row, "rushing_YDS") + 20 * g(row, "rushing_TD") + 0.5 * g(row, "receiving_YDS") + 10 * g(row, "receiving_TD")
    if grp in ("WR", "TE"):
        return g(row, "receiving_YDS") + 20 * g(row, "receiving_TD")
    if grp == "DL":
        return g(row, "defensive_TOT") + 4 * g(row, "defensive_SACKS") + 2 * g(row, "defensive_TFL") + 6 * g(row, "defensive_TD")
    if grp == "LB":
        return (g(row, "defensive_TOT") + 3 * g(row, "defensive_SACKS") + 1.5 * g(row, "defensive_TFL")
                + 6 * g(row, "defensive_TD") + 3 * g(row, "interceptions_INT"))
    if grp == "DB":
        return g(row, "defensive_TOT") + 3 * g(row, "interceptions_INT") + 10 * g(row, "interceptions_TD") + 1.5 * g(row, "defensive_PD")
    if grp == "K":
        return g(row, "kicking_PTS")
    if grp == "P":
        return g(row, "punting_NO") * g(row, "punting_YPP")
    if grp == "KR":
        return g(row, "kickReturns_YDS") + 20 * g(row, "kickReturns_TD")
    if grp == "PR":
        return g(row, "puntReturns_YDS") + 20 * g(row, "puntReturns_TD")
    return 0


# Production score (Roster Analysis page)
PRODUCTION = {
    "QB": (["passing_YDS", "passing_TD", "rushing_YDS", "rushing_TD"], [1, 20, 1, 6]),
    "RB": (["rushing_YDS", "rushing_TD", "receiving_YDS", "receiving_TD"], [1, 6, 1, 6]),
    "WR": (["receiving_YDS", "receiving_TD", "receiving_REC", "rushing_YDS"], [1, 6, 2, 1]),
    "TE": (["receiving_YDS", "receiving_TD", "receiving_REC"], [1, 6, 2]),
    "DL": (["defensive_SACKS", "defensive_TFL", "defensive_TOT"], [3, 2, 1]),
    "LB": (["defensive_TOT", "defensive_SACKS", "defensive_TFL"], [1, 3, 2]),
    "DB": (["defensive_TOT", "defensive_PD", "interceptions_INT"], [1, 2, 5]),
    "K": (["kicking_FGM", "kicking_XPM", "kicking_PTS"], [3, 1, 1]),
}


def production_score(stats, grp):
    if grp not in PRODUCTION:
        return pd.Series(0.0, index=stats.index)
    cols, w = PRODUCTION[grp]
    total = pd.Series(0.0, index=stats.index)
    for c, wt in zip(cols, w):
        if c in stats.columns:
            total += pd.to_numeric(stats[c], errors="coerce").fillna(0) * wt
    return total


# ----------------------------------------------------------------------------- load
def main():
    if os.path.exists(OUT):
        try:
            shutil.rmtree(OUT)   # start clean so last week's files don't linger
        except OSError:
            pass                 # can't delete here: files are overwritten instead
    os.makedirs(OUT, exist_ok=True)

    teams_csv = pd.read_csv("data/teams.csv")
    teams_csv["slug"] = teams_csv["school"].map(slugify)
    team_by_school = {r["school"]: r for r in teams_csv.to_dict("records")}

    def team_ref(school):
        t = team_by_school.get(school)
        if t is None:
            return {"school": school, "slug": None, "abbr": school[:4].upper(), "color": "#1E2A36",
                    "alt": "#8D99A8", "logo": None}
        level = str(t.get("classification") or "").lower()
        return {"school": school, "slug": t["slug"] if level in TEAM_PAGE_LEVELS else None,
                "abbr": t.get("abbreviation") if isinstance(t.get("abbreviation"), str) else school[:4].upper(),
                "color": t.get("color") if isinstance(t.get("color"), str) else "#1E2A36",
                "alt": t.get("alternateColor") if isinstance(t.get("alternateColor"), str) else "#8D99A8",
                "logo": t.get("logos") if isinstance(t.get("logos"), str) else None}

    # every school, compact, used for logos/colors everywhere on the site
    write("teams.json", {r["school"]: dict({k: v for k, v in team_ref(r["school"]).items() if k != "school"},
                                           conference=r.get("conference"), level=r.get("classification"),
                                           mascot=r.get("mascot"))
                         for r in teams_csv.to_dict("records")})

    roster_prior = pd.read_csv(ROSTER_PRIOR)
    roster_cur = pd.read_csv(ROSTER_CURRENT)
    for r in (roster_prior, roster_cur):
        r["id"] = r["id"].astype(str)
        r["grp"] = r["position"].map(pos_group)
    pstats = pd.read_csv(PLAYER_STATS)
    pstats["playerId"] = pstats["playerId"].astype(str)
    pstats = pstats.drop_duplicates("playerId")
    stat_cols = [c for c in pstats.columns if c != "playerId"]
    for c in stat_cols:
        pstats[c] = pd.to_numeric(pstats[c], errors="coerce").fillna(0)
    recruits = pd.read_csv(RECRUITS)
    recruits["athleteId"] = recruits["athleteId"].astype("Int64").astype(str)
    draft = pd.read_csv(DRAFT)
    draft["collegeAthleteId"] = draft["collegeAthleteId"].astype(str)
    transfers = pd.read_csv(TRANSFERS).dropna(subset=["origin", "destination"])
    transfers["playerId"] = transfers["playerId"].astype(str)
    transfers["rating"] = pd.to_numeric(transfers["rating"], errors="coerce")
    tstats = read(TRANSFER_STATS)

    # ------------------------------------------------------------------ team season stats + returning production
    season_frames = {}
    for yr in (SEASON, PRIOR_SEASON):
        df = read(f"data/team_season_stats_{yr}.csv")
        if df is not None:
            season_frames[yr] = df.set_index("team")

    def team_stats(team):
        for yr in (SEASON, PRIOR_SEASON):
            df = season_frames.get(yr)
            if df is not None and team in df.index:
                row = df.loc[team]
                if yr == SEASON and num(row.get("games"), 0) < 1:
                    continue
                return {"season": yr, **row.to_dict()}
        return None

    prior_with_stats = roster_prior.merge(pstats, left_on="id", right_on="playerId", how="left")
    for c in stat_cols:
        prior_with_stats[c] = prior_with_stats[c].fillna(0)
    prior_with_stats["impact"] = prior_with_stats.apply(impact_score, axis=1).clip(lower=0)
    cur_ids_by_team = roster_cur.groupby("team")["id"].apply(set).to_dict()
    prior_with_stats["returning"] = [pid in cur_ids_by_team.get(t, ()) for pid, t in
                                     zip(prior_with_stats["id"], prior_with_stats["team"])]

    def returning_production(team):
        last = prior_with_stats[prior_with_stats["team"] == team]
        if last.empty:
            return None
        total = last["impact"].sum()
        return {"pct": (last.loc[last["returning"], "impact"].sum() / total * 100) if total else None,
                "returning_players": int(last["returning"].sum()), "total_players": int(len(last))}

    # ------------------------------------------------------------------ predictions / picks
    tier_hist = pd.read_csv(os.path.join(PRED, "tier_history.csv"))
    tier_hist["by_season"] = tier_hist["by_season"].apply(json.loads)
    tiers = {r["tier"]: r for r in tier_hist.to_dict("records")}
    acc_path = os.path.join(PRED, "model_accuracy.json")
    acc = json.load(open(acc_path, encoding="utf-8")) if os.path.exists(acc_path) else None
    qbc_path = os.path.join(PRED, "qb_check.json")
    qbc = json.load(open(qbc_path, encoding="utf-8")) if os.path.exists(qbc_path) else None

    lines_cur = pd.read_csv(f"data/espnBetLines_{SEASON}.csv")
    log = pd.read_csv(os.path.join(PRED, f"picks_log_{SEASON}.csv"))
    log = log.merge(lines_cur[["id", "homeScore", "awayScore"]].rename(columns={"id": "gameId"}), on="gameId", how="left")
    cover = (log["homeScore"] - log["awayScore"]) + log["spread"]
    played = log["homeScore"].notna()
    pick_home = log["pick_side"] == "home"
    log["result"] = np.where(~played, "Pending", np.where(cover == 0, "Push",
                             np.where((cover > 0) == pick_home, "Win", "Loss")))
    log["units"] = log["result"].map({"Win": 100 / 110, "Loss": -1.0, "Push": 0.0, "Pending": 0.0})
    graded = log.set_index("gameId")["result"].to_dict()
    done = log[log["result"] != "Pending"]

    def record(df):
        w, l = int((df["result"] == "Win").sum()), int((df["result"] == "Loss").sum())
        p = int((df["result"] == "Push").sum())
        return {"w": w, "l": l, "p": p, "pct": (100 * w / (w + l)) if w + l else None,
                "units": float(df["units"].sum())}

    week_files = {}
    for f in glob.glob(os.path.join(PRED, f"week_*_picks_{SEASON}.csv")):
        m = re.search(r"week_(\d+)_picks", f)
        if m:
            week_files[int(m.group(1))] = f
    weeks = sorted(week_files)
    sched = {}
    for f in glob.glob(f"data/schedule/week_*_games_{SEASON}.csv"):
        s = pd.read_csv(f)
        for r in s.to_dict("records"):
            sched[r["gameId"]] = r

    week_index = []
    all_games = {}
    for wk in weeks:
        picks = pd.read_csv(week_files[wk])
        games = []
        for r in picks.to_dict("records"):
            gid = r["gameId"]
            sc = sched.get(gid, {})
            game = {
                "id": gid, "week": wk, "kick": r["startDate"],
                "home": team_ref(r["homeTeam"]), "away": team_ref(r["awayTeam"]),
                "homeConf": r.get("homeConference"), "awayConf": r.get("awayConference"),
                "venue": sc.get("venue"), "neutral": bool(r.get("neutral")) if r.get("neutral") == r.get("neutral") else False,
                "confGame": bool(r.get("conf_game")) if r.get("conf_game") == r.get("conf_game") else False,
                "spread": num(r.get("spread")), "spreadOpen": num(r.get("spreadOpen")),
                "overUnder": num(r.get("overUnder")),
                "predHome": num(r.get("pred_home")), "predAway": num(r.get("pred_away")),
                "modelSpread": num(r.get("model_spread")), "modelTotal": num(r.get("model_total")),
                "edge": num(r.get("edge")), "tier": r.get("tier") if isinstance(r.get("tier"), str) else None,
                "pickSide": r.get("pick_side") if isinstance(r.get("pick_side"), str) else None,
                "pick": r.get("pick_line") if isinstance(r.get("pick_line"), str) else None,
                "result": graded.get(gid) if graded.get(gid) in ("Win", "Loss", "Push") else None,
                "why": json.loads(r["why"]) if isinstance(r.get("why"), str) else [],
                "watch": json.loads(r["watch"]) if isinstance(r.get("watch"), str) else [],
                "homeQb": {"name": r.get("home_qb"), "starts": num(r.get("home_qb_starts"))} if isinstance(r.get("home_qb"), str) else None,
                "awayQb": {"name": r.get("away_qb"), "starts": num(r.get("away_qb_starts"))} if isinstance(r.get("away_qb"), str) else None,
            }
            # score if played
            lr = lines_cur[lines_cur["id"] == gid]
            if not lr.empty and pd.notna(lr.iloc[0]["homeScore"]):
                game["homeScore"], game["awayScore"] = lr.iloc[0]["homeScore"], lr.iloc[0]["awayScore"]
            games.append(game)
            detail = dict(game)
            detail["homeStats"] = team_stats(r["homeTeam"])
            detail["awayStats"] = team_stats(r["awayTeam"])
            detail["homeReturning"] = returning_production(r["homeTeam"])
            detail["awayReturning"] = returning_production(r["awayTeam"])
            all_games[gid] = detail
        games.sort(key=lambda x: x["kick"])
        write(f"weeks/{wk}.json", {"week": wk, "season": SEASON, "games": games})
        week_index.append({"week": wk, "games": len(games),
                           "watchlist": sum(1 for x in games if x["tier"] == "fav_value"),
                           "edges": sum(1 for x in games if x["tier"] in ("fav_value", "big_gap", "lean"))})
    # ------------------------------------------------------------------ moneyline value (moneyline_value.py)
    ml_model_path = os.path.join(PRED, "ml_model.json")
    ml_log_path = os.path.join(PRED, f"ml_log_{SEASON}.csv")
    if os.path.exists(ml_model_path):
        ml_model = json.load(open(ml_model_path, encoding="utf-8"))
        scores = lines_cur.set_index("id")[["homeTeam", "homeScore", "awayScore"]]
        mlog = read(ml_log_path)
        graded = []
        if mlog is not None and len(mlog):
            for r in mlog.to_dict("records"):
                res, profit, score = "Pending", 0.0, None
                if r["gameId"] in scores.index and pd.notna(scores.loc[r["gameId"], "homeScore"]):
                    hs, as_ = scores.loc[r["gameId"], "homeScore"], scores.loc[r["gameId"], "awayScore"]
                    us, them = (hs, as_) if r["side"] == "home" else (as_, hs)
                    score = f"{int(us)}-{int(them)}"
                    dec = 1 + r["ml"] / 100
                    res, profit = ("Win", dec - 1) if us > them else ("Loss", -1.0) if us < them else ("Push", 0.0)
                graded.append({"week": int(r["week"]), "id": r["gameId"], "kick": r["startDate"], "team": team_ref(r["team"]),
                               "opp": r["opponent"], "home": r["side"] == "home", "line": num(r["line"]), "ml": int(r["ml"]),
                               "pMkt": num(r["p_mkt"]), "pModel": num(r["p_model"]), "pBlend": num(r["p_blend"]),
                               "ev": num(r["ev"]), "result": res, "profit": round(profit, 3), "score": score})
        done_ml = [x for x in graded if x["result"] in ("Win", "Loss")]
        live = {"bets": len(done_ml), "won": sum(1 for x in done_ml if x["result"] == "Win"),
                "units": round(sum(x["profit"] for x in done_ml), 2),
                "roi": round(100 * sum(x["profit"] for x in done_ml) / len(done_ml), 1) if done_ml else None,
                "pending": sum(1 for x in graded if x["result"] == "Pending")}
        ml_weeks = {}
        for wk in weeks:
            fpath = os.path.join(PRED, f"week_{wk}_ml_value_{SEASON}.csv")
            if os.path.exists(fpath):
                v = pd.read_csv(fpath)
                v = v[v["value"].astype(str) == "True"]
                ml_weeks[str(wk)] = [x for x in graded if x["week"] == wk] or [
                    {"week": wk, "id": r["gameId"], "kick": r["startDate"], "team": team_ref(r["team"]), "opp": r["opponent"],
                     "home": r["side"] == "home", "line": num(r["line"]), "ml": int(r["ml"]), "pMkt": num(r["p_mkt"]),
                     "pModel": num(r["p_model"]), "pBlend": num(r["p_blend"]), "ev": num(r["ev"]), "result": "Pending",
                     "profit": 0.0, "score": None} for r in v.to_dict("records")]
        write("ml.json", {"model": ml_model, "live": live, "weeks": ml_weeks, "log": sorted(graded, key=lambda x: x["kick"], reverse=True)})
        by_game = {x["id"]: x for wk_rows in ml_weeks.values() for x in wk_rows}
        for gid, d in all_games.items():
            if gid in by_game:
                d["mlValue"] = by_game[gid]

    for gid, d in all_games.items():
        write(f"games/{gid}.json", d)

    # track record
    chart = done.sort_values(["week", "gameId"])
    series = {}
    for key, mask in (("watchlist", chart["tier"] == "fav_value"), ("big_gap", chart["tier"] == "big_gap"),
                      ("all", chart["tier"] != "pass")):
        s = chart[mask].groupby("week")["units"].sum().cumsum()
        series[key] = [{"week": int(w), "units": round(float(u), 2)} for w, u in s.items()]
    pick_log = log[log["tier"] != "pass"].sort_values(["week", "gameId"], ascending=[False, True])
    write("track_record.json", {
        "season": SEASON, "breakEven": BREAK_EVEN,
        "tiers": [{k: t[k] for k in ("tier", "label", "wins", "losses", "pushes", "win_pct", "units", "by_season", "description")}
                  for t in tiers.values()],
        "accuracy": acc, "qbCheck": qbc,
        "season_records": {"watchlist": record(done[done["tier"] == "fav_value"]),
                           "big_gap": record(done[done["tier"] == "big_gap"]),
                           "lean": record(done[done["tier"] == "lean"]),
                           "watchlist_live": record(done[(done["tier"] == "fav_value") & (done["source"] == "live")]),
                           "all": record(done[done["tier"] != "pass"])},
        "series": series,
        "log": [{"week": int(r["week"]), "id": r["gameId"], "away": r["awayTeam"], "home": r["homeTeam"],
                 "pick": r["pick_line"], "tier": r["tier"], "gap": abs(num(r["edge"], 0)),
                 "score": (f"{int(r['awayScore'])}-{int(r['homeScore'])}" if pd.notna(r["homeScore"]) else None),
                 "result": r["result"], "source": r["source"]} for r in pick_log.to_dict("records")],
    })

    # ------------------------------------------------------------------ betting results (per season)
    betting_by_team = {}
    bet_seasons = []
    for yr in (SEASON, PRIOR_SEASON):
        df = read(f"data/espnBetLines_{yr}.csv")
        if df is None:
            continue
        bet_seasons.append(yr)
        for c in ("homeScore", "awayScore", "spread", "homeMoneyline", "awayMoneyline"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        fs = df["formattedSpread"].astype(str)
        df["favorite"] = np.where([a.startswith(str(h)) for a, h in zip(fs, df["homeTeam"])], df["homeTeam"],
                                  np.where([a.startswith(str(w)) for a, w in zip(fs, df["awayTeam"])], df["awayTeam"], None))
        df["mag"] = df["spread"].abs()

        def categorize(r):
            if pd.isna(r["homeScore"]) or pd.isna(r["awayScore"]) or pd.isna(r["spread"]) or r["favorite"] is None:
                return None
            fav_home = r["favorite"] == r["homeTeam"]
            margin = (r["homeScore"] - r["awayScore"]) if fav_home else (r["awayScore"] - r["homeScore"])
            if margin < 0:
                return "Underdog Win"
            return "Favorite Covered" if margin > r["mag"] else "Favorite Won, Did Not Cover"
        df["category"] = df.apply(categorize, axis=1)

        played_df = df.dropna(subset=["homeScore", "awayScore"])
        rows = []
        for side, opp in (("home", "away"), ("away", "home")):
            rows.append(pd.DataFrame({
                "team": played_df[f"{side}Team"], "opponent": played_df[f"{opp}Team"], "week": played_df["week"],
                "is_home": side == "home", "team_score": played_df[f"{side}Score"], "opp_score": played_df[f"{opp}Score"],
                "ml": played_df[f"{side}Moneyline"], "favorite": played_df["favorite"], "mag": played_df["mag"]}))
        L = pd.concat(rows, ignore_index=True)
        L["role"] = np.where(L["favorite"].isna(), "Pick'em", np.where(L["favorite"] == L["team"], "Favorite", "Underdog"))
        L["margin"] = L["team_score"] - L["opp_score"]
        L["result"] = np.where(L["margin"] > 0, "W", np.where(L["margin"] < 0, "L", "T"))
        L["ats_margin"] = np.where(L["role"] == "Favorite", L["margin"] - L["mag"],
                                   np.where(L["role"] == "Underdog", L["margin"] + L["mag"], L["margin"]))
        L["ats"] = np.where(L["ats_margin"] > 0, "Covered", np.where(L["ats_margin"] < 0, "No Cover", "Push"))

        def ml_profit(r):  # per $1
            if pd.isna(r["ml"]):
                return 0.0
            if r["result"] != "W":
                return -1.0
            return 100 / abs(r["ml"]) if r["ml"] < 0 else r["ml"] / 100
        L["ml_profit"] = L.apply(ml_profit, axis=1)
        L["ats_profit"] = np.where(L["ats"] == "Push", 0.0, np.where(L["ats"] == "Covered", 100 / 110, -1.0))

        def summarize(gdf):
            c, n, p = int((gdf["ats"] == "Covered").sum()), int((gdf["ats"] == "No Cover").sum()), int((gdf["ats"] == "Push").sum())
            return {"games": int(len(gdf)), "w": int((gdf["result"] == "W").sum()), "l": int((gdf["result"] == "L").sum()),
                    "cover": c, "noCover": n, "push": p, "pct": round(c / (c + n) * 100, 1) if c + n else 0.0}

        rankings = []
        for team, gdf in L.groupby("team"):
            rankings.append({"team": team, "all": summarize(gdf),
                             "fav": summarize(gdf[gdf["role"] == "Favorite"]),
                             "dog": summarize(gdf[gdf["role"] == "Underdog"])})
            betting_by_team.setdefault(team, {})[yr] = {
                "summary": summarize(gdf), "fav": summarize(gdf[gdf["role"] == "Favorite"]),
                "dog": summarize(gdf[gdf["role"] == "Underdog"]),
                "mlProfit": float(gdf["ml_profit"].sum()), "atsProfit": float(gdf["ats_profit"].sum()),
                "log": [{"week": int(r["week"]), "opp": r["opponent"], "home": bool(r["is_home"]), "role": r["role"],
                         "line": r["mag"], "score": f"{int(r['team_score'])}-{int(r['opp_score'])}", "result": r["result"],
                         "ats": r["ats"], "atsMargin": r["ats_margin"]} for r in gdf.sort_values("week").to_dict("records")]}

        ups = L[(L["role"] == "Underdog") & (L["result"] == "W")].sort_values("mag", ascending=False)
        per_game = L[(L["is_home"]) & (L["ats"] != "Push")].copy()
        per_game["abs"] = per_game["ats_margin"].abs()

        def game_rows(d, margin_col):
            return [{"week": int(r["week"]), "away": r["opponent"], "home": r["team"],
                     "score": f"{int(r['opp_score'])}-{int(r['team_score'])}", "margin": round(float(r[margin_col]), 1)}
                    for r in d.head(15).to_dict("records")]

        # FIX: the Streamlit simulator charged a lost bet for every game without a final
        # score (including all unplayed 2026 games). Only graded games count here.
        cat = df[df["category"].notna()].copy()

        def fav_profit(r):
            if r["category"] == "Underdog Win":
                return -1.0
            ml = r["homeMoneyline"] if r["favorite"] == r["homeTeam"] else r["awayMoneyline"]
            if pd.isna(ml):
                return 0.0
            return 100 / abs(ml) if ml < 0 else ml / 100

        def dog_profit(r):
            if r["category"] != "Underdog Win":
                return -1.0
            ml = r["awayMoneyline"] if r["favorite"] == r["homeTeam"] else r["homeMoneyline"]
            if pd.isna(ml):
                return 0.0
            return 100 / abs(ml) if ml < 0 else ml / 100

        write(f"betting/{yr}.json", {
            "season": yr, "final": yr != SEASON, "gamesAnalyzed": int(len(played_df)),
            "rankings": rankings,
            "upsets": [{"week": int(r["week"]), "team": r["team"], "opp": r["opponent"], "home": bool(r["is_home"]),
                        "line": r["mag"], "score": f"{int(r['team_score'])}-{int(r['opp_score'])}"} for r in ups.head(15).to_dict("records")],
            "nailBiters": game_rows(per_game.sort_values("abs"), "abs"),
            "bigCovers": game_rows(per_game[per_game["ats_margin"] > 0].sort_values("ats_margin", ascending=False), "ats_margin"),
            "outcomes": cat["category"].value_counts().to_dict(),
            "favProfit": float(cat.apply(fav_profit, axis=1).sum()), "dogProfit": float(cat.apply(dog_profit, axis=1).sum()),
            "graded": int(len(cat)),
            "games": [{"week": int(r["week"]), "home": r["homeTeam"], "away": r["awayTeam"], "homeScore": r["homeScore"],
                       "awayScore": r["awayScore"], "line": r["formattedSpread"] if isinstance(r["formattedSpread"], str) else None,
                       "category": r["category"]} for r in df.sort_values(["week", "startDate"]).to_dict("records")],
        })

    # ------------------------------------------------------------------ roster turnover (per team)
    page_teams = sorted(set(teams_csv.loc[teams_csv["classification"].isin(TEAM_PAGE_LEVELS), "school"])
                        & set(roster_cur["team"].dropna()))

    # Team Comparison "net impact" model
    drafted = roster_prior.merge(draft, left_on="id", right_on="collegeAthleteId", how="inner", suffixes=("", "_draft"))
    drafted["overall"] = pd.to_numeric(drafted["overall"], errors="coerce")
    drafted["impact"] = (300 - drafted["overall"]).clip(lower=1).fillna(0)
    moved = roster_prior[["id", "team", "position", "firstName", "lastName"]].merge(
        roster_cur[["id", "team"]], on="id", how="inner", suffixes=("_prior", "_cur"))
    moved = moved[moved["team_prior"] != moved["team_cur"]].copy()
    moved = moved.merge(pstats, left_on="id", right_on="playerId", how="left")
    for c in stat_cols:
        moved[c] = moved[c].fillna(0)
    moved["impact"] = moved.apply(impact_score, axis=1)
    gone_ids = set(drafted["id"]) | set(moved["id"]) | set(roster_cur["id"])
    graduated = prior_with_stats[~prior_with_stats["id"].isin(gone_ids)].copy()
    graduated["impact"] = graduated.apply(impact_score, axis=1)
    rec_on_roster = roster_cur.merge(recruits, left_on="id", right_on="athleteId", how="inner", suffixes=("", "_rec"))
    rec_on_roster["impact"] = pd.to_numeric(rec_on_roster["rating"], errors="coerce").fillna(0) * 100

    # FIX: the Streamlit Team Comparison never counted transfers out as losses (those rows
    # had no "team" column, so the team filter dropped them). They count here.
    losses = pd.concat([drafted[["team", "position", "impact"]],
                        moved.rename(columns={"team_prior": "team"})[["team", "position", "impact"]],
                        graduated[["team", "position", "impact"]]], ignore_index=True)
    adds = pd.concat([moved.rename(columns={"team_cur": "team"})[["team", "position", "impact"]],
                      pd.DataFrame({"team": rec_on_roster["committedTo"], "position": rec_on_roster["position"],
                                    "impact": rec_on_roster["impact"]})],
                     ignore_index=True)
    losses["grp"], adds["grp"] = losses["position"].map(pos_group), adds["position"].map(pos_group)
    UNITS = {"Offense": ["QB", "RB", "WR", "TE", "OL"], "Defense": ["DL", "LB", "DB"], "Special Teams": ["K", "P", "KR", "PR", "LS"]}
    loss_tbl = losses.groupby(["team", "grp"])["impact"].sum()
    add_tbl = adds.groupby(["team", "grp"])["impact"].sum()

    def unit_impact(team):
        lt = loss_tbl.get(team, pd.Series(dtype=float)) if team in loss_tbl.index.get_level_values(0) else pd.Series(dtype=float)
        at = add_tbl.get(team, pd.Series(dtype=float)) if team in add_tbl.index.get_level_values(0) else pd.Series(dtype=float)
        net = at.reindex(at.index.union(lt.index), fill_value=0) - lt.reindex(at.index.union(lt.index), fill_value=0)
        out = {u: float(net[net.index.isin(p)].sum()) for u, p in UNITS.items()}
        out["Total"] = float(net.sum())
        out["byPosition"] = {k: float(v) for k, v in net.items()}
        return out

    # Roster Analysis production breakdown.
    # FIX: positions are grouped (CB/S -> DB, DE/DT/EDGE -> DL, PK -> K, OT/G/C -> OL) so
    # safeties, corners, edge rushers and kickers are counted; before, only players listed
    # exactly as "DB"/"DL"/"K" were.
    prior_prod = roster_prior.merge(pstats, left_on="id", right_on="playerId", how="inner")
    prior_prod["prod"] = 0.0
    for grp in PRODUCTION:
        m = prior_prod["grp"] == grp
        prior_prod.loc[m, "prod"] = production_score(prior_prod[m], grp)
    tr_prod = transfers.merge(pstats, on="playerId", how="inner")
    tr_prod["grp"] = tr_prod["position_y"].map(pos_group)
    tr_prod["prod"] = 0.0
    for grp in PRODUCTION:
        m = tr_prod["grp"] == grp
        tr_prod.loc[m, "prod"] = production_score(tr_prod[m], grp)

    portal_rows = []
    rin = transfers.groupby("destination")["rating"].sum()
    rout = transfers.groupby("origin")["rating"].sum()
    for team in sorted(set(transfers["origin"]) | set(transfers["destination"])):
        portal_rows.append({"team": team, "in": float(rin.get(team, 0)), "out": float(rout.get(team, 0)),
                            "net": float(rin.get(team, 0) - rout.get(team, 0)),
                            "nIn": int((transfers["destination"] == team).sum()),
                            "nOut": int((transfers["origin"] == team).sum())})

    units_all = {}
    directory = []
    for team in page_teams:
        ref = team_ref(team)
        cur = roster_cur[roster_cur["team"] == team]
        prior = roster_prior[roster_prior["team"] == team]
        t_out = transfers[transfers["origin"] == team]
        t_in = transfers[transfers["destination"] == team]
        t_draft = draft[draft["collegeTeam"] == team].merge(
            roster_prior[["id", "firstName", "lastName", "position"]], left_on="collegeAthleteId", right_on="id",
            how="left", suffixes=("_draft", ""))
        t_rec = recruits[recruits["committedTo"] == team]

        cur_ids = set(cur["id"])
        pp = prior_prod[prior_prod["team"] == team]
        tp = tr_prod[tr_prod["destination"] == team]
        production = []
        for grp in PRODUCTION:
            ret = float(pp.loc[(pp["grp"] == grp) & pp["id"].isin(cur_ids), "prod"].sum())
            lost = float(pp.loc[(pp["grp"] == grp) & ~pp["id"].isin(cur_ids), "prod"].sum())
            inc = float(tp.loc[tp["grp"] == grp, "prod"].sum())
            if ret or lost or inc:
                production.append({"pos": grp, "returning": ret, "lost": lost, "incoming": inc})

        units = unit_impact(team)
        units_all[team] = {k: v for k, v in units.items() if k != "byPosition"}

        # transfer portal detail
        flows_in = t_in.groupby("origin").size().sort_values(ascending=False)
        flows_out = t_out.groupby("destination").size().sort_values(ascending=False)
        diff = []
        if tstats is not None:
            tin_s, tout_s = tstats[tstats["destination"] == team], tstats[tstats["origin"] == team]
            for cat, stats in {"Passing": ["passing_YDS", "passing_TD", "passing_COMPLETIONS"],
                               "Rushing": ["rushing_YDS", "rushing_TD", "rushing_CAR"],
                               "Receiving": ["receiving_YDS", "receiving_TD", "receiving_REC"],
                               "Defense": ["defensive_TOT", "defensive_TFL", "defensive_SACKS", "defensive_PD"],
                               "Returns": ["kickReturns_YDS", "puntReturns_YDS"], "Kicking": ["kicking_PTS"]}.items():
                for s in stats:
                    if s in tstats.columns:
                        diff.append({"cat": cat, "stat": s, "in": float(tin_s[s].sum()), "out": float(tout_s[s].sum())})

        def tplayer(r, other_col):
            p = {"name": f"{r.get('firstName_y') or r.get('firstName_x')} {r.get('lastName_y') or r.get('lastName_x')}",
                 "pos": r.get("position_y") or r.get("position_x"), "team": r.get(other_col),
                 "stars": num(r.get("stars")), "rating": num(r.get("rating"))}
            if tstats is not None:
                srow = tstats[(tstats["playerId"].astype(str) == r["playerId"]) & (tstats[other_col] == r[other_col])]
                if not srow.empty:
                    s = srow.iloc[0]
                    grp = pos_group(p["pos"])
                    keys = (["passing_COMPLETIONS", "passing_ATT", "passing_YDS", "passing_TD", "passing_INT"] if grp == "QB"
                            else ["rushing_CAR", "rushing_YDS", "rushing_TD", "receiving_REC", "receiving_YDS", "receiving_TD"]
                            if grp in ("RB", "WR", "TE") else
                            ["defensive_TOT", "defensive_TFL", "defensive_SACKS", "interceptions_INT", "defensive_PD"]
                            if grp in ("DL", "LB", "DB") else [])
                    p["stats"] = {k: num(s.get(k), 0) for k in keys}
            return p

        bet = betting_by_team.get(team, {})
        sched_rows = lines_cur[(lines_cur["homeTeam"] == team) | (lines_cur["awayTeam"] == team)].sort_values("startDate")
        schedule = []
        for r in sched_rows.to_dict("records"):
            home = r["homeTeam"] == team
            gid = r["id"]
            schedule.append({"id": gid, "week": int(r["week"]), "kick": r["startDate"], "home": home,
                             "opp": r["awayTeam"] if home else r["homeTeam"],
                             "us": num(r["homeScore"] if home else r["awayScore"]),
                             "them": num(r["awayScore"] if home else r["homeScore"]),
                             "line": r["formattedSpread"] if isinstance(r["formattedSpread"], str) else None,
                             "hasPage": gid in all_games})
        for gid, d in all_games.items():   # upcoming games not yet in the lines file
            if (d["home"]["school"] == team or d["away"]["school"] == team) and not any(s["id"] == gid for s in schedule):
                home = d["home"]["school"] == team
                schedule.append({"id": gid, "week": d["week"], "kick": d["kick"], "home": home,
                                 "opp": d["away"]["school"] if home else d["home"]["school"], "us": None, "them": None,
                                 "line": None, "hasPage": True})
        schedule.sort(key=lambda s: s["kick"])

        team_doc = {
            "team": ref, "school": team, "conference": team_by_school[team].get("conference"),
            "mascot": team_by_school[team].get("mascot"), "level": team_by_school[team].get("classification"),
            "stats": team_stats(team), "returning": returning_production(team), "schedule": schedule,
            "overview": {"roster": int(len(cur)), "recruits": int(len(t_rec)), "transfersIn": int(len(t_in)),
                         "transfersOut": int(len(t_out)), "drafted": int(len(t_draft)),
                         "byPosition": cur["position"].value_counts().to_dict()},
            "production": production, "units": units,
            "drafted": sorted([{"name": f"{r['firstName']} {r['lastName']}" if isinstance(r.get("firstName"), str) else None,
                                "pick": int(r["overall"]), "pos": r.get("position_draft")} for r in t_draft.to_dict("records")],
                              key=lambda x: x["pick"]),
            "transfersOut": [tplayer(r, "destination") for r in t_out.to_dict("records")],
            "transfersIn": [tplayer(r, "origin") for r in t_in.to_dict("records")],
            "recruits": [{"name": r["name"], "pos": r["position"], "stars": num(r["stars"]), "rating": num(r["rating"]),
                          "home": ", ".join(str(x) for x in (r.get("city"), r.get("stateProvince")) if isinstance(x, str))}
                         for r in t_rec.sort_values("rating", ascending=False).to_dict("records")],
            "roster": [{"name": f"{r['firstName']} {r['lastName']}", "pos": r["position"], "grp": r["grp"],
                        "year": num(r.get("year")), "height": num(r.get("height")), "weight": num(r.get("weight")),
                        "jersey": num(r.get("jersey"))} for r in cur.sort_values(["grp", "lastName"]).to_dict("records")],
            "portal": {"in": {"n": int(len(t_in)), "total": float(t_in["rating"].sum()), "avg": num(t_in["rating"].mean())},
                       "out": {"n": int(len(t_out)), "total": float(t_out["rating"].sum()), "avg": num(t_out["rating"].mean())},
                       "flowsIn": [{"team": k, "n": int(v)} for k, v in flows_in.items()],
                       "flowsOut": [{"team": k, "n": int(v)} for k, v in flows_out.items()],
                       "differential": diff},
            "betting": bet,
        }
        write(f"teams/{ref['slug']}.json", team_doc)
        st = team_stats(team)
        directory.append({**ref, "conference": team_by_school[team].get("conference"),
                          "level": team_by_school[team].get("classification"),
                          "record": None})
    write("team_directory.json", directory)
    write("compare.json", {"units": units_all,
                           "stats": {t: team_stats(t) for t in page_teams},
                           "returning": {t: returning_production(t) for t in page_teams}})
    write("portal.json", sorted(portal_rows, key=lambda r: -r["net"]))

    # ------------------------------------------------------------------ quarterbacks
    FBS_CONF = {"SEC", "Big Ten", "Big 12", "ACC", "Pac-12", "American Athletic", "Sun Belt", "Mid-American",
                "Mountain West", "Conference USA", "FBS Independents"}
    qb_seasons = []
    for yr, roster_path in ((SEASON, ROSTER_CURRENT), (PRIOR_SEASON, ROSTER_PRIOR)):
        qpath = f"data/QB_Stats/{yr}_QBstats.csv"
        if not os.path.exists(qpath):
            continue
        qb_seasons.append(yr)
        df = pd.read_csv(qpath)
        roster = pd.read_csv(roster_path)
        rq = roster[roster["position"] == "QB"][["id", "firstName", "lastName", "team"]].copy()
        rq["full_name"] = rq["firstName"] + " " + rq["lastName"]
        pool = df.merge(rq.drop_duplicates("id").rename(columns={"id": "player_id", "team": "roster_team"}),
                        on="player_id", how="inner")
        # radar normalisation across every QB in the season file (same as before)
        norm = {}
        for col in ("att", "qbr", "yds", "td", "int"):
            v = df[col].astype(float)
            if col == "int":
                v = v.max() - v
            span = v.max() - v.min()
            norm[col] = dict(zip(df["player_id"], ((v - v.min()) / span * 100) if span else v * 0 + 50))
        games = read(f"data/all_qb_game_stats_{yr}.csv")
        # where each QB throws: six zones (short/deep x left/middle/right) from update_data.py
        ZONES = ["deep left", "deep middle", "deep right", "short left", "short middle", "short right"]
        locs, zone_avg = {}, {}
        ldf = read(f"data/QB_Stats/{yr}_pass_locations.csv")
        if ldf is not None and not ldf.empty:
            ldf["player_id"] = pd.to_numeric(ldf["player_id"], errors="coerce")
            for pid, grp in ldf.groupby("player_id"):
                z = {r["zone"]: r for r in grp.to_dict("records")}
                zones = {}
                for name in ZONES:
                    r = z.get(name, {})
                    att, comp = num(r.get("zone_att"), 0), num(r.get("zone_comp"), 0)
                    zones[name] = {"att": int(att), "comp": int(comp), "int": int(num(r.get("zone_int"), 0)),
                                   "ypa": num(r.get("zone_ypa")), "adot": num(r.get("zone_adot")),
                                   "success": num(r.get("zone_success"))}
                unk = z.get("unknown", {})
                locs[int(pid)] = {"zones": zones, "unknown": int(num(unk.get("zone_att"), 0))}
            fbs_rows = ldf[ldf["conference"].isin(FBS_CONF) & (ldf["zone"] != "unknown")]
            total = fbs_rows["zone_att"].sum()
            for name, grp in fbs_rows.groupby("zone"):
                a = grp["zone_att"].sum()
                w = grp.dropna(subset=["zone_ypa"])
                zone_avg[name] = {"pct": float(grp["zone_comp"].sum() / a * 100) if a else None,
                                  "share": float(a / total * 100) if total else None,
                                  "ypa": float((w["zone_ypa"] * w["zone_att"]).sum() / w["zone_att"].sum()) if len(w) and w["zone_att"].sum() else None}
        qbs = []
        for r in pool.to_dict("records"):
            att = num(r["att"], 0)
            pid = r["player_id"]
            gl = []
            if games is not None:
                for x in games[games["player_id"] == pid].sort_values("week").to_dict("records"):
                    gl.append({"week": int(x["week"]), "opp": x["opponent"], "comp": num(x["comp"]), "att": num(x["att"]),
                               "yds": num(x["yds"]), "td": num(x["td"]), "int": num(x["int"]), "qbr": num(x["qbr"])})
            qbs.append({"id": pid, "name": r["player_name"], "team": r["roster_team"], "statTeam": r["team"],
                        "conf": r["conference"], "fbs": r["conference"] in FBS_CONF,
                        "att": att, "comp": num(r["comp"]), "yds": num(r["yds"]), "td": num(r["td"]), "int": num(r["int"]),
                        "qbr": num(r["qbr"]),
                        "compPct": (num(r["comp"], 0) / att * 100) if att else None,
                        "ypa": (num(r["yds"], 0) / att) if att else None,
                        "rating": ((8.4 * num(r["yds"], 0) + 330 * num(r["td"], 0) + 100 * num(r["comp"], 0) - 200 * num(r["int"], 0)) / att) if att else None,
                        "radar": {c: num(norm[c].get(pid)) for c in norm}, "games": gl,
                        "locations": locs.get(int(pid))})
        write(f"qbs/{yr}.json", {"season": yr, "final": yr != SEASON, "gamesPlayed": int(df["week"].max()),
                                 "zoneAvg": zone_avg, "qbs": qbs})

    # ------------------------------------------------------------------ meta
    latest = weeks[-1] if weeks else None
    write("meta.json", {"season": SEASON, "priorSeason": PRIOR_SEASON, "weeks": week_index, "currentWeek": latest,
                        "bettingSeasons": bet_seasons, "qbSeasons": qb_seasons,
                        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                        "teamCount": len(page_teams), "breakEven": BREAK_EVEN})
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    print(f"Wrote {n} files ({size / 1e6:.1f} MB) to {OUT}/ -- weeks {weeks}, {len(page_teams)} team pages, "
          f"{len(all_games)} game pages.")


if __name__ == "__main__":
    main()
