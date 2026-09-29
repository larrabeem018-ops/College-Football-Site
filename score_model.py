"""
score_model.py -- score predictions + "Sharp Bets" picks for the site.

How it works
------------
1. Opponent-adjusted team ratings. Before every week, a ridge regression is fit
   on all games played so far (plus the prior season at reduced weight):

       points_scored(team vs opp) = avg + home_edge + OFF[team] + DEF[opp]

   That gives an opponent-adjusted "expected points" for any matchup. Two more
   versions are fit the same way: one on total yards, and one that counts the
   last 3 weeks three times as heavily (recent form).

2. Score regression. A linear regression maps those pre-game numbers to the
   points each team actually scored:

       team_points ~ expected points + recent-form expected points
                     + expected yards + home/away + home/away in a conference game

   (Home field is worth ~3 pts less on the spread in conference games.)

3. Picks. The model's line is compared with the Vegas line. Each game gets a
   tier, a plain-English explanation, and the historical record of that tier
   from a two-season out-of-sample backtest.

Every feature uses only games played before the week being predicted.

Outputs (data/predictions/)
-------
  week_{W}_predictions_{SEASON}.csv  model scores for every game this week
  week_{W}_picks_{SEASON}.csv        tier + explanation for every game (read by pages/Sharp Bets.py)
  picks_log_{SEASON}.csv             every pick made this season, graded by the page once games finish
  tier_history.csv                   how each pick tier has done historically (backtest)
  model_accuracy.json                model vs Vegas accuracy (backtest)
  model_summary.txt                  coefficients + accuracy

Run from the project root after update_data.py:  python score_model.py  [--week 5]
"""
import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd


# Small numpy-only stand-ins for scikit-learn's Ridge / LinearRegression, so the
# script only needs pandas + numpy (both already in requirements.txt).
class Ridge:
    """Weighted ridge regression with an unpenalized intercept (same math as sklearn's Ridge)."""
    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def fit(self, X, y, sample_weight=None):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        w = np.ones(len(y)) if sample_weight is None else np.asarray(sample_weight, dtype=float)
        x_mean = (X * w[:, None]).sum(0) / w.sum()
        y_mean = (y * w).sum() / w.sum()
        Xc, yc = X - x_mean, y - y_mean
        A = Xc.T @ (Xc * w[:, None]) + self.alpha * np.eye(X.shape[1])
        self.coef_ = np.linalg.solve(A, Xc.T @ (yc * w))
        self.intercept_ = y_mean - x_mean @ self.coef_
        return self

    def predict(self, X):
        return np.asarray(X, dtype=float) @ self.coef_ + self.intercept_


class LinearRegression(Ridge):
    """Ordinary least squares (ridge with no penalty)."""
    def __init__(self):
        super().__init__(alpha=0.0)

    def fit(self, X, y, sample_weight=None):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        x_mean, y_mean = X.mean(0), y.mean()
        self.coef_ = np.linalg.lstsq(X - x_mean, y - y_mean, rcond=None)[0]
        self.intercept_ = y_mean - x_mean @ self.coef_
        return self

SEASON = 2026
PRIOR = 2025
DATA = "data"
OUT = os.path.join(DATA, "predictions")

RIDGE_ALPHA = 3.0        # shrinkage on team ratings (higher = pulled harder to average)
PRIOR_WEIGHT = 0.60      # weight of last season's games in this season's ratings
PRIOR_DECAY = 0.06       # prior weight drops by this much per week played
RECENT_WEEKS = 3         # "recent form" = last N weeks...
RECENT_MULT = 3.0        # ...counted this many times as heavily
MIN_TRAIN_WEEK_FIRST_SEASON = 4   # 2025 has no prior season in the data, so skip its first weeks
OPTION_TEAMS = {"Army", "Navy", "Air Force"}   # run-heavy, clock-killing offenses the model can't see


# --------------------------------------------------------------------------- data
def load_lines(year):
    return pd.read_csv(os.path.join(DATA, f"espnBetLines_{year}.csv"))


