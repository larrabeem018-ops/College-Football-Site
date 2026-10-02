import os

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from style import apply_style, ACCENT, CHART_SEQUENCE, BG, BORDER, TEXT_PRIMARY, TEXT_SECONDARY
# Configure Streamlit page
st.set_page_config(page_title="Quarterback Comparison", page_icon="🏈", layout="wide")
apply_style()

# ---------------------------------------------------------------------------
# Season selection -- QB stats are pulled per-season by update_data.py into
# data/QB_Stats/{season}_QBstats.csv and data/all_qb_game_stats_{season}.csv,
# so 2025's finished season and 2026's in-progress season never mix. Each
# season pairs with the roster from that time: Roster_2025.csv holds the
# 2026 preseason roster (used for the current, in-progress season), and
# Roster_2024.csv holds the final 2025 roster.
# ---------------------------------------------------------------------------
SEASON_ROSTER = {2026: "data/Roster_2025.csv", 2025: "data/Roster_2024.csv"}
AVAILABLE_SEASONS = [
    yr for yr in (2026, 2025)
    if os.path.exists(f"data/QB_Stats/{yr}_QBstats.csv") and os.path.exists(SEASON_ROSTER[yr])
]

st.title("🏈 Quarterback Comparison")

if not AVAILABLE_SEASONS:
    st.warning(
        "No QB stats found yet. Run `python update_data.py` (with a CFBD_API_KEY set) "
        "to pull QB stats for the 2025 and 2026 seasons."
    )
    st.stop()

season = st.radio("Season", AVAILABLE_SEASONS, horizontal=True, key="qb_season")

# Load data
df = pd.read_csv(f"data/QB_Stats/{season}_QBstats.csv")
team_info = pd.read_csv("data/team_info.csv")
roster = pd.read_csv(SEASON_ROSTER[season])

# Merge team info into QB data (match on team name, not player id vs team id)
df = df.merge(team_info[['school', 'logos']], left_on='team', right_on='school', how='left')

# Roster QBs that have stats available to compare (matched by player id,
# since a QB's team for the selected season can differ from the team on
# their stat row if they transferred).
roster_qbs = roster[roster['position'] == 'QB'][['id', 'firstName', 'lastName', 'team']].copy()
roster_qbs['full_name'] = roster_qbs['firstName'] + ' ' + roster_qbs['lastName']
roster_qbs = roster_qbs.merge(
    df[['player_id', 'player_name']].drop_duplicates(),
    left_on='id', right_on='player_id', how='inner',
)

if roster_qbs.empty:
    st.info(f"No {season} quarterbacks with enough stats to compare yet.")
    st.stop()

# ---------------------------------------------------------------------------
# Two views on this page: "leaders" (the landing view -- a chart of the best
# QBs by a chosen stat) and "compare" (the head-to-head tool). The leaders
# view hands the chosen QBs to the compare view via session_state.
# ---------------------------------------------------------------------------
if "qb_view" not in st.session_state:
    st.session_state["qb_view"] = "leaders"

FBS_CONFERENCES = {
    "SEC", "Big Ten", "Big 12", "ACC", "Pac-12", "American Athletic", "Sun Belt",
    "Mid-American", "Mountain West", "Conference USA", "FBS Independents",
}

# label -> (column, value format, blurb)
LEADER_METRICS = {
    "Passer Rating": ("rating", "{:.1f}", "NCAA passer efficiency rating: (8.4×Yds + 330×TD + 100×Comp − 200×INT) ÷ Att."),
    "Passing Yards": ("yds", "{:,.0f}", "Total passing yards."),
    "Passing TDs": ("td", "{:.0f}", "Total passing touchdowns."),
    "Yards per Attempt": ("ypa", "{:.2f}", "Passing yards per attempt."),
    "Completion %": ("comp_pct", "{:.1f}%", "Completions ÷ attempts."),
    "ESPN QBR": ("qbr", "{:.1f}", "ESPN's Total QBR. ESPN doesn't publish one for every QB, so only QBs with a QBR are ranked."),
}

