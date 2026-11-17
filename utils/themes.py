"""
Theme definitions for Factory Monitor Pro.
PREMIUM_DARK is the default theme applied on every page load.
LIGHT resets to Streamlit's native styling.
"""

PREMIUM_DARK_CSS = """
<style>
/* ── Base page background ── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 18% 10%, rgba(255,255,255,0.028) 0%, transparent 52%),
        radial-gradient(ellipse at 82% 90%, rgba(0,0,0,0.50)         0%, transparent 58%),
        linear-gradient(160deg,
            #2e2e2e  0%,
            #222222 38%,
            #1a1a1a 65%,
            #111111 100%
        ) !important;
    background-attachment: fixed !important;
}

/* ── Subtle top highlight ── */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: radial-gradient(
        ellipse at 50% 0%,
        rgba(255,255,255,0.022) 0%,
        transparent 62%
    );
    pointer-events: none;
    z-index: 0;
}

/* ── Bottom-corner depth vignette ── */
[data-testid="stAppViewContainer"]::after {
    content: "";
    position: fixed;
    inset: 0;
    background: radial-gradient(
        ellipse at 100% 100%,
        rgba(0,0,0,0.40) 0%,
        transparent 55%
    );
    pointer-events: none;
    z-index: 0;
}

/* ── Main content block ── */
[data-testid="stMain"] {
    background: transparent !important;
}
[data-testid="block-container"] {
    background: transparent !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        rgba(40,40,40,0.97) 0%,
        rgba(28,28,28,0.97) 100%
    ) !important;
    border-right: 0.5px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.75) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] p {
    color: rgba(255,255,255,0.60) !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.042) !important;
    border: 0.5px solid rgba(255,255,255,0.09) !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
}
[data-testid="stMetricValue"] {
    color: #f0f0f0 !important;
}
[data-testid="stMetricLabel"] {
    color: rgba(255,255,255,0.45) !important;
}
[data-testid="stMetricDelta"] {
    color: rgba(255,255,255,0.55) !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.025) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
}

/* ── Plotly / chart containers ── */
[data-testid="stPlotlyChart"] {
    background: rgba(255,255,255,0.028) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 12px !important;
    padding: 4px !important;
}

/* ── Component iframes (3D view, mobile) ── */
iframe {
    border-radius: 12px !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
}

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: rgba(255,255,255,0.06) !important;
    border: 0.5px solid rgba(255,255,255,0.14) !important;
    color: rgba(255,255,255,0.80) !important;
    border-radius: 8px !important;
    transition: background 0.18s ease, border-color 0.18s ease !important;
}
[data-testid="stButton"] > button:hover {
    background: rgba(255,255,255,0.10) !important;
    border-color: rgba(255,255,255,0.24) !important;
}
[data-testid="stButton"] > button:active {
    background: rgba(255,255,255,0.14) !important;
    transform: scale(0.98) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.05) !important;
    border: 0.5px solid rgba(255,255,255,0.10) !important;
    border-radius: 8px !important;
    color: rgba(255,255,255,0.80) !important;
}

/* ── Text input ── */
[data-testid="stTextInput"] > div > div > input {
    background: rgba(255,255,255,0.05) !important;
    border: 0.5px solid rgba(255,255,255,0.10) !important;
    border-radius: 8px !important;
    color: rgba(255,255,255,0.80) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.030) !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
}

/* ── Alert / info boxes ── */
[data-testid="stAlert"] {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
}

/* ── Dividers ── */
hr {
    border-color: rgba(255,255,255,0.08) !important;
}

/* ── General text ── */
h1, h2, h3, h4 {
    color: rgba(255,255,255,0.88) !important;
}
p, li, span, div {
    color: rgba(255,255,255,0.70);
}
.stMarkdown p {
    color: rgba(255,255,255,0.70) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 10px !important;
    border: 0.5px solid rgba(255,255,255,0.07) !important;
}
[data-testid="stTabs"] button[role="tab"] {
    color: rgba(255,255,255,0.50) !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: rgba(255,255,255,0.88) !important;
    background: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar       { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.20); }

/* ── Status pill helpers ── */
.status-on   { background: rgba(29,158,117,0.15); color: #5DCAA5;
               border: 0.5px solid rgba(93,202,165,0.25); border-radius: 20px;
               padding: 2px 10px; font-size: 12px; font-weight: 500; }
.status-off  { background: rgba(226,75,74,0.14);  color: #F09595;
               border: 0.5px solid rgba(240,149,149,0.25); border-radius: 20px;
               padding: 2px 10px; font-size: 12px; font-weight: 500; }
.status-maint{ background: rgba(239,159,39,0.14); color: #FAC775;
               border: 0.5px solid rgba(250,199,117,0.25); border-radius: 20px;
               padding: 2px 10px; font-size: 12px; font-weight: 500; }
.status-zone { background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.45);
               border: 0.5px solid rgba(255,255,255,0.10); border-radius: 20px;
               padding: 2px 10px; font-size: 12px; }
</style>
"""

LIGHT_CSS = """
<style>
[data-testid="stAppViewContainer"] {
    background: #f5f5f5 !important;
}
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 0.5px solid #e0e0e0 !important;
}
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 0.5px solid #e0e0e0 !important;
    border-radius: 12px !important;
    padding: 1rem 1.25rem !important;
}
[data-testid="stButton"] > button {
    background: #ffffff !important;
    border: 0.5px solid #d0d0d0 !important;
    color: #333333 !important;
    border-radius: 8px !important;
}
[data-testid="stButton"] > button:hover {
    background: #f0f0f0 !important;
}
</style>
"""
