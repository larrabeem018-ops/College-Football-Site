"""
moneyline_value.py -- underdog moneylines where a market-anchored win probability
says the price is too long. Run after score_model.py each week:

    python score_model.py
    python moneyline_value.py          # (start_week.bat does both)

How it works
------------
1. Rebuilds the model's out-of-sample predictions for every 2025-26 game (each
   season predicted by a model fit on the other), exactly like score_model.py's
   tier backtest.
2. Turns the projected margin into a win probability: P(win) = Phi(margin / sigma),
   sigma fit by maximum likelihood.
3. The raw model is overconfident when it disagrees with Vegas, so the win
   probability used for betting value is a BLEND fit on those games:
       logit(p) = a * logit(market) + k * (logit(model) - logit(market))
   (market = moneyline implied probability with the vig removed).
4. Flags every underdog whose blended expected value at the posted moneyline is
   positive, and logs them. Picks lock once a game kicks off; re-running mid-week
   only refreshes games that haven't started.

Writes data/predictions/:
    ml_model.json                     fitted sigma / blend + cross-season backtest
    week_{W}_ml_value_{SEASON}.csv    every underdog this week with market/model/blend %
    ml_log_{SEASON}.csv               flagged value bets, graded by export_web_data.py
"""
import argparse, glob, json, os, re
from datetime import datetime, timezone
from math import erf, sqrt

import numpy as np
import pandas as pd

import score_model as sm

OUT = os.path.join("data", "predictions")
SEASON = sm.SEASON
SIGMAS = np.arange(8, 25, 0.25)
A_GRID, K_GRID = np.arange(0.8, 1.31, 0.05), np.arange(0, 1.01, 0.05)
_phi = np.vectorize(lambda x: 0.5 * (1 + erf(x / sqrt(2))))


def logit(p): p = np.clip(p, 1e-4, 1 - 1e-4); return np.log(p / (1 - p))
def sigmoid(z): return 1 / (1 + np.exp(-z))
def implied(ml):
    ml = np.asarray(ml, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ml < 0, -ml / (-ml + 100), 100 / (ml + 100))
