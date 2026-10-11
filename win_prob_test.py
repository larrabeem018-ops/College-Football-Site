"""
win_prob_test.py -- does a rating built on POSTGAME WIN PROBABILITY improve the score model?

Postgame win probability (CFBD) = how likely each team was to win given how it
actually played (its per-play efficiency), not the final score. A team that
dominated but lost on a fluke gets a high number. Rating teams on it filters
some luck out of the points-based ratings.

Needs data/postgame_wp_2025.csv and _2026.csv:
    python update_data.py --only-win-prob        (~16 API calls per season)

Each version becomes an opponent-adjusted rating built like the existing ones
(only games before the week predicted, last season at reduced weight):

    wp(team vs opp) = avg + home_edge + OFF[team] + DEF[opp]

"logit" versions stretch the 0-1 probability so a 99% game counts as much more
dominant than a 90% one (closer to how point margins behave).

Same out-of-sample test as the other scripts: fit on one season, predict the
other, both directions.
Run from the project root:  python win_prob_test.py
Writes data/predictions/win_prob_test.csv
"""
import os
import sys

import numpy as np
import pandas as pd

import score_model as sm


def load_wp(year):
    path = os.path.join(sm.DATA, f"postgame_wp_{year}.csv")
    if not os.path.exists(path):
        sys.exit(f"{path} not found -- run `python update_data.py --only-win-prob` first.")
    w = pd.read_csv(path)
    h = w[["gameId", "homeTeam", "homePostgameWinProbability"]].set_axis(["gameId", "team", "wp"], axis=1)
    a = w[["gameId", "awayTeam", "awayPostgameWinProbability"]].set_axis(["gameId", "team", "wp"], axis=1)
    out = pd.concat([h, a], ignore_index=True)
    out["wp"] = pd.to_numeric(out["wp"], errors="coerce")
    p = out["wp"].clip(0.005, 0.995)
    out["wp_logit"] = np.log(p / (1 - p))
    return out


def main():
    lp, lc = sm.load_lines(sm.PRIOR), sm.load_lines(sm.SEASON)
    cls = sm.classification_map([lc, lp])
    games = pd.concat([sm.load_games(sm.PRIOR, lp), sm.load_games(sm.SEASON, lc)], ignore_index=True)
    games = games.merge(pd.concat([load_wp(sm.PRIOR), load_wp(sm.SEASON)]), on=["gameId", "team"], how="left")
    print(f"Team-games with postgame win probability: {games['wp'].notna().sum():,} of {len(games):,}")
    m = games.dropna(subset=["wp"])
    won = (m["points"] > m["opp_points"]).astype(float)
    print(f"Games where the team that 'deserved' to win (wp > 50%) lost: {((m['wp'] > .5) & (won == 0)).mean() * 2:.1%}")

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
        rec = hist.copy()
        rec.loc[(rec.season == season) & (rec.week >= week - sm.RECENT_WEEKS), "w"] *= sm.RECENT_MULT
        for name, h, k in (("wp", hist, "wp"), ("wpl", hist, "wp_logit"), ("wpl_rec", rec, "wp_logit")):
            h = h.dropna(subset=[k])
            if len(h) < 50:
                rows[f"exp_{name}"] = np.nan
                continue
            r, mu, hfa = sm.fit_ratings(h, k, cls)
            rows[f"exp_{name}"] = mu + hfa * rows["home"] + rows["team"].map(r["off"]).fillna(0).values \
                + rows["opponent"].map(r["def"]).fillna(0).values
        parts.append(rows)
        print(f"  ratings: {season} week {week}   ", end="\r")
    d = pd.concat(parts, ignore_index=True)
    trainable = ~((d.season == sm.PRIOR) & (d.week < sm.MIN_TRAIN_WEEK_FIRST_SEASON))
    L = pd.concat([lp, lc]).rename(columns={"id": "gameId"})[["gameId", "spread", "overUnder"]]

    base = list(sm.FEATURES)
    swap = lambda drop, add: [f for f in base if f not in drop] + add
    variants = {
        "Current model": base,
        "+ win-prob rating": base + ["exp_wp"],
        "+ win-prob rating (logit)": base + ["exp_wpl"],
        "+ win-prob logit, season + recent form": base + ["exp_wpl", "exp_wpl_rec"],
        "Win-prob logit replaces points rating": swap(["exp_pts"], ["exp_wpl"]),
        "Win-prob logit replaces points + recent-form points": swap(["exp_pts", "exp_rec"], ["exp_wpl", "exp_wpl_rec"]),
    }
    results, coefs = [], {}
    for name, F in variants.items():
        dd = d.dropna(subset=F)
        tm = trainable.loc[dd.index]
        res = []
        for tr, te in [(sm.PRIOR, sm.SEASON), (sm.SEASON, sm.PRIOR)]:
            trn = dd[tm & (dd.season == tr)]
            mdl = sm.LinearRegression().fit(trn[F], trn.points)
            t = dd[dd.season == te].copy(); t["p"] = mdl.predict(t[F])
            res.append(sm.to_games(t, "p"))
        coefs[name] = pd.Series(sm.LinearRegression().fit(dd[tm][F], dd[tm].points).coef_, index=F).round(3)
        r = sm.add_pick_cols(pd.concat(res).merge(L, on="gameId").dropna(subset=["spread", "overUnder"]))
        am, pm = r.home_pts - r.away_pts, r.pred_home - r.pred_away
        at, pt = r.home_pts + r.away_pts, r.pred_home + r.pred_away
        cover = am + r.spread
        ok = cover != 0
        win = np.sign(r.edge) == np.sign(cover)
        rec_ = lambda msk: f"{int(win[ok & msk].sum())}-{int((~win)[ok & msk].sum())} ({win[ok & msk].mean():.1%})"
        ou = (np.sign(pt - r.overUnder) == np.sign(at - r.overUnder))[at != r.overUnder]
        results.append({
            "variant": name,
            "margin_MAE": round(float(np.abs(am - pm).mean()), 3),
            "wk1-4_margin_MAE": round(float(np.abs(am - pm)[r.week <= 4].mean()), 3),
            "total_MAE": round(float(np.abs(at - pt).mean()), 3),
            "winner_%": round(float((np.sign(am) == np.sign(pm)).mean() * 100), 1),
            "ATS_3+gap": rec_(r.tier != "pass"),
            "ATS_big_gap": rec_(r.tier == "big_gap"),
            "ATS_fav_value": rec_(r.tier == "fav_value"),
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
    out.to_csv(os.path.join(sm.OUT, "win_prob_test.csv"), index=False)
    print(f"\nWrote {sm.OUT}/win_prob_test.csv")


if __name__ == "__main__":
    main()
