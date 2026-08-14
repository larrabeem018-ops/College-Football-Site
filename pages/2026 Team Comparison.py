# app.py
import streamlit as st
import pandas as pd

Roster_2024=pd.read_csv("Roster_2024.csv")
Roster_2025=pd.read_csv("Roster_2025.csv")
Draft_Position= pd.read_csv("Draft_Position.csv")
Recruits_2025=pd.read_csv("Recruits_2025.csv")
player_stats_2024=pd.read_csv("data/player_stats_2024.csv")


# -----------------------------
# 1) Helpers & Position Mapping
# -----------------------------

POSITION_MAP = {
    # Offense
    "QB": "QB", "RB": "RB", "TB": "RB", "HB": "RB",
    "WR": "WR", "TE": "TE", "FB": "RB",
    "OL": "OL", "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL", "RT": "OL",
    # Defense
    "DL": "DL", "DE": "DL", "DT": "DL", "NT": "DL", "EDGE": "DL",
    "LB": "LB", "ILB": "LB", "OLB": "LB",
    "DB": "DB", "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB",
    # Special teams
    "K": "K", "P": "P", "KR": "KR", "PR": "PR", "LS": "LS"
}

def normalize_position(pos: str) -> str:
    if not isinstance(pos, str) or pos == "":
        return "OTHER"
    pos = pos.strip().upper()
    return POSITION_MAP.get(pos, pos)

def _safe_get(row, col):
    return row[col] if col in row and pd.notna(row[col]) else 0

def compute_performance_metric(row) -> float:
    g = normalize_position(row.get("position", ""))
    # Passing
    p_yards = _safe_get(row, "passing_YDS")
    p_td    = _safe_get(row, "passing_TD")
    p_int   = _safe_get(row, "passing_INT")
    p_ypa   = _safe_get(row, "passing_YPA")
    # Rushing
    r_yards = _safe_get(row, "rushing_YDS")
    r_td    = _safe_get(row, "rushing_TD")
    # Receiving
    rec_yards = _safe_get(row, "receiving_YDS")
    rec_td    = _safe_get(row, "receiving_TD")
    # Defense
    d_tot  = _safe_get(row, "defensive_TOT")
    d_sack = _safe_get(row, "defensive_SACKS")
    d_tfl  = _safe_get(row, "defensive_TFL")
    d_pd   = _safe_get(row, "defensive_PD")
    d_td   = _safe_get(row, "defensive_TD")
    ints   = _safe_get(row, "interceptions_INT")
    ints_td= _safe_get(row, "interceptions_TD")
    # Special teams
    kick_pts = _safe_get(row, "kicking_PTS")
    punt_no  = _safe_get(row, "punting_NO")
    punt_ypp = _safe_get(row, "punting_YPP")
    kr_yds   = _safe_get(row, "kickReturns_YDS")
    kr_td    = _safe_get(row, "kickReturns_TD")
    pr_yds   = _safe_get(row, "puntReturns_YDS")
    pr_td    = _safe_get(row, "puntReturns_TD")

    if g == "QB":
        return p_yards + 20*p_td - 45*p_int + r_yards + 20*r_td + 5*p_ypa
    if g == "RB":
        return r_yards + 20*r_td + 0.5*rec_yards + 10*rec_td
    if g in ("WR", "TE"):
        return rec_yards + 20*rec_td
    if g == "OL":
        return 0
    if g == "DL":
        return d_tot + 4*d_sack + 2*d_tfl + 6*d_td
    if g == "LB":
        return d_tot + 3*d_sack + 1.5*d_tfl + 6*d_td + 3*ints
    if g == "DB":
        return d_tot + 3*ints + 10*ints_td + 1.5*d_pd
    if g == "K":
        return kick_pts
    if g == "P":
        return punt_no * punt_ypp
    if g == "KR":
        return kr_yds + 20*kr_td
    if g == "PR":
        return pr_yds + 20*pr_td
    return 0

# -----------------------------
# 2) Departures & Additions
# -----------------------------

