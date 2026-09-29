"""
feature_search.py -- tests which extra variables improve the score model.

Every candidate is a pre-game variable (home minus away where it applies). Each
one is tested out of sample (fit on one season, predict the other, both ways):

  1. Stats model:  margin ~ baseline + candidate      -> does accuracy improve?
  2. Vs Vegas:     (margin - Vegas line) ~ candidate  -> does it explain what Vegas misses?

Run from the project root:  python feature_search.py
Writes data/predictions/feature_search.csv
"""
import os
import numpy as np
import pandas as pd
import score_model as sm
from score_model import LinearRegression

DATA = "data"


# ------------------------------------------------------------- rating variants
def form_stats(games):
    """Weighted season-to-date per-game form (not opponent adjusted)."""
    d = games.assign(to_margin=games["opp_turnovers"] - games["turnovers"])
    w = d["w"]
    agg = pd.DataFrame({
        "to_margin": (d["to_margin"] * w).groupby(d["team"]).sum(),
        "3dm": (d["thirdDownMade"] * w).groupby(d["team"]).sum(),
        "3da": (d["thirdDownAtt"] * w).groupby(d["team"]).sum(),
        "d3dm": (d["opp_3dm"] * w).groupby(d["team"]).sum(),
        "d3da": (d["opp_3da"] * w).groupby(d["team"]).sum(),
        "wsum": w.groupby(d["team"]).sum(),
    })
    k = 2.0  # shrink toward league norms with 2 pseudo-games
    out = pd.DataFrame(index=agg.index)
    out["to_margin"] = agg["to_margin"] / (agg["wsum"] + k)
    out["third_pct"] = (agg["3dm"] + 0.4 * 12 * k) / (agg["3da"] + 12 * k)
    out["def_third_pct"] = (agg["d3dm"] + 0.4 * 12 * k) / (agg["d3da"] + 12 * k)
    return out


def ratings_variant(hist, cls, target, cap=None):
    h = hist.copy()
    if cap is not None:  # cap blowouts: points above (opp_points + cap) don't count
        h[target] = np.minimum(h[target], h["opp_points"] + cap)
    r, mu, hfa = sm.fit_ratings(h, target, cls)
    return r, mu, hfa


def weekly_features(games, cls, season, week):
    cur = games[(games.season == season) & (games.week < week)].copy(); cur["w"] = 1.0
    prev = games[games.season == season - 1].copy()
    prev["w"] = max(sm.PRIOR_WEIGHT - sm.PRIOR_DECAY * max(week - 1, 0), 0.05)
    hist = pd.concat([cur, prev]) if len(prev) else cur
    out = {}
    out["base"] = ratings_variant(hist, cls, "points")
    out["yds"] = ratings_variant(hist, cls, "totalYards")
    out["cap21"] = ratings_variant(hist, cls, "points", cap=21)
    # recent form: current-season games weighted up for the last 3 weeks
    rec = hist.copy()
    rec.loc[(rec.season == season) & (rec.week >= week - 3), "w"] *= 3
    out["recent"] = ratings_variant(rec, cls, "points")
    # current season only (no prior-season carryover)
    out["cur_only"] = ratings_variant(cur, cls, "points") if len(cur) > 50 else out["base"]
    # "luck": points scored minus what yards alone would predict
    h2 = hist.copy()
    h2["pts_over_yds"] = h2["points"] - h2["totalYards"] * (h2["points"].sum() / h2["totalYards"].sum())
    out["luck"] = ratings_variant(h2, cls, "pts_over_yds")
    form = form_stats(hist)
    return out, form


def exp_margin(r, home_t, away_t, home_flag):
    rt, mu, hfa = r
    off, de = rt["off"], rt["def"]
    g = lambda s, t: s.reindex(t).fillna(0).values
    return (mu + hfa * home_flag + g(off, home_t) + g(de, away_t)) - \
           (mu - hfa * home_flag + g(off, away_t) + g(de, home_t)), \
           (2 * mu + g(off, home_t) + g(de, away_t) + g(off, away_t) + g(de, home_t))


# ------------------------------------------------------------------ QB data
def qb_table():
    rows = []
    for y in (2025, 2026):
        q = pd.read_csv(os.path.join(DATA, f"all_qb_game_stats_{y}.csv"))
        q["season"] = y
        rows.append(q)
    return pd.concat(rows)


def qb_features(q, team, season, week):
    """Pre-game QB features for `team`.

    Careful: "starter = QB with the most attempts in THIS game" leaks the result
    (a starter benched in a blowout makes the backup the 'starter'). So a QB
    change is only flagged when last game's starter threw zero passes in this
    game (he sat out, which is normally known before kickoff). Experience and
    yards/attempt are for the incumbent (last game's starter), from earlier games only.
    """
    t = q[q.team == team]
    before = t[(t.season < season) | ((t.season == season) & (t.week < week))]
    now = t[(t.season == season) & (t.week == week)]
    if now.empty or before.empty:
        return np.nan, np.nan, np.nan
    last_game = before[(before.season == before.season.iloc[-1]) & (before.week == before.week.iloc[-1])]
    incumbent = last_game.sort_values("att").player_id.iloc[-1]
    changed = float(incumbent not in set(now.player_id))
    inc = before[before.player_id == incumbent]
    starts = min(int((inc.att >= 10).sum()), 15)
    ypa = (inc.yds.sum() + 6.8 * 60) / (inc.att.sum() + 60)  # shrunk to ~league avg
    return changed, starts, ypa


