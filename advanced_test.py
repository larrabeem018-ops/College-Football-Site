"""
advanced_test.py -- does CFBD advanced data (EPA/PPA, success rate, pace,
returning production, talent) improve the score model?

Same out-of-sample test as before: fit on one season, predict the other,
both directions. Every rating uses only games before the week predicted.
Run from the project root:  python advanced_test.py
"""
import json
import os

import numpy as np
import pandas as pd

import score_model as sm

ADV_SUFFIX = "_nogt"   # garbage time removed
ADV_TARGETS = {        # column in advanced stats -> short name
    "offense_ppa": "ppa",
    "offense_successRate": "sr",
    "offense_plays": "plays",
    "offense_explosiveness": "expl",
}


def load_adv(year):
    a = pd.read_csv(os.path.join(sm.DATA, f"advanced_game_stats{ADV_SUFFIX}_{year}.csv"))
    return a[["gameId", "team"] + list(ADV_TARGETS)].rename(columns=ADV_TARGETS)


def load_preseason(year):
    ret = pd.read_csv(os.path.join(sm.DATA, f"returning_production_{year}.csv"))[["team", "percentPPA"]]
    tal = pd.read_csv(os.path.join(sm.DATA, f"talent_{year}.csv"))[["team", "talent"]]
    df = ret.merge(tal, on="team", how="outer")
    df["talent_z"] = (df["talent"] - df["talent"].mean()) / df["talent"].std()
    df["ret_c"] = df["percentPPA"] - df["percentPPA"].mean()
    df["season"] = year
    return df[["season", "team", "ret_c", "talent_z"]]


def adv_ratings(all_games, season, week, cls):
    cur = all_games[(all_games.season == season) & (all_games.week < week)].copy(); cur["w"] = 1.0
    prev = all_games[all_games.season == season - 1].copy()
    prev["w"] = max(sm.PRIOR_WEIGHT - sm.PRIOR_DECAY * max(week - 1, 0), 0.05)
    hist = pd.concat([cur, prev]) if len(prev) else cur
    out, attrs = {}, {}
    for k in ADV_TARGETS.values():
        h = hist.dropna(subset=[k])
        r, mu, hfa = sm.fit_ratings(h, k, cls)
        out[k] = r
        attrs[k] = (mu, hfa)
    return out, attrs


