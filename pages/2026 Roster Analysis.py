import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="CFB Roster Analyzer",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🏈 College Football Roster Turnover Analyzer")
st.markdown("*Analyze roster changes, production loss/gain, and team comparisons*")

@st.cache_data
def load_data():
    """Load all CSV files"""
    try:
        # Load datasets
        draft = pd.read_csv('data/Draft_Position.csv')
        recruits = pd.read_csv('data/Recruits_2025.csv')
        roster_2024 = pd.read_csv('data/Roster_2024.csv')
        roster_2025 = pd.read_csv('data/Roster_2025.csv')
        player_stats = pd.read_csv('player_stats_2024.csv')
        transfers = pd.read_csv('data/Transfers_2025.csv')
        teams = pd.read_csv('data/teams.csv')  # Add this line
        
        return draft, recruits, roster_2025, player_stats, transfers, teams # Add teams
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        return None, None, None, None, None, None  # Add None for teams

def calculate_position_production(stats_df, roster_df=None):
    """Calculate production metrics by position with player mapping"""
    
    # Define position mapping for standardization
    position_mapping = {
        'CB': 'DB',
        'S': 'DB',
        'SAF': 'DB',
        'FS': 'DB',
        'SS': 'DB',
        'DB': 'DB',
        # Add any other position mappings as needed
    }
    
    # Define key stats by position with weights for importance
    position_stats = {
        'QB': {
            'stats': ['passing_YDS', 'passing_TD', 'rushing_YDS', 'rushing_TD'],
            'weights': [1, 20, 1, 6],  # TDs worth more than yards
            'name': 'QB Production'
        },
        'RB': {
            'stats': ['rushing_YDS', 'rushing_TD', 'receiving_YDS', 'receiving_TD'],
            'weights': [1, 6, 1, 6],
            'name': 'RB Production'
        },
        'WR': {
            'stats': ['receiving_YDS', 'receiving_TD', 'receiving_REC', 'rushing_YDS'],
            'weights': [1, 6, 2, 1],
            'name': 'WR Production'
        },
        'TE': {
            'stats': ['receiving_YDS', 'receiving_TD', 'receiving_REC'],
            'weights': [1, 6, 2],
            'name': 'TE Production'
        },
        'DL': {
            'stats': ['defensive_SACKS', 'defensive_TFL', 'defensive_TOT'],
            'weights': [3, 2, 1],
            'name': 'DL Production'
        },
        'LB': {
            'stats': ['defensive_TOT', 'defensive_SACKS', 'defensive_TFL'],
            'weights': [1, 3, 2],
            'name': 'LB Production'
        },
        'DB': {
            'stats': ['defensive_TOT', 'defensive_PD', 'interceptions_INT'],
            'weights': [1, 2, 5],
            'name': 'DB Production'
        },
        'K': {
            'stats': ['kicking_FGM', 'kicking_XPM', 'kicking_PTS'],
            'weights': [3, 1, 1],
            'name': 'K Production'
        }
    }
    
    # Merge with roster to get positions if provided
    if roster_df is not None:
        stats_with_pos = stats_df.merge(
            roster_df[['id', 'position']], 
            left_on='playerId', 
            right_on='id', 
            how='left'
        )
        # Standardize positions using the mapping
        stats_with_pos['position'] = stats_with_pos['position'].map(position_mapping).fillna(stats_with_pos['position'])
    else:
        stats_with_pos = stats_df.copy()
        stats_with_pos['position'] = 'Unknown'
    
    production_by_position = {}
    
    for pos_group, config in position_stats.items():
        # Filter players by position
        pos_players = stats_with_pos[stats_with_pos['position'] == pos_group].copy()
        
        if len(pos_players) > 0:
            # Calculate weighted production score
            pos_players['production_score'] = 0
            for i, stat in enumerate(config['stats']):
                if stat in pos_players.columns:
                    pos_players['production_score'] += (
                        pos_players[stat].fillna(0) * config['weights'][i]
                    )
            
            production_by_position[pos_group] = pos_players[['playerId', 'production_score']].copy()
        else:
            production_by_position[pos_group] = pd.DataFrame(columns=['playerId', 'production_score'])
    
    return production_by_position, position_stats

