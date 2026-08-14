import streamlit as st 
import pandas as pd
import plotly.graph_objects as go
import os
# Configure Streamlit page
st.set_page_config(page_title="QB Comparison Tool", layout="wide")

# Load data
df = pd.read_csv("data/QB_Stats/2025_QBstats.csv")
team_info = pd.read_csv("data/team_info.csv")

# Merge team info into QB data (match on team name, not player id vs team id)
df = df.merge(team_info[['school', 'logos']], left_on='team', right_on='school', how='left')

# Define metrics
metrics = ['att', 'qbr', 'yds', 'td', 'int']

# Normalize for radar chart
df_norm = df.copy()
for col in metrics:
    if col == 'Int':
        df_norm[col] = df_norm[col].max() - df_norm[col]
    df_norm[col] = (df_norm[col] - df_norm[col].min()) / (df_norm[col].max() - df_norm[col].min())

# Sidebar selections
st.sidebar.title("🏈 Compare Quarterbacks")
qb1 = st.sidebar.selectbox("Select QB 1", df['player_name'], index=0)
qb2 = st.sidebar.selectbox("Select QB 2", df['player_name'], index=1)

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

# Radar chart
fig = go.Figure()
fig.add_trace(go.Scatterpolar(r=radar1, theta=metrics, fill='toself', name=qb1))
fig.add_trace(go.Scatterpolar(r=radar2, theta=metrics, fill='toself', name=qb2))
fig.update_layout(
    title="🎯 QB Radar Comparison",
    polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
    showlegend=True
)

st.plotly_chart(fig, use_container_width=True)

# Chart explanation
with st.expander("ℹ️ How to Read This Chart"):
    st.markdown("""
    - Each stat is scaled from **0 to 1**, where 1 is the best.
    - **Interceptions are inverted**, so fewer INTs = better.
    - Use this to visually compare strengths and weaknesses between QBs.
    """)

# Raw stat table
st.markdown("### 📋 Raw Stat Comparison")
stats_df = pd.DataFrame({
    "Metric": metrics,
    qb1: raw1,
    qb2: raw2
})
st.dataframe(stats_df.set_index("Metric"), use_container_width=True)

# Load game-by-game stats
weekly_stats = pd.read_csv("data/all_qb_game_stats_2024.csv")

# Filter for selected QBs and sort by week
qb1_weekly = weekly_stats[weekly_stats['player_name'] == qb1].sort_values('week')
qb2_weekly = weekly_stats[weekly_stats['player_name'] == qb2].sort_values('week')

# Create separate QBR charts
st.markdown("### 📈 Weekly QBR Progression")

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