def main():
    lp, lc = sm.load_lines(2025), sm.load_lines(2026)
    cls = sm.classification_map([lc, lp])
    games = pd.concat([sm.load_games(2025, lp), sm.load_games(2026, lc)], ignore_index=True)
    adv = pd.concat([load_adv(2025).assign(season=2025), load_adv(2026).assign(season=2026)])
    games = games.merge(adv.drop(columns="season"), on=["gameId", "team"], how="left")
    pre = pd.concat([load_preseason(2025), load_preseason(2026)])

    keys = [(2025, w) for w in range(2, 17)] + [(2026, w) for w in range(1, 5)]
    parts = []
    for season, week in keys:
        feats = sm.ratings_before(games, season, week, cls)
        wk = games[(games.season == season) & (games.week == week)]
        rows = sm.team_rows(wk[["gameId", "season", "week", "team", "opponent", "home", "conf_game", "points"]], feats)
        ar, attrs = adv_ratings(games, season, week, cls)
        for k, r in ar.items():
            mu, hfa = attrs[k]
            rows[f"exp_{k}"] = mu + hfa * rows["home"] + rows["team"].map(r["off"]).fillna(0).values \
                + rows["opponent"].map(r["def"]).fillna(0).values
        rows["exp_ppa_x_plays"] = rows["exp_ppa"] * rows["exp_plays"]
        # preseason info, faded out over the first ~6 weeks
        fade = max(0.0, 1 - (week - 1) / 6)
        p = pre[pre.season == season].set_index("team")
        rows["ret_fade"] = rows["team"].map(p["ret_c"]).fillna(0).values * fade
        rows["opp_ret_fade"] = rows["opponent"].map(p["ret_c"]).fillna(0).values * fade
        rows["talent_fade"] = rows["team"].map(p["talent_z"]).fillna(0).values * fade
        rows["opp_talent_fade"] = rows["opponent"].map(p["talent_z"]).fillna(0).values * fade
        parts.append(rows)
    d = pd.concat(parts, ignore_index=True)
    trainable = ~((d.season == 2025) & (d.week < sm.MIN_TRAIN_WEEK_FIRST_SEASON))
    L = pd.concat([lp, lc]).rename(columns={"id": "gameId"})[["gameId", "spread", "overUnder"]]

    base = sm.FEATURES
    pre_f = ["ret_fade", "opp_ret_fade", "talent_fade", "opp_talent_fade"]
    variants = {
        "Current model": base,
        "+ EPA per play rating": base + ["exp_ppa"],
        "+ success rate rating": base + ["exp_sr"],
        "+ EPA + success rate": base + ["exp_ppa", "exp_sr"],
        "+ EPA + success + pace": base + ["exp_ppa", "exp_sr", "exp_plays", "exp_ppa_x_plays"],
        "+ explosiveness": base + ["exp_ppa", "exp_sr", "exp_expl"],
        "Efficiency only (no points ratings)": ["exp_ppa", "exp_sr", "exp_plays", "exp_ppa_x_plays", "exp_yds", "home", "conf_home"],
        "+ returning production & talent": base + pre_f,
        "+ EPA + success + pace + preseason": base + ["exp_ppa", "exp_sr", "exp_plays", "exp_ppa_x_plays"] + pre_f,
    }
    results = []
    preds = {}
    for name, F in variants.items():
        res = []
        for tr, te in [(2025, 2026), (2026, 2025)]:
            m = sm.LinearRegression().fit(d[trainable & (d.season == tr)][F], d[trainable & (d.season == tr)].points)
            t = d[d.season == te].copy(); t["p"] = m.predict(t[F])
            res.append(sm.to_games(t, "p"))
        r = pd.concat(res).merge(L, on="gameId").dropna(subset=["spread", "overUnder"])
        r = sm.add_pick_cols(r)
        preds[name] = r
        am, pm = r.home_pts - r.away_pts, r.pred_home - r.pred_away
        at, pt = r.home_pts + r.away_pts, r.pred_home + r.pred_away
        cover = am + r.spread
        ok = cover != 0
        win = (np.sign(r.edge) == np.sign(cover))
        wl = win[ok & (r.tier == "fav_value")]
        g3 = win[ok & (r.tier != "pass")]
        early = r.week <= 2
        ou_ok = at != r.overUnder
        ou = (np.sign(pt - r.overUnder) == np.sign(at - r.overUnder))[ou_ok]
        results.append({
            "variant": name,
            "margin_MAE": round(float(np.abs(am - pm).mean()), 2),
            "wk1-2_margin_MAE": round(float(np.abs(am - pm)[early].mean()), 2),
            "total_MAE": round(float(np.abs(at - pt).mean()), 2),
            "winner_%": round(float((np.sign(am) == np.sign(pm)).mean() * 100), 1),
            "ATS_3+gap": f"{int(g3.sum())}-{int((~g3).sum())} ({g3.mean():.1%})",
            "watchlist": f"{int(wl.sum())}-{int((~wl).sum())} ({wl.mean():.1%})",
            "O/U_%": round(float(ou.mean() * 100), 1),
        })
    out = pd.DataFrame(results)
    r = preds["Current model"]
    am = r.home_pts - r.away_pts
    at = r.home_pts + r.away_pts
    vegas = {"variant": "VEGAS", "margin_MAE": round(float(np.abs(am + r.spread).mean()), 2),
             "wk1-2_margin_MAE": round(float(np.abs(am + r.spread)[r.week <= 2].mean()), 2),
             "total_MAE": round(float(np.abs(at - r.overUnder).mean()), 2),
             "winner_%": round(float((np.sign(am) == np.sign(-r.spread)).mean() * 100), 1)}
    out = pd.concat([out, pd.DataFrame([vegas])], ignore_index=True)
    pd.set_option("display.width", 250)
    print(f"Games with a line: {len(r)}")
    print(out.to_string(index=False))
    os.makedirs("data/predictions", exist_ok=True)
    out.to_csv("data/predictions/advanced_test.csv", index=False)
    d.to_pickle(os.path.join(os.environ.get("SCRATCH", "."), "adv_rows.pkl"))


if __name__ == "__main__":
    main()
