"""
box_advanced_test.py -- scans every team stat from CFBD's advanced box score
(/game/box/advanced) and tests each one as an addition to the score model.

Sources (each used if the file exists):
  advanced_game_stats_nogt_{year}.csv  EPA/success rate by down type and play type,
                                       line yards, stuff rate, power success,
                                       second-level / open-field yards, explosiveness, pace
  havoc_game_stats_{year}.csv          havoc rate (total, front seven, DBs)
  drives_{year}.csv                    field position, scoring opportunities,
                                       points per opportunity
  (the last two come from `python update_data.py --only-test-inputs`)

Every stat becomes an opponent-adjusted rating built like the existing ones
(OFF = what an offense does, DEF = what a defense allows), using only games
before the week predicted. Each is added to the current model ONE AT A TIME
and scored out of sample (fit on one season, predict the other, both ways).

Three "random noise" controls show how much the numbers move by chance alone --
a stat only matters if it clearly beats those.

Run from the project root:  python box_advanced_test.py
Writes data/predictions/box_advanced_test.csv
"""
import os

import numpy as np
import pandas as pd

import score_model as sm

SKIP = {"offense_ppa", "offense_successRate"}           # already in the model
LABELS = {
    "plays": "Plays per game (pace)", "drives": "Drives per game", "totalPPA": "Total EPA",
    "explosiveness": "Explosiveness", "powerSuccess": "Power success (short-yardage runs)",
    "stuffRate": "Stuff rate (runs stopped at/behind line)", "lineYards": "Line yards per carry",
    "lineYardsTotal": "Line yards total", "secondLevelYards": "Second-level yards per carry",
    "secondLevelYardsTotal": "Second-level yards total", "openFieldYards": "Open-field yards per carry",
    "openFieldYardsTotal": "Open-field yards total",
    "standardDowns_ppa": "Standard downs EPA", "standardDowns_successRate": "Standard downs success rate",
    "standardDowns_explosiveness": "Standard downs explosiveness",
    "passingDowns_ppa": "Passing downs EPA", "passingDowns_successRate": "Passing downs success rate",
    "passingDowns_explosiveness": "Passing downs explosiveness",
    "rushingPlays_ppa": "Rushing EPA", "rushingPlays_totalPPA": "Rushing total EPA",
    "rushingPlays_successRate": "Rushing success rate", "rushingPlays_explosiveness": "Rushing explosiveness",
    "passingPlays_ppa": "Passing EPA", "passingPlays_totalPPA": "Passing total EPA",
    "passingPlays_successRate": "Passing success rate", "passingPlays_explosiveness": "Passing explosiveness",
    "havocRate": "Havoc rate", "frontSevenHavocRate": "Front-seven havoc rate", "dbHavocRate": "DB havoc rate",
    "fp_start": "Avg starting field position", "opp_rate": "Scoring opportunities per drive",
    "ppo": "Points per scoring opportunity",
}


def drive_stats(year):
    path = os.path.join(sm.DATA, f"drives_{year}.csv")
    if not os.path.exists(path):
        return None
    d = pd.read_csv(path)
    d = d[d["startPeriod"] <= 4]
    if "endYardsToGoal" not in d.columns:
        d["endYardsToGoal"] = d["startYardsToGoal"] - d["yards"]
    res = d["driveResult"].astype(str).str.upper()
    d["pts"] = np.where(d["scoring"].astype(str) == "True",
                        np.where(res.str.contains("FG"), 3, np.where(res == "TD", 7, 0)), 0)
    d["opp"] = (d["endYardsToGoal"] <= 40) | (d["pts"] > 0)
    g = d.groupby(["gameId", "offense"]).agg(fp_start=("startYardsToGoal", "mean"), opps=("opp", "sum"),
                                             n=("opp", "size"), opp_pts=("pts", "sum")).reset_index()
    g["opp_rate"] = g["opps"] / g["n"]
    g["ppo"] = np.where(g["opps"] > 0, g["opp_pts"] / g["opps"].clip(lower=1), np.nan)
    return g.rename(columns={"offense": "team"})[["gameId", "team", "fp_start", "opp_rate", "ppo"]]


def add_candidates(games):
    parts, cands = [], None
    for year in (sm.PRIOR, sm.SEASON):
        g = games[games.season == year]
        a = pd.read_csv(os.path.join(sm.DATA, f"advanced_game_stats_nogt_{year}.csv"))
        cols = [c for c in a.columns if c.startswith("offense_") and c not in SKIP
                and pd.api.types.is_numeric_dtype(a[c])]
        a = a[["gameId", "team"] + cols].rename(columns={c: c[len("offense_"):] for c in cols})
        g = g.merge(a, on=["gameId", "team"], how="left")
        names = [c[len("offense_"):] for c in cols]
        hv = os.path.join(sm.DATA, f"havoc_game_stats_{year}.csv")
        if os.path.exists(hv):
            h = pd.read_csv(hv)
            hc = {f"offense_{k}": k for k in ("havocRate", "frontSevenHavocRate", "dbHavocRate")
                  if f"offense_{k}" in h.columns}
            g = g.merge(h[["gameId", "team"] + list(hc)].rename(columns=hc), on=["gameId", "team"], how="left")
            names += list(hc.values())
        ds = drive_stats(year)
        if ds is not None:
            g = g.merge(ds, on=["gameId", "team"], how="left")
            names += ["fp_start", "opp_rate", "ppo"]
        cands = names if cands is None else [c for c in cands if c in names]
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    rng = np.random.default_rng(7)
    for i in range(1, 4):
        out[f"noise{i}"] = rng.normal(size=len(out))
        LABELS[f"noise{i}"] = f"Random noise (control {i})"
        cands.append(f"noise{i}")
    return out, cands