if st.session_state["qb_view"] == "leaders":
    st.caption(
        f"Who's playing the best football at quarterback — {season} season"
        + (" (in progress)." if season == 2026 else " (final).")
        + " Rank the field by any stat, then dive into a head-to-head."
    )

    pool = df.merge(
        roster_qbs[['id', 'full_name', 'team']].drop_duplicates('id')
        .rename(columns={'id': 'player_id', 'team': 'roster_team'}),
        on='player_id', how='inner',
    )
    pool['comp_pct'] = pool['comp'] / pool['att'] * 100
    pool['ypa'] = pool['yds'] / pool['att']
    pool['rating'] = (8.4 * pool['yds'] + 330 * pool['td'] + 100 * pool['comp'] - 200 * pool['int']) / pool['att']
    pool['is_fbs'] = pool['conference'].isin(FBS_CONFERENCES)

    # Default qualifier: ~15 attempts per game played so far (the NCAA
    # rule of thumb), capped so the default never hides everyone.
    games_played = int(df['week'].max())
    max_att = int(pool['att'].max())
    default_min_att = int(min(15 * games_played, pool['att'].quantile(0.9), max_att))

    c1, c2, c3, c4 = st.columns([1.6, 1.2, 1.6, 1.2])
    with c1:
        metric_label = st.selectbox("Rank quarterbacks by", list(LEADER_METRICS), key="qb_leader_metric")
    with c2:
        level = st.radio("Level", ["FBS", "All levels"], horizontal=True, key="qb_leader_level")
    with c3:
        min_att = st.slider("Minimum pass attempts", 0, max_att, default_min_att, step=5, key=f"qb_leader_minatt_{season}")
    with c4:
        top_n = st.slider("QBs shown", 5, 25, 15, key="qb_leader_topn")

    col, fmt, blurb = LEADER_METRICS[metric_label]
    ranked = pool[pool['att'] >= min_att]
    if level == "FBS":
        ranked = ranked[ranked['is_fbs']]
    ranked = ranked.dropna(subset=[col]).sort_values(col, ascending=False).reset_index(drop=True)

    if ranked.empty:
        st.info("No quarterbacks match these filters — try lowering the minimum attempts.")
        st.stop()

    top = ranked.head(top_n)
    st.caption(f"{blurb} Showing the top {len(top)} of {len(ranked)} qualifying QBs. **Click a bar** to pick a quarterback to compare.")

    fig = go.Figure(go.Bar(
        x=top[col],
        y=[f"{n} · {t}" for n, t in zip(top['player_name'], top['roster_team'])],
        orientation='h',
        marker=dict(color=ACCENT),
        text=[fmt.format(v) for v in top[col]],
        textposition='outside',
        cliponaxis=False,
        hovertemplate="%{y}<br>" + metric_label + ": %{text}<extra></extra>",
    ))
    fig.update_layout(
        title=dict(
            text=f"{metric_label} Leaders — {season} Season",
            font=dict(family="Spectral, serif", size=20, color=TEXT_PRIMARY),
        ),
        height=max(340, 32 * len(top) + 110),
        yaxis=dict(autorange="reversed", tickfont=dict(size=13, color=TEXT_PRIMARY)),
        xaxis=dict(gridcolor=BORDER, zeroline=False, tickfont=dict(color=TEXT_SECONDARY)),
        font=dict(family="Manrope, sans-serif"),
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(t=60, b=30, l=10, r=60),
        clickmode="event+select",
    )
    event = st.plotly_chart(
        fig, use_container_width=True, on_select="rerun", selection_mode="points",
        key=f"qb_leaders_chart_{season}_{metric_label}_{level}_{min_att}_{top_n}",
    )
    clicked_idx = None
    pts = event.selection.points if event and event.selection else []
    if pts and pts[0].get("point_index") is not None and pts[0]["point_index"] < len(top):
        clicked_idx = int(pts[0]["point_index"])

    # ---- Head-to-head launcher ------------------------------------------
    st.markdown("### 🆚 Dive into a head-to-head")
    if len(ranked) < 2:
        st.info("Need at least two qualifying quarterbacks to compare — try lowering the minimum attempts.")
    else:
        labels = [f"{r.player_name} — {r.roster_team} ({fmt.format(getattr(r, col))} {metric_label})" for r in ranked.itertuples()]
        default_a = clicked_idx if clicked_idx is not None else 0
        default_b = 1 if default_a == 0 else 0
        if clicked_idx is not None:
            st.caption(f"Selected from the chart: **{ranked.loc[clicked_idx, 'player_name']}**. Pick an opponent below.")
        l1, l2 = st.columns(2)
        with l1:
            a = st.selectbox("Quarterback 1", range(len(ranked)), index=default_a,
                             format_func=lambda i: labels[i], key=f"qb_lead_a_{default_a}")
        with l2:
            b = st.selectbox("Quarterback 2", range(len(ranked)), index=default_b,
                             format_func=lambda i: labels[i], key=f"qb_lead_b_{default_a}")
        b1, b2, _ = st.columns([1.3, 1.3, 3])
        with b1:
            go_compare = st.button("Compare these QBs →", type="primary", disabled=(a == b), key="qb_go_compare")
        with b2:
            go_tool = st.button("Open full comparison tool", key="qb_go_tool")
        if go_compare:
            ra, rb = ranked.iloc[a], ranked.iloc[b]
            st.session_state["qb_team1"], st.session_state["qb1_name"] = ra['roster_team'], ra['full_name']
            st.session_state["qb_team2"], st.session_state["qb2_name"] = rb['roster_team'], rb['full_name']
            st.session_state["qb_view"] = "compare"
            st.rerun()
        if go_tool:
            st.session_state["qb_view"] = "compare"
            st.rerun()

    # ---- Leaderboard table ----------------------------------------------
    st.markdown("### 📋 Leaderboard")
    board = pd.DataFrame({
        "Rank": range(1, len(top) + 1),
        "": top['logos'],
        "Quarterback": top['player_name'],
        "Team": top['roster_team'],
        "Conf": top['conference'],
        "Att": top['att'],
        "Comp %": top['comp_pct'].round(1),
        "Yds": top['yds'],
        "TD": top['td'],
        "INT": top['int'],
        "Y/A": top['ypa'].round(2),
        "Rating": top['rating'].round(1),
        "QBR": top['qbr'].round(1),
    })
    st.dataframe(
        board, use_container_width=True, hide_index=True,
        column_config={"": st.column_config.ImageColumn("", width="small")},
    )
    st.stop()

