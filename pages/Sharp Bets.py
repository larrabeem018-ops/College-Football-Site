"""
Sharp Bets -- where our score model disagrees with the Vegas line, why, and
how those picks have actually done.

Reads files written by score_model.py (run it after update_data.py each week):
  data/predictions/week_{W}_picks_{SEASON}.csv
  data/predictions/picks_log_{SEASON}.csv
  data/predictions/tier_history.csv
  data/predictions/model_accuracy.json
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from style import apply_style, html, ACCENT, ACCENT_TINT, BORDER, TEXT_SECONDARY, NEUTRAL_MID

st.set_page_config(page_title="Sharp Bets", page_icon="🏈", layout="wide")
apply_style()

PRED = "data/predictions"
SEASON = 2026
BREAK_EVEN = 52.4          # win % needed to profit at standard -110 odds
LOSS_RED = "#A63D32"
AMBER = "#7A5A00"
WATCHLIST = "fav_value"    # the only tier above break-even in every backtest so far
TIER_LABEL = {"fav_value": "Model backs the favorite", "big_gap": "Big disagreement",
              "lean": "Lean", "pass": "No edge"}

html(f"""
<style>
.sb-tier {{ display:inline-block; font-size:11.5px; font-weight:700; letter-spacing:.04em; white-space:nowrap;
  text-transform:uppercase; padding:3px 9px; border-radius:999px; margin:0 6px 4px 0; }}
