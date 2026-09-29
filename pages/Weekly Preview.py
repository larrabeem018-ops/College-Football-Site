import glob
import os
import re

import pandas as pd
import streamlit as st

from style import apply_style, html, ACCENT, ACCENT_TINT, TEXT_SECONDARY, TEXT_FOOTER

st.set_page_config(page_title="Weekly Preview", page_icon="🏈", layout="wide")
apply_style()

PRIOR_SEASON = 2025      # last completed season -> season stats fall back here early in the year
UPCOMING_SEASON = 2026   # current season -> schedule/spreads + (eventually) in-season stats
MIN_GAMES_FOR_CURRENT_SEASON = 1  # below this many games played, prefer last year's numbers

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_team_info():
    try:
        info = pd.read_csv("data/team_info.csv")
        logo_map = dict(zip(info["school"], info["logos"]))
        conf_map = dict(zip(info["school"], info["conference"]))
        return logo_map, conf_map
    except Exception:
        return {}, {}


@st.cache_data
def load_rosters_and_stats():
    roster_prior = pd.read_csv("Roster_2024.csv")
    roster_upcoming = pd.read_csv("Roster_2025.csv")
    player_stats = pd.read_csv("data/player_stats_2024.csv")
    roster_prior["id"] = roster_prior["id"].astype(str)
    roster_upcoming["id"] = roster_upcoming["id"].astype(str)
    player_stats["playerId"] = player_stats["playerId"].astype(str)
    return roster_prior, roster_upcoming, player_stats


@st.cache_data
def load_fbs_teams():
    """FBS team names, used to filter the schedule to FBS games (at least one
    team is FBS) -- keeps marquee week-1 buy games against an FCS/DII
    opponent, drops FCS/DII/DIII-only matchups. Applied here (not just in
    update_data.py) so it also cleans up a schedule file you already pulled
    before this filter existed, with no re-fetch needed."""
    try:
        teams = pd.read_csv("data/teams.csv")
        return set(teams.loc[teams["classification"].str.lower() == "fbs", "school"])
    except Exception:
        return None


@st.cache_data
def load_team_season_stats():
    frames = {}
    for yr in (UPCOMING_SEASON, PRIOR_SEASON):
        path = f"data/team_season_stats_{yr}.csv"
        if os.path.exists(path):
            frames[yr] = pd.read_csv(path).set_index("team")
    return frames


@st.cache_data
def discover_week_files():
    files = sorted(glob.glob(f"data/schedule/week_*_games_{UPCOMING_SEASON}.csv"))
    weeks = []
    for f in files:
        m = re.search(r"week_(\d+)_games_", f)
        if m:
            weeks.append((int(m.group(1)), f))
    return sorted(weeks)


# ---------------------------------------------------------------------------
# "Returning production" -- reuses the same usage-weighted impact score the
# Team Comparison / Roster Analysis pages use, so the numbers stay consistent
# across the site. A player "returns" if their id shows up on the same
# team's UPCOMING_SEASON roster.
# ---------------------------------------------------------------------------

POSITION_MAP = {
    "QB": "QB", "RB": "RB", "TB": "RB", "HB": "RB",
    "WR": "WR", "TE": "TE", "FB": "RB",
    "OL": "OL", "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    "DL": "DL", "DE": "DL", "DT": "DL", "NT": "DL", "EDGE": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB",
    "DB": "DB", "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB",
    "K": "K", "P": "P", "KR": "KR", "PR": "PR", "LS": "LS",
}


def normalize_position(pos):
    if not isinstance(pos, str) or pos == "":
        return "OTHER"
    pos = pos.strip().upper()
    return POSITION_MAP.get(pos, pos)


def _safe_get(row, col):
    return row[col] if col in row and pd.notna(row[col]) else 0