# ---------------------------------------------------------------------------
# Head-to-head comparison view
# ---------------------------------------------------------------------------
if st.button("← Back to QB leaders", key="qb_back"):
    st.session_state["qb_view"] = "leaders"
    st.rerun()

st.caption(
    f"Comparing quarterbacks using {season} season stats"
    + (" (in progress)." if season == 2026 else " (final).")
)

# Define metrics
metrics = ['att', 'qbr', 'yds', 'td', 'int']
METRIC_LABELS = {'att': 'Attempts', 'qbr': 'QBR', 'yds': 'Pass Yards', 'td': 'TD', 'int': 'INT'}

# Normalize for radar chart (0-100 scale, higher = better on every axis)
df_norm = df.copy()
for col in metrics:
    if col == 'int':  # fewer interceptions is better, so invert before scaling
        df_norm[col] = df_norm[col].max() - df_norm[col]
    span = df_norm[col].max() - df_norm[col].min()
    df_norm[col] = ((df_norm[col] - df_norm[col].min()) / span * 100) if span else 50.0

# QB selections (main page) — look up by team from the selected season's
# roster, then pick the quarterback on that team.
st.caption(f"Pick a team to see the quarterbacks on its {season} roster with stats available to compare.")

team_options = sorted(roster_qbs['team'].unique())

# Drop stale widget state (e.g. after switching seasons) so selectboxes never
# hold a value that isn't in their option list.
for _k in ("qb_team1", "qb_team2"):
    if st.session_state.get(_k) not in team_options:
        st.session_state.pop(_k, None)

qb_col1, qb_col2 = st.columns(2)
with qb_col1:
    team1 = st.selectbox("Team", team_options, index=0, key="qb_team1")
    team1_qbs = roster_qbs[roster_qbs['team'] == team1]
    if st.session_state.get('qb1_name') not in set(team1_qbs['full_name']):
        st.session_state.pop('qb1_name', None)
    qb1_full_name = st.selectbox("Quarterback", team1_qbs['full_name'], key="qb1_name")
    qb1 = team1_qbs.loc[team1_qbs['full_name'] == qb1_full_name, 'player_name'].iloc[0]
with qb_col2:
    default_team2_index = 1 if len(team_options) > 1 else 0
    team2 = st.selectbox("Team", team_options, index=default_team2_index, key="qb_team2")
    team2_qbs = roster_qbs[roster_qbs['team'] == team2]
    default_qb2_index = 1 if (team2 == team1 and len(team2_qbs) > 1) else 0
    if st.session_state.get('qb2_name') not in set(team2_qbs['full_name']):
        st.session_state.pop('qb2_name', None)
    qb2_full_name = st.selectbox("Quarterback", team2_qbs['full_name'], index=default_qb2_index, key="qb2_name")
    qb2 = team2_qbs.loc[team2_qbs['full_name'] == qb2_full_name, 'player_name'].iloc[0]

