import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Transfer Portal Sankey", layout="wide")

st.title("🏈 Transfer Portal Movement (2025)")

# Load transfer data
df = pd.read_csv("data/transfers_2025.csv")
df = df.dropna(subset=["origin", "destination"])

# Minimal conference mapping (expand as needed)
conf_map = {
    "Alabama": "SEC", "Georgia": "SEC", "Florida": "SEC",
    "Ohio State": "Big Ten", "Michigan": "Big Ten",
    "USC": "Big Ten", "Penn State": "Big Ten",
    "Clemson": "ACC", "Florida State": "ACC",
    "Oregon": "Big Ten", "LSU": "SEC",
    # Add more as needed
}

# Add conference columns
df["origin_conf"] = df["origin"].map(conf_map).fillna("Other")
df["destination_conf"] = df["destination"].map(conf_map).fillna("Other")

# Dropdown to filter by team
selected_team = st.selectbox("🎯 Filter by School (optional):", ["None"] + sorted(df["origin"].dropna().unique()))

if selected_team == "None":
    st.subheader("Transfers Between Conferences")

    # Group by conference movement
    grouped = df.groupby(["origin_conf", "destination_conf"]).size().reset_index(name="count")
    nodes = pd.unique(grouped[["origin_conf", "destination_conf"]].values.ravel())
    node_map = {name: i for i, name in enumerate(nodes)}

    grouped["source"] = grouped["origin_conf"].map(node_map)
    grouped["target"] = grouped["destination_conf"].map(node_map)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            label=nodes,
            color="blue",
        ),
        link=dict(
            source=grouped["source"],
            target=grouped["target"],
            value=grouped["count"]
        )
    )])

    fig.update_layout(
        title="Transfer Portal Movement Between Conferences",
        font_size=16,
        width=1400,
        height=700,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=False)

else:
    st.subheader(f"Transfers In/Out for **{selected_team}**")

    filtered_df = df[(df["origin"] == selected_team) | (df["destination"] == selected_team)].copy()

    schools = pd.unique(pd.concat([filtered_df["origin"], filtered_df["destination"]]).dropna())
    label_map = {name: i for i, name in enumerate(schools)}

    flow = filtered_df.groupby(["origin", "destination"]).size().reset_index(name="count")
    flow["source"] = flow["origin"].map(label_map)
    flow["target"] = flow["destination"].map(label_map)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            label=schools,
            color="blue",
        ),
        link=dict(
            source=flow["source"],
            target=flow["target"],
            value=flow["count"]
        )
    )])

    fig.update_layout(
        title=f"Transfer Portal Movement: {selected_team}",
        font_size=16,
        width=1400,
        height=700,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=False)

    # Show raw player data
    st.markdown("### Player Details")
    incoming = filtered_df[filtered_df["destination"] == selected_team][["firstName", "lastName", "rating","position","stars","origin"]]
    outgoing = filtered_df[filtered_df["origin"] == selected_team][["firstName", "lastName", "rating","position","stars","destination"]]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Incoming Transfers")
        st.dataframe(incoming.reset_index(drop=True))
    with col2:
        st.markdown("#### Outgoing Transfers")
        st.dataframe(outgoing.reset_index(drop=True))