def load_games(year, lines):
    """Team-game long table with week and home flag filled in.

    team_game_stats_*.csv has an empty `week` column, but update_data.py writes
    rows week by week, so file order is chronological. Weeks come from the
    betting-lines file where the game has a line, and are forward-filled by file
    order for the rest (mostly FCS/D2 games).
    """
    g = pd.read_csv(os.path.join(DATA, f"team_game_stats_{year}.csv"))
    wk = lines.set_index("id")["week"]
    g["week"] = g["gameId"].map(wk)
    order = g.drop_duplicates("gameId")[["gameId", "week"]].copy()
    order["week"] = order["week"].cummax().ffill().bfill()
    g = g.drop(columns="week").merge(order, on="gameId")
    g["season"] = year
    g["home"] = np.where(g["homeAway"] == "home", 1.0, -1.0)

    sched = os.path.join(DATA, "schedule", f"week_1_games_{year}.csv")
    if os.path.exists(sched):  # neutral sites (only known for the week 1 schedule)
        s = pd.read_csv(sched)
        neutral = set(s.loc[s["neutralSite"].astype(str) == "True", "gameId"])
        g.loc[g["gameId"].isin(neutral), "home"] = 0.0

    opp = g[["gameId", "team", "conference", "points", "totalYards", "turnovers",
             "thirdDownMade", "thirdDownAtt"]].rename(columns={
        "team": "opponent", "conference": "opp_conference", "points": "opp_points",
        "totalYards": "opp_yards", "turnovers": "opp_turnovers",
        "thirdDownMade": "opp_3dm", "thirdDownAtt": "opp_3da"})
    g = g.merge(opp, on=["gameId", "opponent"], how="left")
    g["conf_game"] = (g["conference"] == g["opp_conference"]).astype(float)
    return g


def classification_map(lines_list):
    cls = {}
    for l in lines_list:
        for side in ("home", "away"):
            for t, c in zip(l[f"{side}Team"], l[f"{side}Classification"]):
                cls.setdefault(t, c)
    return cls


# ------------------------------------------------------------------- ratings
def fit_ratings(games, target, cls):
    """Ridge rating fit. games: team-game rows with column `w` (sample weight)."""
    teams = pd.Index(sorted(set(games["team"]) | set(games["opponent"])))
    n, k = len(games), len(teams)
    ti = teams.get_indexer(games["team"])
    oi = teams.get_indexer(games["opponent"])
    rows = np.arange(n)
    X_off = np.zeros((n, k)); X_off[rows, ti] = 1.0
    X_def = np.zeros((n, k)); X_def[rows, oi] = 1.0
    # group terms let low-sample teams shrink toward their division's level, not the global mean
    grp = lambda s: np.column_stack([(s.map(cls).fillna("other") == c).astype(float)
                                     for c in ("fbs", "fcs")])
    X_fixed = np.column_stack([games["home"].values,
                               grp(games["team"]) * 3, grp(games["opponent"]) * 3])
    X = np.hstack([X_off, X_def, X_fixed])
    m = Ridge(alpha=RIDGE_ALPHA)
    m.fit(X, games[target].values, sample_weight=games["w"].values)
    c = m.coef_
    t_cls = pd.Series(teams, index=teams).map(cls).fillna("other")
    grp_off = t_cls.map({"fbs": c[2 * k + 1] * 3, "fcs": c[2 * k + 2] * 3}).fillna(0).values
    grp_def = t_cls.map({"fbs": c[2 * k + 3] * 3, "fcs": c[2 * k + 4] * 3}).fillna(0).values
    return pd.DataFrame({"off": c[:k] + grp_off, "def": c[k:2 * k] + grp_def}, index=teams), \
        m.intercept_, c[2 * k]