def decimal(ml):
    ml = np.asarray(ml, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(ml < 0, 1 + 100 / (-ml), 1 + ml / 100)


def valid_ml(col):
    return col.notna() & (col.abs() >= 100)
def nll(p, y): p = np.clip(p, 1e-4, 1 - 1e-4); return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def fit_sigma(margin, won):
    return float(min(SIGMAS, key=lambda s: nll(_phi(margin / s), won)))


def fit_blend(z_mkt, z_mod, won):
    best = None
    for a in A_GRID:
        for k in K_GRID:
            ll = nll(sigmoid(a * z_mkt + k * (z_mod - z_mkt)), won)
            if best is None or ll < best[2]:
                best = (float(a), float(k), ll)
    return best[0], best[1]


def oos_predictions():
    """Out-of-sample predictions for every game of both seasons (as in score_model.main)."""
    lines_p, lines_c = sm.load_lines(sm.PRIOR), sm.load_lines(SEASON)
    cls = sm.classification_map([lines_c, lines_p])
    games = pd.concat([sm.load_games(sm.PRIOR, lines_p), sm.load_games(SEASON, lines_c)], ignore_index=True)
    played = games.loc[games["season"] == SEASON, "week"]
    prior_weeks = sorted(games.loc[games["season"] == sm.PRIOR, "week"].unique())
    data = sm.build_dataset(games, cls, [(sm.PRIOR, w) for w in prior_weeks if w >= 2] +
                            [(SEASON, w) for w in sorted(played.unique())])
    trainable = ~((data["season"] == sm.PRIOR) & (data["week"] < sm.MIN_TRAIN_WEEK_FIRST_SEASON))
    oos = []
    for tr_s, te_s in [(sm.PRIOR, SEASON), (SEASON, sm.PRIOR)]:
        m = sm.fit_model(data[trainable & (data["season"] == tr_s)])
        oos.append(sm.pred_games(m, data[data["season"] == te_s]))
    lines = pd.concat([lines_p, lines_c]).rename(columns={"id": "gameId"})
    return pd.concat(oos).merge(lines[["gameId", "spread", "homeMoneyline", "awayMoneyline"]], on="gameId", how="left")


def sides(df, p_home_model, p_home_mkt):
    """One row per team per game."""
    out = []
    for side in ("home", "away"):
        h = side == "home"
        t = pd.DataFrame({
            "gameId": df["gameId"].values, "side": side,
            "ml": (df["homeMoneyline"] if h else df["awayMoneyline"]).values,
            "line": (df["spread"] if h else -df["spread"]).values,
            "p_model": p_home_model if h else 1 - p_home_model,
            "p_mkt": p_home_mkt if h else 1 - p_home_mkt,
        })
        for c in ("season", "week", "home_pts", "away_pts"):
            if c in df:
                t[c] = df[c].values
        if "home_pts" in df:
            diff = df["home_pts"] - df["away_pts"]
            t["won"] = ((diff > 0) if h else (diff < 0)).astype(float).values
        out.append(t)
    return pd.concat(out, ignore_index=True)


def summarize(x):
    if not len(x):
        return {"bets": 0}
    return {"bets": int(len(x)), "won": int(x["won"].sum()), "win_pct": round(float(x["won"].mean() * 100), 1),
            "median_odds": int(np.median(x["ml"])), "units": round(float(x["profit"].sum()), 1),
            "roi": round(float(x["profit"].mean() * 100), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None, help="week to evaluate (default: latest week_N_predictions file)")
    args = ap.parse_args()
    week = args.week or max(int(re.search(r"week_(\d+)_pred", f).group(1))
                            for f in glob.glob(os.path.join(OUT, f"week_*_predictions_{SEASON}.csv")))

    # ---- 1) fit on out-of-sample history
    o = oos_predictions()
    o = o[o["home_pts"].notna() & o["spread"].notna() & valid_ml(o["homeMoneyline"]) & valid_ml(o["awayMoneyline"])
          & (o["home_pts"] != o["away_pts"])].copy()
    margin = (o["pred_home"] - o["pred_away"]).values
    won_home = (o["home_pts"] > o["away_pts"]).astype(float).values
    ph, pa = implied(o["homeMoneyline"]), implied(o["awayMoneyline"])
    mkt = ph / (ph + pa)

    # cross-season backtest: params fit on one season, applied to the other
    bt = []
    for yr in (sm.PRIOR, SEASON):
        tr, te = (o["season"] != yr).values, (o["season"] == yr).values
        s = fit_sigma(margin[tr], won_home[tr])
        pm = _phi(margin / s)
        a, k = fit_blend(logit(mkt[tr]), logit(pm[tr]), won_home[tr])
        sd = sides(o[te], pm[te], mkt[te])
        sd["p_blend"] = sigmoid(a * logit(sd["p_mkt"]) + k * (logit(sd["p_model"]) - logit(sd["p_mkt"])))
        bt.append(sd)
    bt = pd.concat(bt)
    bt["dec"] = decimal(bt["ml"])
    bt["ev"] = bt["p_blend"] * bt["dec"] - 1
    bt["profit"] = np.where(bt["won"] == 1, bt["dec"] - 1, -1.0)
    flagged = bt[(bt["ml"] > 0) & (bt["ev"] > 0)]

    # final params on everything
    sigma = fit_sigma(margin, won_home)
    a, k = fit_blend(logit(mkt), logit(_phi(margin / sigma)), won_home)

    buckets = []
    for lo, hi, label in ((0.5, 2.5, "+1 to +2.5"), (3, 5, "+3 to +5"), (5.5, 7, "+5.5 to +7"),
                          (7.5, 10, "+7.5 to +10"), (10.5, 14, "+10.5 to +14"), (14.5, 99, "+14.5 or more")):
        buckets.append({"label": label, **summarize(flagged[flagged["line"].between(lo, hi)])})
    model = {
        "sigma": sigma, "market_weight": round(a, 2), "model_tilt": round(k, 2),
        "games": int(len(o)), "fitted": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "backtest": {"all": summarize(flagged),
                     "by_season": {str(y): summarize(g) for y, g in flagged.groupby("season")},
                     "every_dog": summarize(bt[bt["ml"] > 0]),
                     "by_line": buckets},
    }
    with open(os.path.join(OUT, "ml_model.json"), "w") as f:
        json.dump(model, f, indent=2)

    # ---- 2) this week
    pred = pd.read_csv(os.path.join(OUT, f"week_{week}_predictions_{SEASON}.csv"))
    sched = pd.read_csv(os.path.join("data", "schedule", f"week_{week}_games_{SEASON}.csv"))[
        ["gameId", "homeMoneyline", "awayMoneyline"]]
    g = pred.drop(columns=[c for c in ("homeMoneyline", "awayMoneyline") if c in pred]).merge(sched, on="gameId", how="left")
    g = g[valid_ml(g["homeMoneyline"]) & valid_ml(g["awayMoneyline"]) & g["spread"].notna()].copy()
    ph, pa = implied(g["homeMoneyline"]), implied(g["awayMoneyline"])
    s = sides(g, _phi((g["pred_home"] - g["pred_away"]).values / sigma), (ph / (ph + pa)))
    s["p_blend"] = sigmoid(a * logit(s["p_mkt"]) + k * (logit(s["p_model"]) - logit(s["p_mkt"])))
    s["ev"] = s["p_blend"] * decimal(s["ml"]) - 1
    info = g[["gameId", "week", "startDate", "homeTeam", "awayTeam"]]
    s = s.drop(columns=["week"], errors="ignore").merge(info, on="gameId")
    s["team"] = np.where(s["side"] == "home", s["homeTeam"], s["awayTeam"])
    s["opponent"] = np.where(s["side"] == "home", s["awayTeam"], s["homeTeam"])
    s["value"] = (s["ml"] > 0) & (s["ev"] > 0)
    cols = ["gameId", "week", "startDate", "team", "opponent", "side", "line", "ml", "p_mkt", "p_model", "p_blend", "ev", "value"]
    dogs = s[s["ml"] > 0][cols].sort_values("ev", ascending=False)
    dogs.to_csv(os.path.join(OUT, f"week_{week}_ml_value_{SEASON}.csv"), index=False)

    # ---- 3) log: lock games that have kicked off, refresh the rest
    log_path = os.path.join(OUT, f"ml_log_{SEASON}.csv")
    now = datetime.now(timezone.utc)
    new = dogs[dogs["value"]].drop(columns=["value"]).assign(logged_at=now.strftime("%Y-%m-%d %H:%M UTC"))
    if os.path.exists(log_path):
        log = pd.read_csv(log_path)
        started = pd.to_datetime(log["startDate"], utc=True) <= now
        keep = log[(log["week"] != week) | started]
        new = new[~new["gameId"].isin(keep["gameId"])]
        new = new[pd.to_datetime(new["startDate"], utc=True) > now]
        log = pd.concat([keep, new], ignore_index=True)
    else:
        log = new[pd.to_datetime(new["startDate"], utc=True) > now]
    log.to_csv(log_path, index=False)

    b = model["backtest"]["all"]
    print(f"Moneyline value, week {week}: {int(dogs['value'].sum())} underdogs with positive blended EV "
          f"(blend: market x{a:.2f}, model tilt {k:.2f}, sigma {sigma}).")
    print(f"  backtest: {b['bets']} bets, {b['units']:+.1f}u, ROI {b['roi']:+.1f}%  "
          + " | ".join(f"{y}: {v['roi']:+.1f}%" for y, v in model["backtest"]["by_season"].items()))


if __name__ == "__main__":
    main()
