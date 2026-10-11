"""
split_test.py -- does splitting the offense/defense ratings into RUSHING and
PASSING (and adding explosive plays) improve the score model?

Each candidate gets its own opponent-adjusted rating, built exactly like the
existing ones (ridge fit, last season at reduced weight, only games before the
week being predicted):

    stat(team vs opp) = avg + home_edge + OFF[team] + DEF[opp]

so DEF is "rushing yards allowed", "passing EPA allowed", etc., adjusted for
who each defense played.

Candidates (each is tested only if its data exists):
  rush / pass EPA per play, rush / pass success rate   -- advanced_game_stats_nogt_{year}.csv (garbage time removed)
  rushing yards / passing yards                        -- team_game_stats_{year}.csv (rushingYards, netPassingYards)
  20+ yard plays (rush, pass, total)                   -- explosive_plays_{year}.csv

To pull the yards split and explosive plays:  python update_data.py --only-test-inputs

Same out-of-sample test as advanced_test.py: fit on one season, predict the
other, both directions.
Run from the project root:  python split_test.py
Writes data/predictions/split_test.csv
"""
import os

import numpy as np
import pandas as pd

import score_model as sm

ADV = {"offense_rushingPlays_ppa": "rppa", "offense_passingPlays_ppa": "pppa",
       "offense_rushingPlays_successRate": "rsr", "offense_passingPlays_successRate": "psr"}


def add_columns(games):
    parts = []
    for year in (sm.PRIOR, sm.SEASON):
        g = games[games.season == year]
        a = pd.read_csv(os.path.join(sm.DATA, f"advanced_game_stats_nogt_{year}.csv"))
        g = g.merge(a[["gameId", "team"] + list(ADV)].rename(columns=ADV), on=["gameId", "team"], how="left")
        t = pd.read_csv(os.path.join(sm.DATA, f"team_game_stats_{year}.csv"))
        if {"rushingYards", "netPassingYards"} <= set(t.columns):
            g = g.merge(t[["gameId", "team", "rushingYards", "netPassingYards"]].rename(
                columns={"rushingYards": "ryds", "netPassingYards": "pyds"}), on=["gameId", "team"], how="left")
        ex = os.path.join(sm.DATA, f"explosive_plays_{year}.csv")
        if os.path.exists(ex):
            e = pd.read_csv(ex)[["gameId", "team", "explosive_rush", "explosive_pass"]]
            e["explosive"] = e["explosive_rush"] + e["explosive_pass"]
            g = g.merge(e.rename(columns={"explosive_rush": "xr", "explosive_pass": "xp", "explosive": "xt"}),
                        on=["gameId", "team"], how="left")
            # a game with no explosive-play rows for a team really had zero, if the game is in the file
            seen = set(e["gameId"])
            for c in ("xr", "xp", "xt"):
                g.loc[g["gameId"].isin(seen), c] = g.loc[g["gameId"].isin(seen), c].fillna(0)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def hist_for(games, season, week):
    cur = games[(games.season == season) & (games.week < week)].copy(); cur["w"] = 1.0
    prev = games[games.season == season - 1].copy()
    prev["w"] = max(sm.PRIOR_WEIGHT - sm.PRIOR_DECAY * max(week - 1, 0), 0.05)
    return pd.concat([cur, prev]) if len(prev) else cur