.sb-tier-fav_value {{ background:{ACCENT_TINT}; color:{ACCENT}; }}
.sb-tier-big_gap {{ background:#F3ECDA; color:{AMBER}; }}
.sb-record {{ font-size:12.5px; color:{TEXT_SECONDARY}; }}
.sb-matchup {{ display:flex; align-items:center; gap:10px; margin:8px 0 2px; flex-wrap:wrap; }}
.sb-matchup img {{ width:30px; height:30px; object-fit:contain; }}
.sb-matchup-name {{ font-family:'Spectral', serif; font-weight:600; font-size:20px; }}
.sb-kick {{ font-size:12.5px; color:{TEXT_SECONDARY}; margin-bottom:12px; }}
.sb-pick {{ font-family:'Spectral', serif; font-size:26px; font-weight:600; color:{ACCENT}; line-height:1.1; }}
.sb-pick.sb-muted {{ color:{AMBER}; font-size:22px; }}
.sb-pick-label {{ font-size:11.5px; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
  color:{TEXT_SECONDARY}; }}
.sb-lines {{ display:flex; gap:22px; flex-wrap:wrap; margin:12px 0 4px; padding:10px 0;
  border-top:1px solid {BORDER}; border-bottom:1px solid {BORDER}; }}
.sb-lines div {{ font-size:12px; color:{TEXT_SECONDARY}; }}
.sb-lines b {{ display:block; font-size:15px; color:#0A0906; font-weight:700; }}
.sb-callout {{ background:#FFFFFF; border:1px solid {BORDER}; border-left:4px solid #B8860B;
  border-radius:8px; padding:14px 18px; font-size:14px; line-height:1.55; }}
.sb-sub {{ font-size:13px; font-weight:600; margin-top:4px; }}
</style>
""")


# ----------------------------------------------------------------------------- data
def week_files():
    out = {}
    for f in glob.glob(os.path.join(PRED, f"week_*_picks_{SEASON}.csv")):
        m = re.search(r"week_(\d+)_picks", f)
        if m:
            out[int(m.group(1))] = f
    return dict(sorted(out.items()))


def mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0


@st.cache_data
def load_picks(path, _mtime):
    df = pd.read_csv(path)
    for c in ("why", "watch"):
        df[c] = df[c].apply(lambda s: json.loads(s) if isinstance(s, str) else [])
    df["kick"] = pd.to_datetime(df["startDate"], utc=True).dt.tz_convert("America/New_York")
    return df


@st.cache_data
def load_logos():
    try:
        info = pd.read_csv("data/team_info.csv")
        return dict(zip(info["school"], info["logos"]))
    except Exception:
        return {}


@st.cache_data
def load_tier_history(_mtime):
    th = pd.read_csv(os.path.join(PRED, "tier_history.csv"))
    th["by_season"] = th["by_season"].apply(json.loads)
    return th.set_index("tier")


@st.cache_data
def load_graded_log(_m1, _m2):
    log = pd.read_csv(os.path.join(PRED, f"picks_log_{SEASON}.csv"))
    lines = pd.read_csv(f"data/espnBetLines_{SEASON}.csv")[["id", "homeScore", "awayScore"]]
    log = log.merge(lines.rename(columns={"id": "gameId"}), on="gameId", how="left")
    cover = (log["homeScore"] - log["awayScore"]) + log["spread"]
    played = log["homeScore"].notna()
    pick_home = log["pick_side"] == "home"
    log["result"] = np.where(~played, "Pending",
                             np.where(cover == 0, "Push",
                                      np.where((cover > 0) == pick_home, "Win", "Loss")))
    log["units"] = log["result"].map({"Win": 100 / 110, "Loss": -1.0, "Push": 0.0, "Pending": 0.0})
    return log


def record(df):
    w, l = int((df["result"] == "Win").sum()), int((df["result"] == "Loss").sum())
    p = int((df["result"] == "Push").sum())
    return w, l, p, (100 * w / (w + l) if w + l else None)


def fmt_record(w, l, p=0):
    return f"{w}-{l}" + (f"-{p}" if p else "")


def line_text(team, home, spread_home):
    v = spread_home if team == home else -spread_home
    return f"{team} {'+' if v > 0 else ''}{v:.1f}" if abs(v) > 0.01 else f"{team} PK"


def kick_long(ts):
    """'Sat Oct 3, 12:00 PM ET' without %-d / %-I, which don't work on Windows."""
    return f"{ts:%a %b} {ts.day}, {ts.hour % 12 or 12}:{ts:%M %p} ET"


def kick_short(ts):
    return f"{ts:%a} {ts.hour % 12 or 12}:{ts:%M %p}"


def stat_card(value, label, sub=None, sub_color=None):
    sub_html = f'<div class="sb-sub" style="color:{sub_color or TEXT_SECONDARY}">{sub}</div>' if sub else ""
    html(f"""
    <div class="cfb-stat-card">
      <div class="cfb-stat-value">{value}</div>
      <div class="cfb-stat-label">{label}</div>
      {sub_html}
    </div>
    """)


def pct_color(pct):
    return ACCENT if pct is not None and pct >= BREAK_EVEN else LOSS_RED


# ----------------------------------------------------------------------------- guard
weeks = week_files()
if not weeks or not os.path.exists(os.path.join(PRED, "tier_history.csv")):
    st.title("Sharp Bets")
    st.warning("No model picks found yet. Run `python score_model.py` after `python update_data.py` "
               "to generate this week's picks.")
    st.stop()

logos = load_logos()
tier_hist = load_tier_history(mtime(os.path.join(PRED, "tier_history.csv")))
acc_path = os.path.join(PRED, "model_accuracy.json")
acc = json.load(open(acc_path)) if os.path.exists(acc_path) else None
log = load_graded_log(mtime(os.path.join(PRED, f"picks_log_{SEASON}.csv")),
                      mtime(f"data/espnBetLines_{SEASON}.csv"))
done = log[log["result"] != "Pending"]

# ----------------------------------------------------------------------------- header
html('<div class="cfb-eyebrow">Model vs. the line</div>')
st.title("Sharp Bets")
html(f"""
<p style="font-size:15.5px; line-height:1.6; max-width:760px; color:{TEXT_SECONDARY}; margin-top:-6px;">
Each week our score model sets its own point spread for every game. When it disagrees with Vegas in the
one way that has held up in testing, the game makes the watchlist, with a plain-English explanation of
why. Every pick is saved before kickoff and graded afterward, so you can see whether it's working.
</p>
""")

tab_week, tab_record, tab_how = st.tabs(["This Week", "Track Record", "How It Works"])

# ============================================================================= THIS WEEK
with tab_week:
    wk = st.selectbox("Week", list(weeks), index=len(weeks) - 1, format_func=lambda w: f"Week {w}")
    picks = load_picks(weeks[wk], mtime(weeks[wk]))
    graded = log[log["week"] == wk].set_index("gameId")["result"].to_dict()

    # --- trust strip
    fav = tier_hist.loc[WATCHLIST]
    by = fav["by_season"]
    season_live = done[(done["tier"] == WATCHLIST)]
    sw, sl, sp, spct = record(season_live)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card(int((picks["tier"] == WATCHLIST).sum()), "Watchlist games this week")
    with c2:
        stat_card(f"{fav['wins']}-{fav['losses']}", "Watchlist record in past-season testing",
                  f"{fav['win_pct']}% · " + " · ".join(f"{y}: {v[0]}-{v[1]}" for y, v in by.items()),
                  pct_color(fav["win_pct"]))
    with c3:
        stat_card(fmt_record(sw, sl, sp) if sw + sl else "—", f"Watchlist this season ({SEASON})",
                  f"{spct:.1f}% · need {BREAK_EVEN}% to profit" if spct is not None else f"need {BREAK_EVEN}% to profit",
                  pct_color(spct))
    with c4:
        if acc:
            stat_card(f"{acc['Model']['margin_MAE']:.1f} pts", "Model's average miss on the final margin",
                      f"Vegas: {acc['Vegas']['margin_MAE']:.1f} pts", TEXT_SECONDARY)

    html("<div style='height:14px'></div>")
    html(f"""
    <div class="sb-callout">
    <b>Read this first.</b> Across all games, Vegas is more accurate than this model. The watchlist is
    the one kind of disagreement that has beaten the {BREAK_EVEN}% break-even rate in every test so far,
    and only by a few points. Treat these picks as leads to research (injuries, weather, QB news), not locks.
    </div>
    """)
    html("<div style='height:18px'></div>")

    # --- cards
    def card(r, muted=False):
        th = tier_hist.loc[r["tier"]]
        seasons = " · ".join(f"{y}: {v[0]}-{v[1]}" for y, v in th["by_season"].items())
        away_logo, home_logo = logos.get(r["awayTeam"], ""), logos.get(r["homeTeam"], "")
        res = graded.get(r["gameId"])
        badge = ""
        if res in ("Win", "Loss", "Push"):
            col = ACCENT if res == "Win" else (LOSS_RED if res == "Loss" else NEUTRAL_MID)
            badge = f'<span class="sb-tier" style="background:{col}; color:#fff;">{res}</span>'
        with st.container(border=True):
            html(f"""
            <div><span class="sb-tier sb-tier-{r['tier']}">{TIER_LABEL[r['tier']]}</span>{badge}</div>
            <div class="sb-record">Past record for this kind of pick: <b>{th['wins']}-{th['losses']}</b>
              ({th['win_pct']}%) · {seasons}</div>
            <div class="sb-matchup">
              {'<img src="' + away_logo + '">' if away_logo else ''}
              <span class="sb-matchup-name">{r['awayTeam']} @ {r['homeTeam']}</span>
              {'<img src="' + home_logo + '">' if home_logo else ''}
            </div>
            <div class="sb-kick">{kick_long(r['kick'])}</div>
            <div class="sb-pick-label">{'Model lean' if muted else 'The pick'}</div>
            <div class="sb-pick{' sb-muted' if muted else ''}">{r['pick_line']}</div>
            <div class="sb-lines">
              <div>Vegas line<b>{line_text(r['homeTeam'], r['homeTeam'], r['spread'])}</b></div>
              <div>Model line<b>{line_text(r['homeTeam'], r['homeTeam'], round(r['model_spread'], 1))}</b></div>
              <div>Model score<b>{r['awayTeam']} {r['pred_away']:.0f}, {r['homeTeam']} {r['pred_home']:.0f}</b></div>
            </div>
            """)
            st.markdown("**Why the model likes it**")
            st.markdown("\n".join(f"- {b}" for b in r["why"]))
            with st.expander("What could go wrong", expanded=muted):
                st.markdown("\n".join(f"- {b}" for b in r["watch"]))

    def card_grid(df, muted=False):
        for i in range(0, len(df), 2):
            cols = st.columns(2)
            for col, (_, r) in zip(cols, df.iloc[i:i + 2].iterrows()):
                with col:
                    card(r, muted)

    st.subheader(f"Week {wk} watchlist")
    st.caption("A 3.5- to 14-point favorite that the model thinks should be favored by at least 3 more points.")
    wl_games = picks[picks["tier"] == WATCHLIST].sort_values("edge", key=lambda s: -s.abs())
    if wl_games.empty:
        st.info("No watchlist games this week. The model and Vegas mostly agree on the favorites.")
    else:
        card_grid(wl_games)

    big = picks[picks["tier"] == "big_gap"].sort_values("edge", key=lambda s: -s.abs())
    if not big.empty:
        html("<div style='height:10px'></div>")
        st.subheader("Big disagreements: check the news")
        bg = tier_hist.loc["big_gap"]
        st.caption(f"The model's line is 10+ points from Vegas. These have gone {bg['wins']}-{bg['losses']} "
                   f"({bg['win_pct']}%) in testing, but they lost in {SEASON}. A gap this big usually means Vegas "
                   f"knows something the box scores don't, so they're not recommended as picks.")
        card_grid(big, muted=True)

    # --- everything else
    html("<div style='height:10px'></div>")
    st.subheader("All games this week")
    ln, ps = tier_hist.loc["lean"], tier_hist.loc["pass"]
    st.caption(f"Smaller disagreements (3–10 points) have gone {ln['wins']}-{ln['losses']} ({ln['win_pct']}%) in "
               f"testing, and games where the model roughly agrees with Vegas {ps['wins']}-{ps['losses']} "
               f"({ps['win_pct']}%). Both are below break-even, so they're shown for reference only.")

    allg = picks.copy()
    allg["Matchup"] = allg["awayTeam"] + " @ " + allg["homeTeam"]
    allg["Kickoff"] = allg["kick"].apply(kick_short)
    allg["Vegas"] = [line_text(h, h, s) if not pd.isna(s) else "No line"
                     for h, s in zip(allg["homeTeam"], allg["spread"])]
    allg["Model"] = [line_text(h, h, round(s, 1)) for h, s in zip(allg["homeTeam"], allg["model_spread"])]
    allg["Gap"] = allg["edge"].abs().round(1)
    allg["Model lean"] = np.where(allg["tier"].isna(), "—",
                                  np.where(allg["tier"] == "pass", "No edge", allg["pick_line"]))
    allg["Category"] = allg["tier"].map(TIER_LABEL).fillna("No line")
    allg["Model score"] = (allg["awayTeam"] + " " + allg["pred_away"].round().astype(int).astype(str)
                           + ", " + allg["homeTeam"] + " " + allg["pred_home"].round().astype(int).astype(str))
    allg["O/U"] = allg["overUnder"]
    allg["Model total"] = allg["model_total"].round(1)
    allg["Result"] = allg["gameId"].map(graded).fillna("")
    order = {"fav_value": 0, "big_gap": 1, "lean": 2, "pass": 3}
    allg = allg.assign(_o=allg["tier"].map(order).fillna(4), _g=-allg["Gap"].fillna(0)).sort_values(["_o", "_g"])
    show = ["Matchup", "Kickoff", "Vegas", "Model", "Gap", "Model lean", "Category", "Model score", "O/U", "Model total"]
    if allg["Result"].isin(["Win", "Loss", "Push"]).any():
        show.append("Result")
    st.dataframe(allg[show], use_container_width=True, hide_index=True,
                 column_config={
                     "Gap": st.column_config.NumberColumn(format="%.1f", help="Points between the model's line and Vegas"),
                     "O/U": st.column_config.NumberColumn(format="%.1f"),
                     "Model total": st.column_config.NumberColumn(
                         format="%.1f", help="For reference only: the model's totals haven't beaten the over/under.")})

    explainable = allg[allg["tier"].notna()]
    choice = st.selectbox("Explain any game", ["—"] + explainable["Matchup"].tolist())
    if choice != "—":
        r = explainable[explainable["Matchup"] == choice].iloc[0]
        if r["tier"] == "pass":
            st.markdown(f"The model and Vegas are within **{abs(r['edge']):.1f} points** here, so there's "
                        f"no lean. The model has it {r['Model']}.")
        else:
            st.markdown(f"**Model lean: {r['pick_line']}** ({TIER_LABEL[r['tier']]})")
            st.markdown("\n".join(f"- {b}" for b in r["why"]))
            st.markdown("**What could go wrong**")
            st.markdown("\n".join(f"- {b}" for b in r["watch"]))

# ============================================================================= TRACK RECORD
with tab_record:
    st.subheader(f"{SEASON} season")
    st.caption("Each pick is graded against the line it was made at. **Live** picks are saved before kickoff "
               "by score_model.py and locked once the game starts. **Backtest** picks cover the weeks before "
               "this page existed; they were rebuilt using only information available before each game.")
    rows = [("Watchlist", done[done["tier"] == WATCHLIST]),
            ("Big disagreements", done[done["tier"] == "big_gap"]),
            ("Leans (3–10 pt gap)", done[done["tier"] == "lean"]),
            ("Watchlist, live picks only", done[(done["tier"] == WATCHLIST) & (done["source"] == "live")])]
    for col, (name, df) in zip(st.columns(4), rows):
        w, l, p, pct = record(df)
        with col:
            units = df["units"].sum()
            stat_card(fmt_record(w, l, p) if w + l else "None yet", name,
                      f"{pct:.1f}% · {units:+.1f} units" if pct is not None else "Graded after this week's games",
                      pct_color(pct) if pct is not None else TEXT_SECONDARY)

    chart = done.sort_values(["week", "gameId"])
    fig = go.Figure()
    for name, mask, color, dash in [
        ("Watchlist", chart["tier"] == WATCHLIST, ACCENT, "solid"),
        ("Big disagreements", chart["tier"] == "big_gap", "#B8860B", "dash"),
        ("Every game with a 3+ pt gap", chart["tier"] != "pass", NEUTRAL_MID, "dot"),
    ]:
        s = chart[mask].groupby("week")["units"].sum().cumsum()
        if len(s):
            fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, mode="lines+markers",
                                     line=dict(color=color, width=2.6 if dash == "solid" else 1.8, dash=dash),
                                     hovertemplate="Week %{x}: %{y:+.1f} units<extra>" + name + "</extra>"))
    fig.add_hline(y=0, line_color="#BDBBB6")
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="white",
                      paper_bgcolor="rgba(0,0,0,0)", title="Running profit in units (1 unit per pick at -110 odds)",
                      xaxis=dict(title="Week", dtick=1, gridcolor="#F0EFEC"),
                      yaxis=dict(title="Units", gridcolor="#F0EFEC", zeroline=False),
                      legend=dict(orientation="h", y=-0.25), font=dict(family="Manrope"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Pick log**")
    which = st.radio("Show", ["Watchlist", "Big disagreements", "All picks"], horizontal=True, label_visibility="collapsed")
    t = log[log["tier"] != "pass"]
    if which == "Watchlist":
        t = t[t["tier"] == WATCHLIST]
    elif which == "Big disagreements":
        t = t[t["tier"] == "big_gap"]
    t = t.sort_values(["week", "gameId"], ascending=[False, True]).copy()
    t["Matchup"] = t["awayTeam"] + " @ " + t["homeTeam"]
    t["Score"] = np.where(t["homeScore"].notna(),
                          t["awayScore"].fillna(0).astype(int).astype(str) + "-"
                          + t["homeScore"].fillna(0).astype(int).astype(str), "")
    t["Category"] = t["tier"].map(TIER_LABEL)
    t["Source"] = t["source"].str.title()
    t["Gap"] = t["edge"].abs().round(1)
    st.dataframe(t[["week", "Matchup", "pick_line", "Category", "Gap", "Score", "result", "Source"]]
                 .rename(columns={"week": "Wk", "pick_line": "Pick", "result": "Result"}),
                 use_container_width=True, hide_index=True)

# ============================================================================= HOW IT WORKS
with tab_how:
    st.subheader("How the model sets its line")
    st.markdown("""
1. **Rate every team, adjusted for schedule.** Each week, every game played so far goes into one big
   regression that estimates how many points each offense scores and each defense allows compared with
   average, *after accounting for who they played*. Scoring 35 on a top-10 defense counts for more than
   scoring 35 on a bottom-10 one. Last season's games count too, at a reduced weight that fades as the
   season goes on.
2. **Weight recent form.** A second version counts the last 3 weeks three times as heavily, which catches
   teams that are improving or slipping.
3. **Rate play-by-play efficiency.** Final scores are noisy: a fluky touchdown or a pick-six can swing
   them. So the model also rates every offense and defense on **success rate** (the share of plays that
   keep an offense on schedule) and **EPA per play** (expected points added), with garbage time removed
   and adjusted for schedule. Adding these improved both accuracy and the pick record in both seasons tested.
4. **Predict each team's score.** A regression turns those ratings, plus yards and home field, into a
   predicted score for each team. Home field is worth much less in conference games (about 1 pt)
   than in non-conference games, where home teams usually host opponents they match up well against.
5. **Compare with Vegas.** The gap between the model's spread and the Vegas spread puts each game in a category.
    """)

    st.subheader("How each category has done")
    st.caption("Past-season testing: each season's picks come from a model fit on the *other* season, then graded "
               "against the closing line. Break-even at -110 odds is 52.4%.")
    th = tier_hist.reset_index()
    th["Record"] = th["wins"].astype(str) + "-" + th["losses"].astype(str)
    for y in ("2025", "2026"):
        th[y] = th["by_season"].apply(lambda d: f"{d[y][0]}-{d[y][1]}" if y in d else "—")
    th["Shown as a pick?"] = np.where(th["tier"] == WATCHLIST, "Yes (watchlist)",
                                      np.where(th["tier"] == "big_gap", "Flagged, not picked", "No"))
    st.dataframe(th[["label", "description", "Record", "win_pct", "units", "2025", "2026", "Shown as a pick?"]]
                 .rename(columns={"label": "Category", "description": "What it means", "win_pct": "Win %",
                                  "units": "Profit (units)"}),
                 use_container_width=True, hide_index=True,
                 column_config={"Win %": st.column_config.ProgressColumn(format="%.1f%%", min_value=40, max_value=60),
                                "What it means": st.column_config.TextColumn(width="large")})

    st.subheader("What we tested that didn't help")
    st.markdown("""
- **Turnover margin, 3rd-down %, travel distance, time zones, rest days, bye weeks, altitude**: none of
  these improved the model's accuracy or its record against the spread.
- **A neural network**: no better than the simple model at picking winners, and worse at win probabilities.
- **Betting against a team with a new starting QB**: looked like a 60% edge at first, but it turned out
  to be a data leak. Measured cleanly it's a coin flip, because Vegas already prices in QB changes.
- **Returning production and roster talent**: made early-season scores more accurate, but made the picks
  worse. Vegas already prices this in, so it's left out.
- **Pace (plays per game)**: didn't help the over/under.
- **Over/unders**: the model's totals haven't beaten the posted total, so totals are for reference only.
    """)
    st.subheader("What the model can't see")
    st.markdown("""
Injuries (beyond what already shows up in results), weather, suspensions, motivation, coaching changes,
and anything else that isn't in a box score. When the model disagrees with Vegas by 10+ points, one of
these is often the reason.
    """)

html("""
<div class="cfb-footer">
  <span>For entertainment and analysis, not betting advice. If you bet, only bet what you can afford to lose.</span>
  <span>Model: opponent-adjusted scoring + efficiency ratings, linear regression · updated weekly by score_model.py</span>
</div>
""")
