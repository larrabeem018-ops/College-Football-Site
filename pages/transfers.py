import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Transfer Portal Sankey", layout="wide")

st.title("🏈 Transfer Portal Movement (2026)")

# Load transfer data
df = pd.read_csv("data/transfers_2025.csv")
df = df.dropna(subset=["origin", "destination"])
team_info = pd.read_csv("data/team_info.csv")  # Or load however you're doing it



# Dropdown to filter by team
selected_team = st.selectbox("🎯 Filter by School (optional):", ["None"] + sorted(df["origin"].dropna().unique()))


if selected_team == "None":

    # Ensure ratings are numeric
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)

    # Calculate total rating in and out
    rating_in = df.groupby('destination')['rating'].sum().reset_index()
    rating_in.columns = ['team', 'rating_in']

    rating_out = df.groupby('origin')['rating'].sum().reset_index()
    rating_out.columns = ['team', 'rating_out']

    # Combine and calculate net
    rating_net = pd.merge(rating_in, rating_out, on='team', how='outer').fillna(0)
    rating_net['net_rating'] = rating_net['rating_in'] - rating_net['rating_out']
    rating_net_sorted = rating_net.sort_values(by='net_rating', ascending=False)

    # Plot bar chart
    fig = px.bar(
        rating_net_sorted,
        x='team',
        y='net_rating',
        color='net_rating',
        color_continuous_scale='RdYlGn',
        title='Net Transfer Rating Gained vs. Lost by Team (2026)',
        labels={'net_rating': 'Net Rating (Gained - Lost)', 'team': 'Team'}
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        yaxis_title='Net Rating',
        xaxis_title='Team',
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

else:  

    st.subheader(f"Transfers In/Out for **{selected_team}**")

    # Load all data at the start
    transfers_stats = pd.read_csv("data/transfers_2025_stats.csv")
    
    # Create filtered_df only once
    filtered_df = df[(df["origin"] == selected_team) | (df["destination"] == selected_team)].copy()

    # Create incoming/outgoing dataframes early
    incoming = filtered_df[filtered_df["destination"] == selected_team][
        ["firstName_x", "lastName_x", "rating", "position_x", "stars", "origin"]
    ].copy()
    outgoing = filtered_df[filtered_df["origin"] == selected_team][
        ["firstName_x", "lastName_x", "rating", "position_x", "stars", "destination"]
    ].copy()

    # Calculate summary stats
    avg_rating_in = incoming["rating"].mean()
    avg_rating_out = outgoing["rating"].mean()
    total_rating_in = incoming["rating"].sum()
    total_rating_out = outgoing["rating"].sum()

    # Round values for display
    avg_rating_in = round(avg_rating_in, 2)
    avg_rating_out = round(avg_rating_out, 2)
    total_rating_in = round(total_rating_in, 2)
    total_rating_out = round(total_rating_out, 2)

    # Get logo for selected team
    team_row = team_info[team_info["school"] == selected_team]
    team_logo_url = team_row["logos"].values[0] if not team_row.empty else ""


     # Display summary with logo
    st.markdown(f"""
    <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 10px;'>
        <img src="{team_logo_url}" width="60">
        <h3 style='margin: 0;'>Transfer Summary for {selected_team}</h3>
    </div>

    - **Incoming Players:** {len(incoming)}  
    • Total Rating Gained: **{total_rating_in}**  
    • Average Rating: **{avg_rating_in}**

    - **Outgoing Players:** {len(outgoing)}  
    • Total Rating Lost: **{total_rating_out}**  
    • Average Rating: **{avg_rating_out}**
    """, unsafe_allow_html=True)

    # Sankey Diagram
    st.markdown("### 🔄 Transfer Flow Visualization")
    
    # Create node lists for Sankey
    schools = pd.unique(pd.concat([filtered_df["origin"], filtered_df["destination"]]).dropna())
    label_map = {name: i for i, name in enumerate(schools)}
    
    # Create source-target pairs
    sources = [label_map[school] for school in filtered_df["origin"]]
    targets = [label_map[school] for school in filtered_df["destination"]]
    
    # Create node labels and colors
    node_colors = ['#17408B' if school == selected_team else '#C9082A' 
                  for school in schools]
    
    # Create Sankey diagram
    fig_sankey = go.Figure(data=[go.Sankey(
        node = dict(
            pad = 15,
            thickness = 20,
            line = dict(color = "black", width = 0.5),
            label = schools,
            color = node_colors
        ),
        link = dict(
            source = sources,
            target = targets,
            value = [1] * len(sources)  # Each transfer counts as 1
        )
    )])
    
    # Update layout
    fig_sankey.update_layout(
        title=f"Transfer Portal Movement - {selected_team}",
        font_size=16,
        height=700
    )
    
    st.plotly_chart(fig_sankey, use_container_width=True)

    with st.expander("ℹ️ How to Read This Chart"):
        st.markdown("""
        - Each connection represents a player transfer
        - **Blue node** represents the selected school
        - **Red nodes** represent other schools involved in transfers
        - Links flowing left to right show player movement
        - Thickness of lines is equal as each transfer represents one player
        """)

        # Production Differential Analysis
        st.markdown("### 📈 Transfer Portal Production Differential")
        
        # Define stat categories for comparison
        stat_categories = {
            'Passing': ['passing_YDS', 'passing_TD', 'passing_COMPLETIONS'],
            'Rushing': ['rushing_YDS', 'rushing_TD', 'rushing_CAR'],
            'Receiving': ['receiving_YDS', 'receiving_TD', 'receiving_REC'],
            'Defense': ['defensive_TOT', 'defensive_TFL', 'defensive_SACKS', 'defensive_PD'],
            'Returns': ['kickReturns_YDS', 'puntReturns_YDS'],
            'Kicking': ['kicking_PTS']
        }
    
    # Filter stats for incoming/outgoing players (move this above)
    incoming_stats = transfers_stats[transfers_stats['destination'] == selected_team]
    outgoing_stats = transfers_stats[transfers_stats['origin'] == selected_team]
    
    # Define which stats should be scaled
    yardage_stats_list = [
        'passing_YDS', 'rushing_YDS', 'receiving_YDS',
        'kickReturns_YDS', 'puntReturns_YDS'
    ]
    yardage_scale_factor = 0.1  # divide by 10 for visualization
    
    # Calculate differentials
    differentials = []
    for category, stats in stat_categories.items():
        for stat in stats:
            if stat in transfers_stats.columns:
                incoming_total = incoming_stats[stat].sum()
                outgoing_total = outgoing_stats[stat].sum()
                diff = incoming_total - outgoing_total
    
                # Apply scaling for yardage stats (only for plotting)
                scaled_diff = diff * yardage_scale_factor if stat in yardage_stats_list else diff
    
                differentials.append({
                    'Category': category,
                    'Stat': stat,
                    'Differential': diff,          # real value
                    'ScaledDifferential': scaled_diff  # visualization value
                })
    
    # Create DataFrame
    diff_df = pd.DataFrame(differentials)
    
    # Create bar chart with scaled values but real numbers in tooltip
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=diff_df['Category'] + " - " + diff_df['Stat'],
        y=diff_df['ScaledDifferential'],
        text=diff_df['Differential'],  # show real values on hover
        hovertemplate='<b>%{x}</b><br>Real Diff: %{text}<extra></extra>',
        marker_color=diff_df['ScaledDifferential'].apply(
            lambda x: 'rgb(0, 150, 0)' if x > 0 else 'rgb(150, 0, 0)'
        )
    ))
    
    fig.update_layout(
        title=f"Production Differential Through Transfer Portal - {selected_team} (scaled for visibility)",
        xaxis_title="Statistical Category",
        yaxis_title="Scaled Differential (incoming - outgoing)",
        xaxis_tickangle=-45,
        height=500,
        showlegend=False,
        plot_bgcolor='white'
    )
    
    # Add horizontal line at y=0
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("ℹ️ How to Read This Chart"):
        st.markdown(f"""
            - **Positive values (green)** = incoming transfers bring more production than lost
            - **Negative values (red)** = more production lost than gained
            - **Values in tooltip** are the real differentials  
            - Yardage stats (Passing/Rushing/Receiving/Returns YDS) are divided by `{yardage_scale_factor}` for visualization only
            """)
    
    
    # Define stat columns by position group
    qb_stats = ['passing_COMPLETIONS', 'passing_ATT', 'passing_PCT', 'passing_YDS', 'passing_TD', 'passing_INT', 'passing_YPA']
    skill_stats = ['rushing_CAR', 'rushing_YDS', 'rushing_TD', 'receiving_REC', 'receiving_YDS', 'receiving_TD']
    def_stats = ['defensive_TOT', 'defensive_TFL', 'defensive_SACKS', 'interceptions_INT', 'defensive_PD']
    
    # Function to get relevant stats based on position
    def get_stats_columns(pos):
        if pos == 'QB':
            return qb_stats
        elif pos in ['RB', 'WR', 'TE']:
            return skill_stats
        elif pos in ['DE','DL', 'DT', 'LB', 'CB', 'S','DB']:
            return def_stats
        return []
    
    # ...existing code until player stats section...
    
    # Display stats tables by position group
    st.markdown("### 📊 Player Statistics (2025)")
    
    # Incoming Players Stats (full width)
    st.markdown("#### Incoming Players Stats")
    for pos in incoming_stats['position_x'].unique():
        pos_players = incoming_stats[incoming_stats['position_x'] == pos]
        if not pos_players.empty:
            st.markdown(f"**{pos}**")
            stats_cols = get_stats_columns(pos)
            if stats_cols:
                display_cols = ['firstName_x', 'lastName_x', 'origin'] + stats_cols
                st.dataframe(pos_players[display_cols].reset_index(drop=True), use_container_width=True)
    
    # Outgoing Players Stats (full width)
    st.markdown("#### Outgoing Players Stats")
    for pos in outgoing_stats['position_x'].unique():
        pos_players = outgoing_stats[outgoing_stats['position_x'] == pos]
        if not pos_players.empty:
            st.markdown(f"**{pos}**")
            stats_cols = get_stats_columns(pos)
            if stats_cols:
                display_cols = ['firstName_x', 'lastName_x', 'destination'] + stats_cols
            st.dataframe(pos_players[display_cols].reset_index(drop=True), use_container_width=True)