def calculate_team_production_breakdown(team_name, roster_2025, transfers, draft, player_stats):
    """Calculate returning vs lost vs incoming production for a team"""
    
    # Get production scores by position
    production_data, position_config = calculate_position_production(player_stats, roster_2025)
    
    # Initialize results
    production_breakdown = {}
    
    # Load 2024 roster for comparison
    roster_2024 = pd.read_csv('data/Roster_2024.csv')
    
    # Get all 2024 players for this team
    roster_2024_team = roster_2024[roster_2024['team'] == team_name]
    
    # Get current 2025 roster IDs
    roster_2025_team = roster_2025[roster_2025['team'] == team_name]
    roster_2025_ids = set(roster_2025_team['id'].tolist())
    
    for position, config in position_config.items():
        # Initialize production categories
        returning_production = 0
        lost_production = 0
        incoming_production = 0
        
        # Process all 2024 players at this position
        pos_players_2024 = roster_2024_team[roster_2024_team['position'] == position]
        
        for _, player in pos_players_2024.iterrows():
            player_id = player['id']
            # Get player's 2024 stats
            player_stats_row = player_stats[player_stats['playerId'] == player_id]
            
            if not player_stats_row.empty:
                # Calculate player's production
                production_value = 0
                for i, stat in enumerate(config['stats']):
                    if stat in player_stats_row.columns:
                        production_value += player_stats_row[stat].fillna(0).iloc[0] * config['weights'][i]
                
                # If player is in 2025 roster, count as returning
                # Otherwise count as lost (regardless of reason - draft, transfer, graduation, etc.)
                if player_id in roster_2025_ids:
                    returning_production += production_value
                else:
                    lost_production += production_value
        
        # Calculate incoming production from transfers
        transfers_in = transfers[
            (transfers['destination'] == team_name) & 
            (transfers['position_y'] == position)
        ]
        
        for _, transfer in transfers_in.iterrows():
            player_stats_row = player_stats[player_stats['playerId'] == transfer['playerId']]
            if not player_stats_row.empty:
                score = 0
                for i, stat in enumerate(config['stats']):
                    if stat in player_stats_row.columns:
                        score += player_stats_row[stat].fillna(0).iloc[0] * config['weights'][i]
                incoming_production += score
        
        production_breakdown[position] = {
            'returning': returning_production,
            'lost': lost_production,
            'incoming': incoming_production,
            'position_name': config['name']
        }
    
    return production_breakdown

def analyze_team_changes(team_name, roster_2025, transfers, draft, player_stats):
    """Analyze all roster changes for a team"""
    
    # Current roster
    current_roster = roster_2025[roster_2025['team'] == team_name].copy()
    
    # Players who transferred OUT
    transfers_out = transfers[transfers['origin'] == team_name].copy()
    
    # Players who transferred IN  
    transfers_in = transfers[transfers['destination'] == team_name].copy()
    
    # Players drafted (assuming they're from this team)
    drafted_players = draft[draft['collegeTeam'] == team_name].copy()
    
    # Get stats for analysis
    stats_with_team = player_stats.merge(
        current_roster[['id', 'position']], 
        left_on='playerId', 
        right_on='id', 
        how='left'
    )
    
    return {
        'current_roster': current_roster,
        'transfers_out': transfers_out,
        'transfers_in': transfers_in,
        'drafted': drafted_players,
        'stats': stats_with_team
    }

def calculate_player_production(player_stats_row, position, position_stats):
    """Calculate production score for an individual player"""
    if position not in position_stats:
        return 0
        
    config = position_stats[position]
    score = 0
    
    for i, stat in enumerate(config['stats']):
        if stat in player_stats_row.columns:
            score += player_stats_row[stat].fillna(0).iloc[0] * config['weights'][i]
            
    return score

