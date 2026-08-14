import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    file_path = "data/espnBetLines.csv"  # path to your CSV
    df = pd.read_csv(file_path)

    # Convert numeric columns
    numeric_cols = ["homeScore", "awayScore", "spread", "homeMoneyline", "awayMoneyline"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data
def load_team_logos():
    try:
        info = pd.read_csv("data/team_info.csv")
        return dict(zip(info["school"], info["logos"]))
    except Exception:
        return {}


df = load_data()
logo_map = load_team_logos()


# -----------------------------
# Who was favored in each game, from the formattedSpread text (e.g. "Michigan -3")
# -----------------------------
def get_favorite(row):
    fs = str(row["formattedSpread"])
    if fs.startswith(str(row["homeTeam"])):
        return row["homeTeam"]
    if fs.startswith(str(row["awayTeam"])):
        return row["awayTeam"]
    return None


# -----------------------------
# Categorize Games (game-centric — used for the raw game log / simulator)
# -----------------------------
def categorize_game(row):
    if pd.isna(row["homeScore"]) or pd.isna(row["awayScore"]) or pd.isna(row["spread"]):
        return None, None, None

    home_score, away_score = row["homeScore"], row["awayScore"]
    spread = row["spread"]
    fav_info = str(row.get("formattedSpread", ""))

    if fav_info.startswith(row["homeTeam"]):
        margin = home_score - away_score
        cover_margin = margin - abs(spread)
        covered = margin > abs(spread)
        underdog_win = away_score > home_score
        if underdog_win:
            return "Underdog Win", cover_margin, margin
        return ("Favorite Covered" if covered else "Favorite Won, Did Not Cover"), cover_margin, margin

    elif fav_info.startswith(row["awayTeam"]):
        margin = away_score - home_score
        cover_margin = margin - abs(spread)
        covered = margin > abs(spread)
        underdog_win = home_score > away_score
        if underdog_win:
            return "Underdog Win", cover_margin, margin
        return ("Favorite Covered" if covered else "Favorite Won, Did Not Cover"), cover_margin, margin

    return None, None, None


df[["category", "cover_margin", "win_margin"]] = df.apply(
    lambda r: pd.Series(categorize_game(r)), axis=1
)


# -----------------------------
# Team-game log: one row per team per completed game, with that team's
# favorite/underdog role and ATS result. Shared by both the single-team view
# and the league-wide rankings, so the numbers always agree between the two.
# -----------------------------
@st.cache_data
def build_team_game_log(df):
    base = df.copy()
    base["favorite"] = base.apply(get_favorite, axis=1)
    base["spread_magnitude"] = base["spread"].abs()
    played = base.dropna(subset=["homeScore", "awayScore"]).copy()

    home_rows = pd.DataFrame({
        "team": played["homeTeam"],
        "opponent": played["awayTeam"],
        "week": played["week"],
        "is_home": True,
        "team_score": played["homeScore"],
        "opp_score": played["awayScore"],
        "team_moneyline": played["homeMoneyline"],
        "favorite": played["favorite"],
        "spread_magnitude": played["spread_magnitude"],
    })
    away_rows = pd.DataFrame({
        "team": played["awayTeam"],
        "opponent": played["homeTeam"],
        "week": played["week"],
        "is_home": False,
        "team_score": played["awayScore"],
        "opp_score": played["homeScore"],
        "team_moneyline": played["awayMoneyline"],
        "favorite": played["favorite"],
        "spread_magnitude": played["spread_magnitude"],
    })
    long_df = pd.concat([home_rows, away_rows], ignore_index=True)

    long_df["role"] = np.where(
        long_df["favorite"].isna(),
        "Pick'em",
        np.where(long_df["favorite"] == long_df["team"], "Favorite", "Underdog"),
    )
    long_df["margin"] = long_df["team_score"] - long_df["opp_score"]
    long_df["result"] = np.where(
        long_df["margin"] > 0, "W", np.where(long_df["margin"] < 0, "L", "T")
    )
    long_df["ats_margin"] = np.where(
        long_df["role"] == "Favorite",
        long_df["margin"] - long_df["spread_magnitude"],
        np.where(long_df["role"] == "Underdog", long_df["margin"] + long_df["spread_magnitude"], long_df["margin"]),
    )
    long_df["ats_result"] = np.where(
        long_df["ats_margin"] > 0, "Covered",
        np.where(long_df["ats_margin"] < 0, "No Cover", "Push"),
    )
    return long_df


long_df = build_team_game_log(df)

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("College Football Spread & Payouts Dashboard 🏈")

# -----------------------------
# Team Filter
# -----------------------------
team_options = sorted(pd.unique(df[["homeTeam", "awayTeam"]].values.ravel("K")))
selected_team = st.selectbox("🔍 Filter by Team", ["All Teams"] + team_options)


# =============================================================================
# TEAM VIEW — per-matchup favorite/underdog + cover breakdown for one team
# =============================================================================
def render_team_view(team, team_log):
    st.caption(f"Showing {len(team_log)} games involving {team}")

    if team_log.empty:
        st.info(f"No completed games with lines found for {team} yet.")
        return

    wins = int((team_log["result"] == "W").sum())
    losses = int((team_log["result"] == "L").sum())
    covers = int((team_log["ats_result"] == "Covered").sum())
    no_covers = int((team_log["ats_result"] == "No Cover").sum())
    pushes = int((team_log["ats_result"] == "Push").sum())

    fav_games = team_log[team_log["role"] == "Favorite"]
    dog_games = team_log[team_log["role"] == "Underdog"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Overall Record", f"{wins}-{losses}")
    m2.metric("ATS Record", f"{covers}-{no_covers}" + (f"-{pushes}" if pushes else ""))
    m3.metric(
        "As Favorite (ATS)",
        f"{(fav_games['ats_result'] == 'Covered').sum()}-{(fav_games['ats_result'] == 'No Cover').sum()}",
        help=f"{len(fav_games)} games as the favorite",
    )
    m4.metric(
        "As Underdog (ATS)",
        f"{(dog_games['ats_result'] == 'Covered').sum()}-{(dog_games['ats_result'] == 'No Cover').sum()}",
        help=f"{len(dog_games)} games as the underdog",
    )

    # ---------------- Game-by-game log ----------------
    st.subheader("📋 Game-by-Game Betting Log")

    log = team_log.sort_values("week").copy()
    log["Wk"] = log["week"]
    log["Matchup"] = np.where(log["is_home"], "vs " + log["opponent"], "@ " + log["opponent"])
    log["Role"] = np.where(log["role"] == "Favorite", "⭐ Favorite", np.where(log["role"] == "Underdog", "🐶 Underdog", "🤝 Pick'em"))
    log["Line"] = log.apply(
        lambda r: "PK" if r["role"] == "Pick'em" else f"{'-' if r['role']=='Favorite' else '+'}{r['spread_magnitude']:.1f}",
        axis=1,
    )
    log["Score"] = log["team_score"].astype(int).astype(str) + "-" + log["opp_score"].astype(int).astype(str)
    log["W/L"] = log["result"].map({"W": "✅ W", "L": "❌ L", "T": "➖ T"})
    log["ATS"] = log["ats_result"].map({"Covered": "✅ Covered", "No Cover": "❌ No Cover", "Push": "➖ Push"})
    log["ATS Margin"] = log["ats_margin"].round(1)

    st.dataframe(
        log[["Wk", "Matchup", "Role", "Line", "Score", "W/L", "ATS", "ATS Margin"]],
        use_container_width=True,
        hide_index=True,
    )

    # ---------------- ATS margin chart ----------------
    st.subheader("📊 ATS Margin by Game")
    chart_df = log.copy()
    chart_df["label"] = "Wk " + chart_df["Wk"].astype(str) + ": " + chart_df["Matchup"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=chart_df["label"],
            y=chart_df["ats_margin"],
            marker_color=[
                "rgb(0,150,0)" if v > 0 else ("rgb(150,0,0)" if v < 0 else "rgb(150,150,0)")
                for v in chart_df["ats_margin"]
            ],
            text=chart_df["Role"],
            hovertemplate="<b>%{x}</b><br>ATS Margin: %{y:.1f}<br>%{text}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=f"{team}: Cover Margin Above/Below the Spread",
        xaxis_title="",
        yaxis_title="Points vs. Spread",
        xaxis_tickangle=-45,
        height=450,
        showlegend=False,
        plot_bgcolor="white",
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("ℹ️ How to read this"):
        st.markdown(
            """
            - **Favorite**: bars show how many points *more* than the spread they won by (positive = covered).
            - **Underdog**: bars show how many points of "cushion" they had against the spread
              (positive = covered, either by winning outright or losing by less than the spread).
            - Green = covered, red = did not cover, yellow = push.
            """
        )

    # ---------------- Hypothetical betting simulator, scoped to this team ----------------
    st.subheader("💰 If You Bet on Every Game")
    wager = st.number_input("Wager per game ($)", min_value=1, max_value=1000, value=10, key="team_wager")

    def moneyline_profit(row):
        ml = row["team_moneyline"]
        if pd.isna(ml):
            return 0.0
        if row["result"] != "W":
            return -wager
        return wager * 100 / abs(ml) if ml < 0 else wager * (ml / 100)

    def ats_profit(row, standard_juice=-110):
        if row["ats_result"] == "Push":
            return 0.0
        if row["ats_result"] != "Covered":
            return -wager
        return wager * 100 / abs(standard_juice)

    team_log = team_log.copy()
    team_log["moneyline_profit"] = team_log.apply(moneyline_profit, axis=1)
    team_log["ats_profit"] = team_log.apply(ats_profit, axis=1)

    p1, p2 = st.columns(2)
    with p1:
        st.metric(f"Betting {team} to Win (Moneyline)", f"${team_log['moneyline_profit'].sum():,.2f}")
    with p2:
        st.metric(f"Betting {team} ATS (assumes -110 odds)", f"${team_log['ats_profit'].sum():,.2f}")


# =============================================================================
# LEAGUE VIEW — ATS power rankings + fan-friendly leaderboards
# =============================================================================
def summarize_team(g):
    covers = int((g["ats_result"] == "Covered").sum())
    no_covers = int((g["ats_result"] == "No Cover").sum())
    pushes = int((g["ats_result"] == "Push").sum())
    wins = int((g["result"] == "W").sum())
    losses = int((g["result"] == "L").sum())
    decided = covers + no_covers
    cover_pct = round(covers / decided * 100, 1) if decided else 0.0
    return pd.Series({
        "Games": len(g),
        "Record": f"{wins}-{losses}",
        "ATS": f"{covers}-{no_covers}" + (f"-{pushes}" if pushes else ""),
        "Cover %": cover_pct,
    })


def ranking_table(long_df, subset_role=None, min_games=1):
    subset = long_df if subset_role is None else long_df[long_df["role"] == subset_role]
    tbl = subset.groupby("team").apply(summarize_team, include_groups=False).reset_index().rename(columns={"team": "Team"})
    tbl = tbl[tbl["Games"] >= min_games].sort_values("Cover %", ascending=False).reset_index(drop=True)
    tbl.insert(0, "Rank", range(1, len(tbl) + 1))
    tbl["Logo"] = tbl["Team"].map(logo_map)
    return tbl[["Rank", "Logo", "Team", "Games", "Record", "ATS", "Cover %"]]


def show_ranking_table(tbl, caption):
    st.dataframe(
        tbl,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Logo": st.column_config.ImageColumn(""),
            "Cover %": st.column_config.ProgressColumn("Cover %", format="%.1f%%", min_value=0, max_value=100),
        },
    )
    st.caption(caption)


def render_league_view(df, long_df):
    played_games = df.dropna(subset=["homeScore", "awayScore"])

    # ---------------- Headline metrics ----------------
    qualified = ranking_table(long_df, min_games=5)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Games Analyzed", len(played_games))
    if not qualified.empty:
        best = qualified.iloc[0]
        worst = qualified.iloc[-1]
        m2.metric("🔥 Best ATS Team", best["Team"], f"{best['Cover %']}% cover")
        m3.metric("🥶 Worst ATS Team", worst["Team"], f"{worst['Cover %']}% cover")
    else:
        m2.metric("🔥 Best ATS Team", "—")
        m3.metric("🥶 Worst ATS Team", "—")

    upsets = long_df[(long_df["role"] == "Underdog") & (long_df["result"] == "W")]
    if not upsets.empty:
        top_upset = upsets.loc[upsets["spread_magnitude"].idxmax()]
        m4.metric(
            "😱 Biggest Upset",
            f"{top_upset['team']} +{top_upset['spread_magnitude']:.1f}",
            f"beat {top_upset['opponent']}",
        )
    else:
        m4.metric("😱 Biggest Upset", "—")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🏆 ATS Power Rankings", "😱 Upsets & Nail-Biters", "💰 Betting Simulator", "📄 Full Game Log"]
    )

    # ---------------- Tab 1: ATS Power Rankings ----------------
    with tab1:
        max_games = int(long_df.groupby("team").size().max()) if not long_df.empty else 1
        min_games = st.slider("Minimum games played", 1, max(max_games, 1), value=min(5, max_games))

        sub1, sub2, sub3 = st.tabs(["Overall ATS", "As Favorite", "As Underdog"])
        with sub1:
            show_ranking_table(
                ranking_table(long_df, min_games=min_games),
                "Ranked by ATS cover % across every game (as favorite or underdog).",
            )
        with sub2:
            show_ranking_table(
                ranking_table(long_df, subset_role="Favorite", min_games=min_games),
                "Ranked by ATS cover % only in games where the team was favored.",
            )
        with sub3:
            show_ranking_table(
                ranking_table(long_df, subset_role="Underdog", min_games=min_games),
                "Ranked by ATS cover % only in games where the team was the underdog.",
            )

    # ---------------- Tab 2: Upsets & Nail-Biters ----------------
    with tab2:
        st.subheader("😱 Biggest Upsets")
        st.caption("Underdogs who won outright, sorted by how many points they were getting.")
        upset_tbl = upsets.sort_values("spread_magnitude", ascending=False).head(15).copy()
        upset_tbl["Matchup"] = np.where(
            upset_tbl["is_home"], upset_tbl["team"] + " (home) vs " + upset_tbl["opponent"],
            upset_tbl["team"] + " @ " + upset_tbl["opponent"],
        )
        upset_tbl["Score"] = upset_tbl["team_score"].astype(int).astype(str) + "-" + upset_tbl["opp_score"].astype(int).astype(str)
        upset_tbl["Spread"] = "+" + upset_tbl["spread_magnitude"].round(1).astype(str)
        st.dataframe(
            upset_tbl[["week", "Matchup", "Spread", "Score"]].rename(columns={"week": "Wk"}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("😬 Nail-Biters (Closest ATS Games)")
        st.caption("Games decided against the spread by the smallest margin.")
        one_row_per_game = long_df[(long_df["is_home"]) & (long_df["ats_result"] != "Push")].copy()
        one_row_per_game["abs_margin"] = one_row_per_game["ats_margin"].abs()
        nail_biters = one_row_per_game.sort_values("abs_margin").head(15).copy()
        nail_biters["Matchup"] = nail_biters["opponent"] + " @ " + nail_biters["team"]
        nail_biters["Score"] = nail_biters["team_score"].astype(int).astype(str) + "-" + nail_biters["opp_score"].astype(int).astype(str)
        nail_biters["ATS Margin"] = nail_biters["abs_margin"].round(1)
        st.dataframe(
            nail_biters[["week", "Matchup", "Score", "ATS Margin"]].rename(columns={"week": "Wk"}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("💥 Biggest Covers")
        st.caption("Games won most convincingly against the spread.")
        blowouts = one_row_per_game[one_row_per_game["ats_margin"] > 0].sort_values("ats_margin", ascending=False).head(15).copy()
        blowouts["Matchup"] = blowouts["opponent"] + " @ " + blowouts["team"]
        blowouts["Score"] = blowouts["team_score"].astype(int).astype(str) + "-" + blowouts["opp_score"].astype(int).astype(str)
        blowouts["ATS Margin"] = blowouts["ats_margin"].round(1)
        st.dataframe(
            blowouts[["week", "Matchup", "Score", "ATS Margin"]].rename(columns={"week": "Wk"}),
            use_container_width=True, hide_index=True,
        )

    # ---------------- Tab 3: Betting Simulator ----------------
    with tab3:
        st.subheader("📊 Spread Results")
        fig = px.histogram(df, x="category", title="Game Outcomes")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("💰 Betting Simulator")
        wager = st.number_input("Wager per game ($)", min_value=1, max_value=1000, value=10, key="league_wager")

        def calculate_profit(row, bet_on="favorite"):
            if bet_on == "favorite":
                fav = row["homeTeam"] if row["category"] in ["Favorite Covered", "Favorite Won, Did Not Cover"] else None
                if fav:
                    moneyline = row["homeMoneyline"] if str(row["formattedSpread"]).startswith(row["homeTeam"]) else row["awayMoneyline"]
                    if moneyline < 0:
                        return wager * 100 / abs(moneyline)
                    else:
                        return wager * (moneyline / 100)
                return -wager
            elif bet_on == "underdog":
                if row["category"] == "Underdog Win":
                    moneyline = row["awayMoneyline"] if str(row["formattedSpread"]).startswith(row["homeTeam"]) else row["homeMoneyline"]
                    if moneyline < 0:
                        return wager * 100 / abs(moneyline)
                    else:
                        return wager * (moneyline / 100)
                return -wager
            return 0

        df_sim = df.copy()
        df_sim["profit_fav"] = df_sim.apply(lambda r: calculate_profit(r, "favorite"), axis=1)
        df_sim["profit_dog"] = df_sim.apply(lambda r: calculate_profit(r, "underdog"), axis=1)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Profit Betting All Favorites", f"${df_sim['profit_fav'].sum():,.2f}")
        with col2:
            st.metric("Profit Betting All Underdogs", f"${df_sim['profit_dog'].sum():,.2f}")

    # ---------------- Tab 4: Full Game Log ----------------
    with tab4:
        st.dataframe(df[[
            "week", "homeTeam", "awayTeam", "homeScore", "awayScore",
            "spread", "formattedSpread", "category", "cover_margin",
        ]].rename(columns={"week": "Wk"}), use_container_width=True, hide_index=True)


if selected_team != "All Teams":
    team_log = long_df[long_df["team"] == selected_team]
    render_team_view(selected_team, team_log)
else:
    render_league_view(df, long_df)