def ratings_before(all_games, season, week, cls):
    """Ratings for every team using only games before (season, week)."""
    cur = all_games[(all_games["season"] == season) & (all_games["week"] < week)].copy()
    cur["w"] = 1.0
    prev = all_games[all_games["season"] == season - 1].copy()
    prev["w"] = max(PRIOR_WEIGHT - PRIOR_DECAY * max(week - 1, 0), 0.05)
    hist = pd.concat([cur, prev]) if len(prev) else cur
    if hist.empty:
        return None
    rec = hist.copy()
    rec.loc[(rec["season"] == season) & (rec["week"] >= week - RECENT_WEEKS), "w"] *= RECENT_MULT
    pts, mu, hfa = fit_ratings(hist, "points", cls)
    yds, ymu, yhfa = fit_ratings(hist, "totalYards", cls)
    rcn, rmu, rhfa = fit_ratings(rec, "points", cls)
    feats = pts.add_prefix("pts_").join(yds.add_prefix("yds_")).join(rcn.add_prefix("rec_"))
    feats["games_played"] = cur.groupby("team").size().reindex(feats.index).fillna(0)
    # Off/def levels aren't separately identified (only their sum is), so the
    # model uses each rating model's full expected value for the matchup.
    feats.attrs = {"pts": (mu, hfa), "yds": (ymu, yhfa), "rec": (rmu, rhfa)}
    return feats


# ------------------------------------------------------------- design matrix
FEATURES = ["exp_pts", "exp_rec", "exp_yds", "home", "conf_home"]


def team_rows(pairs, feats):
    """pairs: DataFrame with team, opponent, home, conf_game -> feature rows."""
    d = pairs.copy()
    for k in ("pts", "yds", "rec"):
        mu, hfa = feats.attrs[k]
        off = d["team"].map(feats[f"{k}_off"]).fillna(0)
        de = d["opponent"].map(feats[f"{k}_def"]).fillna(0)
        d[f"exp_{k}"] = mu + hfa * d["home"] + off + de
    d["conf_home"] = d["home"] * d["conf_game"]
    d["games_played"] = d["team"].map(feats["games_played"]).fillna(0)
    return d


def build_dataset(all_games, cls, keys):
    parts = []
    for season, week in keys:
        feats = ratings_before(all_games, season, week, cls)
        if feats is None:
            continue
        wk = all_games[(all_games["season"] == season) & (all_games["week"] == week)]
        parts.append(team_rows(wk[["gameId", "season", "week", "team", "opponent", "home",
                                   "conf_game", "points"]], feats))
    return pd.concat(parts, ignore_index=True)


def to_games(rows, pred_col):
    h = rows[rows["home"] >= 0].drop_duplicates("gameId", keep="first")
    a = rows[~rows.index.isin(h.index)]
    return h[["gameId", "season", "week", "team", "points", pred_col]].rename(
        columns={"team": "homeTeam", "points": "home_pts", pred_col: "pred_home"}).merge(
        a[["gameId", "team", "points", pred_col]].rename(
            columns={"team": "awayTeam", "points": "away_pts", pred_col: "pred_away"}), on="gameId")


# ------------------------------------------------------------------- pick tiers
TIERS = {
    "fav_value": "Model backs the favorite",
    "big_gap": "Big disagreement",
    "lean": "Lean",
    "pass": "No edge",
}
TIER_BLURB = {
    "fav_value": "The model thinks a 3.5-14 point favorite should be favored by at least 3 more points.",
    "big_gap": "The model's line is 10+ points away from Vegas.",
    "lean": "The model and Vegas disagree by 3-10 points.",
    "pass": "The model and Vegas are within 3 points of each other.",
}


def tier_for(spread, model_spread):
    """spread / model_spread use the Vegas convention: negative = home favored."""
    if pd.isna(spread):
        return None
    edge = spread - model_spread               # >0 -> model likes home vs the line
    fav_home = spread < 0
    model_on_fav = spread != 0 and (edge > 0) == fav_home
    if abs(edge) < 3:
        return "pass"
    if model_on_fav and 3.5 <= abs(spread) <= 14:
        return "fav_value"
    if abs(edge) >= 10:
        return "big_gap"
    return "lean"


def grade(row):
    """ATS result of the model's side, or None if not played."""
    if pd.isna(row.get("home_pts")) or pd.isna(row["spread"]):
        return None
    cover = (row["home_pts"] - row["away_pts"]) + row["spread"]   # >0 -> home covered
    if cover == 0:
        return "Push"
    return "Win" if (cover > 0) == (row["pick_side"] == "home") else "Loss"