def compute_performance_metric(row):
    g = normalize_position(row.get("position", ""))
    p_yards, p_td = _safe_get(row, "passing_YDS"), _safe_get(row, "passing_TD")
    p_int, p_ypa = _safe_get(row, "passing_INT"), _safe_get(row, "passing_YPA")
    r_yards, r_td = _safe_get(row, "rushing_YDS"), _safe_get(row, "rushing_TD")
    rec_yards, rec_td = _safe_get(row, "receiving_YDS"), _safe_get(row, "receiving_TD")
    d_tot, d_sack = _safe_get(row, "defensive_TOT"), _safe_get(row, "defensive_SACKS")
    d_tfl, d_pd = _safe_get(row, "defensive_TFL"), _safe_get(row, "defensive_PD")
    d_td, ints = _safe_get(row, "defensive_TD"), _safe_get(row, "interceptions_INT")
    ints_td = _safe_get(row, "interceptions_TD")
    kick_pts = _safe_get(row, "kicking_PTS")
    punt_no, punt_ypp = _safe_get(row, "punting_NO"), _safe_get(row, "punting_YPP")
    kr_yds, kr_td = _safe_get(row, "kickReturns_YDS"), _safe_get(row, "kickReturns_TD")
    pr_yds, pr_td = _safe_get(row, "puntReturns_YDS"), _safe_get(row, "puntReturns_TD")

    if g == "QB":
        return p_yards + 20 * p_td - 45 * p_int + r_yards + 20 * r_td + 5 * p_ypa
    if g == "RB":
        return r_yards + 20 * r_td + 0.5 * rec_yards + 10 * rec_td
    if g in ("WR", "TE"):
        return rec_yards + 20 * rec_td
    if g == "OL":
        return 0
    if g == "DL":
        return d_tot + 4 * d_sack + 2 * d_tfl + 6 * d_td
    if g == "LB":
        return d_tot + 3 * d_sack + 1.5 * d_tfl + 6 * d_td + 3 * ints
    if g == "DB":
        return d_tot + 3 * ints + 10 * ints_td + 1.5 * d_pd
    if g == "K":
        return kick_pts
    if g == "P":
        return punt_no * punt_ypp
    if g == "KR":
        return kr_yds + 20 * kr_td
    if g == "PR":
        return pr_yds + 20 * pr_td
    return 0


def returning_production(team, roster_prior, roster_upcoming, player_stats):
    last = roster_prior[roster_prior["team"] == team].copy()
    if last.empty:
        return None
    last = last.merge(player_stats, left_on="id", right_on="playerId", how="left")
    stat_cols = [c for c in player_stats.columns if c != "playerId"]
    for c in stat_cols:
        last[c] = pd.to_numeric(last[c], errors="coerce").fillna(0)
    last["impact"] = last.apply(compute_performance_metric, axis=1).clip(lower=0)

    this_year_ids = set(roster_upcoming.loc[roster_upcoming["team"] == team, "id"])
    last["returning"] = last["id"].isin(this_year_ids)

    total = last["impact"].sum()
    returning = last.loc[last["returning"], "impact"].sum()
    pct = (returning / total * 100) if total else None
    return {
        "pct": pct,
        "returning_players": int(last["returning"].sum()),
        "total_players": len(last),
    }


def _valid_logo(url):
    # team_info.csv can have a blank/missing logo for some schools, which
    # pandas reads back as NaN (a float) -- and bool(nan) is True in Python,
    # so a plain truthiness check lets NaN slip through into st.image() and
    # crashes the page. Require an actual non-empty string.
    return isinstance(url, str) and url.strip() != ""


# ---------------------------------------------------------------------------
# Team season stats lookup, preferring in-season (UPCOMING_SEASON) numbers
# once a team has played enough games, otherwise falling back to last year.
# ---------------------------------------------------------------------------

def get_team_stats(team, season_frames):
    for yr in (UPCOMING_SEASON, PRIOR_SEASON):
        df = season_frames.get(yr)
        if df is None or team not in df.index:
            continue
        row = df.loc[team]
        if yr == UPCOMING_SEASON and row.get("games", 0) < MIN_GAMES_FOR_CURRENT_SEASON:
            continue
        return row, yr
    for yr in (UPCOMING_SEASON, PRIOR_SEASON):
        df = season_frames.get(yr)
        if df is not None and team in df.index:
            return df.loc[team], yr
    return None, None


STAT_ROWS = [
    ("Offensive Yards / Game", "off_yards_pg", "higher", "{:.0f}"),
    ("Points / Game", "off_points_pg", "higher", "{:.1f}"),
    ("3rd Down Conversion % (Off.)", "off_third_down_pct", "higher", "{:.1f}%"),
    ("Yards Allowed / Game", "def_yards_pg", "lower", "{:.0f}"),
    ("Points Allowed / Game", "def_points_pg", "lower", "{:.1f}"),
    ("3rd Down Allowed % (Def.)", "def_third_down_pct", "lower", "{:.1f}%"),
    ("Turnovers Forced / Game", "turnovers_forced_pg", "higher", "{:.2f}"),
    ("Turnover Margin / Game", "turnover_margin_pg", "higher", "{:+.2f}"),
]


def render_stat_table(home, home_stats, away, away_stats):
    rows_html = []
    for label, col, better, fmt in STAT_ROWS:
        hv = home_stats.get(col) if home_stats is not None else None
        av = away_stats.get(col) if away_stats is not None else None
        h_txt = fmt.format(hv) if hv is not None and pd.notna(hv) else "—"
        a_txt = fmt.format(av) if av is not None and pd.notna(av) else "—"

        h_better = a_better = False
        if hv is not None and av is not None and pd.notna(hv) and pd.notna(av) and hv != av:
            if better == "higher":
                h_better, a_better = hv > av, av > hv
            else:
                h_better, a_better = hv < av, av < hv

        h_class = "cfb-stat-better" if h_better else ""
        a_class = "cfb-stat-better" if a_better else ""
        rows_html.append(
            f'<tr><td class="{h_class}">{h_txt}</td>'
            f'<td class="cfb-stat-label-cell">{label}</td>'
            f'<td class="{a_class}">{a_txt}</td></tr>'
        )

    html(
        f"""
        <table class="cfb-stat-table">
          <thead>
            <tr><th>{home}</th><th></th><th>{away}</th></tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
        """
    )