# ------------------------------------------------------------- build dataset
def build():
    lp, lc = sm.load_lines(2025), sm.load_lines(2026)
    cls = sm.classification_map([lc, lp])
    games = pd.concat([sm.load_games(2025, lp), sm.load_games(2026, lc)], ignore_index=True)
    lines = pd.concat([lp, lc]).rename(columns={"id": "gameId"})
    lines["date"] = pd.to_datetime(lines["startDate"]).dt.tz_convert("America/New_York").dt.normalize()
    teams = pd.read_csv(os.path.join(DATA, "teams.csv")).drop_duplicates("school").set_index("school")
    q = qb_table()

    # rest days: previous game date per team from the lines file
    tg = pd.concat([lines[["gameId", "season", "date", "homeTeam"]].rename(columns={"homeTeam": "team"}),
                    lines[["gameId", "season", "date", "awayTeam"]].rename(columns={"awayTeam": "team"})])
    tg = tg.sort_values("date")
    tg["rest"] = tg.groupby(["season", "team"])["date"].diff().dt.days
    rest = tg.set_index(["gameId", "team"])["rest"]

    rows = []
    keys = [(2025, w) for w in range(2, 17)] + [(2026, w) for w in range(1, 5)]
    for season, week in keys:
        feats, form = weekly_features(games, cls, season, week)
        wk = games[(games.season == season) & (games.week == week)]
        h = wk[wk.home >= 0].drop_duplicates("gameId")
        a = wk[wk.gameId.isin(h.gameId) & ~wk.index.isin(h.index)]
        g = h[["gameId", "season", "week", "team", "opponent", "home", "points", "opp_points"]] \
            .rename(columns={"team": "homeTeam", "opponent": "awayTeam", "points": "home_pts", "opp_points": "away_pts"})
        g = g[g.gameId.isin(a.gameId)]
        for name, r in feats.items():
            m, t = exp_margin(r, g.homeTeam, g.awayTeam, g.home.values)
            g[f"m_{name}"] = m
            if name in ("base", "cap21", "recent"):
                g[f"t_{name}"] = t
        f = form
        for c in ("to_margin", "third_pct", "def_third_pct"):
            g[f"d_{c}"] = g.homeTeam.map(f[c]).fillna(0).values - g.awayTeam.map(f[c]).fillna(0).values
        # QB
        for side in ("home", "away"):
            qb = [qb_features(q, t, season, week) for t in g[f"{side}Team"]]
            g[[f"{side}_qb_change", f"{side}_qb_starts", f"{side}_qb_ypa"]] = np.array(qb, dtype=float).reshape(-1, 3)
        rows.append(g)
    d = pd.concat(rows, ignore_index=True)
    d = d.merge(lines[["gameId", "spread", "spreadOpen", "overUnder", "overUnderOpen", "date"]], on="gameId", how="left")

    # rest / bye
    d["home_rest"] = [rest.get((gid, t), np.nan) for gid, t in zip(d.gameId, d.homeTeam)]
    d["away_rest"] = [rest.get((gid, t), np.nan) for gid, t in zip(d.gameId, d.awayTeam)]
    d["d_rest"] = (d.home_rest.clip(upper=14) - d.away_rest.clip(upper=14))
    d["d_bye"] = (d.home_rest >= 12).astype(float) - (d.away_rest >= 12).astype(float)

    # travel / time zones / altitude
    lat, lon = teams["location.latitude"], teams["location.longitude"]
    hl, hL = d.homeTeam.map(lat), d.homeTeam.map(lon)
    al, aL = d.awayTeam.map(lat), d.awayTeam.map(lon)
    R = 3959
    p1, p2 = np.radians(hl), np.radians(al)
    dist = 2 * R * np.arcsin(np.sqrt(np.sin((p2 - p1) / 2) ** 2 +
                                     np.cos(p1) * np.cos(p2) * np.sin(np.radians(aL - hL) / 2) ** 2))
    d["travel_miles"] = (dist * (d.home > 0)).fillna(0) / 1000
    d["tz_shift"] = (((hL - aL) / 15).round() * (d.home > 0)).fillna(0)       # + = away team travelled east
    d["west_to_east"] = (d.tz_shift >= 2).astype(float)
    d["altitude"] = (d.homeTeam.map(teams["location.elevation"]).fillna(0) * (d.home > 0)) / 1000

    # game-type flags
    cls_s = pd.Series(cls)
    d["home_fbs"] = (d.homeTeam.map(cls_s) == "fbs").astype(float)
    d["away_fbs"] = (d.awayTeam.map(cls_s) == "fbs").astype(float)
    conf = teams["conference"]
    d["conf_game"] = (d.homeTeam.map(conf) == d.awayTeam.map(conf)).astype(float)

    # QB differentials
    d["d_qb_change"] = d.home_qb_change.fillna(0) - d.away_qb_change.fillna(0)
    d["d_qb_starts"] = d.home_qb_starts.fillna(d.home_qb_starts.median()) - d.away_qb_starts.fillna(d.away_qb_starts.median())
    d["d_qb_ypa"] = d.home_qb_ypa.fillna(6.8) - d.away_qb_ypa.fillna(6.8)
    # market movement
    d["line_move"] = -(d.spread - d.spreadOpen)          # + = money moved toward home
    d["total_move"] = d.overUnder - d.overUnderOpen
    d["margin"] = d.home_pts - d.away_pts
    d["total"] = d.home_pts + d.away_pts
    return d