def line_str(team, home, spread_home):
    """Line from `team`'s point of view, e.g. 'Iowa State -3.5'."""
    v = spread_home if team == home else -spread_home
    return f"{team} {'+' if v > 0 else ''}{v:.1f}" if abs(v) > 0.01 else f"{team} PK"


# ---------------------------------------------------------- plain-English reasons
def describe_game(row, feats, cls, hfa_pts):
    """Build the 'why' bullets and 'watch out' bullets for one game."""
    home, away = row["homeTeam"], row["awayTeam"]
    pick = home if row["pick_side"] == "home" else away
    other = away if pick == home else home
    is_fbs = np.asarray(feats.index.map(lambda t: cls.get(t) == "fbs"), dtype=bool)
    fbs = feats[is_fbs]
    off_c = feats["pts_off"] - fbs["pts_off"].mean()
    def_c = feats["pts_def"] - fbs["pts_def"].mean()     # + = allows more (bad)
    n_fbs = int(is_fbs.sum())
    off_rank = off_c[is_fbs].rank(ascending=False, method="min")
    def_rank = def_c[is_fbs].rank(ascending=True, method="min")
    net = off_c - def_c
    net_rec = (feats["rec_off"] - fbs["rec_off"].mean()) - (feats["rec_def"] - fbs["rec_def"].mean())
    trend = net_rec - net

    def rk(r, t):
        return f"#{int(r[t])} of {n_fbs} FBS" if t in r.index else "non-FBS"

    spread, mspread = row["spread"], row["model_spread"]
    why, watch = [], []

    # 1. the gap
    model_fav = home if mspread < 0 else away
    vegas_fav = home if spread < 0 else away
    why.append(f"The model makes this **{model_fav} by {abs(mspread):.1f}**; Vegas has "
               f"**{vegas_fav} by {abs(spread):.1f}**. That's a **{abs(row['edge']):.1f}-point** gap "
               f"in {pick}'s favor.")

    # 2. biggest matchup advantage for the picked side (opponent-adjusted, vs FBS average)
    adv = []
    if pick in off_c.index and other in def_c.index:
        adv.append((off_c[pick] + def_c[other],
                    f"{pick}'s offense scores {off_c[pick]:+.1f} pts/game vs. an average FBS offense "
                    f"({rk(off_rank, pick)}), and {other}'s defense allows {def_c[other]:+.1f} vs. average "
                    f"({rk(def_rank, other)}). Both adjusted for schedule strength."))
    if pick in def_c.index and other in off_c.index:
        adv.append((-def_c[pick] - off_c[other],
                    f"{pick}'s defense allows {def_c[pick]:+.1f} pts/game vs. average ({rk(def_rank, pick)}), "
                    f"facing a {other} offense at {off_c[other]:+.1f} ({rk(off_rank, other)}). "
                    f"Both adjusted for schedule strength."))
    best = max(adv, key=lambda a: a[0]) if adv else None
    if best is not None and best[0] > 0:
        why.append(best[1])
    elif pick in net.index and other in net.index and is_fbs[feats.index.get_loc(pick)] \
            and is_fbs[feats.index.get_loc(other)]:
        net_rank = net[is_fbs].rank(ascending=False, method="min")
        if net[other] > net[pick]:
            why.append(f"{other} is the better team ({rk(net_rank, other)} overall vs. {pick} at "
                       f"{rk(net_rank, pick)}), but the model sees a smaller gap than the "
                       f"{abs(spread):.1f}-point line implies.")
        else:
            why.append(f"The model rates {pick} {rk(net_rank, pick)} overall and {other} "
                       f"{rk(net_rank, other)}, adjusted for schedule strength.")

    # 3. recent form
    for t, is_pick in ((pick, True), (other, False)):
        if t in trend.index and abs(trend[t]) >= 2.5:
            up = trend[t] > 0
            txt = (f"{t} has played about {abs(trend[t]):.0f} pts/game {'better' if up else 'worse'} "
                   f"over the last {RECENT_WEEKS} weeks than its full-season rating.")
            (why if up == is_pick else watch).append(txt + ("" if up == is_pick else " That works against this pick."))

    # 4. home field / conference game
    if row.get("neutral"):
        why.append("Neutral site, so no home-field edge either way.")
    elif row["conf_game"]:
        if pick == home:
            why.append(f"{home} is at home, though home field is worth only about {hfa_pts:.1f} pts "
                       f"in conference games.")
        else:
            why.append(f"It's a conference game, where home field is worth only about {hfa_pts:.1f} pts, "
                       f"so playing on the road costs {away} less than usual.")
    elif pick == home:
        why.append(f"{home} is hosting a non-conference game. Home teams in these games have beaten "
                   f"their ratings by several points on average, since hosts usually pick opponents "
                   f"they match up well against.")

    # 5. line movement
    so = row.get("spreadOpen")
    if so is not None and not pd.isna(so) and abs(spread - so) >= 1.5:
        toward = home if spread < so else away
        with_model = toward == pick
        (why if with_model else watch).append(
            f"The line has moved {abs(spread - so):.1f} pts toward {toward} since it opened "
            f"({line_str(home, home, so)} → {line_str(home, home, spread)}), so bettors are "
            f"{'agreeing with' if with_model else 'going against'} the model.")

    # 6. blind spots
    for t in (home, away):
        gp = int(feats["games_played"].get(t, 0))
        if gp < 3:
            watch.append(f"{t} has played only {gp} games this season, so its rating still leans on last year.")
        if cls.get(t) != "fbs":
            watch.append(f"{t} isn't an FBS team. Ratings for lower-division teams are less reliable.")
    if {home, away} & OPTION_TEAMS:
        watch.append("Service-academy option offenses shorten games in ways this model doesn't capture.")
    if abs(row["edge"]) >= 10:
        watch.append("A gap this big often means Vegas knows something the box scores don't "
                     "(an injury, a QB change, a suspension). Check the news first.")
    watch.append("The model only sees points, yards and home field. It knows nothing about injuries, "
                 "weather or motivation.")
    return pick, why, watch