def render_watch_column(team, roster_prior, roster_upcoming, player_stats):
    rp = returning_production(team, roster_prior, roster_upcoming, player_stats)
    if rp and rp["pct"] is not None:
        html(
            f"""
            <div class="cfb-pill">Returning Production: <b>{rp['pct']:.0f}%</b></div>
            <div style="font-size:12px; color:{TEXT_SECONDARY}; margin:4px 0 12px;">
              {rp['returning_players']} of {rp['total_players']} contributors from last season's roster are back
            </div>
            """
        )
    else:
        html(f'<div style="font-size:12px; color:{TEXT_SECONDARY}; margin-bottom:12px;">Returning production data unavailable.</div>')


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

html('<div class="cfb-eyebrow">GAME WEEK</div>')
html('<h1 style="margin-bottom:6px;">Weekly Preview</h1>')
html(
    f"""
    <p style="font-size:15px; color:{TEXT_SECONDARY}; max-width:680px; margin-bottom:20px;">
      This week's matchups with the spread, a stat-for-stat team comparison, and what to watch
      for in each game. Early in the season, stat comparisons use last year's full-season numbers
      until a team has played {MIN_GAMES_FOR_CURRENT_SEASON}+ games this year, then switch over automatically.
    </p>
    """
)

logo_map, conf_map = load_team_info()
roster_prior, roster_upcoming, player_stats = load_rosters_and_stats()
season_frames = load_team_season_stats()
week_files = discover_week_files()

use_sample = False
games_df = pd.DataFrame()
selected_week = None

if week_files:
    week_numbers = [w for w, _ in week_files]
    selected_week = st.selectbox("Select week", week_numbers, format_func=lambda w: f"Week {w}")
    path = dict(week_files)[selected_week]
    games_df = pd.read_csv(path)

    # Filter down to FBS games (at least one team is FBS) even if this file was
    # pulled before update_data.py did this filtering itself -- no re-fetch needed.
    fbs_teams = load_fbs_teams()
    if fbs_teams and {"homeTeam", "awayTeam"}.issubset(games_df.columns):
        before = len(games_df)
        games_df = games_df[
            games_df["homeTeam"].isin(fbs_teams) | games_df["awayTeam"].isin(fbs_teams)
        ].copy()
        if before > len(games_df):
            st.caption(f"Showing {len(games_df)} FBS games (filtered out {before - len(games_df)} FCS/DII/DIII-only matchups).")
else:
    html(
        f"""
        <div class="cfb-card" style="margin-bottom:16px;">
          <div class="cfb-card-title">No schedule loaded yet</div>
          <div class="cfb-card-desc">
            This page reads <code>data/schedule/week_N_games_{UPCOMING_SEASON}.csv</code>, which
            <code>update_data.py</code> doesn't pull by default (it needs a specific week).
            Run it locally once you know which week to preview:
          </div>
          <div style="font-family:monospace; background:{ACCENT_TINT}; padding:8px 12px; border-radius:6px; margin-top:8px; font-size:13px;">
            python update_data.py --week 1
          </div>
        </div>
        """
    )
    use_sample = st.checkbox("Preview the layout with sample matchups (not real data)", value=True)
    if use_sample:
        games_df = pd.DataFrame([
            {"gameId": -1, "week": 1, "startDate": "2026-08-29T23:30:00Z", "homeTeam": "Ohio State", "awayTeam": "Texas", "formattedSpread": "Ohio State -3.5", "overUnder": 51.5},
            {"gameId": -2, "week": 1, "startDate": "2026-08-30T16:00:00Z", "homeTeam": "Alabama", "awayTeam": "Florida State", "formattedSpread": "Alabama -9.5", "overUnder": 47.5},
            {"gameId": -3, "week": 1, "startDate": "2026-08-30T19:30:00Z", "homeTeam": "Georgia", "awayTeam": "Marshall", "formattedSpread": "Georgia -27.5", "overUnder": 55.5},
        ])
        selected_week = 1