def get_drafted_players(Roster_2024, draft_df):
    Roster_2024 = Roster_2024.copy()
    draft_df = draft_df.copy()
    Roster_2024["id"] = Roster_2024["id"].astype(str)
    draft_df["collegeAthleteId"] = draft_df["collegeAthleteId"].astype(str)
    drafted = Roster_2024.merge(
        draft_df, left_on="id", right_on="collegeAthleteId", how="inner"
    )
    drafted["departure_type"] = "draft"
    drafted["overall"] = pd.to_numeric(drafted["overall"], errors="coerce")
    drafted["impact"] = (300 - drafted["overall"]).clip(lower=1).fillna(0)
    return drafted

def attach_stats(df, player_stats_2024):
    df = df.copy()
    player_stats_2024 = player_stats_2024.copy()
    df["id"] = df["id"].astype(str)
    player_stats_2024["playerId"] = player_stats_2024["playerId"].astype(str)
    merged = df.merge(
        player_stats_2024,
        left_on="id",
        right_on="playerId",
        how="left",
        suffixes=(None, "_stat")
    )
    stat_cols = [
        'defensive_PD','defensive_QB HUR','defensive_SACKS','defensive_SOLO','defensive_TD','defensive_TFL','defensive_TOT',
        'fumbles_FUM','fumbles_LOST','fumbles_REC','interceptions_AVG','interceptions_INT','interceptions_TD','interceptions_YDS',
        'kickReturns_AVG','kickReturns_LONG','kickReturns_NO','kickReturns_TD','kickReturns_YDS',
        'kicking_FGA','kicking_FGM','kicking_LONG','kicking_PCT','kicking_PTS','kicking_XPA','kicking_XPM',
        'passing_ATT','passing_COMPLETIONS','passing_INT','passing_PCT','passing_TD','passing_YDS','passing_YPA',
        'puntReturns_AVG','puntReturns_LONG','puntReturns_NO','puntReturns_TD','puntReturns_YDS',
        'punting_In 20','punting_LONG','punting_NO','punting_TB','punting_YDS','punting_YPP',
        'receiving_LONG','receiving_REC','receiving_TD','receiving_YDS','receiving_YPR',
        'rushing_CAR','rushing_LONG','rushing_TD','rushing_YDS','rushing_YPC'
    ]
    for c in stat_cols:
        if c in merged.columns:
            merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)
    return merged

def get_transfers(Roster_2024, Roster_2025, player_stats_2024):
    Roster_2024 = Roster_2024.copy()
    Roster_2025 = Roster_2025.copy()
    player_stats_2024 = player_stats_2024.copy()
    Roster_2024["id"] = Roster_2024["id"].astype(str)
    Roster_2025["id"] = Roster_2025["id"].astype(str)
    player_stats_2024["playerId"] = player_stats_2024["playerId"].astype(str)

    merged = Roster_2024[["id","team","position","firstName","lastName"]].merge(
        Roster_2025[["id","team"]], on="id", how="inner", suffixes=("_2024","_2025")
    )
    transfers_out = merged[merged["team_2024"] != merged["team_2025"]].copy()
    transfers_out["departure_type"] = "transfer_out"
    transfers_out = attach_stats(transfers_out, player_stats_2024)
    transfers_out["impact"] = transfers_out.apply(compute_performance_metric, axis=1)

    transfers_in = transfers_out.copy()
    transfers_in["arrival_type"] = "transfer_in"
    return transfers_out, transfers_in

def get_graduated(Roster_2024, Roster_2025, drafted, transfers_out, player_stats_2024):
    drafted_ids = set(drafted["id"].astype(str))
    transfer_ids = set(transfers_out["id"].astype(str))
    roster_2025_ids = set(Roster_2025["id"].astype(str))
    mask = ~Roster_2024["id"].astype(str).isin(drafted_ids | transfer_ids | roster_2025_ids)
    graduated = Roster_2024[mask].copy()
    graduated["departure_type"] = "graduated"
    graduated = attach_stats(graduated, player_stats_2024)
    graduated["impact"] = graduated.apply(compute_performance_metric, axis=1)
    return graduated