# ------------------------------------------------------------------------ main
def fit_model(rows):
    return LinearRegression().fit(rows[FEATURES], rows["points"])


def pred_games(model, rows):
    return to_games(rows.assign(p=model.predict(rows[FEATURES])), "p")


def add_pick_cols(g):
    g = g.copy()
    g["model_spread"] = -(g["pred_home"] - g["pred_away"])
    g["edge"] = g["spread"] - g["model_spread"]
    g["tier"] = [tier_for(s, m) for s, m in zip(g["spread"], g["model_spread"])]
    g["pick_side"] = np.where(g["edge"] > 0, "home", "away")
    g["pick"] = np.where(g["pick_side"] == "home", g["homeTeam"], g["awayTeam"])
    g["pick_line"] = [line_str(t, h, s) if not pd.isna(s) else None
                      for t, h, s in zip(g["pick"], g["homeTeam"], g["spread"])]
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None, help="week to predict (default: next unplayed)")
    args = ap.parse_args()

    lines_p, lines_c = load_lines(PRIOR), load_lines(SEASON)
    cls = classification_map([lines_c, lines_p])
    games = pd.concat([load_games(PRIOR, lines_p), load_games(SEASON, lines_c)], ignore_index=True)
    played = games.loc[games["season"] == SEASON, "week"]
    last_week = int(played.max())
    week = args.week or last_week + 1
    os.makedirs(OUT, exist_ok=True)
    lines_all = pd.concat([lines_p, lines_c]).rename(columns={"id": "gameId"})[
        ["gameId", "spread", "spreadOpen", "overUnder", "startDate"]]

    prior_weeks = sorted(games.loc[games["season"] == PRIOR, "week"].unique())
    cur_weeks = sorted(played.unique())
    data = build_dataset(games, cls, [(PRIOR, w) for w in prior_weeks if w >= 2] +
                         [(SEASON, w) for w in cur_weeks])
    trainable = ~((data["season"] == PRIOR) & (data["week"] < MIN_TRAIN_WEEK_FIRST_SEASON))

    # ---- 1) two-season out-of-sample backtest -> accuracy + tier history
    oos = []
    for tr_s, te_s in [(PRIOR, SEASON), (SEASON, PRIOR)]:
        m = fit_model(data[trainable & (data["season"] == tr_s)])
        oos.append(pred_games(m, data[data["season"] == te_s]))
    oos = pd.concat(oos).merge(lines_all, on="gameId", how="left")
    oos = add_pick_cols(oos[oos["spread"].notna()])
    oos["result"] = oos.apply(grade, axis=1)
    hist = []
    for t in list(TIERS) + ["all_3plus"]:
        s = oos[oos["tier"] == t] if t != "all_3plus" else oos[oos["tier"] != "pass"]
        w, l = int((s["result"] == "Win").sum()), int((s["result"] == "Loss").sum())
        hist.append({"tier": t, "label": TIERS.get(t, "All picks (3+ pt gap)"), "wins": w, "losses": l,
                     "pushes": int((s["result"] == "Push").sum()),
                     "win_pct": round(100 * w / max(w + l, 1), 1),
                     "units": round(w * (100 / 110) - l, 1),
                     "by_season": json.dumps({str(int(y)): [int((g["result"] == "Win").sum()),
                                                            int((g["result"] == "Loss").sum())]
                                              for y, g in s.groupby("season")}),
                     "description": TIER_BLURB.get(t, "Every game where the model and Vegas differ by 3+ points.")})
    tier_hist = pd.DataFrame(hist)
    tier_hist.to_csv(os.path.join(OUT, "tier_history.csv"), index=False)

    g = oos.dropna(subset=["overUnder"])
    am = g["home_pts"] - g["away_pts"]
    acc = {}
    for name, pm in {"Model": g["pred_home"] - g["pred_away"], "Vegas": -g["spread"]}.items():
        acc[name] = {"margin_MAE": round(float(np.abs(am - pm).mean()), 2),
                     "winner_pct": round(float((np.sign(am) == np.sign(pm)).mean() * 100), 1),
                     "games": int(len(g))}
    with open(os.path.join(OUT, "model_accuracy.json"), "w") as f:
        json.dump(acc, f, indent=2)

    # ---- 2) walk-forward picks for weeks already played this season (graded track record)
    past = []
    for w in cur_weeks:
        m = fit_model(data[trainable & ((data["season"] == PRIOR) |
                                        ((data["season"] == SEASON) & (data["week"] < w)))])
        past.append(pred_games(m, data[(data["season"] == SEASON) & (data["week"] == w)]))
    past = add_pick_cols(pd.concat(past).merge(lines_all, on="gameId", how="left"))
    past = past[past["tier"].notna()].assign(source="backtest")

    # ---- 3) final fit on everything, predict the upcoming week
    final = fit_model(data[trainable])
    sched = pd.read_csv(os.path.join(DATA, "schedule", f"week_{week}_games_{SEASON}.csv"))
    feats = ratings_before(games, SEASON, week, cls)
    neutral = (sched["neutralSite"].astype(str) == "True").values
    hs = np.where(neutral, 0.0, 1.0)
    conf = (sched["homeConference"] == sched["awayConference"]).astype(float).values
    home_rows = team_rows(pd.DataFrame({"team": sched["homeTeam"], "opponent": sched["awayTeam"],
                                        "home": hs, "conf_game": conf}), feats)
    away_rows = team_rows(pd.DataFrame({"team": sched["awayTeam"], "opponent": sched["homeTeam"],
                                        "home": -hs, "conf_game": conf}), feats)
    p = sched[["gameId", "week", "startDate", "homeTeam", "awayTeam", "homeConference", "awayConference",
               "spread", "overUnder"]].copy()
    p = p.merge(lines_c.rename(columns={"id": "gameId"})[["gameId", "spreadOpen"]], on="gameId", how="left")
    p["neutral"] = neutral
    p["conf_game"] = conf.astype(bool)
    p["pred_home"] = final.predict(home_rows[FEATURES]).clip(min=0)
    p["pred_away"] = final.predict(away_rows[FEATURES]).clip(min=0)
    p["model_total"] = p["pred_home"] + p["pred_away"]
    p["total_edge"] = p["model_total"] - p["overUnder"]
    p["home_games_played"] = home_rows["games_played"].values
    p["away_games_played"] = away_rows["games_played"].values
    p = add_pick_cols(p)
    p.round(1).to_csv(os.path.join(OUT, f"week_{week}_predictions_{SEASON}.csv"), index=False)

    # ---- 4) picks with plain-English explanations
    coef = dict(zip(FEATURES, final.coef_))
    hfa_pts = 2 * (feats.attrs["pts"][1] * coef["exp_pts"] + feats.attrs["rec"][1] * coef["exp_rec"] +
                   feats.attrs["yds"][1] * coef["exp_yds"] + coef["home"])
    hfa_conf = hfa_pts + 2 * coef["conf_home"]
    why_col, watch_col = [], []
    for _, r in p.iterrows():
        if pd.isna(r["tier"]):
            why_col.append(None); watch_col.append(None); continue
        _, why, watch = describe_game(r, feats, cls, hfa_conf if r["conf_game"] else hfa_pts)
        why_col.append(json.dumps(why)); watch_col.append(json.dumps(watch))
    p["why"], p["watch"] = why_col, watch_col
    pick_cols = ["gameId", "week", "startDate", "homeTeam", "awayTeam", "homeConference", "awayConference",
                 "spread", "spreadOpen", "overUnder", "pred_home", "pred_away", "model_spread", "model_total",
                 "edge", "total_edge", "tier", "pick_side", "pick", "pick_line", "conf_game", "neutral",
                 "home_games_played", "away_games_played", "why", "watch"]
    p[pick_cols].round(1).to_csv(os.path.join(OUT, f"week_{week}_picks_{SEASON}.csv"), index=False)

    # ---- 5) picks log: backtest rows for played weeks + live rows (locked at kickoff)
    keep = ["gameId", "week", "startDate", "homeTeam", "awayTeam", "spread", "model_spread", "edge",
            "tier", "pick_side", "pick", "pick_line", "source", "logged_at"]
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    live = p[p["tier"].notna()].assign(source="live", logged_at=stamp)
    log_path = os.path.join(OUT, f"picks_log_{SEASON}.csv")
    old_live = pd.DataFrame(columns=keep)
    if os.path.exists(log_path):
        old = pd.read_csv(log_path)
        old_live = old[old["source"] == "live"]
    kicked = pd.to_datetime(old_live["startDate"], utc=True, errors="coerce") <= now
    locked = old_live[kicked]                         # kicked-off live picks never change
    live = live[~live["gameId"].isin(locked["gameId"])]
    live_all = pd.concat([old_live[~old_live["gameId"].isin(live["gameId"])], live[keep]], ignore_index=True)
    past["logged_at"] = "backtest"
    backtest = past[~past["gameId"].isin(live_all["gameId"])][keep]
    log = pd.concat([backtest, live_all], ignore_index=True).sort_values(["week", "gameId"])
    log.round(1).to_csv(log_path, index=False)

    # ---- summary
    summary = [
        f"Score model -- trained on {PRIOR} wk{MIN_TRAIN_WEEK_FIRST_SEASON}+ and {SEASON} wk1-{last_week}"
        f" ({int(trainable.sum())} team-games)",
        f"Intercept: {final.intercept_:.2f}", "Coefficients:",
        pd.Series(final.coef_, index=FEATURES).round(3).to_string(),
        f"Home field on the spread: {hfa_pts:.1f} pts (non-conference), {hfa_conf:.1f} pts (conference)", "",
        "Out-of-sample backtest (fit on one season, predict the other):",
        json.dumps(acc, indent=2), "",
        "Pick tiers (against the spread, -110 odds):",
        tier_hist[["label", "wins", "losses", "win_pct", "units", "by_season"]].to_string(index=False),
    ]
    txt = "\n".join(summary)
    with open(os.path.join(OUT, "model_summary.txt"), "w") as f:
        f.write(txt + "\n")
    print(txt)
    print(f"\nWrote picks for week {week}: {OUT}/week_{week}_picks_{SEASON}.csv")


if __name__ == "__main__":
    main()