if not games_df.empty:
    # Conference filter -- driven by team_info.csv's conference for each team
    # (not the schedule file's own homeConference/awayConference columns, so
    # this works the same way for real and sample data alike). A game counts
    # if either team belongs to the selected conference, so interconference
    # matchups still show up under both teams' conferences.
    games_df["_homeConf"] = games_df["homeTeam"].map(conf_map)
    games_df["_awayConf"] = games_df["awayTeam"].map(conf_map)
    conferences = sorted(
        {c for c in pd.concat([games_df["_homeConf"], games_df["_awayConf"]]).dropna().unique()}
    )
    selected_conf = "All Conferences"
    if conferences:
        selected_conf = st.selectbox("Filter by conference", ["All Conferences"] + conferences)
        if selected_conf != "All Conferences":
            games_df = games_df[
                (games_df["_homeConf"] == selected_conf) | (games_df["_awayConf"] == selected_conf)
            ]

    if use_sample:
        html(f'<div class="cfb-pill" style="background:#FFF3CD; color:#7A5B00;">Sample data — not this week\'s real matchups</div>')

    if "startDate" in games_df.columns:
        parsed = pd.to_datetime(games_df["startDate"], errors="coerce", utc=True)
        try:
            parsed = parsed.dt.tz_convert("America/New_York")
        except Exception:
            pass
        games_df = games_df.assign(_kickoff=parsed)
        games_df = games_df.sort_values("_kickoff")

    week_label = f"{len(games_df)} games — Week {selected_week}"
    if selected_conf != "All Conferences":
        week_label += f" · {selected_conf}"
    st.caption(week_label)

    for _, game in games_df.iterrows():
        home, away = game.get("homeTeam"), game.get("awayTeam")
        home_logo, away_logo = logo_map.get(home, ""), logo_map.get(away, "")

        kickoff_txt = "Time TBD"
        if pd.notna(game.get("_kickoff")):
            dt = game["_kickoff"]
            hour12 = dt.hour % 12
            hour12 = 12 if hour12 == 0 else hour12
            ampm = "AM" if dt.hour < 12 else "PM"
            # Built manually rather than with %-d / %-I (no-pad strftime flags are
            # Linux-only and raise on Windows, which is where this app actually runs).
            kickoff_txt = f"{dt.strftime('%a, %b')} {dt.day} · {hour12}:{dt.strftime('%M')} {ampm} ET"

        spread_txt = game.get("formattedSpread")
        spread_txt = spread_txt if isinstance(spread_txt, str) and spread_txt.strip() else "Spread not posted"
        ou = game.get("overUnder")
        ou_txt = f"O/U {ou:g}" if pd.notna(ou) else ""

        html('<div class="cfb-card" style="margin-bottom:18px;">')
        cols = st.columns([1, 2, 1])
        with cols[0]:
            if _valid_logo(away_logo):
                st.image(away_logo, width=64)
            st.markdown(f"**{away}**")
            st.caption(conf_map.get(away, ""))
        with cols[1]:
            html(
                f"""
                <div style="text-align:center;">
                  <div style="font-size:12.5px; color:{TEXT_SECONDARY};">{kickoff_txt}</div>
                  <div style="font-family:'Spectral', serif; font-size:20px; font-weight:600; margin:4px 0;">{spread_txt}</div>
                  <div style="font-size:12px; color:{TEXT_SECONDARY};">{ou_txt}</div>
                </div>
                """
            )
        with cols[2]:
            if _valid_logo(home_logo):
                st.image(home_logo, width=64)
            st.markdown(f"**{home}**")
            st.caption(conf_map.get(home, ""))

        home_stats, home_yr = get_team_stats(home, season_frames)
        away_stats, away_yr = get_team_stats(away, season_frames)

        if home_stats is None and away_stats is None:
            html(f'<div style="font-size:12.5px; color:{TEXT_SECONDARY}; padding:8px 0;">No season stats available for either team yet — run <code>python update_data.py</code> to pull them.</div>')
        else:
            src_note = []
            if home_yr:
                src_note.append(f"{home}: {home_yr} season")
            if away_yr:
                src_note.append(f"{away}: {away_yr} season")
            html(f'<div style="font-size:11.5px; color:{TEXT_FOOTER}; margin-top:10px;">Stats shown — {" · ".join(src_note)}</div>')
            render_stat_table(home, home_stats, away, away_stats)

        with st.expander(f"👀 Things to Watch — {away} @ {home}"):
            wcols = st.columns(2)
            with wcols[0]:
                html(f'<div style="font-weight:700;">{away}</div>')
                render_watch_column(away, roster_prior, roster_upcoming, player_stats)
            with wcols[1]:
                html(f'<div style="font-weight:700;">{home}</div>')
                render_watch_column(home, roster_prior, roster_upcoming, player_stats)

        html("</div>")

html(
    f"""
    <div class="cfb-footer">
      <span>Spreads via ESPN Bet (or first available book) — line movement not tracked.</span>
      <span>Refresh with <code>python update_data.py --week N</code></span>
    </div>
    """
)