# ------------------------------------------------------------------ evaluation
def cv(d, target, X, model="ols"):
    """Two-way season CV. Returns out-of-sample predictions."""
    pred = pd.Series(np.nan, index=d.index)
    for tr_s, te_s in [(2025, 2026), (2026, 2025)]:
        tr = d[(d.season == tr_s) & ~((d.season == 2025) & (d.week < 4))]
        te = d[d.season == te_s]
        if not X:
            pred[te.index] = tr[target].mean(); continue
        m = LinearRegression().fit(tr[X], tr[target])
        pred[te.index] = m.predict(te[X])
    return pred


CANDIDATES = {
    "Opponent-adj yards margin": ["m_yds"],
    "Blowout-capped ratings (cap 21)": ["m_cap21"],
    "Recent form (last 3 wks x3)": ["m_recent"],
    "Current season only ratings": ["m_cur_only"],
    "Points-vs-yards 'luck'": ["m_luck"],
    "Turnover margin": ["d_to_margin"],
    "3rd down % (off & def)": ["d_third_pct", "d_def_third_pct"],
    "QB change (incumbent sat out)": ["d_qb_change"],
    "Incumbent QB experience (starts)": ["d_qb_starts"],
    "Incumbent QB yards/att": ["d_qb_ypa"],
    "Rest days": ["d_rest"],
    "Coming off bye": ["d_bye"],
    "Travel distance": ["travel_miles"],
    "Time zones crossed": ["tz_shift"],
    "West-to-east trip (2+ zones)": ["west_to_east"],
    "Altitude": ["altitude"],
    "Conference game": ["conf_game"],
    "FBS/FCS flags": ["home_fbs", "away_fbs"],
    "Line movement (open->close)": ["line_move"],
}


def main():
    d = build()
    d = d[d.week >= 2].copy()
    lined = d.spread.notna() & d.overUnder.notna()
    d["vegas_margin"] = -d.spread
    d["resid"] = d.margin - d.vegas_margin
    d["t_resid"] = d.total - d.overUnder
    base = ["m_base", "home"]
    res = []
    b_pred = cv(d, "margin", base)
    b_mae = (d.margin - b_pred).abs()[lined].mean()
    b_win = (np.sign(b_pred) == np.sign(d.margin))[lined].mean()
    for name, X in CANDIDATES.items():
        dd = d.copy()
        dd[X] = dd[X].fillna(0)
        p = cv(dd, "margin", base + X)
        mae = (dd.margin - p).abs()[lined].mean()
        win = (np.sign(p) == np.sign(dd.margin))[lined].mean()
        # vs Vegas: does the feature (plus our model's disagreement) predict the residual?
        dl = dd[lined].copy()
        dl["model_edge"] = cv(dd, "margin", base)[lined] - dl.vegas_margin
        rp = cv(dl, "resid", X + ["model_edge"])
        rp0 = cv(dl, "resid", ["model_edge"])
        v_mae = (dl.resid - rp).abs().mean()
        v0 = (dl.resid - rp0).abs().mean()
        ok = dl.resid != 0
        ats = (np.sign(rp) == np.sign(dl.resid))[ok].mean()
        ats0 = (np.sign(rp0) == np.sign(dl.resid))[ok].mean()
        res.append({"variable": name,
                    "margin_MAE": round(mae, 2), "vs_baseline": round(mae - b_mae, 2),
                    "winner_pct": round(win * 100, 1),
                    "vegas_resid_MAE_change": round(v_mae - v0, 2),
                    "ATS_pct": round(ats * 100, 1), "ATS_vs_model_only": round((ats - ats0) * 100, 1),
                    "n_nonmissing": int(d[X[0]].notna().sum())})
    out = pd.DataFrame(res).sort_values("vs_baseline")
    print(f"Baseline stats model: margin MAE {b_mae:.2f}, winner {b_win:.1%};"
          f" Vegas margin MAE {(d.margin - d.vegas_margin).abs()[lined].mean():.2f}  (n={lined.sum()})")
    pd.set_option("display.width", 220)
    print(out.to_string(index=False))
    os.makedirs("data/predictions", exist_ok=True)
    out.to_csv("data/predictions/feature_search.csv", index=False)
    return d


if __name__ == "__main__":
    main()