def main():
    lp, lc = sm.load_lines(sm.PRIOR), sm.load_lines(sm.SEASON)
    cls = sm.classification_map([lc, lp])
    games = pd.concat([sm.load_games(sm.PRIOR, lp), sm.load_games(sm.SEASON, lc)], ignore_index=True)
    games, cands = add_candidates(games)
    print(f"Scanning {len(cands)} stats")

    played = games.loc[games.season == sm.SEASON, "week"]
    keys = [(sm.PRIOR, w) for w in sorted(games.loc[games.season == sm.PRIOR, "week"].unique()) if w >= 2] + \
           [(sm.SEASON, w) for w in sorted(played.unique())]
    parts = []
    for season, week in keys:
        feats = sm.ratings_before(games, season, week, cls)
        if feats is None:
            continue
        wk = games[(games.season == season) & (games.week == week)]
        rows = sm.team_rows(wk[["gameId", "season", "week", "team", "opponent", "home", "conf_game", "points"]], feats)
        cur = games[(games.season == season) & (games.week < week)].copy(); cur["w"] = 1.0
        prev = games[games.season == season - 1].copy()
        prev["w"] = max(sm.PRIOR_WEIGHT - sm.PRIOR_DECAY * max(week - 1, 0), 0.05)
        hist = pd.concat([cur, prev]) if len(prev) else cur
        for k in cands:
            h = hist.dropna(subset=[k])
            if len(h) < 50:
                rows[f"exp_{k}"] = np.nan
                continue
            r, mu, hfa = sm.fit_ratings(h, k, cls)
            rows[f"exp_{k}"] = mu + hfa * rows["home"] + rows["team"].map(r["off"]).fillna(0).values \
                + rows["opponent"].map(r["def"]).fillna(0).values
        parts.append(rows)
        print(f"  ratings: {season} week {week}   ", end="\r")
    d = pd.concat(parts, ignore_index=True)
    trainable = ~((d.season == sm.PRIOR) & (d.week < sm.MIN_TRAIN_WEEK_FIRST_SEASON))
    L = pd.concat([lp, lc]).rename(columns={"id": "gameId"})[["gameId", "spread", "overUnder"]]

    def score(F):
        dd = d.dropna(subset=F)
        tm = trainable.loc[dd.index]
        res = []
        for tr, te in [(sm.PRIOR, sm.SEASON), (sm.SEASON, sm.PRIOR)]:
            trn = dd[tm & (dd.season == tr)]
            m = sm.LinearRegression().fit(trn[F], trn.points)
            t = dd[dd.season == te].copy(); t["p"] = m.predict(t[F])
            res.append(sm.to_games(t, "p"))
        r = sm.add_pick_cols(pd.concat(res).merge(L, on="gameId").dropna(subset=["spread", "overUnder"]))
        am, pm = r.home_pts - r.away_pts, r.pred_home - r.pred_away
        at, pt = r.home_pts + r.away_pts, r.pred_home + r.pred_away
        cover = am + r.spread
        ok = cover != 0
        win = np.sign(r.edge) == np.sign(cover)
        g3, bg = ok & (r.tier != "pass"), ok & (r.tier == "big_gap")
        ou = (np.sign(pt - r.overUnder) == np.sign(at - r.overUnder))[at != r.overUnder]
        return {"margin_MAE": float(np.abs(am - pm).mean()), "total_MAE": float(np.abs(at - pt).mean()),
                "winner_%": float((np.sign(am) == np.sign(pm)).mean() * 100),
                "ATS_3+gap_%": float(win[g3].mean() * 100), "ATS_3+gap_n": int(g3.sum()),
                "ATS_big_gap_%": float(win[bg].mean() * 100), "O/U_%": float(ou.mean() * 100), "games": len(r)}

    base = score(list(sm.FEATURES))
    rows = [{"stat": "CURRENT MODEL (baseline)", **base}]
    for k in cands:
        s = score(list(sm.FEATURES) + [f"exp_{k}"])
        rows.append({"stat": LABELS.get(k, k), **s})
    out = pd.DataFrame(rows)
    for c in ("margin_MAE", "total_MAE", "ATS_3+gap_%", "O/U_%"):
        out[f"{c}_chg"] = out[c] - base[c]
    out = pd.concat([out.iloc[:1], out.iloc[1:].sort_values("margin_MAE")], ignore_index=True)
    out = out[["stat", "margin_MAE", "margin_MAE_chg", "total_MAE", "total_MAE_chg", "winner_%",
               "ATS_3+gap_%", "ATS_3+gap_%_chg", "ATS_3+gap_n", "ATS_big_gap_%", "O/U_%", "games"]].round(3)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
    print("\n" + out.to_string(index=False))
    os.makedirs(sm.OUT, exist_ok=True)
    out.to_csv(os.path.join(sm.OUT, "box_advanced_test.csv"), index=False)
    print(f"\nWrote {sm.OUT}/box_advanced_test.csv")


if __name__ == "__main__":
    main()
