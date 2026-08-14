import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- Load Data ---
@st.cache_data
def load_plays():
    return pd.read_csv("data/Drives/week_1_plays_2025.csv")

@st.cache_data
def load_team_info():
    return pd.read_csv("data/team_info.csv")  # columns: school, id, logos

plays_df = load_plays()
teams_df = load_team_info()

st.title("📊 College Football Drive Visualizer")

# --- Create matchup column ---
plays_df['matchup'] = plays_df['away'] + " vs " + plays_df['home']

# --- Select matchup ---
matchups = plays_df[['gameId', 'matchup']].drop_duplicates()
selected_matchup = st.selectbox("Choose a game:", matchups['matchup'])
game_id = matchups.loc[matchups['matchup'] == selected_matchup, 'gameId'].values[0]

# --- Filter plays for that game ---
game_df = plays_df[plays_df['gameId'] == game_id]

# --- Drive selector with scroll ---
drive_info = game_df.groupby(['driveId', 'offense', 'driveNumber']).first().reset_index()
drive_info['label'] = drive_info['offense'] + " - Drive " + drive_info['driveNumber'].astype(str)

selected_drive_id = st.select_slider(
    "Scroll through drives:",
    options=drive_info['driveId'],
    format_func=lambda x: drive_info.loc[drive_info['driveId'] == x, 'label'].values[0]
)

# Filter for selected drive
drive_df = game_df[game_df['driveId'] == selected_drive_id]
last_play = drive_df.iloc[-1]

# --- Team logos ---
offense_logo = teams_df.loc[teams_df['school'] == last_play['offense'], 'logos'].values[0]
defense_logo = teams_df.loc[teams_df['school'] == last_play['defense'], 'logos'].values[0]

# Display scoreboard with logos
cols = st.columns([1,2,1])
with cols[0]:
    st.image(offense_logo, width=80)
with cols[1]:
    st.markdown(
        f"### {last_play['offenseScore']} - {last_play['defenseScore']}  |  Period {last_play['period']}  |  {last_play['clock.minutes']}:{str(last_play['clock.seconds']).zfill(2)}"
    )
with cols[2]:
    st.image(defense_logo, width=80)

# --- Prepare drive plays ---
drive_df = game_df[game_df['driveId'] == selected_drive_id].copy()

# Combine minutes and seconds into a single column
drive_df['Time Remaining'] = drive_df['clock.minutes'].astype(str).str.zfill(2) + ":" + drive_df['clock.seconds'].astype(str).str.zfill(2)

# Sort plays chronologically: by period, then descending clock (since football counts down)
drive_df = drive_df.sort_values(by=['period', 'clock.minutes', 'clock.seconds'], ascending=[True, False, False])

last_play = drive_df.iloc[-1]

# --- Table of plays ---
st.subheader("Drive Plays")
display_cols = ['playNumber', 'playType', 'yardsGained', 'playText', 
                'offenseScore', 'defenseScore', 'Time Remaining']
st.dataframe(drive_df[display_cols])

# --- Plot football field ---
fig, ax = plt.subplots(figsize=(24, 9))
ax.set_facecolor("green")
ax.set_xlim(0, 100)
ax.set_ylim(0, 53.3)
ax.set_yticks([])
ax.set_xticks(range(0, 101, 10))

# Yard lines
for x in range(0, 101, 10):
    ax.axvline(x, color="white", lw=1, ls="--")

# Endzones
ax.add_patch(plt.Rectangle((0, 0), 10, 53.3, color='darkgreen'))
ax.add_patch(plt.Rectangle((90, 0), 10, 53.3, color='darkgreen'))

ax.set_xlabel("Yards from Own Goal Line")
ax.set_title(f"{last_play['offense']} - Drive {last_play['driveNumber']}")

import matplotlib.image as mpimg
import os

# Path to icons
icon_path = "Icons"

# Load icons
field_goal_icon = mpimg.imread(os.path.join(icon_path, "field_goal.png"))
rush_icon = mpimg.imread(os.path.join(icon_path, "rush.png"))
touchdown_icon = mpimg.imread(os.path.join(icon_path, "touchdown.png"))
punt_icon = mpimg.imread(os.path.join(icon_path, "punt.png"))
football_icon = mpimg.imread(os.path.join(icon_path, "football.png"))

def draw_play(start_yard, end_yard, play_type):
    x_start = 100 - start_yard
    x_end = 100 - end_yard
    y = np.random.uniform(15, 40)  # vertical offset

    # Place football icon at start
    ax.imshow(football_icon, extent=[x_start-2, x_start+2, y-2, y+2], zorder=6)

    # Rush: red straight line
    if play_type in ["Rush", "Rushing Touchdown"]:
        ax.plot([x_start, x_end], [y, y], color="red", lw=3, solid_capstyle="round")
    # Pass: purple arched line
    elif play_type in ["Pass Completion", "Pass Incompletion", "Passing Touchdown"]:
        mid_x = (x_start + x_end) / 2
        arc_y = y + 10
        ax.plot([x_start, mid_x, x_end], [y, arc_y, y], color="purple", lw=3, ls="--")

    # Icons for special plays
    if "Field Goal" in play_type:
        ax.imshow(field_goal_icon, extent=[x_end-3, x_end+3, y-3, y+3], zorder=5)
    elif "Rush" in play_type:
        ax.imshow(rush_icon, extent=[x_end-3, x_end+3, y-3, y+3], zorder=5)
    elif "Touchdown" in play_type:
        ax.imshow(touchdown_icon, extent=[x_end-3, x_end+3, y-3, y+3], zorder=5)
    elif "Punt" in play_type:
        ax.imshow(punt_icon, extent=[x_end-3, x_end+3, y-3, y+3], zorder=5)


# --- Draw all plays in drive ---
for _, row in drive_df.iterrows():
    start_yard = row['yardsToGoal']
    yards_gained = row.get('yardsGained', 0)
    end_yard = max(0, start_yard - yards_gained)
    draw_play(start_yard, end_yard, row['playType'])

# Show field
st.pyplot(fig)
