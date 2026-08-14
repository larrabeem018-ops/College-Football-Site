import streamlit as st
# Page configuration
st.set_page_config(
    page_title="College Football Analytics Hub",
    page_icon="🏈",
    layout="wide"
)

# Title and subtitle
st.title("🏈 College Football Analytics Hub")
st.markdown("""
Welcome to the **College Football Analytics Hub**, your one-stop shop for in-depth data visualizations, predictive modeling, and advanced team/player insights — built using the [CollegeFootballData API](https://collegefootballdata.com).

Whether you're a fan, analyst, or coach, this platform gives you interactive tools to explore the sport beyond the scoreboard.
""")

# Divider
st.markdown("---")

# Section: What You Can Do
st.header("🚀 Features")

st.markdown("""
### 📊 Interactive Visuals
Dive into intuitive visualizations like:
- **Quarterback Radar Charts** – Compare QBs on attempts, completion %, yards, TDs, and INTs
- [Future] **Receiver Trees**, **Team Radar Charts**, and more

### 🔀 Transfer Portal Tracker
Explore the 2026 transfer portal using:
- **Interactive Sankey Charts** – See where players are coming from and going to
- **Player Ratings** – Hover to see names and rating details
- **Team Filters** – Focus on a specific team’s movement

### 📈 Predictive Modeling (In Progress)
- **Point Differential Model** using ELO, efficiency metrics, and play data
- [Planned] **Win Probability Models** and **Spread Projections**

### 📂 Data Sources
- 🧠 Powered by: [collegefootballdata.com](https://collegefootballdata.com)
- 🔢 Built with: Python, Pandas, Plotly, Streamlit

### 📅 Coming Soon
- **Team Dashboards** with custom visuals and metrics
- **Game Pick Tools** using model projections
- **Historical Trend Analysis**
""")

# Final note
st.markdown("---")
st.markdown("Built by a college football fan and data enthusiast. Feedback always welcome!")

