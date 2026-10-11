"""
field_position_test.py -- does average starting field position improve the score model?

Needs data/drives_2025.csv and data/drives_2026.csv:
    python update_data.py --only-drives

Builds an opponent-adjusted starting-field-position rating the same way as the
other ratings (ridge fit, last season at reduced weight, only games before the
week being predicted):

    avg_start_yards_to_goal(team vs opp) = avg + home_edge + OFF[team] + DEF[opp]

  OFF = where a team's own drives start (special teams, its defense's takeaways/stops)
  DEF = where it lets opponents start (its punting/coverage, its offense's turnovers)

Then runs the same out-of-sample test as advanced_test.py (fit on one season,
predict the other, both directions) for the current model with and without it.

Run from the project root:  python field_position_test.py
Writes data/predictions/field_position_test.csv
"""
import os
import sys

import numpy as np
import pandas as pd

import score_model as sm

MAX_PERIOD = 4   # overtime drives always start at the 25 -- leave them out


def load_fp(year):
    path = os.path.join(sm.DATA, f"drives_{year}.csv")
    if not os.path.exists(path):
        sys.exit(f"{path} not found -- run `python update_data.py --only-drives` first.")
    d = pd.read_csv(path)
    d = d[(d["startPeriod"] <= MAX_PERIOD) & d["startYardsToGoal"].between(1, 99)]
    g = d.groupby(["gameId", "offense"]).agg(fp=("startYardsToGoal", "mean"),
                                             fp_drives=("startYardsToGoal", "size")).reset_index()
    return g.rename(columns={"offense": "team"})


def fp_ratings(games, season, week, cls):
    cur = games[(games.season == season) & (games.week < week)].copy(); cur["w"] = 1.0
    prev = games[games.season == season - 1].copy()
    prev["w"] = max(sm.PRIOR_WEIGHT - sm.PRIOR_DECAY * max(week - 1, 0), 0.05)
    hist = pd.concat([cur, prev]) if len(prev) else cur
    hist = hist.dropna(subset=["fp"])
    if len(hist) < 50:
        return None
    return sm.fit_ratings(hist, "fp", cls)


def main():
    lp, lc = sm.load_lines(sm.PRIOR), sm.load_lines(sm.SEASON)
    cls = sm.classification_map([lc, lp])
    games = pd.concat([sm.load_games(sm.PRIOR, lp), sm.load_games(sm.SEASON, lc)], ignore_index=True)
    fp = pd.concat([load_fp(sm.PRIOR), load_fp(sm.SEASON)], ignore_index=True)
    games = games.merge(fp, on=["gameId", "team"], how="left")
    print(f"Team-games with drive data: {games['fp'].notna().sum():,} of {len(games):,}")
    print(f"Avg start (yards to goal): {games['fp'].mean():.1f}, team-game std {games['fp'].std():.1f}")

    played = games.loc[games.season == sm.SEASON, "week"]
    keys = [(sm.PRIOR, w) for w in sorted(games.loc[games.season == sm.PRIOR, "week"].unique()) if w >= 2] + \
           [(sm.SEASON, w) for w in sorted(played.unique())]
    parts = []
    for season, week in keys:
        feats = sm.ratings_before(games, season, week, cls)
        fr = fp_ratings(games, season, week, cls)
        if feats is None or fr is None:
            continue
        wk = games[(games.season == season) & (games.week == week)]
        rows = sm.team_rows(wk[["gameId", "season", "week", "team", "opponent", "home", "conf_game", "points"]], feats)
        r, mu, hfa = fr
        rows["exp_fp"] = mu + hfa * rows["home"] + rows["team"].map(r["off"]).fillna(0).values \
            + rows["opponent"].map(r["def"]).fillna(0).values
        rows["opp_exp_fp"] = mu - hfa * rows["home"] + rows["opponent"].map(r["off"]).fillna(0).values \
            + rows["team"].map(r["def"]).fillna(0).values
        parts.append(rows)
    d = pd.concat(parts, ignore_index=True)
    trainable = ~((d.season == sm.PRIOR) & (d.week < sm.MIN_TRAIN_WEEK_FIRST_SEASON))
    L = pd.concat([lp, lc]).rename(columns={"id": "gameId"})[["gameId", "spread", "overUnder"]]

    base = sm.FEATURES
    variants = {
        "Current model": base,
        "+ own starting field position": base + ["exp_fp"],
        "+ own & opponent's starting field position": base + ["exp_fp", "opp_exp_fp"],
    }
    results, coefs = [], {}
    for name, F in variants.items():
        res = []
        for tr, te in [(sm.PRIOR, sm.SEASON), (sm.SEASON, sm.PRIOR)]:
            trn = d[trainable & (d.season == tr)]
            m = sm.LinearRegression().fit(trn[F], trn.points)
            t = d[d.season == te].copy(); t["p"] = m.predict(t[F])
            res.append(sm.to_games(t, "p"))
        full = sm.LinearRegression().fit(d[trainable][F], d[trainable].points)
        coefs[name] = dict(zip(F, full.coef_))
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
            "wk1-3_margin_MAE": round(float(np.abs(am - pm)[r.week <= 3].mean()), 3),
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
    print(out.to_string(index=False))
    print("\nCoefficient on field position (points per yard closer to the end zone is the NEGATIVE of these):")
    for name, c in coefs.items():
        extra = {k: round(v, 3) for k, v in c.items() if "fp" in k}
        if extra:
            print(f"  {name}: {extra}")
    os.makedirs(sm.OUT, exist_ok=True)
    out.to_csv(os.path.join(sm.OUT, "field_position_test.csv"), index=False)
    print(f"\nWrote {sm.OUT}/field_position_test.csv")


if __name__ == "__main__":
    main()