def main():
    # Load data
    with st.spinner("Loading data..."):
        draft, recruits, roster_2025, player_stats, transfers, teams = load_data()
    
    if draft is None:
        st.error("Could not load data files. Please ensure all CSV files are in the correct location.")
        return
    
    # Sidebar controls
    st.sidebar.header("Team Selection")
    
    # Get unique teams and their logos
    all_teams = sorted(roster_2025['team'].unique())
    
    # Create a logo dictionary for easy lookup
    logo_dict = dict(zip(teams['school'], teams['logos']))
    
    selected_team = st.sidebar.selectbox("Select Team", all_teams, index=0)
    
    # Display team logo at the top
    if selected_team in logo_dict:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(logo_dict[selected_team], width=100)
        with col2:
            st.title(f"{selected_team} - Roster Analysis")
    else:
        st.title(f"{selected_team} - Roster Analysis")
    
    # Analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Production Analysis", "🔄 Player Movement", "🎯 Position Deep Dive"])
    
    # Analyze selected team
    team_analysis = analyze_team_changes(selected_team, roster_2025, transfers, draft, player_stats)
    
    with tab1:
        st.subheader("Roster Overview")
        
        # Create three columns for better layout
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Current roster size
            roster_size = len(team_analysis['current_roster'])
            st.metric("Current Roster", roster_size)
            
            # Recruiting class
            team_recruits = recruits[recruits['committedTo'] == selected_team]
            total_recruits = len(team_recruits)
            st.metric("2026 Recruits", total_recruits, delta=f"+{total_recruits}")
        
        with col2:
            transfers_out_count = len(team_analysis['transfers_out'])
            transfers_in_count = len(team_analysis['transfers_in'])
            st.metric("Transfers Out", transfers_out_count, delta=f"-{transfers_out_count}")
            st.metric("Transfers In", transfers_in_count, delta=f"+{transfers_in_count}")
        
        with col3:
            drafted_count = len(team_analysis['drafted'])
            net_transfers = transfers_in_count - transfers_out_count
            st.metric("Drafted Players", drafted_count, delta=f"-{drafted_count}")
            st.metric("Net Transfer Balance", net_transfers, 
                     delta=f"{'+' if net_transfers >= 0 else ''}{net_transfers}")
        
        # Position breakdown chart
        st.subheader("Current Roster by Position")
        if not team_analysis['current_roster'].empty:
            pos_breakdown = team_analysis['current_roster']['position'].value_counts()
            fig = px.bar(
                x=pos_breakdown.index, 
                y=pos_breakdown.values, 
                title=f"{selected_team} Position Distribution",
                color=pos_breakdown.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                height=400, 
                showlegend=False,
                xaxis_title="Position",
                yaxis_title="Number of Players"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("📊 Production Analysis")
        
        # Add production score explanation
        with st.expander("ℹ️ Understanding Production Scores"):
            st.markdown("""
            **Production Score Explained:**
            - Production scores are weighted calculations based on key statistics for each position
            - Higher scores indicate more on-field production and impact
            - Scores are position-specific and consider different stats:
                - **QB**: Passing yards (1x), Passing TDs (20x), Rushing yards (1x), Rushing TDs (6x)
                - **RB**: Rushing yards (1x), Rushing TDs (6x), Receiving yards (1x), Receiving TDs (6x)
                - **WR**: Receiving yards (1x), Receiving TDs (6x), Receptions (2x), Rushing yards (1x)
                - **TE**: Receiving yards (1x), Receiving TDs (6x), Receptions (2x)
                - **DL**: Sacks (3x), Tackles for Loss (2x), Total Tackles (1x)
                - **LB**: Total Tackles (1x), Sacks (3x), Tackles for Loss (2x)
                - **DB**: Total Tackles (1x), Pass Deflections (2x), Interceptions (5x)
                - **K**: Field Goals Made (3x), Extra Points Made (1x), Total Points (1x)
                
            *Example: A QB with 3000 passing yards (3000 × 1) and 30 TDs (30 × 20) would have a base production score of 3600*
            """)
        
        st.write("Visual breakdown of returning, lost, and incoming production by position")
        
        # Calculate production breakdown for the selected team
        team_production = calculate_team_production_breakdown(
            selected_team, roster_2025, transfers, draft, player_stats
        )
        
        # Create production visualization
        st.subheader(f"{selected_team} - Production Breakdown by Position")
        
        # Prepare data for chart
        positions = []
        returning_scores = []
        lost_scores = []
        incoming_scores = []
        
        for pos, data in team_production.items():
            if data['returning'] > 0 or data['lost'] > 0 or data['incoming'] > 0:
                positions.append(pos)
                returning_scores.append(data['returning'])
                lost_scores.append(-data['lost'])  # Negative for visual effect
                incoming_scores.append(data['incoming'])
        
        if positions:
            fig = go.Figure()
            
            # Returning production (green)
            fig.add_trace(go.Bar(
                name='Returning Production',
                x=positions,
                y=returning_scores,
                marker_color='#2E8B57',
                text=[f'{x:.0f}' for x in returning_scores],
                textposition='inside'
            ))
            
            # Incoming production (blue)
            fig.add_trace(go.Bar(
                name='Incoming Production',
                x=positions,
                y=incoming_scores,
                marker_color='#4169E1',
                text=[f'+{x:.0f}' for x in incoming_scores],
                textposition='inside'
            ))
            
            # Lost production (red, negative)
            fig.add_trace(go.Bar(
                name='Production Lost',
                x=positions,
                y=lost_scores,
                marker_color='#DC143C',
                text=[f'{abs(x):.0f}' for x in lost_scores],
                textposition='inside'
            ))
            
            fig.update_layout(
                title=f'{selected_team} Production Changes by Position',
                barmode='relative',
                xaxis_title='Position',
                yaxis_title='Production Score',
                height=600,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            
            total_returning = sum(returning_scores)
            total_lost = sum([abs(x) for x in lost_scores])
            total_incoming = sum(incoming_scores)
            net_change = total_returning + total_incoming - total_lost
            
            st.info("""
            💡 **How to interpret these numbers:**
            - Higher production scores indicate more statistical output
            - Net positive changes suggest improved production potential
            - Consider both quantity (total score) and quality (score per player)
            """)
            
            with col1:
                st.metric("Total Returning Production", f"{total_returning:.0f}")
            with col2:
                st.metric("Total Production Lost", f"{total_lost:.0f}", delta=f"-{total_lost:.0f}")
            with col3:
                st.metric("Total Incoming Production", f"{total_incoming:.0f}", delta=f"+{total_incoming:.0f}")
            with col4:
                st.metric("Net Production Change", f"{net_change:.0f}", 
                         delta=f"{'+' if net_change >= 0 else ''}{net_change:.0f}")
        
        # Production by category table
        st.subheader("Position-by-Position Breakdown")
        breakdown_data = []
        for pos, data in team_production.items():
            if data['returning'] > 0 or data['lost'] > 0 or data['incoming'] > 0:
                breakdown_data.append({
                    'Position': pos,
                    'Returning': f"{data['returning']:.0f}",
                    'Lost': f"{data['lost']:.0f}",
                    'Incoming': f"{data['incoming']:.0f}",
                    'Net Change': f"{data['returning'] + data['incoming'] - data['lost']:+.0f}"
                })
        
        breakdown_df = pd.DataFrame(breakdown_data)
        st.dataframe(breakdown_df, use_container_width=True)
    
    with tab3:
        st.header("🔄 Player Movement Details")
        st.write("Detailed breakdown of incoming and outgoing players")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 Players Lost")
            
            # Show drafted players
            if not team_analysis['drafted'].empty:
                st.write("**Drafted Players:**")
                # Load 2024 roster first
                roster_2024 = pd.read_csv('data/Roster_2024.csv')
                
                # Get names from 2024 roster
                draft_with_names = team_analysis['drafted'].merge(
                    roster_2024[['id', 'firstName', 'lastName', 'position']], 
                    left_on='collegeAthleteId',
                    right_on='id',
                    how='left'
                )
                
                # Create display dataframe
                if not draft_with_names.empty:
                    draft_display = draft_with_names.copy()
                    # Combine first and last name
                    draft_display['Player'] = draft_display['firstName'] + ' ' + draft_display['lastName']
                    # Make sure to use the correct column names that exist in the dataframe
                    draft_display = draft_display[['Player','overall']].copy()
                    draft_display.columns = ['Player', 'Draft Pick',]
                    
                    # Sort by draft pick and display
                    draft_display = draft_display.sort_values('Draft Pick')
                    # Remove any rows where Player is just a space
                    draft_display = draft_display[draft_display['Player'].str.strip() != '']
                    st.dataframe(draft_display, use_container_width=True)
            
            # Show transfer out players
            if not team_analysis['transfers_out'].empty:
                st.write("**Transfer Portal Departures:**")
                transfer_out_display = team_analysis['transfers_out'][['firstName_y', 'lastName_y', 'position_y', 'destination']].copy()
                transfer_out_display.columns = ['First Name', 'Last Name', 'Position', 'New Team']
                st.dataframe(transfer_out_display, use_container_width=True)
            
            if team_analysis['drafted'].empty and team_analysis['transfers_out'].empty:
                st.info("No players lost to draft or transfer portal")
        
        with col2:
            st.subheader("📥 Players Gained")
            
            # Transfer portal additions
            if not team_analysis['transfers_in'].empty:
                st.write("**Transfer Portal Additions:**")
                transfer_in_display = team_analysis['transfers_in'][['firstName_y', 'lastName_y', 'position_y', 'origin', 'stars', 'rating']].copy()
                transfer_in_display.columns = ['First Name', 'Last Name', 'Position', 'From Team', 'Stars', 'Rating']
                st.dataframe(transfer_in_display, use_container_width=True)
            
            # Recruiting class
            team_recruits = recruits[recruits['committedTo'] == selected_team]
            if not team_recruits.empty:
                st.write("**2026 Recruiting Class:**")
                recruit_display = team_recruits[['name', 'position', 'stars', 'rating', 'city', 'stateProvince']].copy()
                recruit_display.columns = ['Name', 'Position', 'Stars', 'Rating', 'City', 'State']
                st.dataframe(recruit_display, use_container_width=True)
            
            if team_analysis['transfers_in'].empty and team_recruits.empty:
                st.info("No incoming transfers or recruits found")
        
        # Summary section
        st.subheader("📊 Movement Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_lost = len(team_analysis['drafted']) + len(team_analysis['transfers_out'])
            st.metric("Total Players Lost", total_lost, delta=f"-{total_lost}")
        
        with col2:
            total_gained = len(team_analysis['transfers_in']) + len(team_recruits)
            st.metric("Total Players Gained", total_gained, delta=f"+{total_gained}")
        
        with col3:
            net_change = total_gained - total_lost
            st.metric("Net Player Change", net_change, delta=f"{'+' if net_change >= 0 else ''}{net_change}")
        
        with col4:
            if not team_recruits.empty:
                avg_recruit_rating = team_recruits['rating'].mean()
                st.metric("Avg Recruit Rating", f"{avg_recruit_rating:.1f}")
            else:
                st.metric("Avg Recruit Rating", "N/A")
    
    with tab4:
        st.header("🎯 Position Deep Dive")
        st.write("Detailed position-specific analysis")
        
        # Allow users to dive deeper into specific positions
        position_filter = st.selectbox(
            "Select Position for Analysis",
            sorted(roster_2025['position'].unique().tolist())
        )
        
        st.subheader(f"{position_filter} Analysis for {selected_team}")
        
        # Show current players at position
        current_pos_players = team_analysis['current_roster'][
            team_analysis['current_roster']['position'] == position_filter
        ]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Current {position_filter}s on Roster**")
            if not current_pos_players.empty:
                pos_display = current_pos_players[['firstName', 'lastName', 'year', 'height', 'weight']].copy()
                st.dataframe(pos_display, use_container_width=True)
                st.metric(f"Total {position_filter}s", len(current_pos_players))
            else:
                st.info(f"No {position_filter}s found on current roster")
        
        with col2:
            # Show transfers and recruits at this position
            pos_transfers_in = team_analysis['transfers_in'][
                team_analysis['transfers_in']['position_y'] == position_filter
            ] if not team_analysis['transfers_in'].empty else pd.DataFrame()
            
            pos_recruits = recruits[
                (recruits['committedTo'] == selected_team) & 
                (recruits['position'] == position_filter)
            ]
            
            st.write(f"**Incoming {position_filter}s**")
            
            if not pos_transfers_in.empty:
                st.write("*Transfer Portal:*")
                transfer_display = pos_transfers_in[['firstName_y', 'lastName_y', 'origin', 'stars']].copy()
                transfer_display.columns = ['First Name', 'Last Name', 'From', 'Stars']
                st.dataframe(transfer_display, use_container_width=True)
            
            if not pos_recruits.empty:
                st.write("*2026 Recruits:*")
                recruit_display = pos_recruits[['name', 'stars', 'rating', 'city', 'stateProvince']].copy()
                recruit_display.columns = ['Name', 'Stars', 'Rating', 'City', 'State']  
                st.dataframe(recruit_display, use_container_width=True)
            
            total_incoming = len(pos_transfers_in) + len(pos_recruits)
            st.metric(f"Total Incoming {position_filter}s", total_incoming)
        
        # Position-specific production analysis
        st.subheader(f"{position_filter} Production Analysis")
        
        team_production = calculate_team_production_breakdown(
            selected_team, roster_2025, transfers, draft, player_stats
        )
        
        if position_filter in team_production:
            pos_data = team_production[position_filter]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Returning Production", f"{pos_data['returning']:.0f}")
            with col2:
                st.metric("Production Lost", f"{pos_data['lost']:.0f}", delta=f"-{pos_data['lost']:.0f}")
            with col3:
                st.metric("Incoming Production", f"{pos_data['incoming']:.0f}", delta=f"+{pos_data['incoming']:.0f}")
            
            # Show who left at this position
            pos_transfers_out = team_analysis['transfers_out'][
                team_analysis['transfers_out']['position_y'] == position_filter
            ] if not team_analysis['transfers_out'].empty else pd.DataFrame()
            
            pos_drafted = team_analysis['drafted'][
                team_analysis['drafted']['position'] == position_filter
            ] if not team_analysis['drafted'].empty else pd.DataFrame()
            
            if not pos_transfers_out.empty or not pos_drafted.empty:
                st.write(f"**{position_filter}s Who Left:**")
                
                if not pos_drafted.empty:
                    st.write("*Drafted:*")
                    drafted_display = pos_drafted[['collegeTeam', 'position', 'overall']].copy()
                    st.dataframe(drafted_display, use_container_width=True)
                
                if not pos_transfers_out.empty:
                    st.write("*Transferred Out:*")
                    transfer_out_display = pos_transfers_out[['firstName_y', 'lastName_y', 'destination']].copy()
                    transfer_out_display.columns = ['First Name', 'Last Name', 'New Team']
                    st.dataframe(transfer_out_display, use_container_width=True)
        else:
            st.info(f"No production data available for {position_filter}")
    
    # Summary insights
    st.header("🎯 Key Insights")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📊 Roster Changes")
        net_transfers = len(team_analysis['transfers_in']) - len(team_analysis['transfers_out'])
        total_losses = len(team_analysis['transfers_out']) + len(team_analysis['drafted'])
        
        if net_transfers > 0:
            st.success(f"✅ Net gain of {net_transfers} players from transfer portal")
        elif net_transfers < 0:
            st.error(f"❌ Net loss of {abs(net_transfers)} players to transfer portal")
        else:
            st.info("⚖️ Transfer portal activity is neutral")
        
        st.write(f"📉 Total players lost: **{total_losses}**")
    
    with col2:
        st.subheader("🎓 Recruiting Class")
        team_recruits = recruits[recruits['committedTo'] == selected_team]
        
        if not team_recruits.empty:
            avg_stars = team_recruits['stars'].mean()
            total_recruits = len(team_recruits)
            
            st.metric("Total 2026 Recruits", total_recruits)
            st.metric("Average Star Rating", f"{avg_stars:.1f}")
            
            # Top positions recruited
            top_pos = team_recruits['position'].value_counts().head(3)
            st.write("**Top Recruited Positions:**")
            for pos, count in top_pos.items():
                st.write(f"• {pos}: {count} players")
        else:
            st.info("No 2026 recruiting data available")
    
    with col3:
        st.subheader("⚡ Production Impact")
        team_production = calculate_team_production_breakdown(
            selected_team, roster_2025, transfers, draft, player_stats
        )
        
        total_returning = sum([data['returning'] for data in team_production.values()])
        total_lost = sum([data['lost'] for data in team_production.values()])
        total_incoming = sum([data['incoming'] for data in team_production.values()])
        net_production = total_returning + total_incoming - total_lost
        
        if net_production > 0:
            st.success(f"📈 Net production gain: +{net_production:.0f}")
        elif net_production < 0:
            st.error(f"📉 Net production loss: {net_production:.0f}")
        else:
            st.info("📊 Production impact is neutral")
        
        # Find position with biggest impact
        biggest_change_pos = None
        biggest_change_val = 0
        
        for pos, data in team_production.items():
            change = abs((data['returning'] + data['incoming']) - data['lost'])
            if change > biggest_change_val:
                biggest_change_val = change
                biggest_change_pos = pos
        
        if biggest_change_pos:
            st.write(f"**Biggest Change:** {biggest_change_pos}")

if __name__ == "__main__":
    main()