# Avoid same QB selection
if qb1 == qb2:
    st.warning("Please select two different quarterbacks.")
    st.stop()

# Get player rows
qb1_row = df[df['player_name'] == qb1].iloc[0]
qb2_row = df[df['player_name'] == qb2].iloc[0]

# Headshot URL function
def get_headshot_url(player_id):
    return f"https://a.espncdn.com/combiner/i?img=/i/headshots/college-football/players/full/{player_id}.png&w=350&h=254"

# Construct image and logo URLs
qb1_img_url = get_headshot_url(qb1_row['player_id'])
qb2_img_url = get_headshot_url(qb2_row['player_id'])
qb1_logo_url = qb1_row['logos']
qb2_logo_url = qb2_row['logos']
qb1_school = qb1_row['school']
qb2_school = qb2_row['school']

# Extract radar values
radar1 = df_norm[df_norm['player_name'] == qb1][metrics].values.flatten()
radar2 = df_norm[df_norm['player_name'] == qb2][metrics].values.flatten()

# Raw stats
raw1 = qb1_row[metrics].values.flatten()
raw2 = qb2_row[metrics].values.flatten()

# Display logos and headshots
col1, col2, col3 = st.columns([1, 0.5, 1])
with col1:
    st.image(qb1_logo_url, width=60)
    st.image(qb1_img_url, caption=f"{qb1} ({qb1_school})", width=175)
with col2:
    st.markdown("### 🆚")
with col3:
    st.image(qb2_logo_url, width=60)
    st.image(qb2_img_url, caption=f"{qb2} ({qb2_school})", width=175)

# Radar chart -- the first point/category is repeated at the end of each
# array so the polygon's border actually closes (Scatterpolar's fill='toself'
# shades a closed shape either way, but without the repeated point the outline
# itself is left open between the last and first category).
theta_labels = [METRIC_LABELS[m] for m in metrics] + [METRIC_LABELS[metrics[0]]]
radar1_closed = list(radar1) + [radar1[0]]
radar2_closed = list(radar2) + [radar2[0]]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(
    r=radar2_closed, theta=theta_labels, fill='toself', name=qb2,
    mode='lines+markers',
    line=dict(color=CHART_SEQUENCE[1], width=2.5),
    marker=dict(size=6, color=CHART_SEQUENCE[1]),
    fillcolor="rgba(95,93,89,0.22)",
    hovertemplate="%{theta}: %{r:.0f}<extra>" + qb2 + "</extra>",
))
fig.add_trace(go.Scatterpolar(
    r=radar1_closed, theta=theta_labels, fill='toself', name=qb1,
    mode='lines+markers',
    line=dict(color=CHART_SEQUENCE[0], width=2.5),
    marker=dict(size=6, color=CHART_SEQUENCE[0]),
    fillcolor="rgba(0,116,36,0.28)",
    hovertemplate="%{theta}: %{r:.0f}<extra>" + qb1 + "</extra>",
))
fig.update_layout(
    title=dict(
        text=f"QB Radar Comparison — {season} Season",
        font=dict(family="Spectral, serif", size=20, color=TEXT_PRIMARY),
    ),
    polar=dict(
        bgcolor="#FFFFFF",
        radialaxis=dict(
            visible=True, range=[0, 100], ticksuffix="", tickfont=dict(size=10, color=TEXT_SECONDARY),
            gridcolor=BORDER, linecolor=BORDER,
        ),
        angularaxis=dict(
            tickfont=dict(size=13, color=TEXT_PRIMARY, family="Manrope, sans-serif"),
            gridcolor=BORDER, linecolor=BORDER,
        ),
    ),
    showlegend=True,
    legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
    font=dict(family="Manrope, sans-serif"),
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    margin=dict(t=60, b=60, l=40, r=40),
)

st.plotly_chart(fig, use_container_width=True)

# Chart explanation
with st.expander("ℹ️ How to Read This Chart"):
    st.markdown("""
    - Each stat is scaled **0–100 relative to every QB in this dataset**, where 100 is the best in the pool.
    - **Interceptions are inverted**, so fewer INTs = better (further out on the axis).
    - The two shapes are drawn as closed polygons — use them to visually compare strengths and weaknesses at a glance.
    """)

# Raw stat table
st.markdown("### 📋 Raw Stat Comparison")
stats_df = pd.DataFrame({
    "Metric": [METRIC_LABELS[m] for m in metrics],
    qb1: raw1,
    qb2: raw2
})
st.dataframe(stats_df.set_index("Metric"), use_container_width=True)

