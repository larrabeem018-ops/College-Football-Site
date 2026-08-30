"""
Shared visual theme for the College Football Analytics Hub.

Call apply_style() once near the top of every page, right after
st.set_page_config() (if the page sets one). It injects the Google
Fonts + CSS that give every page the same look: Spectral for headings,
Manrope for body text, a warm off-white background, and a single
turf-green accent color used across buttons, links, metrics, and
chart highlights.

Import chart-safe hex values (ACCENT, ACCENT_TINT, etc.) from this
module wherever a page builds a Plotly/Matplotlib figure, so the
charts pick up the same palette as the rest of the UI.
"""

import textwrap

import streamlit as st


def html(markup: str):
    """st.markdown wrapper for raw HTML/CSS blocks. Streamlit's markdown
    renderer ends a raw-HTML block at the first blank (or whitespace-only)
    line, which silently corrupts any multi-line HTML/CSS string written
    with normal Python source indentation — the rest renders as literal
    text instead of being applied. Dedent and drop blank lines so that
    can't happen. Always route multi-line HTML through this helper
    instead of calling st.markdown(..., unsafe_allow_html=True) directly."""
    text = textwrap.dedent(markup)
    text = "\n".join(line for line in text.split("\n") if line.strip() != "")
    st.markdown(text, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Palette (hex, derived from the approved design canvas — oklch(0.985 0.003 90)
# background / oklch(0.48 0.16 150) turf-green accent, etc.)
# ---------------------------------------------------------------------------
BG = "#FBFAF8"
CARD_BG = "#FFFFFF"
BORDER = "#E2E1DE"
TEXT_PRIMARY = "#0A0906"
TEXT_BODY = "#181611"
TEXT_SECONDARY = "#5F5D59"
TEXT_FOOTER = "#6B6964"
ACCENT = "#007424"          # turf green
ACCENT_TINT = "#E2EFE4"     # accent at low opacity over white, for icon chips
NEUTRAL_MID = "#888681"
NEUTRAL_BORDER = "#D8D7D4"

# A small qualitative sequence built around the accent, for charts that need
# more than one series (radar overlays, grouped bars, etc.)
CHART_SEQUENCE = [ACCENT, "#5F5D59", "#B8860B", "#4A6FA5", "#8B5E83"]

FONTS_LINK = (
    "https://fonts.googleapis.com/css2?"
    "family=Spectral:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap"
)


def apply_style():
    """Inject fonts, colors, and component CSS. Call once per page,
    after st.set_page_config() if the page has one."""
    html(
        f"""
        <link rel="stylesheet" href="{FONTS_LINK}">
        <style>
        html, body, [class*="css"] {{
            font-family: 'Manrope', system-ui, sans-serif;
        }}
        .stApp {{
            background: {BG};
        }}
        h1, h2, h3 {{
            font-family: 'Spectral', serif !important;
            color: {TEXT_PRIMARY} !important;
            font-weight: 600 !important;
        }}
        p, span, label, .stMarkdown {{
            color: {TEXT_BODY};
        }}

        /* Primary buttons -> accent green, matching the mockup CTAs */
        .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
            background-color: {ACCENT} !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
        }}
        .stButton > button:hover, .stLinkButton > a:hover {{
            background-color: #005C1C !important;
        }}

        /* Page links (used for the feature-grid "Open module" links) */
        a {{
            color: {ACCENT} !important;
            font-weight: 600 !important;
        }}
        a:hover {{
            color: #005C1C !important;
        }}
        div[data-testid="stPageLink"] p, div[data-testid="stPageLink"] span {{
            color: {ACCENT} !important;
            font-weight: 600 !important;
        }}
        div[data-testid="stPageLink"]:hover p, div[data-testid="stPageLink"]:hover span {{
            color: #005C1C !important;
        }}

        /* Metric widgets -> card look, accent-colored value */
        div[data-testid="stMetric"] {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 14px 18px;
        }}
        div[data-testid="stMetricValue"] {{
            font-family: 'Spectral', serif;
            color: {TEXT_PRIMARY};
        }}
        div[data-testid="stMetricLabel"] {{
            color: {TEXT_SECONDARY};
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: {CARD_BG};
            border-right: 1px solid {BORDER};
        }}

        /* Custom card classes used by render_feature_card() / render_stat_row() */
        .cfb-eyebrow {{
            font-size: 13px; font-weight: 600; letter-spacing: 0.08em;
            text-transform: uppercase; color: {ACCENT}; margin-bottom: 8px;
        }}
        .cfb-card {{
            background: {CARD_BG}; border: 1px solid {BORDER};
            border-radius: 10px; padding: 22px; height: 100%;
        }}
        .cfb-card-icon {{
            width: 38px; height: 38px; border-radius: 8px; background: {ACCENT_TINT};
            display: flex; align-items: center; justify-content: center; margin-bottom: 14px;
        }}
        .cfb-card-title {{
            font-weight: 700; font-size: 16px; color: {TEXT_PRIMARY}; margin-bottom: 6px;
        }}
        .cfb-card-desc {{
            font-size: 13.5px; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 4px;
        }}
        .cfb-stat-card {{
            background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;
            padding: 18px 20px;
        }}
        .cfb-stat-value {{
            font-family: 'Spectral', serif; font-size: 26px; font-weight: 600; color: {TEXT_PRIMARY};
        }}
        .cfb-stat-label {{
            font-size: 12.5px; color: {TEXT_SECONDARY}; margin-top: 2px;
        }}
        .cfb-footer {{
            font-size: 12.5px; color: {TEXT_FOOTER}; border-top: 1px solid {BORDER};
            padding-top: 18px; margin-top: 32px;
            display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
        }}

        /* Weekly Preview: matchup stat-comparison table */
        .cfb-stat-table {{
            width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13.5px;
        }}
        .cfb-stat-table th {{
            font-family: 'Spectral', serif; font-weight: 600; color: {TEXT_PRIMARY};
            text-align: center; padding: 4px 8px 8px; border-bottom: 1px solid {BORDER};
        }}
        .cfb-stat-table td {{
            text-align: center; padding: 7px 8px; border-bottom: 1px solid {BORDER};
            color: {TEXT_BODY}; width: 30%;
        }}
        .cfb-stat-table td.cfb-stat-label-cell {{
            width: 40%; color: {TEXT_SECONDARY}; font-size: 12.5px;
        }}
        .cfb-stat-table td.cfb-stat-better {{
            color: {ACCENT}; font-weight: 700;
        }}
        .cfb-pill {{
            display: inline-block; background: {ACCENT_TINT}; color: {ACCENT};
            font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px;
            margin: 4px 0;
        }}
        </style>
        """
    )