def main():
    lp, lc = sm.load_lines(sm.PRIOR), sm.load_lines(sm.SEASON)
    cls = sm.classification_map([lc, lp])
    games = pd.concat([sm.load_games(sm.PRIOR, lp), sm.load_games(sm.SEASON, lc)], ignore_index=True)
    games = add_columns(games)
    targets = [k for k in ("rppa", "pppa", "rsr", "psr", "ryds", "pyds", "xr", "xp", "xt") if k in games.columns]
    print("Testing ratings for:", targets)

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
        hist = hist_for(games, season, week)
        for k in targets:
            h = hist.dropna(subset=[k])
            if len(h) < 50:
                rows[f"exp_{k}"] = np.nan
                continue
            r, mu, hfa = sm.fit_ratings(h, k, cls)
            rows[f"exp_{k}"] = mu + hfa * rows["home"] + rows["team"].map(r["off"]).fillna(0).values \
                + rows["opponent"].map(r["def"]).fillna(0).values
        parts.append(rows)
        print(f"  {season} week {week}", end="\r")
    d = pd.concat(parts, ignore_index=True)
    trainable = ~((d.season == sm.PRIOR) & (d.week < sm.MIN_TRAIN_WEEK_FIRST_SEASON))
    L = pd.concat([lp, lc]).rename(columns={"id": "gameId"})[["gameId", "spread", "overUnder"]]

    base = list(sm.FEATURES)
    swap = lambda drop, add: [f for f in base if f not in drop] + add
    variants = {"Current model": base}
    variants["Rush/pass EPA instead of total EPA"] = swap(["exp_ppa"], ["exp_rppa", "exp_pppa"])
    variants["Rush/pass success rate instead of total"] = swap(["exp_sr"], ["exp_rsr", "exp_psr"])
    variants["Rush/pass EPA + success rate (both split)"] = swap(["exp_ppa", "exp_sr"],
                                                                 ["exp_rppa", "exp_pppa", "exp_rsr", "exp_psr"])
    if "ryds" in targets:
        variants["Rush/pass yards instead of total yards"] = swap(["exp_yds"], ["exp_ryds", "exp_pyds"])
    if "xt" in targets:
        variants["+ 20+ yard plays (total)"] = base + ["exp_xt"]
        variants["+ 20+ yard plays (rush & pass)"] = base + ["exp_xr", "exp_xp"]
    if "ryds" in targets and "xt" in targets:
        variants["Everything split + 20+ yard plays"] = swap(["exp_ppa", "exp_sr", "exp_yds"],
            ["exp_rppa", "exp_pppa", "exp_rsr", "exp_psr", "exp_ryds", "exp_pyds", "exp_xr", "exp_xp"])

    results, coefs = [], {}
    for name, F in variants.items():
        dd = d.dropna(subset=F)
        tr_mask = trainable.loc[dd.index]
        res = []
        for tr, te in [(sm.PRIOR, sm.SEASON), (sm.SEASON, sm.PRIOR)]:
            trn = dd[tr_mask & (dd.season == tr)]
            m = sm.LinearRegression().fit(trn[F], trn.points)
            t = dd[dd.season == te].copy(); t["p"] = m.predict(t[F])
            res.append(sm.to_games(t, "p"))
        full = sm.LinearRegression().fit(dd[tr_mask][F], dd[tr_mask].points)
        coefs[name] = pd.Series(full.coef_, index=F).round(3)
        r = sm.add_pick_cols(pd.concat(res).merge(L, on="gameId").dropna(subset=["spread", "overUnder"]))
        am, pm = r.home_pts - r.away_pts, r.pred_home - r.pred_away
        at, pt = r.home_pts + r.away_pts, r.pred_home + r.pred_away
        cover = am + r.spread
        ok = cover != 0
        win = np.sign(r.edge) == np.sign(cover)
        rec = lambda m: f"{int(win[ok & m].sum())}-{int((~win)[ok & m].sum())} ({win[ok & m].mean():.1%})"
        ou_ok = at != r.overUnder
        ou = (np.sign(pt - r.overUnder) == np.sign(at - r.overUnder))[ou_ok]
        results.append({
            "variant": name,
            "margin_MAE": round(float(np.abs(am - pm).mean()), 3),
            "total_MAE": round(float(np.abs(at - pt).mean()), 3),
            "winner_%": round(float((np.sign(am) == np.sign(pm)).mean() * 100), 1),
            "ATS_3+gap": rec(r.tier != "pass"),
            "ATS_big_gap": rec(r.tier == "big_gap"),
            "ATS_fav_value": rec(r.tier == "fav_value"),
            "O/U_%": round(float(ou.mean() * 100), 1),
            "games": len(r),
        })
    out = pd.DataFrame(results)
    pd.set_option("display.width", 250)
    print("\n" + out.to_string(index=False))
    print("\nCoefficients (full fit):")
    for name, c in coefs.items():
        print(f"  {name}: " + ", ".join(f"{k}={v}" for k, v in c.items()))
    os.makedirs(sm.OUT, exist_ok=True)
    out.to_csv(os.path.join(sm.OUT, "split_test.csv"), index=False)
    print(f"\nWrote {sm.OUT}/split_test.csv")


if __name__ == "__main__":
    main()