# Load game-by-game stats
weekly_stats_path = f"data/all_qb_game_stats_{season}.csv"
weekly_stats = pd.read_csv(weekly_stats_path)

# Filter for selected QBs and sort by week
qb1_weekly = weekly_stats[weekly_stats['player_name'] == qb1].sort_values('week')
qb2_weekly = weekly_stats[weekly_stats['player_name'] == qb2].sort_values('week')

# Create separate QBR charts
st.markdown(f"### 📈 Weekly QBR Progression — {season}")
st.caption(
    "ESPN doesn't publish a QBR figure for every game — it's frequently missing for early-season "
    "buy games against weaker non-conference opponents, even when the box score (comp/att, yards, "
    "TD, INT) is complete. Weeks with no QBR show as a gap in the line below; the full game log "
    "further down always shows the raw stats."
)

# Create x-axis labels combining week and opponent
qb1_weekly['x_labels'] = 'Week ' + qb1_weekly['week'].astype(str) + '<br>' + qb1_weekly['opponent']
qb2_weekly['x_labels'] = 'Week ' + qb2_weekly['week'].astype(str) + '<br>' + qb2_weekly['opponent']

# QB1 Chart
fig_qbr1 = go.Figure()
fig_qbr1.add_trace(go.Scatter(
    x=qb1_weekly['x_labels'],
    y=qb1_weekly['qbr'],
    name=qb1,
    mode='lines+markers',
    line=dict(shape='spline', smoothing=0.3),
    hovertemplate="QBR: %{y:.1f}<extra></extra>",
))
fig_qbr1.update_layout(
    title=f"{qb1}'s QBR by Week",
    xaxis_title="",
    yaxis_title="QBR",
    hovermode='x unified',
    xaxis=dict(tickmode='array', ticktext=qb1_weekly['x_labels'], tickangle=45)
)

# QB2 Chart
fig_qbr2 = go.Figure()
fig_qbr2.add_trace(go.Scatter(
    x=qb2_weekly['x_labels'],
    y=qb2_weekly['qbr'],
    name=qb2,
    mode='lines+markers',
    line=dict(shape='spline', smoothing=0.3),
    hovertemplate="QBR: %{y:.1f}<extra></extra>",
))
fig_qbr2.update_layout(
    title=f"{qb2}'s QBR by Week",
    xaxis_title="",
    yaxis_title="QBR",
    hovermode='x unified',
    xaxis=dict(tickmode='array', ticktext=qb2_weekly['x_labels'], tickangle=45)
)

# Display charts in columns
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_qbr1, use_container_width=True)
with col2:
    st.plotly_chart(fig_qbr2, use_container_width=True)

# ---------------------------------------------------------------------------
# Week-by-week game log -- shown for every game regardless of whether ESPN
# published a QBR figure for it, so a missing QBR (common for early-season
# buy games) never hides the fact that the game itself was tracked.
# ---------------------------------------------------------------------------
st.markdown(f"### 📅 Week-by-Week Game Log — {season}")

def format_game_log(weekly_df):
    log = weekly_df.sort_values('week').copy()
    log['Week'] = log['week']
    log['Opponent'] = log['opponent']
    log['Comp/Att'] = log['comp'].astype(int).astype(str) + '/' + log['att'].astype(int).astype(str)
    log['Comp %'] = (log['completion_pct'] * 100).round(1)
    log['Yds'] = log['yds']
    log['TD'] = log['td']
    log['INT'] = log['int']
    log['QBR'] = log['qbr'].round(1)
    return log[['Week', 'Opponent', 'Comp/Att', 'Comp %', 'Yds', 'TD', 'INT', 'QBR']]

log_col1, log_col2 = st.columns(2)
with log_col1:
    st.markdown(f"**{qb1}**")
    st.dataframe(
        format_game_log(qb1_weekly),
        use_container_width=True,
        hide_index=True,
        column_config={"QBR": st.column_config.NumberColumn("QBR", format="%.1f")},
    )
with log_col2:
    st.markdown(f"**{qb2}**")
    st.dataframe(
        format_game_log(qb2_weekly),
        use_container_width=True,
        hide_index=True,
        column_config={"QBR": st.column_config.NumberColumn("QBR", format="%.1f")},
    )
st.caption("A blank QBR cell means ESPN didn't report one for that game — every other column reflects the actual box score.")
