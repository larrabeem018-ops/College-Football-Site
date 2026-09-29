import streamlit as st
from style import apply_style, html, ACCENT, ACCENT_TINT, TEXT_SECONDARY

# Page configuration
st.set_page_config(
    page_title="College Football Analytics Hub",
    page_icon="🏈",
    layout="wide",
)

apply_style()

# ---------------------------------------------------------------------------
# Icons (inline SVG, stroke-based, colored with the accent)
# ---------------------------------------------------------------------------
ICON = {
    "bars": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round"><line x1="5" y1="19" x2="5" y2="11"/><line x1="12" y1="19" x2="12" y2="6"/><line x1="19" y1="19" x2="19" y2="14"/></svg>',
    "compare": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 8h10"/><path d="M15 5l3 3-3 3"/><path d="M17 16H7"/><path d="M9 13l-3 3 3 3"/></svg>',
    "trend": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4,17 10,10 14,13 20,6"/><polyline points="14,6 20,6 20,12"/></svg>',
    "field": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="7" width="18" height="10" rx="1"/><line x1="8" y1="7" x2="8" y2="17"/><line x1="12" y1="7" x2="12" y2="17"/><line x1="16" y1="7" x2="16" y2="17"/></svg>',
    "radar": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polygon points="12,3 20,9 17,19 7,19 4,9"/></svg>',
    "flow": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round"><path d="M3 6h6l6 12h6"/><path d="M3 18h6l6-12h6"/></svg>',
    "calendar": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="16" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><line x1="8" y1="3" x2="8" y2="7"/><line x1="16" y1="3" x2="16" y2="7"/><circle cx="8.5" cy="14.5" r="1.1" fill="{ACCENT}" stroke="none"/><circle cx="15.5" cy="14.5" r="1.1" fill="{ACCENT}" stroke="none"/></svg>',
    "target": f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="0.8" fill="{ACCENT}"/></svg>',
}

LOGO_SVG = f"""
<svg width="26" height="26" viewBox="0 0 32 32" fill="none">
  <ellipse cx="16" cy="16" rx="13" ry="9" transform="rotate(-32 16 16)" stroke="{ACCENT}" stroke-width="1.6"/>
  <line x1="8.5" y1="20.2" x2="23.5" y2="11.8" stroke="{ACCENT}" stroke-width="1.6"/>
  <line x1="11.5" y1="14.6" x2="14" y2="13.2" stroke="{ACCENT}" stroke-width="1.3"/>
  <line x1="14" y1="16.2" x2="16.5" y2="14.8" stroke="{ACCENT}" stroke-width="1.3"/>
  <line x1="16.5" y1="17.8" x2="19" y2="16.4" stroke="{ACCENT}" stroke-width="1.3"/>
</svg>
"""

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
html(
    f"""
    <div style="display:flex; align-items:center; gap:12px; padding-bottom:8px;">
      {LOGO_SVG}
      <span style="font-family:'Spectral', serif; font-weight:600; font-size:22px;">College Football Analytics Hub</span>
    </div>
    """
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
html('<div class="cfb-eyebrow">Built on the CollegeFootballData API</div>')
html(
    """
    <h1 style="font-size:42px; line-height:1.15; margin:0 0 14px; max-width:760px;">
      Every team, every transfer, every drive — in one dashboard.
    </h1>
    """
)
html(
    f"""
    <p style="font-size:16px; line-height:1.6; max-width:620px; color:{TEXT_SECONDARY}; margin-bottom:24px;">
      Seven interactive tools for weekly matchups, model picks, roster turnover, betting markets, quarterback
      play, and the transfer portal — built for fans, analysts, and coaches who want the numbers
      behind the scoreboard.
    </p>
    """
)

cta_col1, cta_col2, _ = st.columns([1.1, 1, 3])
with cta_col1:
    st.page_link("pages/2026 Roster Analysis.py", label="Explore the Dashboards →", icon=None)
with cta_col2:
    st.link_button("View Data Sources", "https://collegefootballdata.com")

html("<div style='height:28px'></div>")

# ---------------------------------------------------------------------------
# Stat strip
# ---------------------------------------------------------------------------
stats = [
    ("134", "FBS teams tracked"),
    ("7", "analytics tools"),
    ("2026", "transfer portal cycle"),
    ("Live", "drive-by-drive charts"),
]
stat_cols = st.columns(4)
for col, (value, label) in zip(stat_cols, stats):
    with col:
        html(
            f"""
            <div class="cfb-stat-card">
              <div class="cfb-stat-value">{value}</div>
              <div class="cfb-stat-label">{label}</div>
            </div>
            """
        )

html("<div style='height:36px'></div>")

# ---------------------------------------------------------------------------
# Feature grid
# ---------------------------------------------------------------------------
html('<div class="cfb-eyebrow" style="color:#5F5D59; letter-spacing:0.08em;">ANALYTICS TOOLS</div>')

features = [
    {
        "icon": "bars",
        "title": "Roster Turnover Analyzer",
        "desc": "Production gained vs. lost by position, weighted by draft impact and transfer flow.",
        "page": "pages/2026 Roster Analysis.py",
        "link_label": "Open Roster Turnover Analyzer",
    },
    {
        "icon": "compare",
        "title": "Team Comparison",
        "desc": "Side-by-side team profiles across efficiency, talent, and roster metrics.",
        "page": "pages/2026 Team Comparison.py",
        "link_label": "Open Team Comparison",
    },
    {
        "icon": "trend",
        "title": "Betting Results & ATS",
        "desc": "Spread cover tracking, favorite/underdog splits, and weekly ATS records.",
        "page": "pages/Betting Results.py",
        "link_label": "Open Betting Results",
    },
    {
        "icon": "radar",
        "title": "QB Radar Comparison",
        "desc": "Head-to-head QB profiles and weekly QBR progression, side by side.",
        "page": "pages/qb_visuals.py",
        "link_label": "Open QB Radar Comparison",
    },
    {
        "icon": "flow",
        "title": "Transfer Portal Tracker",
        "desc": "Sankey flow of incoming/outgoing transfers and net rating by team.",
        "page": "pages/transfers.py",
        "link_label": "Open Transfer Portal Tracker",
    },
    {
        "icon": "calendar",
        "title": "Weekly Preview",
        "desc": "This week's matchups with the spread, a stat-for-stat team comparison, and returning-production storylines.",
        "page": "pages/Weekly Preview.py",
        "link_label": "Open Weekly Preview",
    },
    {
        "icon": "target",
        "title": "Sharp Bets",
        "desc": "Where our score model disagrees with Vegas, why in plain English, and a self-grading track record.",
        "page": "pages/Sharp Bets.py",
        "link_label": "Open Sharp Bets",
    },
]

for row_start in range(0, len(features), 3):
    row = features[row_start:row_start + 3]
    cols = st.columns(3)
    for col, feat in zip(cols, row):
        with col:
            html(
                f"""
                <div class="cfb-card">
                  <div class="cfb-card-icon">{ICON[feat['icon']]}</div>
                  <div class="cfb-card-title">{feat['title']}</div>
                  <div class="cfb-card-desc">{feat['desc']}</div>
                </div>
                """
            )
            st.page_link(feat["page"], label=feat["link_label"] + " →")
    html("<div style='height:16px'></div>")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
html(
    """
    <div class="cfb-footer">
      <span>Built by a college football fan and data enthusiast. Feedback always welcome!</span>
      <span>Data: collegefootballdata.com · Python · Pandas · Plotly · Streamlit</span>
    </div>
    """
)