def get_recruits(Roster_2025, Recruits_2025):
    Roster_2025 = Roster_2025.copy()
    Recruits_2025 = Recruits_2025.copy()
    Roster_2025["id"] = Roster_2025["id"].astype(str)
    Recruits_2025["athleteId"] = Recruits_2025["athleteId"].astype(str)
    recruits = Roster_2025.merge(
        Recruits_2025, left_on="id", right_on="athleteId", how="inner"
    )
    recruits["arrival_type"] = "recruit"
    recruits["impact"] = pd.to_numeric(recruits["rating"], errors="coerce").fillna(0) * 100
    return recruits

# -----------------------------
# 3) Team Analysis
# -----------------------------

def analyze_team(team, Roster_2024, Roster_2025, Draft_Position, Recruits_2025, player_stats_2024):
    drafted = get_drafted_players(Roster_2024, Draft_Position)
    transfers_out, transfers_in = get_transfers(Roster_2024, Roster_2025, player_stats_2024)
    graduated = get_graduated(Roster_2024, Roster_2025, drafted, transfers_out, player_stats_2024)
    recruits = get_recruits(Roster_2025, Recruits_2025)

    losses = pd.concat([drafted, transfers_out, graduated], ignore_index=True)
    team_losses = losses[losses["team"] == team]

    team_additions = pd.concat([
        transfers_in[transfers_in["team_2025"] == team],
        recruits[recruits["committedTo"] == team]
    ], ignore_index=True)

    losses_by_pos = team_losses.assign(
        position_group=lambda d: d["position"].map(normalize_position)
    ).groupby("position_group")["impact"].sum().to_frame("loss_impact")

    adds_by_pos = team_additions.assign(
        position_group=lambda d: d["position"].map(normalize_position)
    ).groupby("position_group")["impact"].sum().to_frame("gain_impact")

    pos_summary = losses_by_pos.merge(adds_by_pos, left_index=True, right_index=True, how="outer").fillna(0)
    pos_summary["net_impact"] = pos_summary["gain_impact"] - pos_summary["loss_impact"]
    pos_summary["status"] = pos_summary["net_impact"].apply(lambda x: "Strong" if x > 0 else ("Weak" if x < 0 else "Neutral"))
    pos_summary = pos_summary.sort_values("net_impact", ascending=True)
    return pos_summary

def aggregate_units(pos_summary):
    units = {
        "Offense": ["QB","RB","WR","TE","OL"],
        "Defense": ["DL","LB","DB"],
        "Special Teams": ["K","P","KR","PR","LS"]
    }
    agg_data = {}
    for unit, positions in units.items():
        agg_data[unit] = pos_summary[pos_summary.index.isin(positions)]["net_impact"].sum()
    agg_data["Total"] = pos_summary["net_impact"].sum()
    return pd.Series(agg_data)

def highlight_comparison(val, avg):
    if val > avg:
        color = "green"
    elif val < avg:
        color = "red"
    else:
        color = "white"
    return f"background-color: {color}; color: black"

# -----------------------------
# 4) Streamlit Front-End
# -----------------------------

st.title("Team Comparison Tool")

team_options = Roster_2025["team"].unique()
team_1 = st.selectbox("Select Team 1", team_options)
team_2 = st.selectbox("Select Team 2", team_options, index=1 if len(team_options) > 1 else 0)

if team_1 == team_2:
    st.warning("Please select two different teams.")
    st.stop()

if team_1 and team_2:
    pos_1 = analyze_team(team_1, Roster_2024, Roster_2025, Draft_Position, Recruits_2025, player_stats_2024)
    pos_2 = analyze_team(team_2, Roster_2024, Roster_2025, Draft_Position, Recruits_2025, player_stats_2024)

    agg_1 = aggregate_units(pos_1)
    agg_2 = aggregate_units(pos_2)

    comparison = pd.DataFrame({
        team_1: agg_1,
        team_2: agg_2,
        "Average (Nat.)": (agg_1 + agg_2)/2
    })

    def color_func(row):
        return [
            highlight_comparison(row[team_1], row["Average (Nat.)"]),
            highlight_comparison(row[team_2], row["Average (Nat.)"]),
            ""
        ]

    st.subheader("Team Net Impact Comparison by Unit")
    st.dataframe(comparison.style.apply(color_func, axis=1))
