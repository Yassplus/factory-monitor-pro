"""
Factory Production Monitor – v4
New in this version:
  1. Realistic 3D machine shapes (saw/drill/press/welder/vertical/sorter)
  2. Animated status pulse rings (Plotly frames)
  3. Worker 3D figures near each machine
  4. Material flow arrows on floor
  5. Camera preset buttons (Overview / Left Zone / Right Zone / Aisle)
  6. Independent scrollable machine list panel
  + Zone swap fix: Left=small-X side, Right=large-X side (as seen from entrance)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from PIL import Image
import io, os, hashlib, struct, base64, json

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Factory Monitor Pro",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE   = os.path.dirname(os.path.abspath(__file__))

# ── Area / Factory configuration ──────────────────────────────────────────────
_F4_EXCEL = os.path.join(BASE, "data", "F4_A1_A2_machine_status.xlsx")
AREAS = {
    "F5 – Area 1": {
        "key":         "F5_A1",
        "excel":       os.path.join(BASE, "data", "F5_A1_machine_status.xlsx"),
        "layout_dark": os.path.join(BASE, "assets", "layout.png"),
        "layout_pro":  os.path.join(BASE, "assets", "layout_pro.png"),
        "title":       "FACTORY 5 — AREA 1",
        "subtitle":    "Production Monitor · Real-Time Machine Status",
    },
    "F5 – Area 2": {
        "key":         "F5_A2",
        "excel":       os.path.join(BASE, "data", "F5_A2_machine_status.xlsx"),
        "layout_dark": os.path.join(BASE, "assets", "F5_A2_layout_dark.png"),
        "layout_pro":  os.path.join(BASE, "assets", "F5_A2_layout_pro.png"),
        "title":       "FACTORY 5 — AREA 2",
        "subtitle":    "Production Monitor · Real-Time Machine Status",
    },
    "F4 – Area 1": {
        "key":         "F4_A1",
        "excel":       _F4_EXCEL,
        "excel_rows":  (0, 15),          # rows 0-14 = A1 machines (blue cells)
        "layout_dark": os.path.join(BASE, "assets", "F4_A1_layout_dark.png"),
        "layout_pro":  os.path.join(BASE, "assets", "F4_A1_layout_pro.png"),
        "title":       "FACTORY 4 — AREA 1",
        "subtitle":    "Production Floor · Real-Time Machine Status",
    },
    "F4 – Area 2": {
        "key":         "F4_A2",
        "excel":       _F4_EXCEL,
        "excel_rows":  (15, 26),         # rows 15-25 = A2 machines (tan cells)
        "layout_dark": os.path.join(BASE, "assets", "F4_A2_layout_dark.png"),
        "layout_pro":  os.path.join(BASE, "assets", "F4_A2_layout_pro.png"),
        "title":       "FACTORY 4 — AREA 2",
        "subtitle":    "Storage, Assembly & Finishing · Real-Time Status",
    },
}
# ── Session state ──────────────────────────────────────────────────────────────
_SS_DEFAULTS = {
    "theme":            "light",
    "view_mode":        "2D Floor Plan",
    "selected_machine": None,
    "df":               None,
    "layout_img":       None,
    "dxf_coords":       None,
    "cam_preset":       "overview",
    "show_roof":        False,
    "show_labels":      True,
    "rate_df":          None,
    "cell_df":          None,
    "bom_data":         None,
    "active_area":      "F5 \u2013 Area 1",
    "history_date":     None,
    "viewing_history":  False,
    "display_lang":     "English",   # "English" | "Arabic"
}
for k, v in _SS_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Theme palette ──────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":         "#0a0a0a",
        "surface":    "#141414",
        "surface2":   "#1e1e1e",
        "border":     "#2a2a2a",
        "text":       "#f0f0f0",
        "text_muted": "#707070",
        "accent":     "#3b82f6",
        "paper_bg":   "#0a0a0a",
        "grid":       "#2a2a2a",
        "sidebar_bg": "#111111",
    },
    "light": {
        "bg":         "#f0f2f5",   # Soft blue-grey — executive, not harsh white
        "surface":    "#e4e7ec",   # Card backgrounds — slightly darker than page bg, no pure white
        "surface2":   "#eaecf0",   # Secondary surface — slightly deeper
        "border":     "#d2d6df",   # Refined, subtle borders
        "text":       "#1a2035",   # Deep navy — easier on eyes than pure black
        "text_muted": "#5e6e8a",   # Slate-blue muted tone
        "accent":     "#1d4ed8",   # Executive blue
        "paper_bg":   "#f0f2f5",   # Chart backgrounds match page
        "grid":       "#dde0e8",   # Chart grid lines
        "sidebar_bg": "#e4e7ed",   # Sidebar slightly deeper than main bg
    },
}
STATUS_COLORS  = {"ON": "#22c55e", "OFF": "#ef4444", "MAINTENANCE": "#f59e0b"}
STATUS_EMOJI   = {"ON": "🟢", "OFF": "🔴", "MAINTENANCE": "🟡"}
STATUS_OPTIONS = ["ON", "OFF", "MAINTENANCE"]
T = THEMES[st.session_state.theme]

# Camera presets — view from entrance (top of DXF = ny≈0), so camera looks
# from positive-Y side toward negative-Y (entrance at y=1 in 3D)
CAM_PRESETS = {
    "overview":   dict(eye=dict(x=0.0,  y=-2.2, z=1.6),  center=dict(x=0,y=0,z=0)),
    "left_zone":  dict(eye=dict(x=-2.0, y=-1.2, z=1.0),  center=dict(x=-0.3,y=0.1,z=0)),
    "right_zone": dict(eye=dict(x=2.0,  y=-1.2, z=1.0),  center=dict(x=0.3,y=0.1,z=0)),
    "aisle":      dict(eye=dict(x=0.0,  y=0.0,  z=2.4),  center=dict(x=0,y=0,z=0)),
}

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ══ RESET & BASE ══════════════════════════════════════════════════════════ */
*, *::before, *::after {{ box-sizing: border-box; }}

html, body, [data-testid="stAppViewContainer"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: {T['bg']} !important;
    color: {T['text']} !important;
}}

[data-testid="stAppViewContainer"] {{
    background: {T['bg']} !important;
    min-height: 100vh;
}}

[data-testid="stAppViewContainer"] > .main > div {{
    padding: 0 2rem 3rem !important;
    max-width: 1600px;
}}

.main .block-container {{
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
}}

/* ══ SIDEBAR ════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: {T['sidebar_bg']} !important;
    border-right: 1px solid {T['border']} !important;
    padding-top: 0 !important;
}}

[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0 !important;
}}

[data-testid="stSidebar"] * {{
    color: {T['text']} !important;
    font-family: 'Inter', sans-serif !important;
}}

/* keep Streamlit's icon font so icons don't render as words */
[data-testid="stSidebar"] [data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] {{
    font-family: 'Material Symbols Rounded' !important;
}}

/* Sidebar brand header */
[data-testid="stSidebar"]::before {{
    content: "Factory Monitor Pro";
    display: block;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.5px;
    color: {T['text']} !important;
    padding: 20px 20px 0;
    margin-bottom: 4px;
    opacity: 0.9;
}}

[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div {{
    background: {T['surface']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important;
    font-size: 13px !important;
}}

[data-testid="stSidebar"] .stRadio > div {{
    gap: 2px !important;
}}

[data-testid="stSidebar"] .stRadio label {{
    font-size: 13px !important;
    padding: 4px 0 !important;
}}

/* ══ SECTION LABELS (sidebar) ══════════════════════════════════════════════ */
.sec-lbl {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: {T['text_muted']};
    font-family: 'JetBrains Mono', monospace !important;
    margin: 18px 0 6px;
    padding-bottom: 6px;
    border-bottom: 1px solid {T['border']};
    display: block;
}}

hr.s {{ border: none; border-top: 1px solid {T['border']}; margin: 14px 0; }}

/* ══ HEADER ═════════════════════════════════════════════════════════════════ */
.factory-header {{
    background: {T['surface']};
    border: 1px solid {T['border']};
    border-radius: 12px;
    padding: 18px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    position: relative;
    overflow: hidden;
}}
.factory-header::after {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #3b82f6 0%, #06b6d4 50%, #22c55e 100%);
}}
.factory-title {{
    font-size: 18px;
    font-weight: 700;
    color: {T['text']};
    letter-spacing: 0.3px;
    line-height: 1.3;
}}
.factory-subtitle {{
    font-size: 11px;
    color: {T['text_muted']};
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 3px;
    font-family: 'JetBrains Mono', monospace;
}}
.live-badge {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.3);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 10px;
    font-weight: 700;
    color: #22c55e;
    letter-spacing: 1.5px;
    font-family: 'JetBrains Mono', monospace;
}}
.live-dot {{
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #22c55e;
    animation: pulse 1.6s infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.4; transform: scale(1.5); }}
}}

/* ══ KPI CARDS ══════════════════════════════════════════════════════════════ */
.kpi-row {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 20px;
}}
.kpi-card {{
    background: {T['surface']};
    border: 1px solid {T['border']};
    border-radius: 10px;
    padding: 18px 20px 14px;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    cursor: default;
}}
.kpi-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.18);
    border-color: rgba(59,130,246,0.3);
}}
/* Colored left accent bar */
.kpi-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    border-radius: 10px 0 0 10px;
}}
.kc-blue::before   {{ background: #3b82f6; }}
.kc-green::before  {{ background: #22c55e; }}
.kc-red::before    {{ background: #ef4444; }}
.kc-yellow::before {{ background: #f59e0b; }}
.kc-grad::before   {{ background: linear-gradient(180deg, #3b82f6, #22c55e); }}
.kpi-icon {{
    font-size: 16px;
    margin-bottom: 10px;
    display: block;
    opacity: 0.85;
}}
.kpi-label {{
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: {T['text_muted']};
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 6px;
}}
.kpi-val {{
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.5px;
    font-variant-numeric: tabular-nums;
}}
.kpi-sub {{
    font-size: 10px;
    color: {T['text_muted']};
    margin-top: 5px;
    font-family: 'JetBrains Mono', monospace;
}}
/* Inline progress bar inside KPI */
.kpi-bar {{
    height: 3px;
    border-radius: 2px;
    margin-top: 8px;
    background: {T['border']};
    overflow: hidden;
}}
.kpi-bar-fill {{
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
}}

/* ══ MACHINE LIST PANEL ═════════════════════════════════════════════════════ */
.machine-scroll-wrapper {{
    height: 620px;
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 2px;
    scrollbar-width: thin;
    scrollbar-color: {T['border']} transparent;
}}
.machine-scroll-wrapper::-webkit-scrollbar {{ width: 3px; }}
.machine-scroll-wrapper::-webkit-scrollbar-track {{ background: transparent; }}
.machine-scroll-wrapper::-webkit-scrollbar-thumb {{
    background: {T['border']}; border-radius: 3px;
}}
.mcard {{
    background: {T['surface']};
    border: 1px solid {T['border']};
    border-radius: 8px;
    padding: 9px 12px;
    margin-bottom: 4px;
    transition: border-color 0.12s, background 0.12s;
    cursor: pointer;
}}
.mcard:hover {{
    border-color: rgba(59,130,246,0.5);
    background: {T['surface2']};
}}
.mcard.sel {{
    border-color: #3b82f6;
    background: {T['surface2']};
    box-shadow: 0 0 0 1px rgba(59,130,246,0.2);
}}
.mname {{
    font-size: 12px;
    font-weight: 600;
    color: {T['text']};
    line-height: 1.3;
}}
.mmeta {{
    display: flex;
    gap: 6px;
    align-items: center;
    margin-top: 4px;
    flex-wrap: wrap;
}}
.mpill {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.5px;
    padding: 2px 7px;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.4;
}}
.p-ON   {{ background: rgba(34,197,94,0.12);  color: #22c55e; border: 1px solid rgba(34,197,94,0.25); }}
.p-OFF  {{ background: rgba(239,68,68,0.12);  color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }}
.p-MAINTENANCE {{ background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.25); }}
.mops {{
    font-size: 10px;
    color: {T['text_muted']};
    font-family: 'JetBrains Mono', monospace;
}}

/* ══ CHARTS & DATA CONTAINERS ═══════════════════════════════════════════════ */
[data-testid="stPlotlyChart"] {{
    border-radius: 10px;
    border: 1px solid {T['border']};
    overflow: hidden;
    background: {T['surface']};
}}
[data-testid="stDataFrame"] {{
    border-radius: 10px;
    border: 1px solid {T['border']};
    overflow: hidden;
}}
[data-testid="stDataFrame"] th {{
    background: {T['surface2']} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    text-transform: uppercase !important;
    color: {T['text_muted']} !important;
    border-bottom: 1px solid {T['border']} !important;
    padding: 8px 12px !important;
}}
[data-testid="stDataFrame"] td {{
    font-size: 13px !important;
    padding: 7px 12px !important;
    border-bottom: 1px solid {T['border']}22 !important;
    font-family: 'JetBrains Mono', monospace !important;
}}

/* ══ TABS ════════════════════════════════════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"] {{
    background: transparent;
    border-bottom: 1px solid {T['border']};
    padding: 0;
    gap: 0;
    margin-bottom: 16px;
}}
[data-testid="stTabs"] [role="tab"] {{
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    color: {T['text_muted']} !important;
    padding: 8px 18px !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    transition: all 0.15s ease !important;
    background: transparent !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #3b82f6 !important;
    border-bottom-color: #3b82f6 !important;
}}
[data-testid="stTabs"] [role="tab"]:hover {{
    color: {T['text']} !important;
    background: {T['surface']} !important;
}}

/* ══ EXPANDER ════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {{
    background: {T['surface']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 10px !important;
    overflow: hidden;
}}
[data-testid="stExpander"] summary {{
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
    border-radius: 10px !important;
}}

/* ══ BUTTONS ═════════════════════════════════════════════════════════════════ */
.stButton > button {{
    background: {T['accent']} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 8px 16px !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 1px 4px rgba(59,130,246,0.25) !important;
}}
.stButton > button:hover {{
    background: #2563eb !important;
    box-shadow: 0 3px 12px rgba(59,130,246,0.35) !important;
    transform: translateY(-1px) !important;
}}
.stButton > button:active {{
    transform: translateY(0) !important;
}}

/* ══ INPUTS ══════════════════════════════════════════════════════════════════ */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea {{
    background: {T['surface']} !important;
    border: 1px solid {T['border']} !important;
    border-radius: 8px !important;
    color: {T['text']} !important;
    font-size: 13px !important;
    transition: border-color 0.15s !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {{
    border-color: {T['accent']} !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important;
}}

/* ══ SCROLLBAR GLOBAL ════════════════════════════════════════════════════════ */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: {T['border']};
    border-radius: 10px;
}}
::-webkit-scrollbar-thumb:hover {{ background: {T['text_muted']}; }}

/* ══ SECTION DIVIDER ═════════════════════════════════════════════════════════ */
.panel-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    padding-bottom: 10px;
    border-bottom: 1px solid {T['border']};
}}
.panel-title {{
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: {T['text_muted']};
    font-family: 'JetBrains Mono', monospace;
}}
.panel-accent {{
    width: 3px;
    height: 14px;
    border-radius: 2px;
    background: {T['accent']};
    flex-shrink: 0;
}}

/* Camera preset buttons */
.cam-btns {{
    display: flex;
    gap: 6px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}}
.cam-btn {{
    background: {T['surface2']};
    border: 1px solid {T['border']};
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 10px;
    font-weight: 600;
    color: {T['text_muted']};
    cursor: pointer;
    transition: all 0.15s;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
}}
.cam-btn:hover, .cam-btn.active {{
    background: rgba(59,130,246,0.12);
    border-color: {T['accent']};
    color: {T['accent']};
}}

/* ══ ALERT BANNER ════════════════════════════════════════════════════════════ */
.alert-banner {{
    background: rgba(245,158,11,0.08);
    border: 1px solid rgba(245,158,11,0.35);
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 14px;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}}
.alert-title {{
    font-size: 10px;
    font-weight: 700;
    color: #f59e0b;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 3px;
}}
.alert-body {{
    font-size: 11px;
    color: {T['text']};
    line-height: 1.5;
}}
</style>
""", unsafe_allow_html=True)

# ── Coordinate helpers ─────────────────────────────────────────────────────────
def _n(x, y):
    """DXF → normalised coords for A1. Matches actual image render bounds."""
    return round((x + 2.15) / 91.30, 4), round(1.0 - (y + 2.57) / 144.51, 4)

def zone_fallback(machine, zone):
    h = struct.unpack("I", hashlib.md5(machine.encode()).digest()[:4])[0]
    j = (h % 80) / 1000.0
    z = (zone or "").strip().lower()
    if z == "left":   return 0.15 + j, 0.45 + j
    if z == "right":  return 0.52 + j, 0.45 + j
    return 0.35 + j, 0.50 + j

# ── Area 1 machine coordinates ────────────────────────────────────
# Bounds = actual matplotlib render extents when layout.png was generated
# X[-2.15..89.15], Y[-2.57..141.94]
def _n_a1(x, y):
    return round((x + 2.15) / 91.30, 4), round(1.0 - (y + 2.57) / 144.51, 4)

A1_COORDS = {
    "RASA Saw":               _n_a1(14.0, 102.8),
    "Assembly Station":       _n_a1(14.0,  93.2),
    "Welding Machine 1":      _n_a1(15.0,  64.2),
    "Welding Machine 2":      _n_a1(15.0,  60.0),
    "Welding Machine 3":      _n_a1(15.0,  55.8),
    "Welding Machine 4":      _n_a1(15.0,  51.6),
    "Welding Machine 5":      _n_a1(15.0,  47.4),
    "Drill #1":               _n_a1(16.5,  76.6),
    "Drill #2":               _n_a1(16.5,  68.9),
    "Drill":                  _n_a1(16.5,  72.0),
    "Manual Saw 1":           _n_a1(42.5, 112.3),
    "Manual Saw 2":           _n_a1(49.5, 112.3),
    "Leadgers Welding 1":     _n_a1(46.0, 107.4),
    "Leadgers Welding 2":     _n_a1(46.0, 103.6),
    "Leadgers Welding 3":     _n_a1(46.0,  99.8),
    "Leadgers Welding 4":     _n_a1(46.0,  96.0),
    "Leadgers Welding 5":     _n_a1(46.0,  92.2),
    "Leadgers Welding 6":     _n_a1(46.0,  88.4),
    "Ring Vertical 1":        _n_a1(46.0,  78.9),
    "Ring Vertical 2":        _n_a1(46.0,  75.1),
    "Ring Vertical 3":        _n_a1(46.0,  71.3),
    "Cup Vertical 1":         _n_a1(46.0,  68.3),
    "Cup Vertical 2":         _n_a1(46.0,  64.5),
    "Cup Vertical 3":         _n_a1(46.0,  60.7),
    "Cup Vertical 4":         _n_a1(46.0,  56.9),
    "Auto Welding":           _n_a1(46.0,  47.0),
    "Production Sorting Area":_n_a1(46.0,  36.7),
}

# Keep alias for code that still references DEFAULT_COORDS
DEFAULT_COORDS = A1_COORDS

# ── Area 2 machine coordinates ────────────────────────────────────────────────
# Bounds = actual matplotlib render extents when F5_A2_layout_dark.png was generated
# X[-1.95..84.95], Y[-6.58..94.08]
def _n_a2(x, y):
    return round((x + 1.95) / 86.90, 4), round(1.0 - (y + 6.58) / 100.66, 4)

A2_COORDS = {
    # Left production line (DXF x≈13-17)
    "Mixer 1":                _n_a2(13.3, 78.6),
    "Mixer 2":                _n_a2(16.3, 78.6),
    "Cup Frame Form Mixer 1": _n_a2(13.2, 71.5),
    "Cup Frame Form Mixer 2": _n_a2(16.4, 71.5),
    "Drrill 1":               _n_a2(12.9, 64.7),
    "Drrill 2":               _n_a2(14.8, 64.7),
    "Drrill 3":               _n_a2(16.7, 64.7),
    "Form & Tap":             _n_a2(14.8, 57.7),
    "Weld Cell 1":            _n_a2(12.2, 50.6),
    "Weld Cell 2":            _n_a2(17.4, 50.6),
    "Weld Cell 3":            _n_a2(12.2, 45.6),
    "Weld Cell 4":            _n_a2(17.4, 45.6),
    "Weld Cell 5":            _n_a2(12.2, 40.6),
    "Weld Cell 6":            _n_a2(17.4, 40.6),
    "Forming ":               _n_a2(14.8, 36.0),
    "Tap":                    _n_a2(14.8, 29.3),
    # Right production line (DXF x≈45-49)
    "Mixer 3":                _n_a2(45.7, 78.6),
    "Mixer 4":                _n_a2(48.7, 78.6),
    "Drill 4":                _n_a2(45.3, 71.6),
    "Drill 5":                _n_a2(47.2, 71.6),
    "Drill 6":                _n_a2(49.1, 71.6),
    "Saw ":                   _n_a2(47.2, 64.4),
    "Drill 7":                _n_a2(45.3, 57.2),
    "Drill 8":                _n_a2(47.2, 57.2),
    "Drill 9":                _n_a2(49.1, 57.2),
    "Multi Drill ":           _n_a2(47.2, 50.1),
    "Cup Weld 1":             _n_a2(45.7, 43.1),
    "Cup Weld 2":             _n_a2(48.7, 43.1),
    # Mixer 5 & 6 — new machines placed below Cup Weld 2
    "Mixer 5":                _n_a2(45.7, 36.5),
    "Mixer 6":                _n_a2(48.7, 36.5),
}

# Map area key → coordinate dict
AREA_COORDS = {
    "F5_A1": A1_COORDS,
    "F5_A2": A2_COORDS,
}

# ── Factory 4 Area 1 coordinates ──────────────────────────────────────────────
# Render bounds: X[-2.12..88.62], Y[-22.02..132.40]
def _n_f4a1(x, y):
    return round((x + 2.12) / 90.74, 4), round(1.0 - (y + 22.02) / 154.42, 4)

F4_A1_COORDS = {
    # Left zone (DXF x≈10-18)
    "Manual Saw":                 _n_f4a1(10.2, 111.0),   # row 0 (two entries)
    "ECO Punch Press":            _n_f4a1(14.0, 101.6),
    "TECH Punch / Drill":         _n_f4a1(14.0,  92.1),
    "ECO Punch + TECH Press":     _n_f4a1(14.0,  82.2),
    "Welding Package":            _n_f4a1(14.0,  73.9),
    "Pre-Assembly Welding Robot": _n_f4a1(14.0,  64.0),
    "9-Frame Assembly":           _n_f4a1(14.0,  53.5),
    "Welding Robot":              _n_f4a1(14.0,  43.1),
    # Right zone (DXF x≈46)
    "Auto Saw":                   _n_f4a1(46.0, 110.5),
    "Presses":                    _n_f4a1(46.0, 101.0),
    "Welding Station":            _n_f4a1(46.0,  93.2),
    "Delivery / QC":              _n_f4a1(46.0,  84.2),
    "Grinding":                   _n_f4a1(46.0,  75.7),
}

# ── Factory 4 Area 2 coordinates ──────────────────────────────────────────────
# Render bounds: X[-2.33..92.83], Y[-21.42..119.80]
def _n_f4a2(x, y):
    return round((x + 2.33) / 95.16, 4), round(1.0 - (y + 21.42) / 141.22, 4)

F4_A2_COORDS = {
    # Left zone (DXF x≈15)  — Storage/WIP/non-machine types included for overlay dots
    "Raw Material Storage":               _n_f4a2(15.0, 101.1),
    "Saw Machine":                        _n_f4a2(15.0,  85.9),
    "Manual Assembly Tools":              _n_f4a2(15.0,  75.4),
    "Storage Cabinet":                    _n_f4a2(15.0,  65.8),
    "Ready Acrow Board Pallets":          _n_f4a2(15.0,  55.3),
    "Pallet Assembly Spread":             _n_f4a2(15.0,  43.1),
    # Right zone (DXF x≈47)
    "Assembly RM Storage":                _n_f4a2(47.0, 101.1),
    "CNC Router Machine":                 _n_f4a2(47.0,  84.9),
    "WIP + Transport Carts + Cabinet Zone": _n_f4a2(47.0, 73.8),
    "TECH, ECO & WIP Area":              _n_f4a2(47.0,  62.8),
    "Paint / Coating Station":            _n_f4a2(47.0,  48.7),
}

AREA_COORDS.update({
    "F4_A1": F4_A1_COORDS,
    "F4_A2": F4_A2_COORDS,
})

DOT_OFFSET_X = 0.022

def _get_area_coords():
    """Return the correct coordinate dict for the currently active area."""
    key = st.session_state.get("active_area", "F5 – Area 1")
    area_key = AREAS.get(key, {}).get("key", "F5_A1")
    return AREA_COORDS.get(area_key, A1_COORDS)

def raw_coords(machine, zone, custom=None):
    """Return (nx, ny) without dot offset — for 3D placement."""
    src = custom if custom else _get_area_coords()
    if machine in src: return src[machine]
    # Fuzzy match — strip trailing spaces/numbers
    m_lower = machine.strip().lower()
    for k, v in src.items():
        if k.strip().lower() == m_lower: return v
        if k.strip().lower() in m_lower or m_lower in k.strip().lower(): return v
    return zone_fallback(machine, zone)

def get_coords(machine, zone, custom=None):
    """Return (nx, ny) with dot offset — for 2D overlay."""
    nx, ny = raw_coords(machine, zone, custom)
    return nx + DOT_OFFSET_X, ny


# ── Arabic translation dictionary ────────────────────────────────────────────
ARABIC_NAMES = {
    # Factory 5 Area 1
    "RASA Saw":                   "\u0645\u0646\u0634\u0627\u0631 \u0631\u0627\u0633\u0627",
    "Assembly Station":           "\u0645\u062d\u0637\u0629 \u0627\u0644\u062a\u062c\u0645\u064a\u0639",
    "Welding Machine 1":          "\u0645\u0627\u0643\u064a\u0646\u0629 \u0644\u062d\u0627\u0645 1",
    "Welding Machine 2":          "\u0645\u0627\u0643\u064a\u0646\u0629 \u0644\u062d\u0627\u0645 2",
    "Welding Machine 3":          "\u0645\u0627\u0643\u064a\u0646\u0629 \u0644\u062d\u0627\u0645 3",
    "Welding Machine 4":          "\u0645\u0627\u0643\u064a\u0646\u0629 \u0644\u062d\u0627\u0645 4",
    "Welding Machine 5":          "\u0645\u0627\u0643\u064a\u0646\u0629 \u0644\u062d\u0627\u0645 5",
    "Manual Saw 1":               "\u0645\u0646\u0634\u0627\u0631 \u064a\u062f\u0648\u064a 1",
    "Manual Saw 2":               "\u0645\u0646\u0634\u0627\u0631 \u064a\u062f\u0648\u064a 2",
    "Leadgers Welding 1":         "\u0644\u062d\u0627\u0645 \u0644\u064a\u062f\u062c\u0631 1",
    "Leadgers Welding 2":         "\u0644\u062d\u0627\u0645 \u0644\u064a\u062f\u062c\u0631 2",
    "Leadgers Welding 3":         "\u0644\u062d\u0627\u0645 \u0644\u064a\u062f\u062c\u0631 3",
    "Leadgers Welding 4":         "\u0644\u062d\u0627\u0645 \u0644\u064a\u062f\u062c\u0631 4",
    "Leadgers Welding 5":         "\u0644\u062d\u0627\u0645 \u0644\u064a\u062f\u062c\u0631 5",
    "Leadgers Welding 6":         "\u0644\u062d\u0627\u0645 \u0644\u064a\u062f\u062c\u0631 6",
    "Ring Vertical 1":            "\u0639\u0645\u0648\u062f\u064a \u062d\u0644\u0642\u064a 1",
    "Ring Vertical 2":            "\u0639\u0645\u0648\u062f\u064a \u062d\u0644\u0642\u064a 2",
    "Ring Vertical 3":            "\u0639\u0645\u0648\u062f\u064a \u062d\u0644\u0642\u064a 3",
    "Cup Vertical 1":             "\u0639\u0645\u0648\u062f\u064a \u0643\u0648\u0628 1",
    "Cup Vertical 2":             "\u0639\u0645\u0648\u062f\u064a \u0643\u0648\u0628 2",
    "Cup Vertical 3":             "\u0639\u0645\u0648\u062f\u064a \u0643\u0648\u0628 3",
    "Cup Vertical 4":             "\u0639\u0645\u0648\u062f\u064a \u0643\u0648\u0628 4",
    "Auto Welding":               "\u0644\u062d\u0627\u0645 \u0623\u0648\u062a\u0648\u0645\u0627\u062a\u064a\u0643\u064a",
    "Production Sorting Area":    "\u0645\u0646\u0637\u0642\u0629 \u0627\u0644\u0641\u0631\u0632 \u0648\u0627\u0644\u0625\u0646\u062a\u0627\u062c",
    "Drill":                      "\u0645\u062b\u0642\u0628",
    # Factory 5 Area 2
    "Mixer 1":  "\u062e\u0644\u0627\u0637 1", "Mixer 2":  "\u062e\u0644\u0627\u0637 2",
    "Mixer 3":  "\u062e\u0644\u0627\u0637 3", "Mixer 4":  "\u062e\u0644\u0627\u0637 4",
    "Mixer 5":  "\u062e\u0644\u0627\u0637 5", "Mixer 6":  "\u062e\u0644\u0627\u0637 6",
    "Cup Frame Form Mixer 1": "\u062e\u0644\u0627\u0637 \u062a\u0634\u0643\u064a\u0644 \u0625\u0637\u0627\u0631 \u0643\u0648\u0628 1",
    "Cup Frame Form Mixer 2": "\u062e\u0644\u0627\u0637 \u062a\u0634\u0643\u064a\u0644 \u0625\u0637\u0627\u0631 \u0643\u0648\u0628 2",
    "Drrill 1": "\u0645\u062b\u0642\u0628 1", "Drrill 2": "\u0645\u062b\u0642\u0628 2", "Drrill 3": "\u0645\u062b\u0642\u0628 3",
    "Drill 4":  "\u0645\u062b\u0642\u0628 4", "Drill 5":  "\u0645\u062b\u0642\u0628 5", "Drill 6":  "\u0645\u062b\u0642\u0628 6",
    "Drill 7":  "\u0645\u062b\u0642\u0628 7", "Drill 8":  "\u0645\u062b\u0642\u0628 8", "Drill 9":  "\u0645\u062b\u0642\u0628 9",
    "Form & Tap":   "\u062a\u0634\u0643\u064a\u0644 \u0648\u062a\u0642\u0644\u064a\u0645",
    "Weld Cell 1":  "\u062e\u0644\u064a\u0629 \u0644\u062d\u0627\u0645 1",
    "Weld Cell 2":  "\u062e\u0644\u064a\u0629 \u0644\u062d\u0627\u0645 2",
    "Weld Cell 3":  "\u062e\u0644\u064a\u0629 \u0644\u062d\u0627\u0645 3",
    "Weld Cell 4":  "\u062e\u0644\u064a\u0629 \u0644\u062d\u0627\u0645 4",
    "Weld Cell 5":  "\u062e\u0644\u064a\u0629 \u0644\u062d\u0627\u0645 5",
    "Weld Cell 6":  "\u062e\u0644\u064a\u0629 \u0644\u062d\u0627\u0645 6",
    "Forming":  "\u062a\u0634\u0643\u064a\u0644",
    "Forming ": "\u062a\u0634\u0643\u064a\u0644",
    "Tap":      "\u062a\u0642\u0644\u064a\u0645",
    "Saw":      "\u0645\u0646\u0634\u0627\u0631",
    "Saw ":     "\u0645\u0646\u0634\u0627\u0631",
    "Multi Drill ":  "\u0645\u062b\u0642\u0628 \u0645\u062a\u0639\u062f\u062f",
    "Multi Drill":   "\u0645\u062b\u0642\u0628 \u0645\u062a\u0639\u062f\u062f",
    "Cup Weld 1":    "\u0644\u062d\u0627\u0645 \u0643\u0648\u0628 1",
    "Cup Weld 2":    "\u0644\u062d\u0627\u0645 \u0643\u0648\u0628 2",
    # Factory 4 Area 1
    "Manual Saw":                   "\u0645\u0646\u0634\u0627\u0631 \u064a\u062f\u0648\u064a",
    "ECO Punch Press":              "\u0628\u0646\u0634 \u062a\u062e\u0631\u064a\u0645 ECO",
    "TECH Punch / Drill":           "\u062a\u062e\u0631\u064a\u0645 TECH",
    "ECO Punch + TECH Press":       "\u0645\u0643\u0628\u0633 ECO + \u062a\u062e\u0631\u064a\u0645 TECH",
    "Welding Package":              "\u0628\u0627\u0643\u064a\u0629 \u0644\u062d\u0627\u0645",
    "Pre-Assembly Welding Robot":   "\u0631\u0648\u0628\u0648\u062a \u0644\u062d\u0627\u0645 \u0645\u0633\u0628\u0642 \u0627\u0644\u062a\u062c\u0645\u064a\u0639",
    "9-Frame Assembly":             "\u062a\u062c\u0645\u064a\u0639 9 \u0625\u0637\u0627\u0631\u0627\u062a",
    "Welding Robot":                "\u0631\u0648\u0628\u0648\u062a \u0644\u062d\u0627\u0645",
    "Auto Saw":                     "\u0645\u0646\u0634\u0627\u0631 \u0623\u0648\u062a\u0648\u0645\u0627\u062a\u064a\u0643",
    "Presses":                      "\u0645\u0643\u0627\u0628\u0633",
    "Welding Station":              "\u0645\u062d\u0637\u0629 \u0644\u062d\u0627\u0645",
    "Delivery / QC":                "\u0627\u0644\u062a\u0633\u0644\u064a\u0645 / \u0636\u0628\u0637 \u0627\u0644\u062c\u0648\u062f\u0629",
    "Grinding":                     "\u062c\u0644\u062e",
    # Factory 4 Area 2
    "Raw Material Storage":                 "\u0645\u062e\u0632\u0646 \u062e\u0627\u0645\u0627\u062a",
    "Saw Machine":                          "\u0645\u0643\u0646\u0629 \u0645\u0646\u0634\u0627\u0631",
    "Manual Assembly Tools":                "\u0623\u062f\u0648\u0627\u062a \u062a\u062c\u0645\u064a\u0639 \u064a\u062f\u0648\u064a",
    "Storage Cabinet":                      "\u062f\u0648\u0644\u0627\u0628 \u062a\u062e\u0632\u064a\u0646",
    "Ready Acrow Board Pallets":            "\u0637\u0628\u0627\u0644\u064a Acrow \u0627\u0644\u062c\u0627\u0647\u0632\u0629",
    "Pallet Assembly Spread":               "\u0641\u0631\u0634 \u062a\u062c\u0645\u064a\u0639 \u0627\u0644\u0637\u0628\u0627\u0644\u064a",
    "Assembly RM Storage":                  "\u0645\u062e\u0632\u0646 \u062e\u0627\u0645\u0627\u062a \u0642\u0633\u0645 \u0627\u0644\u062a\u062c\u0645\u064a\u0639",
    "CNC Router Machine":                   "\u0645\u0643\u0646\u0629 \u0631\u0627\u0648\u062a\u0631 CNC",
    "WIP + Transport Carts + Cabinet Zone": "WIP + \u0639\u0631\u0628\u064a\u0627\u062a \u0646\u0642\u0644 + \u0645\u0646\u0637\u0642\u0629 \u062f\u0648\u0627\u0644\u064a\u0628",
    "TECH, ECO & WIP Area":                 "\u0645\u0646\u0637\u0642\u0629 TECH \u0648 ECO \u0648 WIP",
    "Paint / Coating Station":              "\u0645\u062d\u0637\u0629 \u062f\u0647\u0627\u0646 / \u0637\u0644\u0627\u0621",
    # Zone labels
    "Left":   "\u0627\u0644\u064a\u0633\u0627\u0631",
    "Right":  "\u0627\u0644\u064a\u0645\u064a\u0646",
    "Center": "\u0627\u0644\u0648\u0633\u0637",
}

def _tr(text: str) -> str:
    """Return machine/label text in the active display language."""
    if st.session_state.get("display_lang", "English") == "Arabic":
        key = text.strip()
        # Try exact match, then with trailing space stripped
        return ARABIC_NAMES.get(key, ARABIC_NAMES.get(key.rstrip(), text))
    return text

def machine_type(name):
    n = name.lower().strip()
    if "saw" in n:                                        return "saw"
    if "drill" in n or "drrill" in n or "multi" in n:    return "drill"
    if "press" in n or "rasa" in n:                       return "press"
    if "sort" in n:                                       return "sorter"
    if "ring" in n or "cup" in n or "vertical" in n:     return "vertical"
    if "mix" in n:                                        return "welder"
    if "weld" in n or "assembly" in n or "cell" in n:    return "welder"
    if "form" in n or "tap" in n:                        return "generic"
    return "generic"

def load_rate_data(path_or_file) -> pd.DataFrame:
    """Load Rate & Capacity sheet. Returns columns: Machine, Rate"""
    try:
        raw = pd.read_excel(path_or_file, sheet_name="Rate & Capacity")
    except Exception:
        return pd.DataFrame(columns=["Machine", "Rate"])
    raw.columns = [str(c).strip() for c in raw.columns]
    col_map = {}
    for c in raw.columns:
        cl = c.lower()
        if "machine" in cl and "rate" not in cl: col_map[c] = "Machine"
        elif "rate" in cl:                        col_map[c] = "Rate"
    raw = raw.rename(columns=col_map)
    if "Machine" not in raw.columns: raw["Machine"] = ""
    if "Rate"    not in raw.columns: raw["Rate"]    = None
    raw["Machine"] = raw["Machine"].fillna("").astype(str).str.strip()
    return raw[raw["Machine"] != ""][["Machine", "Rate"]].reset_index(drop=True)


def load_cell_data(path_or_file) -> pd.DataFrame:
    """Load Cell Details sheet. Returns clean DataFrame."""
    try:
        raw = pd.read_excel(path_or_file, sheet_name="Cell Details").dropna(subset=["Cell"] if "Cell" in pd.read_excel(path_or_file, sheet_name="Cell Details", nrows=1).columns else [0])
    except Exception:
        return pd.DataFrame(columns=["Cell","Capacity","Top_Item","Top_Desc"])
    raw = raw.dropna(how="all")
    # Rename columns by position / content
    raw.columns = [str(c).strip() for c in raw.columns]
    col_map = {}
    for c in raw.columns:
        cl = c.lower()
        if "cell" in cl and "cap" not in cl:   col_map[c] = "Cell"
        elif "cap" in cl:                       col_map[c] = "Capacity"
        elif "item" in cl or "sell" in cl or "sold" in cl: col_map[c] = "Top_Item"
        elif "desc" in cl:                      col_map[c] = "Top_Desc"
    raw = raw.rename(columns=col_map)
    for col in ["Cell","Capacity","Top_Item","Top_Desc"]:
        if col not in raw.columns: raw[col] = None
    raw = raw.dropna(subset=["Cell"])
    raw["Cell"]     = raw["Cell"].astype(str).str.strip()
    raw["Top_Item"] = raw["Top_Item"].apply(
        lambda x: f"{x:.0f}" if pd.notna(x) and isinstance(x, float) else str(x) if pd.notna(x) else ""
    )
    return raw[["Cell","Capacity","Top_Item","Top_Desc"]].reset_index(drop=True)


def load_bom_data(path_or_file) -> dict:
    """
    Load Best Items sheet — auto-detects format:
    Format A (A1): Cell names as column headers, 3 groups × 5 cols
    Format B (A2): Generic 'Parent Item' headers, N groups × 5 cols,
                   cell names loaded from Cell Details sheet
    """
    try:
        raw = pd.read_excel(path_or_file, sheet_name="Best Items")
    except Exception:
        return {}
    raw.columns = [str(c).strip() for c in raw.columns]

    # Detect format: Format B has 'Parent Item' or 'Parent Item.1' in first col
    first_col = raw.columns[0].lower()
    if "parent" in first_col or "item" == first_col:
        # Format B (A2): load cell names from Cell Details
        try:
            cd = pd.read_excel(path_or_file, sheet_name="Cell Details").dropna(how="all")
            cell_names_list = cd.dropna(subset=[cd.columns[0]])[cd.columns[0]].astype(str).str.strip().tolist()
        except Exception:
            cell_names_list = [f"Cell {i+1}" for i in range(10)]
        # Build groups: each group is 4 cols, separated by 1 blank col
        CELL_GROUPS = []
        for gi, cname in enumerate(cell_names_list):
            start = gi * 5
            if start + 4 <= raw.shape[1]:
                CELL_GROUPS.append((cname, start))
    else:
        # Format A (A1): cell names encoded in column headers
        CELL_GROUPS = [
            ("Cup & Ring Ledger Cell",  0),
            ("Cup Lock Vertical Cell",  5),
            ("Ring Lock Vertical Cell", 10),
        ]

    result = {}
    for cell_name, start_col in CELL_GROUPS:
        cols = raw.iloc[:, start_col:start_col+4]
        cols.columns = ["Item", "Description", "Op_Desc", "Op_Seq"]
        cols = cols.copy()
        cols["Item"]        = cols["Item"].ffill()
        cols["Description"] = cols["Description"].ffill()

        # Drop rows where item is NaN after ffill
        cols = cols.dropna(subset=["Item"])

        # Format item codes (float → string without decimals)
        def fmt_item(x):
            try:
                return f"{float(x):.0f}"
            except Exception:
                return str(x).strip()

        cols["Item"] = cols["Item"].apply(fmt_item)
        cols["Description"] = cols["Description"].fillna("").astype(str).str.strip()
        cols["Op_Desc"] = cols["Op_Desc"].fillna("").astype(str).str.strip()
        cols["Op_Seq"]  = pd.to_numeric(cols["Op_Seq"], errors="coerce")

        # Determine BOM level from item prefix
        def bom_level(item_str):
            prefix = item_str[:1] if item_str else "0"
            return {"2": 1, "3": 2, "4": 2, "5": 3, "6": 4}.get(prefix, 0)

        # Group rows by item code, collect operations
        nodes = {}
        node_order = []
        for _, r in cols.iterrows():
            item = r["Item"]
            if item not in nodes:
                nodes[item] = {
                    "item":        item,
                    "description": r["Description"],
                    "level":       bom_level(item),
                    "operations":  [],
                }
                node_order.append(item)
            op_desc = r["Op_Desc"]
            op_seq  = r["Op_Seq"]
            if op_desc and op_desc not in ("nan", ""):
                nodes[item]["operations"].append({
                    "op_desc": op_desc,
                    "op_seq":  int(op_seq) if pd.notna(op_seq) else 9999,
                })

        # Sort operations: quality check (9990) last, real ops ascending
        for item in nodes:
            ops = nodes[item]["operations"]
            ops.sort(key=lambda o: (o["op_seq"] == 9990, o["op_seq"]))

        result[cell_name] = [nodes[k] for k in node_order]

    return result


def get_machine_report(machine_name: str, df_status: pd.DataFrame,
                       df_rate: pd.DataFrame) -> dict:
    """Build a complete report dict for one machine."""
    import re
    report = {
        "rate":               None,
        "machines_same_type": None,
        "total_operators":    None,
        "notes":              None,
        "status":             None,
        "zone":               None,
    }
    # Match all rows with this exact machine name (handles duplicate Drill rows)
    status_rows = df_status[df_status["Machine"] == machine_name]
    if not status_rows.empty:
        r = status_rows.iloc[0]
        report["status"]          = r.get("Status", None)
        report["zone"]            = r.get("Zone", None)
        notes = r.get("Notes", "")
        report["notes"]           = str(notes) if pd.notna(notes) and str(notes) not in ("nan","") else None
        report["total_operators"] = int(status_rows["Operator_Count"].sum())

    # Count machines of same type (strip trailing number)
    base = re.sub(r'\s*\d+\s*$', '', machine_name).strip()
    same_type = df_status[df_status["Machine"].str.startswith(base)]
    report["machines_same_type"] = max(len(same_type), 1)

    if df_rate is None or df_rate.empty:
        return report

    rate_rows = df_rate[df_rate["Machine"] == machine_name]
    if not rate_rows.empty:
        rr = rate_rows.iloc[0]
        report["rate"] = rr["Rate"] if pd.notna(rr.get("Rate")) else None

    return report



def clean_df(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    for col in ["Machine", "Status", "Zone"]:
        if col not in df.columns: df[col] = "Unknown"
    if "Notes" not in df.columns:          df["Notes"] = "—"
    if "Operator_Count" not in df.columns: df["Operator_Count"] = 1
    df["Notes"]  = df["Notes"].fillna("—").astype(str)
    # '-' status = non-machine classification (Storage/WIP zones) — keep as ZONE type
    df["Status"] = df["Status"].fillna("ON").astype(str).str.strip().str.upper()
    df["Status"] = df["Status"].apply(lambda s: s if s in STATUS_OPTIONS + ["-"] else "ON")
    df["Zone"]   = df["Zone"].fillna("Center").astype(str).str.strip()
    # Operator_Count: '-' = non-machine (no workers)
    def parse_ops(x):
        try:
            v = pd.to_numeric(x, errors="coerce")
            return int(v) if pd.notna(v) else 0
        except: return 0
    df["Operator_Count"] = df["Operator_Count"].apply(parse_ops)
    df["Machine"] = df["Machine"].astype(str).str.strip().str.replace(r'^\xa0', '', regex=True)
    df = df.dropna(subset=["Machine"])
    df = df[df["Machine"].str.strip() != ""].reset_index(drop=True)
    return df

def _load_excel_for_area(cfg: dict) -> pd.DataFrame:
    """Load the Excel for an area, slicing rows if excel_rows is specified."""
    all_df = pd.read_excel(cfg["excel"])
    if "excel_rows" in cfg:
        r0, r1 = cfg["excel_rows"]
        all_df = all_df.iloc[r0:r1].reset_index(drop=True)
    return all_df

# ── Load data for active area ─────────────────────────────────────────────────
def _load_area(area_name: str):
    """Load all data for the given area into session state."""
    cfg = AREAS[area_name]
    raw = _load_excel_for_area(cfg)
    st.session_state.df         = clean_df(raw)
    st.session_state.rate_df    = load_rate_data(cfg["excel"])
    st.session_state.cell_df    = load_cell_data(cfg["excel"])
    st.session_state.bom_data   = load_bom_data(cfg["excel"])
    st.session_state.dxf_coords = None
    st.session_state.viewing_history = False
    st.session_state.history_date    = None
    layout_path = cfg["layout_dark"]
    if os.path.exists(layout_path):
        with open(layout_path, "rb") as f:
            st.session_state.layout_img = f.read()
    else:
        st.session_state.layout_img = None

if st.session_state.df is None:
    _load_area(st.session_state.active_area)

df = st.session_state.df

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── Area / Factory Selector ───────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">🏭 Factory / Area</div>', unsafe_allow_html=True)
    area_choice = st.selectbox("Select area", list(AREAS.keys()),
                               index=list(AREAS.keys()).index(st.session_state.active_area),
                               key="area_selectbox", label_visibility="collapsed")
    if area_choice != st.session_state.active_area:
        st.session_state.active_area = area_choice
        _load_area(area_choice)
        st.rerun()

    _active_cfg = AREAS[st.session_state.active_area]

    # ── History Browser ───────────────────────────────────────────────────────
    st.markdown('<div class="sec-lbl">📅 Daily History</div>', unsafe_allow_html=True)
    from utils.history import save_run, list_dates, load_run, auto_save_if_needed

    # Auto-save today's state on every load (captures each working day automatically)
    if not st.session_state.viewing_history:
        auto_save_if_needed(BASE, _active_cfg["key"], st.session_state.df)

    _hist_entries = list_dates(BASE, _active_cfg["key"])

    _hcol1, _hcol2 = st.columns(2)
    with _hcol1:
        if st.button("💾 Save Now", use_container_width=True, key="btn_save_run",
                     help="Save today's current data as the official snapshot"):
            save_run(BASE, _active_cfg["key"], st.session_state.df, label="manual")
            st.toast("✅ Today's run saved!", icon="💾")
            st.rerun()
    with _hcol2:
        if st.button("📋 Live View", use_container_width=True, key="btn_live_view"):
            st.session_state.viewing_history = False
            st.session_state.history_date    = None
            st.session_state.df = clean_df(pd.read_excel(_active_cfg["excel"]))
            st.rerun()

    if _hist_entries:
        import datetime as _dt
        # Build display labels: "Today · 14:32", "Yesterday", "Mon 07 Apr", etc.
        _today_str     = _dt.date.today().isoformat()
        _yesterday_str = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()

        def _date_label(entry):
            d, ts, lbl = entry["date"], entry["timestamp"], entry["label"]
            time_str = ts[11:16] if len(ts) >= 16 else ""
            auto_tag = " (auto)" if lbl == "auto" else ""
            if d == _today_str:
                return f"Today {time_str}{auto_tag}"
            if d == _yesterday_str:
                return f"Yesterday{auto_tag}"
            try:
                dt = _dt.date.fromisoformat(d)
                return f"{dt.strftime('%a %d %b')}{auto_tag}"
            except Exception:
                return d

        _date_options = {_date_label(e): e["date"] for e in _hist_entries}
        _display_opts = ["— current live data —"] + list(_date_options.keys())

        _sel_label = st.selectbox("View date", _display_opts,
                                   key="hist_date_sel", label_visibility="collapsed")
        if _sel_label and _sel_label != "— current live data —":
            _sel_date = _date_options[_sel_label]
            if st.button(f"📂 Load  {_sel_label}", use_container_width=True, key="btn_load_hist"):
                _hist_df = load_run(BASE, _active_cfg["key"], _sel_date)
                if _hist_df is not None:
                    st.session_state.df = clean_df(_hist_df)
                    st.session_state.viewing_history = True
                    st.session_state.history_date    = _sel_date
                    st.rerun()
                else:
                    st.warning("No data found for this date.")
    else:
        st.caption("No saved runs yet — data will auto-save daily on first open.")

    st.markdown('<hr class="s">', unsafe_allow_html=True)

    # ── Theme ─────────────────────────────────────────────────────────────────
    tc1, tc2 = st.columns(2)
    with tc1:
        if st.button("🌙 Dark",  key="btn_dark",  use_container_width=True):
            st.session_state.theme = "dark";  st.rerun()
    with tc2:
        if st.button("☀️ Light", key="btn_light", use_container_width=True):
            st.session_state.theme = "light"; st.rerun()

    st.markdown('<hr class="s">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">View Mode</div>', unsafe_allow_html=True)
    view = st.radio("", ["2D Floor Plan", "3D Isometric"],
                    index=0 if st.session_state.view_mode == "2D Floor Plan" else 1,
                    label_visibility="collapsed", horizontal=True)
    st.session_state.view_mode = view

    # Language toggle — EN / AR
    st.markdown('<div class="sec-lbl">🌐 Language / اللغة</div>', unsafe_allow_html=True)
    _lang_cols = st.columns(2)
    with _lang_cols[0]:
        if st.button("🇬🇧 English", key="btn_lang_en", use_container_width=True,
                     help="Display machine names in English"):
            st.session_state.display_lang = "English"; st.rerun()
    with _lang_cols[1]:
        if st.button("🇸🇦 عربي", key="btn_lang_ar", use_container_width=True,
                     help="عرض أسماء الماكينات بالعربية"):
            st.session_state.display_lang = "Arabic"; st.rerun()
    _lang_active = st.session_state.get("display_lang", "English")
    st.caption(f"Active: {'English 🇬🇧' if _lang_active == 'English' else 'عربي 🇸🇦'}")

    # 2D layout style selector
    if st.session_state.view_mode == "2D Floor Plan":
        st.markdown('<div class="sec-lbl">🗺️ Layout Style</div>', unsafe_allow_html=True)
        layout_style = st.radio("", ["AutoCAD Original", "Process Ribbon",
                                     "Node Map", "Resource View",
                                     "Executive View", "Executive Layout View",
                                     "draw.io View"],
                                 key="layout_style",
                                 label_visibility="collapsed", horizontal=False)
    else:
        layout_style = "AutoCAD Original"

    # 3D style selector + options
    if st.session_state.view_mode == "3D Isometric":
        st.markdown('<div class="sec-lbl">🏭 3D Style</div>', unsafe_allow_html=True)
        iso_style = st.radio("", ["Technical", "Factory Simulation"],
                              key="iso_style", label_visibility="collapsed", horizontal=True)
        st.markdown('<div class="sec-lbl">🧊 3D Options</div>', unsafe_allow_html=True)
        roof_col, label_col = st.columns(2)
        with roof_col:
            roof_on = st.toggle("🏗️ Roof", value=st.session_state.show_roof, key="roof_toggle")
            st.session_state.show_roof = roof_on
        with label_col:
            labels_on = st.toggle("🏷️ Labels", value=st.session_state.show_labels, key="labels_toggle")
            st.session_state.show_labels = labels_on
    else:
        iso_style = "Technical"

    st.markdown('<hr class="s">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">🔍 Filters</div>', unsafe_allow_html=True)
    zones_avail  = sorted(df["Zone"].unique().tolist())
    filter_zone  = st.multiselect("Zone",   zones_avail,    default=[], label_visibility="collapsed")
    filter_status= st.multiselect("Status", STATUS_OPTIONS, default=[], label_visibility="collapsed")

    st.markdown('<hr class="s">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">⚙️ Override</div>', unsafe_allow_html=True)
    sel_m  = st.selectbox("Machine", df["Machine"].tolist(), label_visibility="collapsed")
    idx_m  = df.index[df["Machine"] == sel_m][0]
    _cur_st = df.at[idx_m, "Status"]
    # Zone/storage entries (Status='-') cannot be overridden — show info instead
    if str(_cur_st).strip() == "-":
        st.caption("⬆️ This is a zone/storage area — no status override available.")
    else:
        _st_idx = STATUS_OPTIONS.index(_cur_st) if _cur_st in STATUS_OPTIONS else 0
        new_st = st.selectbox("Status", STATUS_OPTIONS,
                              index=_st_idx,
                              label_visibility="collapsed")
        if st.button("✅ Apply", use_container_width=True):
            st.session_state.df.at[idx_m, "Status"] = new_st
            st.rerun()

    st.markdown('<hr class="s">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">🎨 Legend</div>', unsafe_allow_html=True)
    for label, color in STATUS_COLORS.items():
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;padding:4px 0;font-size:12px;color:{T['text']}">
  <div style="width:12px;height:12px;border-radius:50%;background:{color};
              box-shadow:0 0 7px {color}66;flex-shrink:0"></div>
  <span>{label}</span>
</div>""", unsafe_allow_html=True)

    # ── PDF Export ────────────────────────────────────────────────────────────
    st.markdown('<hr class="s">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">📄 Export Report</div>', unsafe_allow_html=True)
    if st.button("⬇️ Download PDF Report", use_container_width=True, key="btn_pdf"):
        with st.spinner("Generating PDF…"):
            try:
                from utils.pdf_report import generate_pdf
                _df_pdf    = st.session_state.df
                _cell_pdf  = st.session_state.cell_df
                _bom_pdf   = st.session_state.bom_data
                _img_pdf   = st.session_state.layout_img
                _tot  = len(_df_pdf)
                _on   = (_df_pdf["Status"] == "ON").sum()
                _off  = (_df_pdf["Status"] == "OFF").sum()
                _mnt  = (_df_pdf["Status"] == "MAINTENANCE").sum()
                _upt  = round(_on / _tot * 100) if _tot else 0
                pdf_bytes = generate_pdf(
                    _df_pdf, _cell_pdf, _bom_pdf, _img_pdf,
                    _tot, _on, _off, _mnt, _upt
                )
                import datetime as _dt
                fname = f"Factory5_Report_{_dt.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.download_button(
                    label="📥 Click to Save PDF",
                    data=pdf_bytes,
                    file_name=fname,
                    mime="application/pdf",
                    use_container_width=True,
                    key="btn_save_pdf",
                )
            except Exception as _e:
                st.error(f"PDF error: {_e}")

    # ── Alert Panel ───────────────────────────────────────────────────────────
    st.markdown('<hr class="s">', unsafe_allow_html=True)
    st.markdown('<div class="sec-lbl">🔔 Send Alert</div>', unsafe_allow_html=True)

    alert_tab = st.radio("Channel", ["📧 Email", "💬 WhatsApp"],
                          horizontal=True, key="alert_channel",
                          label_visibility="collapsed")

    # ── Default contact info (pre-filled, user can override)
    DEFAULT_EMAIL = os.environ.get("FMP_ALERT_EMAIL", "")
    DEFAULT_PHONE = os.environ.get("FMP_ALERT_PHONE", "")

    if alert_tab == "📧 Email":
        sender_type = st.radio("Send from", ["Gmail", "Company Email (@acrow.co)"],
                                horizontal=True, key="sender_type",
                                label_visibility="collapsed")

        if sender_type == "Gmail":
            sender_email = st.text_input("Your Gmail address", key="sender_email",
                                          placeholder="yourname@gmail.com")
            sender_pass  = st.text_input("Gmail App Password", key="sender_pass",
                                          type="password", placeholder="16-character app password")
            smtp_host, smtp_port_val = "smtp.gmail.com", 587
            with st.expander("❓ How to get Gmail App Password"):
                st.markdown("""
1. Go to **myaccount.google.com**
2. **Security** → **2-Step Verification** → **App Passwords**
3. Generate → copy the 16-character code above

> Use the App Password — NOT your Gmail login password.
                """)
        else:
            sender_email  = st.text_input("Your company email", key="sender_email",
                                           placeholder="yourname@acrow.co")
            sender_pass   = st.text_input("Email password", key="sender_pass",
                                           type="password", placeholder="Your email password")
            smtp_host     = st.text_input("SMTP server", key="smtp_host_co",
                                           value="mail.acrow.co",
                                           help="Ask IT if unsure. Try: mail.acrow.co or smtp.office365.com")
            smtp_port_val = st.number_input("SMTP port", value=587, key="smtp_port_val",
                                             min_value=1, max_value=65535)

        recipient  = st.text_input("Send report to", key="recipient_email",
                                    value=DEFAULT_EMAIL)
        attach_pdf = st.checkbox("Attach PDF report", value=True, key="email_attach_pdf")

        if st.button("📤 Send Email", use_container_width=True, key="btn_send_email"):
            if not sender_email or not sender_pass:
                st.warning("Enter your email address and password.")
            elif sender_type == "Gmail" and len(sender_pass.replace(" ","")) != 16:
                st.warning("Gmail App Password must be exactly 16 characters.")
            else:
                with st.spinner("Sending email…"):
                    try:
                        from utils.alert_sender import send_email_alert, build_alert_message
                        from utils.pdf_report import generate_pdf
                        import datetime as _dt2
                        _df2  = st.session_state.df
                        _tot2 = len(_df2)
                        _on2  = (_df2["Status"] == "ON").sum()
                        _off2 = (_df2["Status"] == "OFF").sum()
                        _mnt2 = (_df2["Status"] == "MAINTENANCE").sum()
                        _upt2 = round(_on2 / _tot2 * 100) if _tot2 else 0
                        html_body = build_alert_message(
                            _df2, _tot2, _on2, _off2, _mnt2, _upt2,
                            st.session_state.cell_df, short=False)
                        pdf_att = generate_pdf(
                            _df2, st.session_state.cell_df,
                            st.session_state.bom_data,
                            st.session_state.layout_img,
                            _tot2, _on2, _off2, _mnt2, _upt2
                        ) if attach_pdf else None
                        subject = (f"Factory 5 Report — "
                                   f"{_dt2.datetime.now().strftime('%d %b %Y %H:%M')} "
                                   f"| Uptime {_upt2}%")
                        ok, msg = send_email_alert(
                            smtp_host, smtp_port_val,
                            sender_email, sender_pass.replace(" ",""),
                            recipient, subject, html_body, pdf_att)
                        st.session_state["_alert_result"] = (ok, msg)
                        st.rerun()
                    except Exception as _e:
                        st.session_state["_alert_result"] = (False, f"Error: {_e}")
                        st.rerun()


    else:  # WhatsApp
        st.caption("Requires a free Twilio account (5 min setup).")
        twilio_sid   = st.text_input("Twilio Account SID", key="twilio_sid",
                                      placeholder="ACxxxxxxxxxxxxxxxx")
        twilio_token = st.text_input("Twilio Auth Token", key="twilio_token",
                                      type="password", placeholder="Auth Token")
        wa_to        = st.text_input("Send to WhatsApp number", key="wa_to",
                                      value=DEFAULT_PHONE,
                                      help="Include country code, e.g. +2010XXXXXXXX")

        if st.button("💬 Send WhatsApp", use_container_width=True, key="btn_send_wa"):
            if not twilio_sid or not twilio_token:
                st.warning("Enter your Twilio SID and Auth Token.")
            else:
                with st.spinner("Sending…"):
                    try:
                        from utils.alert_sender import send_whatsapp_alert, build_alert_message
                        _df3  = st.session_state.df
                        _tot3 = len(_df3)
                        _on3  = (_df3["Status"] == "ON").sum()
                        _off3 = (_df3["Status"] == "OFF").sum()
                        _mnt3 = (_df3["Status"] == "MAINTENANCE").sum()
                        _upt3 = round(_on3 / _tot3 * 100) if _tot3 else 0
                        wa_msg = build_alert_message(
                            _df3, _tot3, _on3, _off3, _mnt3, _upt3,
                            st.session_state.cell_df, short=True)
                        TWILIO_SANDBOX = "+14155238886"
                        ok, msg = send_whatsapp_alert(
                            twilio_sid, twilio_token,
                            TWILIO_SANDBOX, wa_to, wa_msg)
                        st.session_state["_alert_result"] = (ok, msg)
                        st.rerun()
                    except Exception as _e:
                        st.session_state["_alert_result"] = (False, f"Error: {_e}")
                        st.rerun()

        with st.expander("❓ WhatsApp Setup (Free, 5 min)"):
            st.markdown(f"""
**Step 1** — Sign up free at [twilio.com](https://twilio.com)

**Step 2** — Go to **Messaging → Try WhatsApp**

**Step 3** — From YOUR WhatsApp (`{DEFAULT_PHONE or 'your number'}`), send this message to **+1 415 523 8886**:
> `join <your-sandbox-word>`
_(Twilio will show you the exact word to use)_

**Step 4** — Paste your **Account SID** and **Auth Token** from the Twilio Console above.

That's it — no credit card needed for the sandbox.
            """)



# ── Re-read after sidebar ──────────────────────────────────────────────────────
df  = st.session_state.df
T   = THEMES[st.session_state.theme]
df_display = df.copy()
if filter_zone:   df_display = df_display[df_display["Zone"].isin(filter_zone)]
if filter_status: df_display = df_display[df_display["Status"].isin(filter_status)]

total  = len(df)
n_on   = (df["Status"] == "ON").sum()
n_off  = (df["Status"] == "OFF").sum()
n_mnt  = (df["Status"] == "MAINTENANCE").sum()
uptime = round(n_on / total * 100) if total else 0
custom_coords = st.session_state.dxf_coords

# Load layout image — use area-specific file if session img is None
if st.session_state.layout_img is None:
    _dark_path = AREAS[st.session_state.active_area]["layout_dark"]
    if os.path.exists(_dark_path):
        with open(_dark_path, "rb") as _f:
            st.session_state.layout_img = _f.read()
img_bytes = st.session_state.layout_img
img       = Image.open(io.BytesIO(img_bytes)) if img_bytes else None

# ── Alert result (rendered outside sidebar to avoid DeltaGenerator errors) ─────
if "_alert_result" in st.session_state:
    _ok, _msg = st.session_state.pop("_alert_result")
    if _ok:
        st.success(_msg)
    else:
        st.error(_msg)

# ── Header ─────────────────────────────────────────────────────────────────────
_area_title    = AREAS[st.session_state.active_area]["title"]
_area_subtitle = AREAS[st.session_state.active_area]["subtitle"]
_hist_badge    = ""
if st.session_state.viewing_history:
    _hist_badge = (f'<span style="background:#f59e0b22;color:#f59e0b;border:1px solid #f59e0b;' +
                   f'border-radius:8px;padding:2px 10px;font-size:11px;margin-left:10px">' +
                   f'📅 Viewing: {st.session_state.history_date}</span>')

# ══════════════════════════════════════════════════════════════════════════════
# TAB NAVIGATION — Dashboard / Area Monitor
# ══════════════════════════════════════════════════════════════════════════════
_main_tab_dashboard, _main_tab_area = st.tabs(["📊 Dashboard", "🏭 Area Monitor"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — EXECUTIVE SCORECARD DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
with _main_tab_dashboard:
    @st.cache_data(ttl=60)
    def _load_all_areas_summary():
        results = {}
        for area_name, cfg in AREAS.items():
            try:
                raw = _load_excel_for_area(cfg)
                adf = clean_df(raw)
                machines = adf[adf["Status"] != "-"]
                results[area_name] = {
                    "df":     adf,
                    "total":  len(machines),
                    "on":     int((machines["Status"] == "ON").sum()),
                    "off":    int((machines["Status"] == "OFF").sum()),
                    "mnt":    int((machines["Status"] == "MAINTENANCE").sum()),
                    "zones":  int((adf["Status"] == "-").sum()),
                    "ops":    int(machines["Operator_Count"].sum()),
                    "uptime": round((machines["Status"] == "ON").sum()
                                    / max(len(machines), 1) * 100),
                }
            except Exception:
                results[area_name] = {
                    "df": pd.DataFrame(), "total": 0, "on": 0, "off": 0,
                    "mnt": 0, "zones": 0, "ops": 0, "uptime": 0,
                }
        return results

    _all_areas_full = _load_all_areas_summary()
    _all_area_names = list(AREAS.keys())

    if "dashboard_areas" not in st.session_state:
        st.session_state.dashboard_areas = _all_area_names

    # ── Area selector — independent from Area Monitor ─────────────────────────
    _sc_sel_c, _ = st.columns([2, 3])
    with _sc_sel_c:
        _dash_selected = st.multiselect(
            "📊 Areas to include",
            _all_area_names,
            default=st.session_state.dashboard_areas,
            key="dashboard_areas_select",
            help="Dashboard filter — does not affect Area Monitor tab",
        )
        if _dash_selected != st.session_state.dashboard_areas:
            st.session_state.dashboard_areas = _dash_selected
    if not _dash_selected:
        st.warning("Select at least one area.")
        st.stop()

    _all_areas = {k: v for k, v in _all_areas_full.items()
                  if k in _dash_selected}

    # ── Global KPIs ───────────────────────────────────────────────────────────
    _g_total  = sum(v["total"]  for v in _all_areas.values())
    _g_on     = sum(v["on"]     for v in _all_areas.values())
    _g_off    = sum(v["off"]    for v in _all_areas.values())
    _g_mnt    = sum(v["mnt"]    for v in _all_areas.values())
    _g_ops    = sum(v["ops"]    for v in _all_areas.values())
    _g_uptime = round(_g_on / max(_g_total, 1) * 100)
    _g_upc    = ("#16a34a" if _g_uptime >= 70 else
                 "#d97706" if _g_uptime >= 50 else "#dc2626")
    _g_ugrad  = ("linear-gradient(90deg,#15803d,#22c55e)" if _g_uptime >= 70 else
                 "linear-gradient(90deg,#b45309,#d97706)"  if _g_uptime >= 50 else
                 "linear-gradient(90deg,#991b1b,#ef4444)")

    _is_dk = st.session_state.theme == "dark"

    # palette — stays clean on both themes
    _C = {
        "page":    T["bg"],
        "card":    T["surface"],
        "card2":   T["surface2"],
        "bord":    T["border"],
        "txt":     T["text"],
        "mut":     T["text_muted"],
        "head":    "#0f172a",                          # always dark header
        "row_ok":  "#f0fdf4" if not _is_dk else "#031a0c",
        "row_ok_b":"#bbf7d0" if not _is_dk else "#14532d",
        "row_ng":  "#fff1f2" if not _is_dk else "#1a0404",
        "row_ng_b":"#fecdd3" if not _is_dk else "#7f1d1d",
        "row_wn":  "#fffbeb" if not _is_dk else "#1a1000",
        "row_wn_b":"#fde68a" if not _is_dk else "#78350f",
        "risk_ok": "#f0fdf4" if not _is_dk else "#031a0c",
        "risk_ng": "#fff1f2" if not _is_dk else "#1a0404",
        "risk_wn": "#fffbeb" if not _is_dk else "#1a1000",
        "lb_row":  "#f8fafc" if not _is_dk else "#141414",
        "lb_crit": "#fff1f2" if not _is_dk else "#1a0404",
    }

    # ── Process health ─────────────────────────────────────────────────────────
    import re as _re_sc
    _SC_TAX = [
        ("⚙️", "Welding",       ["weld"]),
        ("🔪", "Cutting",       ["saw","cut"]),
        ("🔩", "Drilling",      ["drill"]),
        ("🔨", "Pressing",      ["press","punch","mixer"]),
        ("🔧", "Forming",       ["vertical","form","cup","ring"]),
        ("🏗️", "Assembly",      ["assembly","sorting","sort","9-frame"]),
        ("🏁", "Finishing",     ["grind","qc","delivery","coating","paint"]),
    ]

    def _sc_base(n):
        c = _re_sc.sub(r'[\s\-_]*[#]?\s*\d+\s*$', '', n.strip()).strip()
        return c if c else n.strip()

    _sc_df = pd.concat(
        [v["df"] for v in _all_areas.values() if not v["df"].empty],
        ignore_index=True)
    _sc_mc = (_sc_df[_sc_df["Status"] != "-"]
              if not _sc_df.empty else pd.DataFrame())

    _proc_data = []
    _sc_used   = set()
    for _ico, _pn, _kw in _SC_TAX:
        if _sc_mc.empty: continue
        _m = _sc_mc["Machine"].apply(
            lambda m: any(k in _sc_base(m).lower() for k in _kw))
        _g = _sc_mc[_m]
        if _g.empty: continue
        for _ix in _g.index: _sc_used.add(_ix)
        _pt  = len(_g)
        _pon = int((_g["Status"]=="ON").sum())
        _poff= int((_g["Status"]=="OFF").sum())
        _pmnt= int((_g["Status"]=="MAINTENANCE").sum())
        _pops= int(_g["Operator_Count"].sum())
        _pu  = round(_pon/max(_pt,1)*100)
        _proc_data.append((_ico,_pn,_pt,_pon,_poff,_pmnt,_pops,_pu))

    if not _sc_mc.empty:
        _oth = _sc_mc[~_sc_mc.index.isin(_sc_used)]
        if not _oth.empty:
            _ot=len(_oth); _oo=int((_oth["Status"]=="ON").sum())
            _proc_data.append(("🔩","Other",_ot,_oo,
                               int((_oth["Status"]=="OFF").sum()),0,
                               int(_oth["Operator_Count"].sum()),
                               round(_oo/max(_ot,1)*100)))

    _proc_data.sort(key=lambda r: r[7])   # worst uptime first

    # ── Area leaderboard — best uptime at top ─────────────────────────────────
    _lb_sorted = sorted(_dash_selected,
                        key=lambda a: _all_areas[a]["uptime"], reverse=True)

    # ── Build component HTML ───────────────────────────────────────────────────
    import streamlit.components.v1 as _cmp_sc

    _ts = pd.Timestamp.now().strftime("%d %b %Y · %H:%M")
    _area_lbl = (" · ".join(_dash_selected)
                 if len(_dash_selected) <= 3
                 else f"{len(_dash_selected)} areas selected")

    # ─── LEADERBOARD ROWS ────────────────────────────────────────────────────
    _lb_rows_html = ""
    for _ai, _an in enumerate(_lb_sorted):
        _av    = _all_areas[_an]
        _aupt  = _av["uptime"]
        _aon   = _av["on"]; _aoff = _av["off"]
        _atot  = _av["total"]; _aops = _av["ops"]
        _short = _an.replace("F5 – Area","F5–A").replace("F4 – Area","F4–A")
        _auc   = ("#16a34a" if _aupt>=70 else "#d97706" if _aupt>=50 else "#dc2626")
        _agrad = ("linear-gradient(90deg,#15803d,#22c55e)" if _aupt>=70 else
                  "linear-gradient(90deg,#b45309,#d97706)"  if _aupt>=50 else
                  "linear-gradient(90deg,#991b1b,#ef4444)")
        _row_bg  = (_C["lb_crit"] if _aupt<60 else _C["lb_row"])
        _warn_badge = ""
        if _aoff > 0:
            _bg_b = "#dc2626" if _aupt<60 else "#d97706"
            _warn_badge = (f'<span style="font-size:9px;font-weight:700;color:#fff;'
                           f'background:{_bg_b};border-radius:4px;padding:2px 7px;'
                           f'white-space:nowrap;margin-left:6px">'
                           f'{"CRITICAL" if _aupt<60 else "WATCH"}</span>')
        _lb_rows_html += f"""
  <div style="display:grid;grid-template-columns:90px 1fr 180px;
              gap:12px;align-items:center;padding:10px 20px;
              background:{_row_bg};border-bottom:1px solid {_C['bord']}">
    <div style="display:flex;align-items:center;gap:6px">
      <span style="font-size:12px;font-weight:700;color:{_C['txt']}">{_short}</span>
      {_warn_badge}
    </div>
    <div style="position:relative">
      <div style="background:{_C['card2']};border-radius:5px;height:10px;overflow:hidden">
        <div style="width:{_aupt}%;height:100%;background:{_agrad};border-radius:5px"></div>
      </div>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center">
      <span style="font-size:13px;font-weight:800;color:{_auc};
                   font-family:JetBrains Mono,monospace;min-width:38px">{_aupt}%</span>
      <span style="font-size:10px;color:{_C['mut']}">{_aon}/{_atot} M/C</span>
      <span style="font-size:10px;color:{_C['mut']}">👷 {_aops}</span>
    </div>
  </div>"""

    # ─── EXPANDABLE SOURCE REGISTRY — machine-level detail per process ──────
    def _reg_sort_val(s):
        return {"OFF": 0, "MAINTENANCE": 1, "ON": 2}.get(str(s), 3)

    # Build per-process, per-area machine lists (offline-first within each area)
    _proc_machine_data = {}
    for _pie_ico, _pie_pn, _pie_kwds in _SC_TAX:
        _pie_areas = {}
        for _pie_an in _dash_selected:
            _pie_adf = _all_areas[_pie_an]["df"]
            if _pie_adf.empty:
                continue
            _pie_grp = _pie_adf[
                (_pie_adf["Status"] != "-") &
                _pie_adf["Machine"].apply(
                    lambda m: any(k in _sc_base(m).lower() for k in _pie_kwds))
            ]
            if _pie_grp.empty:
                continue
            _pie_sorted = _pie_grp.copy()
            _pie_sorted["_s"] = _pie_sorted["Status"].apply(_reg_sort_val)
            _pie_sorted = _pie_sorted.sort_values("_s").drop(columns="_s",
                                                              errors="ignore")
            _pie_areas[_pie_an] = [
                {"name": r["Machine"],
                 "status": str(r["Status"]),
                 "ops": int(r["Operator_Count"])}
                for _, r in _pie_sorted.iterrows()
            ]
        if _pie_areas:
            _proc_machine_data[_pie_pn] = _pie_areas

    # Helper: render machine rows for one area
    def _reg_machine_rows_html(machines):
        rows = ""
        for _rm in machines:
            _rm_st  = _rm["status"]
            _rm_dot = {"ON":"#16a34a","OFF":"#dc2626",
                       "MAINTENANCE":"#d97706"}.get(_rm_st,"#888888")
            _rm_row_bg = (
                (_C["row_ng"] if _rm_st=="OFF" else
                 _C["row_wn"] if _rm_st=="MAINTENANCE" else "transparent"))
            _rm_sbg  = {"ON":"#dcfce7","OFF":"#fee2e2",
                        "MAINTENANCE":"#fffbeb"}.get(_rm_st,"#f3f4f6")
            _rm_scol = {"ON":"#15803d","OFF":"#991b1b",
                        "MAINTENANCE":"#854d0e"}.get(_rm_st,"#374151")
            _nm = (_rm["name"] if len(_rm["name"]) <= 30
                   else _rm["name"][:28] + "…")
            _ops_lbl = f"{_rm['ops']} op{'s' if _rm['ops']!=1 else ''}"
            rows += (
                f'<div style="display:flex;align-items:center;gap:8px;'
                f'padding:6px 14px;background:{_rm_row_bg};'
                f'border-bottom:.5px solid {_C["bord"]}">'
                f'<div style="width:8px;height:8px;border-radius:50%;'
                f'background:{_rm_dot};flex-shrink:0"></div>'
                f'<span style="font-size:11px;color:{_C["txt"]};flex:1;'
                f'min-width:0;overflow:hidden;text-overflow:ellipsis;'
                f'white-space:nowrap">{_nm}</span>'
                f'<span style="font-size:9px;color:{_C["mut"]};'
                f'white-space:nowrap">{_ops_lbl}</span>'
                f'<span style="font-size:8px;font-weight:600;padding:1px 7px;'
                f'background:{_rm_sbg};color:{_rm_scol};'
                f'border-radius:3px;white-space:nowrap">{_rm_st}</span>'
                f'</div>')
        return rows

    # Build one card per process
    _reg_cards_html = ""
    for (_re_ico, _re_pn, _re_pt, _re_pon,
         _re_poff, _re_pmnt, _re_pops, _re_pu) in _proc_data:
        if _re_pn not in _proc_machine_data:
            continue

        _re_upc  = ("#16a34a" if _re_pu>=70 else
                    "#d97706" if _re_pu>=50 else "#dc2626")
        _re_grad = ("linear-gradient(90deg,#15803d,#22c55e)" if _re_pu>=70 else
                    "linear-gradient(90deg,#b45309,#d97706)"  if _re_pu>=50 else
                    "linear-gradient(90deg,#991b1b,#ef4444)")
        _re_bdg  = ("OK"       if _re_pu>=70 else
                    "WATCH"    if _re_pu>=50 else "CRITICAL")
        _re_bbg  = ("#dcfce7"  if _re_pu>=70 else
                    "#fffbeb"  if _re_pu>=50 else "#fee2e2")
        _re_bcol = ("#15803d"  if _re_pu>=70 else
                    "#854d0e"  if _re_pu>=50 else "#991b1b")
        _re_pid  = (_re_pn.lower()
                    .replace(" ","_").replace("/","_").replace("&",""))
        _re_areas = _proc_machine_data[_re_pn]
        _re_n_areas = len(_re_areas)
        # Auto-expand the two worst-performing processes with offline machines
        _re_auto = False   # all cards collapsed by default; user expands on click
        _re_off_lbl = (f"{_re_poff} offline"
                       if _re_poff > 0 else "all running")
        _re_off_col = "#ef4444" if _re_poff > 0 else _C["mut"]

        # Build area sub-sections (each with its machine rows)
        _area_subs = ""
        for _re_an, _re_machines in _re_areas.items():
            _re_a_on  = sum(1 for m in _re_machines if m["status"]=="ON")
            _re_a_off = sum(1 for m in _re_machines if m["status"]=="OFF")
            _re_a_tot = len(_re_machines)
            _re_a_upt = round(_re_a_on / max(_re_a_tot, 1) * 100)
            _re_an_s  = (_re_an.replace("F5 – Area","F5–A")
                                .replace("F4 – Area","F4–A"))
            _re_a_col = "#dc2626" if _re_a_off > 0 else "#16a34a"
            _area_subs += (
                f'<div>'
                f'<div style="display:flex;justify-content:space-between;'
                f'align-items:center;padding:6px 14px;'
                f'background:{_C["card2"]};'
                f'border-bottom:.5px solid {_C["bord"]}">'
                f'<span style="font-size:9px;font-weight:600;color:{_C["mut"]};'
                f'letter-spacing:.07em;text-transform:uppercase">{_re_an_s}</span>'
                f'<span style="font-size:9px;color:{_re_a_col}">'
                f'{_re_a_on}/{_re_a_tot} running'
                f'{f" · {_re_a_off} offline" if _re_a_off else ""}'
                f' · {_re_a_upt}%</span>'
                f'</div>'
                f'{_reg_machine_rows_html(_re_machines)}'
                f'</div>')

        _reg_cards_html += (
            f'<div id="rc-{_re_pid}" style="margin-bottom:7px;overflow:hidden;'
            f'border-radius:8px;border:.5px solid {_C["bord"]};'
            f'border-left:4px solid {_re_upc};background:{_C["card"]}">'

            # ── card header (always visible, clickable) ──────────────────────
            f'<div onclick="toggle(\'{_re_pid}\')" '
            f'style="display:flex;align-items:center;gap:12px;'
            f'padding:11px 16px;cursor:pointer;user-select:none">'
            f'<span style="font-size:18px;flex-shrink:0">{_re_ico}</span>'
            f'<div style="flex:1;min-width:0">'
            f'<div style="font-size:13px;font-weight:500;color:{_C["txt"]}">'
            f'{_re_pn}</div>'
            f'<div style="font-size:10px;color:{_C["mut"]}">'
            f'{_re_pt} machines · '
            f'{_re_n_areas} area{"s" if _re_n_areas!=1 else ""} · '
            f'{_re_pops} operators</div>'
            f'</div>'
            # uptime mini-bar
            f'<div style="width:120px;flex-shrink:0">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:9px;margin-bottom:3px">'
            f'<span style="color:{_re_off_col}">{_re_off_lbl}</span>'
            f'<span style="font-weight:600;color:{_re_upc}">{_re_pu}%</span>'
            f'</div>'
            f'<div style="background:{_C["card2"]};border-radius:4px;'
            f'height:7px;overflow:hidden">'
            f'<div style="width:{_re_pu}%;height:100%;background:{_re_grad};'
            f'border-radius:4px"></div></div></div>'
            # badge
            f'<span style="font-size:9px;font-weight:700;padding:3px 9px;'
            f'background:{_re_bbg};color:{_re_bcol};'
            f'border-radius:4px;white-space:nowrap;flex-shrink:0">{_re_bdg}</span>'
            # chevron arrow
            f'<span id="arr-{_re_pid}" style="font-size:16px;color:{_C["mut"]};'
            f'transition:transform .2s;flex-shrink:0;line-height:1;display:inline-block;'
            f'{"transform:rotate(180deg)" if _re_auto else ""}">'
            f'&#9660;</span>'
            f'</div>'  # end header

            # ── expandable body ──────────────────────────────────────────────
            f'<div id="bdy-{_re_pid}" '
            f'style="{"display:block" if _re_auto else "display:none"};'
            f'border-top:.5px solid {_C["bord"]}">'
            f'{_area_subs}'
            f'</div>'

            f'</div>')   # end card

    # Full registry HTML (header + cards + JS toggle)
    _registry_html = (
        f'<div style="background:{_C["card"]};border:1px solid {_C["bord"]};'
        f'border-radius:10px;overflow:hidden;margin-top:12px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:10px 16px;background:{_C["card2"]};'
        f'border-bottom:1px solid {_C["bord"]}">'
        f'<span style="font-size:9px;font-weight:700;color:{_C["mut"]};'
        f'letter-spacing:.1em;text-transform:uppercase">'
        f'PROCESS HEALTH — SOURCE MACHINE REGISTRY</span>'
        f'<span style="font-size:10px;color:{_C["mut"]}">'
        f'Worst uptime first · Click any row to expand</span>'
        f'</div>'
        f'<div style="padding:10px 12px">{_reg_cards_html}</div>'
        f'</div>'
        f'<script>'
        f'function toggle(pid){{'
        f'var b=document.getElementById("bdy-"+pid);'
        f'var a=document.getElementById("arr-"+pid);'
        f'if(!b||!a)return;'
        f'if(b.style.display==="none"){{'
        f'b.style.display="block";'
        f'a.style.transform="rotate(180deg)";'
        f'}}else{{'
        f'b.style.display="none";'
        f'a.style.transform="rotate(0deg)";'
        f'}}}}'
        f'</script>')

    # ─── CRITICAL MACHINE ALERTS ────────────────────────────────────────────
    _mac_alerts = []
    for _an, _av in _all_areas.items():
        if _av["df"].empty: continue
        for _, _ar in _av["df"][_av["df"]["Status"] != "-"].iterrows():
            if _ar["Status"] in ("OFF","MAINTENANCE"):
                _mac_alerts.append((_an, _ar["Machine"], _ar["Status"]))
    _mac_alerts.sort(key=lambda x: (x[2]!="OFF", x[0]))

    _alert_rows_html = ""
    for _aan, _amach, _ast in _mac_alerts[:12]:
        _ac3  = "#ef4444" if _ast=="OFF" else "#d97706"
        _ico3 = "🔴" if _ast=="OFF" else "🟡"
        _short_an = _aan.replace("F5 – Area","F5–A").replace("F4 – Area","F4–A")
        _alert_rows_html += f"""
  <div style="display:grid;grid-template-columns:70px 1fr 90px;
              padding:8px 20px;border-bottom:1px solid {_C['bord']};
              align-items:center">
    <span style="font-size:10px;color:{_C['mut']};
                 font-family:JetBrains Mono,monospace">{_short_an}</span>
    <span style="font-size:11px;font-weight:600;color:{_C['txt']}">{_ico3} {_amach}</span>
    <span style="font-size:9px;font-weight:700;color:{_ac3};
                 text-align:right;font-family:JetBrains Mono,monospace">{_ast}</span>
  </div>"""

    _alerts_section = ""
    if _mac_alerts:
        _extra = len(_mac_alerts) - 12
        _alerts_section = f"""
<div style="background:{_C['card']};border:1px solid {_C['bord']};
            border-radius:10px;overflow:hidden;margin-top:12px">
  <div style="display:grid;grid-template-columns:70px 1fr 90px;
              padding:8px 20px;background:{_C['card2']};
              border-bottom:1px solid {_C['bord']};
              font-size:9px;font-weight:700;color:{_C['mut']};
              letter-spacing:.08em;text-transform:uppercase">
    <span>Area</span><span>Machine</span>
    <span style="text-align:right">Status</span>
  </div>
  {_alert_rows_html}
  {"" if _extra<=0 else f'<div style="padding:8px 20px;font-size:10px;color:{_C[chr(109)+chr(117)+chr(116)]}">+ {_extra} more machines need attention</div>'}
</div>"""

    # ─── ASSEMBLE FULL SCORECARD ─────────────────────────────────────────────
    _sc_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{_C['page']};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     color:{_C['txt']};padding:0 0 16px 0}}</style>
</head><body>

<!-- ── SCORECARD HEADER ────────────────────────────────────── -->
<div style="background:{_C['head']};border-radius:10px 10px 0 0;
            padding:13px 22px;display:flex;justify-content:space-between;
            align-items:center">
  <div>
    <div style="font-size:14px;font-weight:700;color:#f1f5f9;
                letter-spacing:.02em">FACTORY MONITOR PRO</div>
    <div style="font-size:9px;color:#475569;letter-spacing:.09em;
                margin-top:1px">EXECUTIVE SCORECARD · {_area_lbl.upper()}</div>
  </div>
  <div style="display:flex;align-items:center;gap:12px">
    <div style="display:flex;align-items:center;gap:5px">
      <div style="width:7px;height:7px;border-radius:50%;
                  background:#22c55e;box-shadow:0 0 7px #22c55e"></div>
      <span style="font-size:10px;color:#22c55e;font-weight:700;
                   letter-spacing:.08em">LIVE</span>
    </div>
    <div style="font-size:10px;color:#475569">{_ts}</div>
  </div>
</div>

<!-- ── HEADLINE UPTIME + KPI GRID ──────────────────────────── -->
<div style="display:grid;grid-template-columns:1fr 1fr;
            background:{_C['card']};border:1px solid {_C['bord']};
            border-top:none">

  <!-- Left: headline uptime -->
  <div style="padding:22px 24px;border-right:1px solid {_C['bord']}">
    <div style="font-size:9px;font-weight:700;color:{_C['mut']};
                letter-spacing:.14em;text-transform:uppercase;
                margin-bottom:10px">OVERALL FLEET UPTIME</div>
    <div style="display:flex;align-items:flex-end;gap:20px;margin-bottom:14px">
      <div style="font-size:68px;font-weight:800;color:{_g_upc};
                  line-height:1;font-variant-numeric:tabular-nums">{_g_uptime}%</div>
      <div style="padding-bottom:8px">
        <div style="font-size:12px;color:#16a34a;font-weight:600">
          {_g_on} machines running
        </div>
        <div style="font-size:12px;color:#ef4444;margin-top:2px">
          {_g_off} offline · needs action
        </div>
        <div style="font-size:11px;color:{_C['mut']};margin-top:2px">
          {_g_mnt} in maintenance
        </div>
      </div>
    </div>
    <!-- Gradient progress bar -->
    <div style="position:relative;height:16px;background:{_C['card2']};
                border-radius:8px;overflow:hidden;margin-bottom:8px">
      <!-- threshold colour wash -->
      <div style="position:absolute;inset:0;
                  background:linear-gradient(90deg,
                    #fca5a5 0%,#fca5a5 40%,
                    #fde68a 40%,#fde68a 60%,
                    #a7f3d0 60%,#a7f3d0 100%);
                  opacity:.25"></div>
      <!-- actual fill -->
      <div style="position:absolute;top:0;left:0;height:100%;width:{_g_uptime}%;
                  background:{_g_ugrad};border-radius:8px"></div>
    </div>
    <div style="display:flex;justify-content:space-between;
                font-size:9px;color:{_C['mut']}">
      <span>0%</span>
      <span style="color:#dc2626">■ Critical &lt;50%</span>
      <span style="color:#d97706">■ Watch 50–70%</span>
      <span style="color:#16a34a">■ Target ≥70%</span>
      <span>100%</span>
    </div>
  </div>

  <!-- Right: 2×2 KPI tiles -->
  <div style="display:grid;grid-template-columns:1fr 1fr;
              grid-template-rows:1fr 1fr;gap:0">
    <div style="padding:20px;border-bottom:1px solid {_C['bord']};
                border-right:1px solid {_C['bord']};text-align:center">
      <div style="font-size:8px;font-weight:700;color:{_C['mut']};
                  letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">
        Total M/C</div>
      <div style="font-size:36px;font-weight:800;color:#1d4ed8;
                  line-height:1">{_g_total}</div>
      <div style="font-size:10px;color:{_C['mut']};margin-top:4px">
        across {len(_dash_selected)} area{"s" if len(_dash_selected)!=1 else ""}
      </div>
    </div>
    <div style="padding:20px;border-bottom:1px solid {_C['bord']};
                text-align:center">
      <div style="font-size:8px;font-weight:700;color:{_C['mut']};
                  letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">
        Operators</div>
      <div style="font-size:36px;font-weight:800;color:#0369a1;
                  line-height:1">{_g_ops}</div>
      <div style="font-size:10px;color:{_C['mut']};margin-top:4px">
        on floor now</div>
    </div>
    <div style="padding:20px;border-right:1px solid {_C['bord']};
                text-align:center;background:{_C['row_ok']}">
      <div style="font-size:8px;font-weight:700;color:#15803d;
                  letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">
        Running</div>
      <div style="font-size:36px;font-weight:800;color:#16a34a;
                  line-height:1">{_g_on}</div>
      <div style="font-size:10px;color:#16a34a;margin-top:4px">
        {round(_g_on/max(_g_total,1)*100)}% of fleet
      </div>
    </div>
    <div style="padding:20px;text-align:center;background:{_C['row_ng']}">
      <div style="font-size:8px;font-weight:700;color:#dc2626;
                  letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">
        Offline</div>
      <div style="font-size:36px;font-weight:800;color:#dc2626;
                  line-height:1">{_g_off}</div>
      <div style="font-size:10px;color:#dc2626;margin-top:4px">
        {round(_g_off/max(_g_total,1)*100)}% of fleet
      </div>
    </div>
  </div>
</div>

<!-- ── AREA LEADERBOARD ─────────────────────────────────────── -->
<div style="background:{_C['card']};border:1px solid {_C['bord']};
            border-top:none;padding:0 0 4px 0">
  <!-- section header -->
  <div style="display:grid;grid-template-columns:90px 1fr 180px;
              gap:12px;padding:10px 20px;
              background:{_C['card2']};border-bottom:1px solid {_C['bord']};
              font-size:9px;font-weight:700;color:{_C['mut']};
              letter-spacing:.1em;text-transform:uppercase">
    <span>Area</span>
    <span>Uptime vs 100% ← Sorted best → worst</span>
    <span>Detail</span>
  </div>
  {_lb_rows_html}
</div>

<!-- ── PROCESS SOURCE REGISTRY ───────────────────────────────── -->
{_registry_html}

<!-- ── CRITICAL MACHINE ALERTS ─────────────────────────────── -->
{_alerts_section}

</body></html>"""

    # ─── dynamic height ──────────────────────────────────────────────────────
    # All registry cards collapsed by default — only card headers contribute height
    _sc_height = (
        56   # header
        + 170  # uptime + KPI
        + 42   # leaderboard header
        + len(_dash_selected) * 52   # lb rows
        + 12   # gap
        + 44   # registry section header
        + 20   # registry padding
        + len(_proc_data) * 56       # collapsed card headers only
        + (len(_mac_alerts) * 38 + 52 if _mac_alerts else 0)
        + 40   # buffer
    )

    _cmp_sc.html(_sc_html, height=_sc_height, scrolling=False)
    st.caption("📊 Executive Scorecard · All process data from live Excel")

# TAB 2 — AREA MONITOR (existing content)
# ─────────────────────────────────────────────────────────────────────────────
# 3D SCENE BUILDER
# ══════════════════════════════════════════════════════════════════════════════
def add_machine_shape(fig, nx, ny, mtype, color, status, hover, scale=1.0):
    """Add realistic 3D shape for each machine type."""
    th = np.linspace(0, 2*np.pi, 20)
    s = scale  # shorthand

    if mtype == "saw":
        W, D, H = 0.030*s, 0.018*s, 0.035*s
        add_box(fig, nx, ny, 0, W, D, H, color, 0.65, hover)
        blade_r = 0.018*s
        bx = nx + blade_r * np.cos(th)
        by = np.full_like(th, ny)
        bz = H + blade_r * np.sin(th)
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=bz, mode="lines",
            line=dict(color=color, width=3), hoverinfo="skip", showlegend=False))

    elif mtype == "drill":
        W, D, H = 0.016*s, 0.016*s, 0.07*s
        add_box(fig, nx, ny, 0, W, D, H, color, 0.65, hover)
        fig.add_trace(go.Scatter3d(
            x=[nx, nx], y=[ny, ny], z=[H, H+0.06*s], mode="lines",
            line=dict(color=color, width=5), hoverinfo="skip", showlegend=False))
        tip_r = 0.006*s
        fig.add_trace(go.Scatter3d(
            x=nx+tip_r*np.cos(th), y=ny+tip_r*np.sin(th),
            z=np.full_like(th, H+0.06*s), mode="lines",
            line=dict(color=color, width=2), hoverinfo="skip", showlegend=False))

    elif mtype == "press":
        W, D, H = 0.018*s, 0.022*s, 0.09*s
        add_box(fig, nx, ny, 0, W, D, H, color, 0.7, hover)
        add_box(fig, nx, ny, H, 0.032*s, 0.030*s, 0.008*s, color, 0.4)

    elif mtype == "welder":
        W, D, H = 0.026*s, 0.018*s, 0.038*s
        add_box(fig, nx, ny, 0, W, D, H, color, 0.65, hover)
        arm_len = 0.04*s
        fig.add_trace(go.Scatter3d(
            x=[nx, nx+arm_len*0.7], y=[ny, ny], z=[H, H+arm_len*0.7], mode="lines",
            line=dict(color=color, width=4), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter3d(
            x=[nx+arm_len*0.7], y=[ny], z=[H+arm_len*0.7+0.01*s], mode="markers",
            marker=dict(size=5, color="#fbbf24", symbol="diamond"),
            hoverinfo="skip", showlegend=False))

    elif mtype == "vertical":
        W, D, H = 0.020*s, 0.020*s, 0.06*s
        add_box(fig, nx, ny, 0, W, D, H, color, 0.65, hover)
        ring_r = 0.016*s
        fig.add_trace(go.Scatter3d(
            x=nx+ring_r*np.cos(th), y=ny+ring_r*np.sin(th),
            z=np.full_like(th, H+0.008*s), mode="lines",
            line=dict(color=color, width=3), hoverinfo="skip", showlegend=False))

    elif mtype == "sorter":
        W, D, H = 0.06*s, 0.028*s, 0.022*s
        add_box(fig, nx, ny, 0, W, D, H, color, 0.65, hover)
        for rx_off in np.linspace(-W/2+0.006*s, W/2-0.006*s, 5):
            fig.add_trace(go.Scatter3d(
                x=[nx+rx_off, nx+rx_off], y=[ny-D/2, ny+D/2],
                z=[H+0.002, H+0.002], mode="lines",
                line=dict(color="#475569", width=2),
                hoverinfo="skip", showlegend=False))
    else:
        add_box(fig, nx, ny, 0, 0.026*s, 0.018*s, 0.04*s, color, 0.65, hover)


def add_box(fig, cx, cy, z0, W, D, H, color, opacity=0.65, hover=None):
    """Add a colored box (Mesh3d) + wireframe at position cx,cy,z0."""
    x0, x1 = cx-W/2, cx+W/2
    y0, y1 = cy-D/2, cy+D/2
    z1 = z0 + H
    vx = [x0,x1,x1,x0, x0,x1,x1,x0]
    vy = [y0,y0,y1,y1, y0,y0,y1,y1]
    vz = [z0,z0,z0,z0, z1,z1,z1,z1]
    i_ = [0,0,0,0,4,4,2,2,1,1,3,3]
    j_ = [1,2,5,4,5,6,3,7,2,5,7,6]
    k_ = [2,3,4,7,6,7,7,6,5,6,6,7]
    kw = dict(hovertemplate=hover+"<extra></extra>") if hover else dict(hoverinfo="skip")
    fig.add_trace(go.Mesh3d(
        x=vx, y=vy, z=vz, i=i_, j=j_, k=k_,
        color=color, opacity=opacity, showlegend=False, **kw,
    ))
    # Colored wireframe edges
    edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    for a, b in edges:
        fig.add_trace(go.Scatter3d(
            x=[vx[a],vx[b]], y=[vy[a],vy[b]], z=[vz[a],vz[b]],
            mode="lines", line=dict(color=color, width=1),
            hoverinfo="skip", showlegend=False,
        ))


def add_worker(fig, wx, wy, wz, color="#94a3b8"):
    """Add a small stick-figure worker: cylinder body + sphere head."""
    body_h = 0.025
    # Body cylinder (approximated as line)
    fig.add_trace(go.Scatter3d(
        x=[wx, wx], y=[wy, wy], z=[wz, wz+body_h],
        mode="lines", line=dict(color=color, width=3),
        hoverinfo="skip", showlegend=False,
    ))
    # Head sphere
    fig.add_trace(go.Scatter3d(
        x=[wx], y=[wy], z=[wz+body_h+0.008],
        mode="markers",
        marker=dict(size=4, color=color, line=dict(color="white", width=0.5)),
        hoverinfo="skip", showlegend=False,
    ))


def get_box_top(mtype, scale=1.0):
    """Return top-of-machine Z for status pin placement."""
    return {"saw":0.035,"drill":0.07,"press":0.098,"welder":0.038,
            "vertical":0.06,"sorter":0.022,"generic":0.04}.get(mtype, 0.04) * scale


# ══════════════════════════════════════════════════════════════════════════════

with _main_tab_area:
    # ── Area header, KPI strip, alert banner — Area Monitor only ─────────────
    st.markdown(f"""
<div class="factory-header">
  <div>
    <div class="factory-title">🏭 {_area_title}{_hist_badge}</div>
    <div class="factory-subtitle">{_area_subtitle}</div>
  </div>
  <div class="live-badge"><div class="live-dot"></div>{("HISTORY" if st.session_state.viewing_history else "LIVE")}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card kc-blue">
    <span class="kpi-icon">🏭</span>
    <div class="kpi-label">Total Machines</div>
    <div class="kpi-val" style="color:#3b82f6">{total}</div>
    <div class="kpi-bar"><div class="kpi-bar-fill" style="width:100%;background:#3b82f6"></div></div>
    <div class="kpi-sub">this area</div>
  </div>
  <div class="kpi-card kc-green">
    <span class="kpi-icon">⚡</span>
    <div class="kpi-label">Running</div>
    <div class="kpi-val" style="color:#22c55e">{n_on}</div>
    <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{round(n_on/total*100) if total else 0}%;background:#22c55e"></div></div>
    <div class="kpi-sub">{round(n_on/total*100) if total else 0}% of fleet</div>
  </div>
  <div class="kpi-card kc-red">
    <span class="kpi-icon">🛑</span>
    <div class="kpi-label">Offline</div>
    <div class="kpi-val" style="color:#ef4444">{n_off}</div>
    <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{round(n_off/total*100) if total else 0}%;background:#ef4444"></div></div>
    <div class="kpi-sub">{round(n_off/total*100) if total else 0}% of fleet</div>
  </div>
  <div class="kpi-card kc-yellow">
    <span class="kpi-icon">🔧</span>
    <div class="kpi-label">Maintenance</div>
    <div class="kpi-val" style="color:#f59e0b">{n_mnt}</div>
    <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{round(n_mnt/total*100) if total else 0}%;background:#f59e0b"></div></div>
    <div class="kpi-sub">{round(n_mnt/total*100) if total else 0}% of fleet</div>
  </div>
  <div class="kpi-card kc-grad">
    <span class="kpi-icon">📈</span>
    <div class="kpi-label">Uptime</div>
    <div class="kpi-val" style="color:{'#22c55e' if uptime>=70 else '#f59e0b' if uptime>=40 else '#ef4444'}">{uptime}%</div>
    <div class="kpi-bar"><div class="kpi-bar-fill" style="width:{uptime}%;background:{'#22c55e' if uptime>=70 else '#f59e0b' if uptime>=40 else '#ef4444'}"></div></div>
    <div class="kpi-sub">machines running</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Operator alert banner ─────────────────────────────────────────────────
    _std_map = {}   # fallback — always defined even if try block fails
    try:
        _orig_raw = _load_excel_for_area(AREAS[st.session_state.active_area])
        _orig_df  = clean_df(_orig_raw)
        _std_map  = dict(zip(_orig_df["Machine"], _orig_df["Operator_Count"]))
        _alerts   = []
        for _, _arow in df.iterrows():
            if str(_arow.get("Status","")).strip() in ("-",""):
                continue
            if _arow["Status"] == "OFF":
                continue
            _std_ops    = _std_map.get(_arow["Machine"], _arow["Operator_Count"])
            _actual_ops = _arow["Operator_Count"]
            if _actual_ops < _std_ops:
                _alerts.append((_arow["Machine"], _std_ops, _actual_ops))
        if _alerts and not st.session_state.viewing_history:
            _is_ar = st.session_state.get("display_lang") == "Arabic"
            _ops_lbl = "مشغل" if _is_ar else "ops"
            _more_lbl = "المزيد" if _is_ar else "more"
            _banner_title = "القوى العاملة أقل من المعيار" if _is_ar else "MANPOWER BELOW STANDARD"
            _alert_parts = " &nbsp;|&nbsp; ".join(
                f"<b>{_tr(m)}</b>: {act}/{std} {_ops_lbl}"
                for m, std, act in _alerts[:6])
            if len(_alerts) > 6:
                _alert_parts += f" &nbsp;|&nbsp; +{len(_alerts)-6} {_more_lbl}"
            st.markdown(
                f'<div class="alert-banner">'
                f'<span style="font-size:16px;flex-shrink:0">⚠️</span>'
                f'<div>'
                f'<div class="alert-title" style="{"direction:rtl;" if _is_ar else ""}">{_banner_title}</div>'
                f'<div class="alert-body" style="{"direction:rtl;" if _is_ar else ""}">{_alert_parts}</div>'
                f'</div></div>', unsafe_allow_html=True)
    except Exception:
        pass

    col_map, col_list = st.columns([3, 1])

    # MAP COLUMN
    # ══════════════════════════════════════════════════════════════════════════════
    with col_map:
        st.markdown('<div class="sec-lbl">📍 Factory Floor — Machine Status Overlay</div>',
                    unsafe_allow_html=True)

        # ── 2D FLOOR PLAN ──────────────────────────────────────────────────────────
        if st.session_state.view_mode == "2D Floor Plan":
            import re as _re_lbl
            _layout_style = st.session_state.get("layout_style", "AutoCAD Original")
            _area_cfg     = AREAS[st.session_state.active_area]
            _is_pro       = (_layout_style == "Process Ribbon")
            _is_cardwall  = (_layout_style == "Node Map")
            _is_resource  = (_layout_style == "Resource View")
            _is_exec      = (_layout_style == "Executive View")
            _is_exec_layout = (_layout_style == "Executive Layout View")
            _dz_view        = (_layout_style == "draw.io View")

            if _is_pro:
                # ══════════════════════════════════════════════════════════════
                # PROCESS RIBBON — two vertical production lines, top→bottom
                # Left line = Left zone machines, Right line = Right zone machines
                # Sorted by DXF Y-coordinate (entrance at top, exit at bottom)
                # ══════════════════════════════════════════════════════════════
                _is_dark_pr = st.session_state.theme == "dark"

                # ── colour helpers ──────────────────────────────────────────
                def _pr_row_colors(status):
                    if status == "OFF":
                        return ("#3a0a0a" if _is_dark_pr else "#fff1f1",
                                "#ef4444", "#ef4444")
                    elif status == "MAINTENANCE":
                        return ("#2a1a00" if _is_dark_pr else "#fffbeb",
                                "#f59e0b", "#f59e0b")
                    else:
                        return ("#031a0c" if _is_dark_pr else "#f0fdf4",
                                "#22c55e", "#22c55e")

                # ── sort machines by zone, then by their DXF Y (top→bottom) ─
                _area_key_pr = AREAS[st.session_state.active_area]["key"]
                _coords_pr   = AREA_COORDS.get(_area_key_pr, A1_COORDS)

                def _pr_sort_key(col):
                    """col is a Series of machine name strings — map each to its DXF Y coord."""
                    return col.map(lambda m: _coords_pr.get(m, (0, 0.5))[1])

                _pr_machines = df_display[df_display["Status"] != "-"].copy()
                _pr_zones_df = df_display[df_display["Status"] == "-"]

                _pr_left  = _pr_machines[_pr_machines["Zone"] == "Left"].copy()
                _pr_right = _pr_machines[_pr_machines["Zone"] == "Right"].copy()
                _pr_other = _pr_machines[~_pr_machines["Zone"].isin(["Left","Right"])].copy()

                for _dfr in (_pr_left, _pr_right, _pr_other):
                    if not _dfr.empty and "Machine" in _dfr.columns:
                        _dfr.sort_values(by="Machine", key=_pr_sort_key,
                                         ascending=True, inplace=True, ignore_index=True)

                # ── KPI strip ──────────────────────────────────────────────
                _pr_total = len(_pr_machines)
                _pr_on  = int((_pr_machines["Status"]=="ON").sum())
                _pr_off = int((_pr_machines["Status"]=="OFF").sum())
                _pr_mnt = int((_pr_machines["Status"]=="MAINTENANCE").sum())
                _pr_upt = round(_pr_on / max(_pr_total,1) * 100)
                _pr_upc = "#22c55e" if _pr_upt>=70 else ("#f59e0b" if _pr_upt>=40 else "#ef4444")

                # alert banner
                _pr_problem = _pr_machines[_pr_machines["Status"].isin(["OFF","MAINTENANCE"])]
                if not _pr_problem.empty:
                    _pr_parts = []
                    for _, _prow in _pr_problem.iterrows():
                        _pst = _prow["Status"]
                        _pc  = "#ef4444" if _pst=="OFF" else "#f59e0b"
                        _ico = "🔴" if _pst=="OFF" else "🟡"
                        _pr_parts.append(
                            f'<span style="background:{_pc}22;color:{_pc};border:1px solid {_pc}55;'
                            f'border-radius:5px;padding:2px 8px;font-size:11px;font-weight:600">'
                            f'{_ico} {_tr(_prow["Machine"])}</span>')
                    st.markdown(
                        f'<div style="background:{"#1a0800" if _is_dark_pr else "#fff7ed"};'
                        f'border:1px solid #f59e0b55;border-left:3px solid #f59e0b;'
                        f'border-radius:8px;padding:8px 14px;margin-bottom:10px;'
                        f'display:flex;gap:8px;flex-wrap:wrap;align-items:center">'
                        f'<span style="font-size:11px;font-weight:700;color:#f59e0b;'
                        f'white-space:nowrap;font-family:JetBrains Mono,monospace">⚠ NEEDS ATTENTION</span>'
                        f'{" ".join(_pr_parts)}</div>',
                        unsafe_allow_html=True)

                st.markdown(
                    f'<div style="background:{T["surface"]};border:1px solid {T["border"]};'
                    f'border-radius:10px;padding:10px 18px;margin-bottom:14px;'
                    f'display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">'
                    f'<div style="display:flex;gap:18px;align-items:center">'
                    f'<span style="font-size:13px;font-weight:700;color:{T["text"]}">{_area_title}</span>'
                    f'<span style="font-size:11px;color:{T["text_muted"]};font-family:JetBrains Mono,monospace">'
                    f'{_pr_total} machines</span></div>'
                    f'<div style="display:flex;gap:14px;align-items:center">'
                    f'<span style="font-size:12px;color:#22c55e;font-weight:600">🟢 {_pr_on}</span>'
                    f'<span style="font-size:12px;color:#ef4444;font-weight:600">🔴 {_pr_off}</span>'
                    f'<span style="font-size:12px;color:#f59e0b;font-weight:600">🟡 {_pr_mnt}</span>'
                    f'<span style="font-size:14px;font-weight:700;color:{_pr_upc}">{_pr_upt}%</span>'
                    f'</div></div>',
                    unsafe_allow_html=True)

                # ── two-column ribbon ──────────────────────────────────────
                _pr_col_l, _pr_col_r = st.columns(2)

                def _render_ribbon(col, machines_df, zone_label, line_color):
                    with col:
                        _z_on  = int((machines_df["Status"]=="ON").sum())
                        _z_off = int((machines_df["Status"]=="OFF").sum())
                        _z_mnt = int((machines_df["Status"]=="MAINTENANCE").sum())
                        _z_tot = len(machines_df)
                        _z_upt = round(_z_on/max(_z_tot,1)*100)
                        _z_upc = "#22c55e" if _z_upt>=70 else ("#f59e0b" if _z_upt>=40 else "#ef4444")

                        # lane header
                        st.markdown(
                            f'<div style="background:{line_color};border-radius:8px 8px 0 0;'
                            f'padding:8px 14px;display:flex;justify-content:space-between;'
                            f'align-items:center;margin-bottom:0">'
                            f'<span style="font-size:11px;font-weight:700;color:white;'
                            f'font-family:JetBrains Mono,monospace;letter-spacing:.06em">'
                            f'{zone_label} PRODUCTION LINE</span>'
                            f'<span style="font-size:10px;color:rgba(255,255,255,0.85)">'
                            f'🟢 {_z_on} &nbsp;🔴 {_z_off} &nbsp;🟡 {_z_mnt} &nbsp;'
                            f'<b>{_z_upt}%</b></span></div>',
                            unsafe_allow_html=True)

                        # entrance marker
                        st.markdown(
                            f'<div style="background:{T["surface2"]};border-left:2px solid {line_color};'
                            f'border-right:2px solid {line_color};padding:4px 14px;'
                            f'text-align:center;font-size:9px;color:{T["text_muted"]};'
                            f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                            f'▼ RM ENTRANCE</div>',
                            unsafe_allow_html=True)

                        if machines_df.empty:
                            st.markdown(
                                f'<div style="background:{T["surface"]};border:1px solid {T["border"]};'
                                f'padding:20px;text-align:center;color:{T["text_muted"]};'
                                f'font-size:12px">No machines in this zone</div>',
                                unsafe_allow_html=True)
                        else:
                            rows_html = ""
                            _prev_group = None
                            for _, _mr in machines_df.iterrows():
                                _mst  = str(_mr.get("Status","")).strip()
                                _mc   = STATUS_COLORS.get(_mst,"#94a3b8")
                                _ops  = int(_mr.get("Operator_Count",0))
                                _note = str(_mr.get("Notes","—"))
                                _mname_pr = _tr(_mr["Machine"])
                                _row_bg, _row_border, _strip = _pr_row_colors(_mst)

                                try:
                                    _std_pr = _std_map.get(_mr["Machine"], _ops)
                                    _ops_warn_pr = (_ops < _std_pr) and _mst != "OFF"
                                except Exception:
                                    _std_pr, _ops_warn_pr = _ops, False

                                _ops_html = (
                                    f'<span style="color:#f59e0b;font-size:10px;font-weight:600">'
                                    f'⚠ {_ops}/{_std_pr} ops</span>'
                                    if _ops_warn_pr else
                                    f'<span style="color:{T["text_muted"]};font-size:10px">'
                                    f'👷 {_ops}</span>')

                                _note_html = ""
                                if _note not in ("—","","nan"):
                                    _note_short = _note[:28]+"…" if len(_note)>28 else _note
                                    _note_html = (
                                        f'<div style="font-size:9px;color:{T["text_muted"]};'
                                        f'font-style:italic;margin-top:2px">{_note_short}</div>')

                                rows_html += (
                                    f'<div style="background:{_row_bg};'
                                    f'border-left:4px solid {_strip};'
                                    f'border-bottom:1px solid {T["border"]};'
                                    f'border-right:2px solid {line_color};'
                                    f'padding:8px 12px;display:flex;'
                                    f'justify-content:space-between;align-items:center;gap:8px">'
                                    f'<div style="min-width:0;flex:1">'
                                    f'<div style="font-size:12px;font-weight:600;color:{T["text"]};'
                                    f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
                                    f'{_mname_pr}</div>'
                                    f'{_ops_html}'
                                    f'{_note_html}</div>'
                                    f'<div style="text-align:right;flex-shrink:0">'
                                    f'<span style="background:{_mc}22;color:{_mc};'
                                    f'border:1px solid {_mc}55;border-radius:5px;'
                                    f'padding:2px 8px;font-size:10px;font-weight:700;'
                                    f'font-family:JetBrains Mono,monospace;white-space:nowrap">'
                                    f'{_mst}</span></div></div>')

                            st.markdown(
                                f'<div style="border-left:2px solid {line_color};'
                                f'border-right:2px solid {line_color}">'
                                f'{rows_html}</div>',
                                unsafe_allow_html=True)

                        # exit marker
                        st.markdown(
                            f'<div style="background:{T["surface2"]};border-left:2px solid {line_color};'
                            f'border-right:2px solid {line_color};border-bottom:2px solid {line_color};'
                            f'border-radius:0 0 8px 8px;padding:4px 14px;'
                            f'text-align:center;font-size:9px;color:{T["text_muted"]};'
                            f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                            f'▲ FG EXIT</div>',
                            unsafe_allow_html=True)

                _render_ribbon(_pr_col_l, _pr_left,  "LEFT",  "#185FA5")
                _render_ribbon(_pr_col_r, _pr_right, "RIGHT", "#166534")

                # other-zone machines (not Left or Right)
                if not _pr_other.empty:
                    st.markdown(
                        f'<div style="font-size:9px;font-family:JetBrains Mono,monospace;'
                        f'letter-spacing:.1em;color:{T["text_muted"]};text-transform:uppercase;'
                        f'border-bottom:1px solid {T["border"]};padding-bottom:6px;margin:16px 0 8px">'
                        f'Other zones ({len(_pr_other)})</div>',
                        unsafe_allow_html=True)
                    _oth_html = ""
                    for _, _or in _pr_other.iterrows():
                        _ost = str(_or.get("Status","")).strip()
                        _oc  = STATUS_COLORS.get(_ost,"#94a3b8")
                        _row_bg2,_,_ = _pr_row_colors(_ost)
                        _oth_html += (
                            f'<div style="background:{_row_bg2};border-left:4px solid {_oc};'
                            f'border:1px solid {T["border"]};border-radius:6px;'
                            f'padding:7px 12px;margin-bottom:5px;display:flex;'
                            f'justify-content:space-between;align-items:center">'
                            f'<span style="font-size:12px;font-weight:600;color:{T["text"]}">'
                            f'{_tr(_or["Machine"])}</span>'
                            f'<span style="color:{_oc};font-size:10px;font-weight:700;'
                            f'font-family:JetBrains Mono,monospace">{_ost}</span></div>')
                    st.markdown(_oth_html, unsafe_allow_html=True)

                # storage/zone entries
                if not _pr_zones_df.empty:
                    _chips = "".join(
                        f'<span style="background:{T["surface2"]};border:1px solid {T["border"]};'
                        f'border-radius:5px;padding:3px 9px;font-size:10px;color:{T["text_muted"]}">'
                        f'🗂 {_tr(r["Machine"])}</span>'
                        for _, r in _pr_zones_df.iterrows())
                    st.markdown(
                        f'<div style="margin-top:14px;font-size:9px;color:{T["text_muted"]};'
                        f'font-family:JetBrains Mono,monospace;margin-bottom:6px">'
                        f'STORAGE / ZONES</div>'
                        f'<div style="display:flex;flex-wrap:wrap;gap:5px">{_chips}</div>',
                        unsafe_allow_html=True)

                st.caption("🎀 Process Ribbon · Left & right production lines · Sorted entrance→exit · Full status, operators and notes always visible")

            elif _is_cardwall:
                # ══════════════════════════════════════════════════════════════
                # NODE MAP — Plotly SVG graph matching the reference image:
                # RM Entrance at top → two branches (Left / Right lines) →
                # stages flow downward → merge → FG EXIT at bottom.
                # Node colour = live status. Dashed red arrow = disrupted flow.
                # ══════════════════════════════════════════════════════════════
                _is_dark_nm  = st.session_state.theme == "dark"
                _nm_bg       = T["bg"]
                _nm_surf     = T["surface"]
                _nm_bord     = T["border"]
                _nm_txt      = T["text"]
                _nm_muted    = T["text_muted"]
                _nm_paper    = "#0a0a0a" if _is_dark_nm else "#ffffff"
                _nm_plot_bg  = "#0a0a0a" if _is_dark_nm else "#ffffff"
                _nm_node_txt = "#ffffff" if _is_dark_nm else "#1a1a1a"

                # ── machine lookup ─────────────────────────────────────────
                _nm_machines = df_display[df_display["Status"] != "-"]
                _nm_lookup   = {r["Machine"]: r for _, r in _nm_machines.iterrows()}

                _area_key_nm = AREAS[st.session_state.active_area]["key"]

                # ── KPI / alert strip ──────────────────────────────────────
                _nm_total = len(_nm_machines)
                _nm_on  = int((_nm_machines["Status"]=="ON").sum())
                _nm_off = int((_nm_machines["Status"]=="OFF").sum())
                _nm_mnt = int((_nm_machines["Status"]=="MAINTENANCE").sum())
                _nm_upt = round(_nm_on/max(_nm_total,1)*100)
                _nm_upc = "#22c55e" if _nm_upt>=70 else ("#f59e0b" if _nm_upt>=40 else "#ef4444")

                _nm_problems = _nm_machines[_nm_machines["Status"].isin(["OFF","MAINTENANCE"])]
                if not _nm_problems.empty:
                    _np_parts = []
                    for _, _npr in _nm_problems.iterrows():
                        _npc = "#ef4444" if _npr["Status"]=="OFF" else "#f59e0b"
                        _npi = "🔴" if _npr["Status"]=="OFF" else "🟡"
                        _np_parts.append(
                            f'<span style="background:{_npc}22;color:{_npc};'
                            f'border:1px solid {_npc}55;border-radius:5px;'
                            f'padding:2px 8px;font-size:11px;font-weight:600">'
                            f'{_npi} {_tr(_npr["Machine"])}</span>')
                    st.markdown(
                        f'<div style="background:{"#1a0800" if _is_dark_nm else "#fff7ed"};'
                        f'border:1px solid #f59e0b55;border-left:3px solid #f59e0b;'
                        f'border-radius:8px;padding:8px 14px;margin-bottom:10px;'
                        f'display:flex;gap:8px;flex-wrap:wrap;align-items:center">'
                        f'<span style="font-size:11px;font-weight:700;color:#f59e0b;'
                        f'white-space:nowrap;font-family:JetBrains Mono,monospace">'
                        f'⚠ FLOW DISRUPTION</span>'
                        f'{" ".join(_np_parts)}</div>',
                        unsafe_allow_html=True)

                st.markdown(
                    f'<div style="background:{_nm_surf};border:1px solid {_nm_bord};'
                    f'border-radius:10px;padding:10px 18px;margin-bottom:14px;'
                    f'display:flex;justify-content:space-between;align-items:center;'
                    f'flex-wrap:wrap;gap:8px">'
                    f'<span style="font-size:13px;font-weight:700;color:{_nm_txt}">'
                    f'{_area_title} — Material Flow</span>'
                    f'<div style="display:flex;gap:14px;align-items:center">'
                    f'<span style="font-size:12px;color:#22c55e;font-weight:600">🟢 {_nm_on}</span>'
                    f'<span style="font-size:12px;color:#ef4444;font-weight:600">🔴 {_nm_off}</span>'
                    f'<span style="font-size:12px;color:#f59e0b;font-weight:600">🟡 {_nm_mnt}</span>'
                    f'<span style="font-size:14px;font-weight:700;color:{_nm_upc}">{_nm_upt}%</span>'
                    f'</div></div>',
                    unsafe_allow_html=True)

                # Each entry: (label, left_group, right_group)
                #   left_group  = list of machine names on left branch
                #   right_group = list of machine names on right branch
                #   None        = no node that side (arrow passes through)
                # Special rows: ("SPLIT",None,None) = branching point
                #               ("MERGE",None,None) = merge point
                #               ("ENTRANCE",None,None) / ("EXIT",None,None)
                _NM_FLOWS2 = {
                    "F5_A1": [
                        ("ENTRANCE", None, None),
                        ("SPLIT",    None, None),
                        ("row", ["RASA Saw"],
                                ["Manual Saw 1","Manual Saw 2"]),
                        ("row", ["Assembly Station"],
                                ["Leadgers Welding 1","Leadgers Welding 2",
                                 "Leadgers Welding 3","Leadgers Welding 4",
                                 "Leadgers Welding 5","Leadgers Welding 6"]),
                        ("row", ["Drill #1","Drill","Drill #2"],
                                ["Ring Vertical 1","Ring Vertical 2","Ring Vertical 3"]),
                        ("row", ["Welding Machine 1","Welding Machine 2",
                                 "Welding Machine 3","Welding Machine 4","Welding Machine 5"],
                                ["Cup Vertical 1","Cup Vertical 2",
                                 "Cup Vertical 3","Cup Vertical 4"]),
                        ("row", None, ["Auto Welding"]),
                        ("MERGE", None, None),
                        ("row_centre", ["Production Sorting Area"], None),
                        ("EXIT", None, None),
                    ],
                    "F5_A2": [
                        ("ENTRANCE", None, None),
                        ("SPLIT",    None, None),
                        ("row", ["Mixer 1","Mixer 2"],
                                ["Mixer 3","Mixer 4","Mixer 5","Mixer 6"]),
                        ("row", ["Cup Frame Form Mixer 1","Cup Frame Form Mixer 2"],
                                ["Drill 4","Drill 5","Drill 6"]),
                        ("row", ["Drrill 1","Drrill 2","Drrill 3"],
                                ["Drill 7","Drill 8","Drill 9"]),
                        ("row", ["Form & Tap","Forming "],
                                ["Saw ","Multi Drill "]),
                        ("row", ["Weld Cell 1","Weld Cell 2","Weld Cell 3"],
                                ["Weld Cell 4","Weld Cell 5","Weld Cell 6"]),
                        ("row", ["Cup Weld 1","Cup Weld 2"],
                                ["Tap"]),
                        ("MERGE", None, None),
                        ("EXIT", None, None),
                    ],
                    "F4_A1": [
                        ("ENTRANCE", None, None),
                        ("SPLIT",    None, None),
                        ("row", ["Manual Saw"],
                                ["Auto Saw"]),
                        ("row", ["ECO Punch Press","ECO Punch + TECH Press"],
                                ["TECH Punch / Drill","Presses"]),
                        ("row", ["Welding Package","Pre-Assembly Welding Robot"],
                                ["Welding Station","Welding Robot"]),
                        ("MERGE", None, None),
                        ("row_centre", ["9-Frame Assembly"], None),
                        ("row_centre", ["Grinding","Delivery / QC"], None),
                        ("EXIT", None, None),
                    ],
                    "F4_A2": [
                        ("ENTRANCE", None, None),
                        ("SPLIT",    None, None),
                        ("row", ["Raw Material Storage"],
                                ["Assembly RM Storage"]),
                        ("row", ["Saw Machine"],
                                ["CNC Router Machine"]),
                        ("row", ["Manual Assembly Tools"],
                                ["WIP + Transport Carts + Cabinet Zone"]),
                        ("row", ["Pallet Assembly Spread"],
                                ["TECH, ECO & WIP Area"]),
                        ("MERGE", None, None),
                        ("row_centre", ["Paint / Coating Station"], None),
                        ("row_centre", ["Storage Cabinet","Ready Acrow Board Pallets"], None),
                        ("EXIT", None, None),
                    ],
                }
                _flow2 = _NM_FLOWS2.get(_area_key_nm, _NM_FLOWS2["F5_A1"])

                # ── Plotly drawing helpers ────────────────────────────────
                # Canvas: x 0..1, y 0..1 (y=1 at top)
                # Nodes: rounded rectangle via SVG path in shapes
                # Arrows: via annotations with arrowhead

                def _node_status(machine_list):
                    """Returns (worst_status, color, ops_str, label_lines)"""
                    if not machine_list:
                        return "ON", "#22c55e", "", []
                    live = [m for m in machine_list if m in _nm_lookup]
                    if not live:
                        return "ON", "#22c55e", "", []
                    statuses = [str(_nm_lookup[m]["Status"]).strip() for m in live]
                    ops_total = sum(int(_nm_lookup[m].get("Operator_Count",0)) for m in live)
                    if "OFF" in statuses:
                        worst, wc = "OFF", "#ef4444"
                    elif "MAINTENANCE" in statuses:
                        worst, wc = "MAINTENANCE", "#f59e0b"
                    else:
                        worst, wc = "ON", "#22c55e"
                    n_on  = statuses.count("ON")
                    n_off = statuses.count("OFF")
                    n_mnt = statuses.count("MAINTENANCE")
                    if len(live) == 1:
                        status_str = f"{worst} · {ops_total} ops"
                    else:
                        parts = []
                        if n_on:  parts.append(f"{n_on} ON")
                        if n_off: parts.append(f"{n_off} OFF")
                        if n_mnt: parts.append(f"{n_mnt} MAINT")
                        status_str = " · ".join(parts)
                    # build display label (group name)
                    if len(live) == 1:
                        base_lbl = _tr(live[0])
                        if len(base_lbl) > 20: base_lbl = base_lbl[:18] + "…"
                        label_lines = [base_lbl]
                    else:
                        import re as _re_nm
                        base = _re_nm.sub(r'\s*[\d#]+\s*$', '', live[0]).strip()
                        base_lbl = _tr(base) + f" ×{len(live)}"
                        label_lines = [base_lbl]
                    return worst, wc, status_str, label_lines

                # ── layout geometry ────────────────────────────────────────
                # Count real rows to compute Y spacing
                _real_rows = [r for r in _flow2 if r[0] in ("row","row_centre")]
                _n_rows = len(_real_rows)
                _special_rows = sum(1 for r in _flow2 if r[0] in
                                    ("ENTRANCE","EXIT","SPLIT","MERGE"))
                _total_slots = _n_rows + _special_rows
                _slot_h = 1.0 / max(_total_slots + 1, 4)

                _NW = 0.22   # node width (fraction of canvas)
                _NH = 0.06   # node height
                _LX = 0.18   # left node centre x
                _RX = 0.82   # right node centre x
                _CX = 0.50   # centre x (for entrance/exit/merge/split)

                _fig_nm = go.Figure()
                _fig_nm.update_layout(
                    xaxis=dict(range=[0,1], showgrid=False, zeroline=False,
                               showticklabels=False, fixedrange=True),
                    yaxis=dict(range=[0,1], showgrid=False, zeroline=False,
                               showticklabels=False, fixedrange=True),
                    plot_bgcolor=_nm_plot_bg, paper_bgcolor=_nm_paper,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=max(520, _total_slots * 100),
                    showlegend=False,
                )

                _shapes  = []
                _annots  = []
                _slot    = 0    # current vertical slot (0=top)

                # track previous node centres per column for arrows
                _prev_L = None  # (cx, cy_bottom) of last left node
                _prev_R = None  # (cx, cy_bottom) of last right node
                _prev_C = None  # (cx, cy_bottom) of last centre node
                _split_y = None # y of the split point
                _merge_y = None # y of the merge point

                def _cy(slot):
                    """Centre Y for a slot (1=top, decreasing)."""
                    return 1.0 - (_slot_h * (slot + 0.5))

                def _add_node(cx, cy, label_lines, status_str, border_col,
                               fill_col_dark, fill_col_light, node_id=""):
                    """Add a rounded rectangle node with text."""
                    _fill = fill_col_dark if _is_dark_nm else fill_col_light
                    _x0, _x1 = cx - _NW/2, cx + _NW/2
                    _y0, _y1 = cy - _NH/2, cy + _NH/2
                    _shapes.append(dict(
                        type="rect", x0=_x0, y0=_y0, x1=_x1, y1=_y1,
                        line=dict(color=border_col, width=2.5),
                        fillcolor=_fill,
                        xref="x", yref="y",
                    ))
                    # main label
                    _main_lbl = label_lines[0] if label_lines else ""
                    _annots.append(dict(
                        x=cx, y=cy + 0.012,
                        text=f"<b>{_main_lbl}</b>",
                        showarrow=False, xref="x", yref="y",
                        font=dict(size=11, color=_nm_node_txt,
                                  family="Inter, sans-serif"),
                        xanchor="center", yanchor="middle",
                    ))
                    # status sub-label
                    _annots.append(dict(
                        x=cx, y=cy - 0.016,
                        text=f"<span style='font-size:9px'>{status_str}</span>",
                        showarrow=False, xref="x", yref="y",
                        font=dict(size=9, color=border_col,
                                  family="JetBrains Mono, monospace"),
                        xanchor="center", yanchor="middle",
                    ))
                    return (_x0, _x1, _y0, _y1, cx, cy)

                def _arrow(x0, y0, x1, y1, col, dashed=False):
                    """Draw an arrow from (x0,y0) to (x1,y1)."""
                    _dash = "dot" if dashed else None
                    _shapes.append(dict(
                        type="line",
                        x0=x0, y0=y0, x1=x1, y1=y1,
                        line=dict(color=col, width=1.8,
                                  dash=_dash if _dash else "solid"),
                        xref="x", yref="y",
                    ))
                    # arrowhead via annotation
                    _dx = x1 - x0; _dy = y1 - y0
                    _annots.append(dict(
                        x=x1, y=y1, ax=x0, ay=y0,
                        xref="x", yref="y", axref="x", ayref="y",
                        showarrow=True,
                        arrowhead=2, arrowsize=1.2, arrowwidth=1.8,
                        arrowcolor=col,
                        text="",
                    ))

                # ── render flow ────────────────────────────────────────────
                for _fi, _frow in enumerate(_flow2):
                    _ftype = _frow[0]
                    _cy_now = _cy(_slot)

                    if _ftype == "ENTRANCE":
                        # grey pill at top centre
                        _shapes.append(dict(
                            type="rect",
                            x0=_CX-0.16, y0=_cy_now-0.035,
                            x1=_CX+0.16, y1=_cy_now+0.035,
                            line=dict(color="#888888", width=1),
                            fillcolor="#cccccc" if not _is_dark_nm else "#333333",
                            xref="x", yref="y",
                        ))
                        _annots.append(dict(
                            x=_CX, y=_cy_now+0.010,
                            text="<b>RM ENTRANCE</b>",
                            showarrow=False, xref="x", yref="y",
                            font=dict(size=11, color="#555555" if not _is_dark_nm else "#cccccc",
                                      family="Inter, sans-serif"),
                            xanchor="center", yanchor="middle",
                        ))
                        _annots.append(dict(
                            x=_CX, y=_cy_now-0.012,
                            text="Raw material in",
                            showarrow=False, xref="x", yref="y",
                            font=dict(size=9, color="#888888",
                                      family="Inter, sans-serif"),
                            xanchor="center", yanchor="middle",
                        ))
                        _prev_C = (_CX, _cy_now - 0.035)
                        _slot += 1

                    elif _ftype == "SPLIT":
                        # draw two dashed diagonal arrows from _prev_C to left and right columns
                        if _prev_C:
                            _sx, _sy = _prev_C
                            _split_y = _cy(_slot) + _slot_h * 0.3
                            # left arrow
                            _arrow(_sx, _sy, _LX, _split_y, "#aaaaaa", dashed=True)
                            # right arrow
                            _arrow(_sx, _sy, _RX, _split_y, "#aaaaaa", dashed=True)
                        _prev_L = (_LX, _split_y) if _split_y else (_LX, _cy_now)
                        _prev_R = (_RX, _split_y) if _split_y else (_RX, _cy_now)
                        _slot += 1

                    elif _ftype == "MERGE":
                        # draw arrows from prev L and R into centre
                        _merge_cy = _cy(_slot)
                        if _prev_L:
                            _col_L = "#ef4444" if any(
                                str(_nm_lookup.get(m,{}).get("Status",""))=="OFF"
                                for m in (_flow2[_fi-1][1] or []) if m in _nm_lookup
                            ) else "#22c55e"
                            _arrow(_prev_L[0], _prev_L[1],
                                   _CX - 0.04, _merge_cy + _NH/2,
                                   _col_L, dashed=(_col_L=="#ef4444"))
                        if _prev_R:
                            _col_R = "#ef4444" if any(
                                str(_nm_lookup.get(m,{}).get("Status",""))=="OFF"
                                for m in (_flow2[_fi-1][2] or []) if m in _nm_lookup
                            ) else "#22c55e"
                            _arrow(_prev_R[0], _prev_R[1],
                                   _CX + 0.04, _merge_cy + _NH/2,
                                   _col_R, dashed=(_col_R=="#ef4444"))
                        _prev_C = (_CX, _merge_cy - _NH/2)
                        _prev_L = None
                        _prev_R = None
                        _slot += 1

                    elif _ftype == "EXIT":
                        # grey pill at bottom centre
                        _shapes.append(dict(
                            type="rect",
                            x0=_CX-0.18, y0=_cy_now-0.030,
                            x1=_CX+0.18, y1=_cy_now+0.030,
                            line=dict(color="#888888", width=1),
                            fillcolor="#cccccc" if not _is_dark_nm else "#333333",
                            xref="x", yref="y",
                        ))
                        _annots.append(dict(
                            x=_CX, y=_cy_now,
                            text="<b>FG EXIT</b> · finished goods out",
                            showarrow=False, xref="x", yref="y",
                            font=dict(size=10, color="#555555" if not _is_dark_nm else "#cccccc",
                                      family="Inter, sans-serif"),
                            xanchor="center", yanchor="middle",
                        ))
                        # arrow down from prev centre
                        if _prev_C:
                            _arrow(_prev_C[0], _prev_C[1],
                                   _CX, _cy_now + 0.030, "#22c55e")
                        _slot += 1

                    elif _ftype == "row":
                        _, _lm_list, _rm_list = _frow
                        _cy_row = _cy(_slot)

                        # ── LEFT node ──
                        if _lm_list:
                            _lm_live = [m for m in _lm_list if m in _nm_lookup]
                            _l_worst, _l_col, _l_status, _l_lbl = _node_status(_lm_list)
                            _l_fill_d = "#1a0404" if _l_worst=="OFF" else (
                                        "#2a1a00" if _l_worst=="MAINTENANCE" else "#031a0c")
                            _l_fill_l = "#fff1f1" if _l_worst=="OFF" else (
                                        "#fffbeb" if _l_worst=="MAINTENANCE" else "#f0fdf4")
                            _add_node(_LX, _cy_row, _l_lbl, _l_status,
                                      _l_col, _l_fill_d, _l_fill_l)
                            # arrow from previous left node
                            if _prev_L:
                                _dashed_l = _l_worst == "OFF"
                                _ac_l = "#ef4444" if _dashed_l else (
                                        "#f59e0b" if _l_worst=="MAINTENANCE" else "#22c55e")
                                _arrow(_prev_L[0], _prev_L[1],
                                       _LX, _cy_row + _NH/2, _ac_l, dashed=_dashed_l)
                            _prev_L = (_LX, _cy_row - _NH/2)
                        else:
                            # pass-through — no node, extend arrow line
                            if _prev_L:
                                _arrow(_prev_L[0], _prev_L[1],
                                       _LX, _cy_row, "#aaaaaa", dashed=True)
                                _prev_L = (_LX, _cy_row)

                        # ── RIGHT node ──
                        if _rm_list:
                            _rm_live = [m for m in _rm_list if m in _nm_lookup]
                            _r_worst, _r_col, _r_status, _r_lbl = _node_status(_rm_list)
                            _r_fill_d = "#1a0404" if _r_worst=="OFF" else (
                                        "#2a1a00" if _r_worst=="MAINTENANCE" else "#031a0c")
                            _r_fill_l = "#fff1f1" if _r_worst=="OFF" else (
                                        "#fffbeb" if _r_worst=="MAINTENANCE" else "#f0fdf4")
                            _add_node(_RX, _cy_row, _r_lbl, _r_status,
                                      _r_col, _r_fill_d, _r_fill_l)
                            if _prev_R:
                                _dashed_r = _r_worst == "OFF"
                                _ac_r = "#ef4444" if _dashed_r else (
                                        "#f59e0b" if _r_worst=="MAINTENANCE" else "#22c55e")
                                _arrow(_prev_R[0], _prev_R[1],
                                       _RX, _cy_row + _NH/2, _ac_r, dashed=_dashed_r)
                            _prev_R = (_RX, _cy_row - _NH/2)
                        else:
                            if _prev_R:
                                _arrow(_prev_R[0], _prev_R[1],
                                       _RX, _cy_row, "#aaaaaa", dashed=True)
                                _prev_R = (_RX, _cy_row)

                        _slot += 1

                    elif _ftype == "row_centre":
                        _, _cm_list, _ = _frow
                        _cy_row = _cy(_slot)
                        if _cm_list:
                            _c_worst, _c_col, _c_status, _c_lbl = _node_status(_cm_list)
                            _c_fill_d = "#1a0404" if _c_worst=="OFF" else (
                                        "#2a1a00" if _c_worst=="MAINTENANCE" else "#031a0c")
                            _c_fill_l = "#fff1f1" if _c_worst=="OFF" else (
                                        "#fffbeb" if _c_worst=="MAINTENANCE" else "#f0fdf4")
                            _add_node(_CX, _cy_row, _c_lbl, _c_status,
                                      _c_col, _c_fill_d, _c_fill_l)
                            if _prev_C:
                                _dashed_c = _c_worst == "OFF"
                                _ac_c = "#ef4444" if _dashed_c else (
                                        "#f59e0b" if _c_worst=="MAINTENANCE" else "#22c55e")
                                _arrow(_prev_C[0], _prev_C[1],
                                       _CX, _cy_row + _NH/2, _ac_c, dashed=_dashed_c)
                            _prev_C = (_CX, _cy_row - _NH/2)
                        _slot += 1

                # apply shapes and annotations
                _fig_nm.update_layout(shapes=_shapes, annotations=_annots)

                st.plotly_chart(_fig_nm, use_container_width=True,
                                config={"displayModeBar": False})

                # zone/storage entries at bottom
                _nm_zone_entries = df_display[df_display["Status"] == "-"]
                if not _nm_zone_entries.empty:
                    _nchips = "".join(
                        f'<span style="background:{_nm_surf};border:1px solid {_nm_bord};'
                        f'border-radius:5px;padding:3px 9px;font-size:10px;color:{_nm_muted}">'
                        f'🗂 {_tr(r["Machine"])}</span>'
                        for _, r in _nm_zone_entries.iterrows())
                    st.markdown(
                        f'<div style="font-size:9px;color:{_nm_muted};'
                        f'font-family:JetBrains Mono,monospace;margin-bottom:6px">'
                        f'STORAGE / ZONES</div>'
                        f'<div style="display:flex;flex-wrap:wrap;gap:5px">{_nchips}</div>',
                        unsafe_allow_html=True)

                st.caption("🔗 Node Map · RM Entrance → Left & Right lines → FG Exit · "
                           "Green arrows = flowing · Red dashed = disrupted")

            elif _is_resource:
                # ══════════════════════════════════════════════════════════════
                # RESOURCE VIEW — Process Ribbon style, visualization only.
                # No ON/OFF status. Similar machines grouped into single blocks.
                # Each block shows:  N M/C  Base Name
                #                   👷 X  For Each Machine
                # ══════════════════════════════════════════════════════════════
                import re as _re_rv

                _is_dark_rv  = st.session_state.theme == "dark"
                _rv_bg       = T["bg"]
                _rv_surf     = T["surface"]
                _rv_s2       = T["surface2"]
                _rv_bord     = T["border"]
                _rv_txt      = T["text"]
                _rv_muted    = T["text_muted"]

                # ── accent colours — neutral, no status meaning ────────────
                _rv_accent_l = "#1d4ed8"   # blue  — left line
                _rv_accent_r = "#15803d"   # green — right line
                _rv_block_bg_d  = "#111827"
                _rv_block_bg_l  = "#f8fafc"
                _rv_block_bg    = _rv_block_bg_d if _is_dark_rv else _rv_block_bg_l
                _rv_count_col   = "#3b82f6" if _is_dark_rv else "#1d4ed8"
                _rv_ops_col     = "#f59e0b"

                # ── grouping helpers ───────────────────────────────────────
                def _rv_base(name):
                    """Strip trailing number/hash to get the group base name."""
                    n = name.strip()
                    cleaned = _re_rv.sub(r'[\s\-_]*[#]?\s*\d+\s*$', '', n).strip()
                    return cleaned if cleaned else n

                # ── get all machines (exclude zone/storage rows) ───────────
                _area_key_rv = AREAS[st.session_state.active_area]["key"]
                _coords_rv   = AREA_COORDS.get(_area_key_rv, A1_COORDS)

                _rv_all = df_display[df_display["Status"] != "-"].copy()
                _rv_zones_df = df_display[df_display["Status"] == "-"]

                # Assign base name
                _rv_all["_base"] = _rv_all["Machine"].apply(_rv_base)

                # Sort by DXF Y-coordinate (entrance → exit) within each zone
                def _rv_sort_key(col):
                    return col.map(lambda m: _coords_rv.get(m, (0, 0.5))[1])

                _rv_all.sort_values(by="Machine", key=_rv_sort_key,
                                    ascending=True, inplace=True,
                                    ignore_index=True)

                # Build ordered groups per zone, preserving entrance→exit order
                def _rv_build_groups(zone_df):
                    """
                    Iterate rows in DXF order; group consecutive (and non-consecutive)
                    rows with the same base name. Returns an ordered list of dicts:
                    {base, count, ops_per_mc, zone}
                    """
                    seen   = {}   # base → index in output list
                    groups = []   # list of dicts in first-occurrence order
                    for _, r in zone_df.iterrows():
                        b    = r["_base"]
                        ops  = int(r.get("Operator_Count", 1))
                        if b not in seen:
                            seen[b] = len(groups)
                            groups.append({"base": b, "count": 1,
                                           "ops": ops, "zone": r.get("Zone","")})
                        else:
                            groups[seen[b]]["count"] += 1
                    return groups

                _rv_left  = _rv_all[_rv_all["Zone"] == "Left"]
                _rv_right = _rv_all[_rv_all["Zone"] == "Right"]
                _rv_other = _rv_all[~_rv_all["Zone"].isin(["Left","Right"])]

                _grp_left  = _rv_build_groups(_rv_left)
                _grp_right = _rv_build_groups(_rv_right)
                _grp_other = _rv_build_groups(_rv_other)

                # ── header strip ───────────────────────────────────────────
                _rv_total_mc  = len(_rv_all)
                _rv_total_ops = int(sum(
                    g["count"] * g["ops"]
                    for grps in (_grp_left, _grp_right, _grp_other)
                    for g in grps
                ))
                _rv_types = sum(1 for grps in (_grp_left, _grp_right, _grp_other)
                                for _ in grps)

                st.markdown(
                    f'<div style="background:{_rv_surf};border:1px solid {_rv_bord};'
                    f'border-radius:10px;padding:12px 20px;margin-bottom:16px;'
                    f'display:flex;justify-content:space-between;align-items:center;'
                    f'flex-wrap:wrap;gap:10px">'
                    f'<div>'
                    f'<div style="font-size:14px;font-weight:700;color:{_rv_txt}">'
                    f'{_area_title}</div>'
                    f'<div style="font-size:11px;color:{_rv_muted};margin-top:2px;'
                    f'font-family:JetBrains Mono,monospace">'
                    f'Resource capacity view · visualization only</div>'
                    f'</div>'
                    f'<div style="display:flex;gap:20px;align-items:center">'
                    f'<div style="text-align:center">'
                    f'<div style="font-size:24px;font-weight:700;color:{_rv_count_col}">'
                    f'{_rv_total_mc}</div>'
                    f'<div style="font-size:9px;color:{_rv_muted};'
                    f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                    f'TOTAL M/C</div></div>'
                    f'<div style="text-align:center">'
                    f'<div style="font-size:24px;font-weight:700;color:{_rv_ops_col}">'
                    f'{_rv_total_ops}</div>'
                    f'<div style="font-size:9px;color:{_rv_muted};'
                    f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                    f'OPERATORS NEEDED</div></div>'
                    f'<div style="text-align:center">'
                    f'<div style="font-size:24px;font-weight:700;color:{_rv_txt}">'
                    f'{_rv_types}</div>'
                    f'<div style="font-size:9px;color:{_rv_muted};'
                    f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                    f'M/C TYPES</div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True)

                # ── block renderer ─────────────────────────────────────────
                def _rv_render_block(g, accent):
                    """Return HTML for one resource block."""
                    _mc   = g["count"]
                    _base = g["base"]
                    _ops  = g["ops"]
                    _total_ops_g = _mc * _ops

                    # Clean the display name:
                    # If the name contains "Station" or "Area", strip the word "Machine"
                    # so "Assembly Machine Station" → "Assembly Station" etc.
                    import re as _re_rvb
                    _disp = _base
                    if _re_rvb.search(r'\b(Station|Area)\b', _disp, _re_rvb.IGNORECASE):
                        _disp = _re_rvb.sub(r'\bMachine\b\s*', '', _disp,
                                            flags=_re_rvb.IGNORECASE).strip()

                    # Choose the correct "For Each ___" label
                    if _re_rvb.search(r'\bStation\b', _base, _re_rvb.IGNORECASE):
                        _for_each_lbl = "For Each Station"
                    elif _re_rvb.search(r'\bArea\b', _base, _re_rvb.IGNORECASE):
                        _for_each_lbl = "For Each Area"
                    else:
                        _for_each_lbl = "For Each Machine"

                    # width of the count badge scales with count
                    _badge_w = "32px" if _mc < 10 else "40px"

                    return (
                        f'<div style="background:{_rv_block_bg};'
                        f'border:1px solid {_rv_bord};'
                        f'border-left:4px solid {accent};'
                        f'border-radius:8px;padding:12px 16px;'
                        f'display:flex;align-items:center;gap:14px;'
                        f'margin-bottom:6px">'
                        # count badge
                        f'<div style="background:{accent}22;border:1.5px solid {accent}55;'
                        f'border-radius:6px;min-width:{_badge_w};height:40px;'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'flex-shrink:0">'
                        f'<span style="font-size:18px;font-weight:800;color:{accent};'
                        f'font-family:JetBrains Mono,monospace;line-height:1">{_mc}</span>'
                        f'</div>'
                        # name + operators
                        f'<div style="flex:1;min-width:0">'
                        f'<div style="font-size:13px;font-weight:600;color:{_rv_txt};'
                        f'line-height:1.3;white-space:nowrap;overflow:hidden;'
                        f'text-overflow:ellipsis">'
                        f'{_disp}</div>'
                        f'<div style="font-size:11px;color:{_rv_muted};margin-top:4px;'
                        f'display:flex;align-items:center;gap:4px">'
                        f'<span style="font-size:14px">👷</span>'
                        f'<span style="font-weight:700;color:{_rv_ops_col};'
                        f'font-family:JetBrains Mono,monospace">{_ops}</span>'
                        f'<span style="color:{_rv_muted}">{_for_each_lbl}</span>'
                        f'</div></div>'
                        # total ops pill
                        f'<div style="flex-shrink:0;text-align:right">'
                        f'<div style="font-size:10px;color:{_rv_muted};'
                        f'font-family:JetBrains Mono,monospace">Total</div>'
                        f'<div style="font-size:14px;font-weight:700;'
                        f'color:{_rv_ops_col};font-family:JetBrains Mono,monospace">'
                        f'{_total_ops_g} 👷</div>'
                        f'</div>'
                        f'</div>')

                # ── lane renderer ──────────────────────────────────────────
                def _rv_render_lane(col_widget, groups, lane_label, accent):
                    with col_widget:
                        _lane_mc  = sum(g["count"] for g in groups)
                        _lane_ops = sum(g["count"] * g["ops"] for g in groups)
                        _lane_types = len(groups)

                        # Lane header
                        st.markdown(
                            f'<div style="background:{accent};border-radius:8px 8px 0 0;'
                            f'padding:10px 16px;display:flex;justify-content:space-between;'
                            f'align-items:center">'
                            f'<span style="font-size:11px;font-weight:700;color:white;'
                            f'font-family:JetBrains Mono,monospace;letter-spacing:.06em">'
                            f'{lane_label} PRODUCTION LINE</span>'
                            f'<span style="font-size:10px;color:rgba(255,255,255,0.85)">'
                            f'{_lane_mc} M/C &nbsp;·&nbsp; '
                            f'{_lane_types} types &nbsp;·&nbsp; '
                            f'{_lane_ops} ops</span>'
                            f'</div>',
                            unsafe_allow_html=True)

                        # Entrance marker
                        st.markdown(
                            f'<div style="background:{_rv_s2};'
                            f'border-left:2px solid {accent};'
                            f'border-right:2px solid {accent};'
                            f'padding:5px 16px;text-align:center;'
                            f'font-size:9px;color:{_rv_muted};'
                            f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                            f'▼ RM ENTRANCE</div>',
                            unsafe_allow_html=True)

                        if not groups:
                            st.markdown(
                                f'<div style="background:{_rv_surf};'
                                f'border-left:2px solid {accent};'
                                f'border-right:2px solid {accent};'
                                f'padding:20px;text-align:center;'
                                f'color:{_rv_muted};font-size:12px">'
                                f'No machines in this zone</div>',
                                unsafe_allow_html=True)
                        else:
                            # Wrap all blocks in a border container
                            blocks_html = "".join(
                                _rv_render_block(g, accent) for g in groups)
                            st.markdown(
                                f'<div style="border-left:2px solid {accent};'
                                f'border-right:2px solid {accent};'
                                f'padding:10px 10px 4px 10px">'
                                f'{blocks_html}</div>',
                                unsafe_allow_html=True)

                        # Exit marker
                        st.markdown(
                            f'<div style="background:{_rv_s2};'
                            f'border:2px solid {accent};border-top:none;'
                            f'border-radius:0 0 8px 8px;padding:5px 16px;'
                            f'text-align:center;font-size:9px;color:{_rv_muted};'
                            f'font-family:JetBrains Mono,monospace;letter-spacing:.08em">'
                            f'▲ FG EXIT</div>',
                            unsafe_allow_html=True)

                        # Lane summary footer
                        st.markdown(
                            f'<div style="background:{accent}11;'
                            f'border:1px solid {accent}33;'
                            f'border-radius:0 0 6px 6px;'
                            f'padding:6px 14px;margin-top:6px;'
                            f'display:flex;justify-content:space-between;'
                            f'font-size:10px;font-family:JetBrains Mono,monospace">'
                            f'<span style="color:{accent};font-weight:600">'
                            f'{_lane_mc} machines total</span>'
                            f'<span style="color:{_rv_ops_col};font-weight:600">'
                            f'{_lane_ops} operators required</span>'
                            f'</div>',
                            unsafe_allow_html=True)

                # ── render the two-column ribbon ───────────────────────────
                _rv_col_l, _rv_col_r = st.columns(2)
                _rv_render_lane(_rv_col_l, _grp_left,  "LEFT",  _rv_accent_l)
                _rv_render_lane(_rv_col_r, _grp_right, "RIGHT", _rv_accent_r)

                # ── other zones (not Left / Right) ─────────────────────────
                if _grp_other:
                    st.markdown(
                        f'<div style="font-size:9px;font-family:JetBrains Mono,monospace;'
                        f'letter-spacing:.1em;color:{_rv_muted};text-transform:uppercase;'
                        f'border-bottom:1px solid {_rv_bord};padding-bottom:6px;'
                        f'margin:18px 0 10px">OTHER ZONES</div>',
                        unsafe_allow_html=True)
                    _rv_col_o1, _rv_col_o2 = st.columns(2)
                    for _oi, _og in enumerate(_grp_other):
                        with (_rv_col_o1 if _oi % 2 == 0 else _rv_col_o2):
                            st.markdown(_rv_render_block(_og, "#6366f1"),
                                        unsafe_allow_html=True)

                # ── storage / zone entries ─────────────────────────────────
                if not _rv_zones_df.empty:
                    _chips = "".join(
                        f'<span style="background:{_rv_s2};border:1px solid {_rv_bord};'
                        f'border-radius:5px;padding:3px 10px;font-size:10px;'
                        f'color:{_rv_muted}">🗂 {_tr(r["Machine"])}</span>'
                        for _, r in _rv_zones_df.iterrows())
                    st.markdown(
                        f'<div style="font-size:9px;font-family:JetBrains Mono,monospace;'
                        f'letter-spacing:.08em;color:{_rv_muted};text-transform:uppercase;'
                        f'margin:16px 0 6px">Storage / Zone Areas</div>'
                        f'<div style="display:flex;flex-wrap:wrap;gap:5px">{_chips}</div>',
                        unsafe_allow_html=True)

                st.caption("🏗 Resource View · Similar machines grouped · "
                           "Shows machine count and manpower per type · "
                           "Visualization only — no live status")

            elif _is_exec:
                # ══════════════════════════════════════════════════════════════
                # EXECUTIVE VIEW — ETO factory process-zone dashboard
                # Machines grouped by production process (cutting, welding, etc.)
                # No left/right lines — organised by workshop/process type
                # Original AutoCAD layout remains accessible via AutoCAD Original
                # ══════════════════════════════════════════════════════════════
                import re as _re_ev

                _is_dark_ev   = st.session_state.theme == "dark"
                _ev_page_bg   = T["bg"]
                _ev_card_bg   = T["surface"]
                _ev_card_bg2  = T["surface2"]
                _ev_bord      = T["border"]
                _ev_txt       = T["text"]
                _ev_muted     = T["text_muted"]
                _ev_head_dark = "#0f172a" if _is_dark_ev else "#1e293b"
                _ev_head_sub  = "#475569" if _is_dark_ev else "#64748b"
                _ev_tag_ops   = ("#bfdbfe","#1e40af") if not _is_dark_ev else ("#1e3a5f","#93c5fd")

                # ── helpers ────────────────────────────────────────────────
                def _ev_base(name):
                    n = name.strip()
                    c = _re_ev.sub(r'[\s\-_]*[#]?\s*\d+\s*$', '', n).strip()
                    return c if c else n

                def _ev_dots(on, off, mnt, max_show=8):
                    """Return HTML coloured square dots (max_show per row)."""
                    dots = (["<span class='ed-on'></span>"] * on
                          + ["<span class='ed-off'></span>"] * off
                          + ["<span class='ed-mnt'></span>"] * mnt)
                    if len(dots) > max_show:
                        shown = dots[:max_show]
                        shown.append(f"<span class='ed-more'>+{len(dots)-max_show}</span>")
                        return "".join(shown)
                    return "".join(dots)

                def _ev_status_pill(on, off, mnt, total):
                    if off == 0 and mnt == 0:
                        return f'<span class="ep ep-on">All operational</span>'
                    parts = []
                    if off:  parts.append(f'{off} offline')
                    if mnt:  parts.append(f'{mnt} maint')
                    if on:   parts.append(f'{on} running')
                    return (f'<span class="ep ep-crit">{" · ".join(parts)}</span>'
                            if off > 0 else
                            f'<span class="ep ep-mnt">{" · ".join(parts)}</span>')

                # ── process zone definitions per area ──────────────────────
                # Groups: zone_display_name → list of base machine names
                _area_key_ev = AREAS[st.session_state.active_area]["key"]

                _EV_ZONE_DEFS = {
                    "F5_A1": [
                        ("Cutting & Sawing",
                         ["RASA Saw", "Manual Saw"]),
                        ("Drilling",
                         ["Drill"]),
                        ("Structural Welding",
                         ["Welding Machine"]),
                        ("Ledger Welding",
                         ["Leadgers Welding"]),
                        ("Vertical Forming",
                         ["Ring Vertical", "Cup Vertical"]),
                        ("Automated Welding",
                         ["Auto Welding"]),
                        ("Assembly & Sorting",
                         ["Assembly Station", "Production Sorting Area"]),
                    ],
                    "F5_A2": [
                        ("Hydraulic Pressing",
                         ["Mixer"]),
                        ("Cup Frame Pressing",
                         ["Cup Frame Form Mixer"]),
                        ("Drilling & Multi-Drill",
                         ["Drrill", "Drill", "Multi Drill"]),
                        ("Forming, Sawing & Tapping",
                         ["Form & Tap", "Forming", "Tap", "Saw"]),
                        ("Welding Cells",
                         ["Weld Cell"]),
                        ("Cup Welding",
                         ["Cup Weld"]),
                    ],
                    "F4_A1": [
                        ("Cutting & Sawing",
                         ["Manual Saw", "Auto Saw"]),
                        ("Punching & Pressing",
                         ["ECO Punch Press", "TECH Punch / Drill",
                          "ECO Punch + TECH Press", "Presses"]),
                        ("Welding",
                         ["Welding Package", "Welding Robot",
                          "Pre-Assembly Welding Robot", "Welding Station"]),
                        ("Frame Assembly",
                         ["9-Frame Assembly"]),
                        ("Finishing & QC",
                         ["Grinding", "Delivery / QC"]),
                    ],
                    "F4_A2": [
                        ("Cutting",
                         ["Saw Machine"]),
                        ("CNC Machining",
                         ["CNC Router Machine"]),
                        ("Assembly",
                         ["Manual Assembly Tools", "Pallet Assembly Spread"]),
                        ("Surface Coating",
                         ["Paint / Coating Station"]),
                    ],
                }

                _zone_defs = _EV_ZONE_DEFS.get(_area_key_ev, [])

                # ── assign machines to zones ───────────────────────────────
                _ev_all      = df_display[df_display["Status"] != "-"].copy()
                _ev_zones_df = df_display[df_display["Status"] == "-"]
                _ev_assigned = set()
                _ev_zone_data = {}   # zone_name → list of pd.Series rows

                for _zn, _zbases in _zone_defs:
                    _zmachines = []
                    for _, _zr in _ev_all.iterrows():
                        if _ev_base(_zr["Machine"]) in _zbases:
                            _zmachines.append(_zr)
                            _ev_assigned.add(_zr["Machine"])
                    if _zmachines:
                        _ev_zone_data[_zn] = _zmachines

                # unassigned machines → "Other Equipment" zone
                _ev_unassigned = [r for _, r in _ev_all.iterrows()
                                   if r["Machine"] not in _ev_assigned]
                if _ev_unassigned:
                    _ev_zone_data["Other Equipment"] = _ev_unassigned

                # ── overall KPI ────────────────────────────────────────────
                _ev_total = len(_ev_all)
                _ev_on    = int((_ev_all["Status"] == "ON").sum())
                _ev_off   = int((_ev_all["Status"] == "OFF").sum())
                _ev_mnt   = int((_ev_all["Status"] == "MAINTENANCE").sum())
                _ev_ops   = int(_ev_all["Operator_Count"].sum())
                _ev_upt   = round(_ev_on / max(_ev_total, 1) * 100)
                _ev_upc   = ("#4ade80" if _ev_upt>=70 else
                             "#fb923c" if _ev_upt>=40 else "#f87171")

                # ── find bottleneck zone (highest % offline) ───────────────
                _ev_bot_zone  = None
                _ev_bot_score = 0.0
                for _zn, _zrows in _ev_zone_data.items():
                    _zt = len(_zrows)
                    _zo = sum(1 for r in _zrows if str(r["Status"])=="OFF")
                    _zm = sum(1 for r in _zrows if str(r["Status"])=="MAINTENANCE")
                    _score = (_zo + _zm) / max(_zt, 1)
                    if _score > _ev_bot_score and (_zo + _zm) > 0:
                        _ev_bot_score = _score
                        _ev_bot_zone  = _zn

                # ── CSS ────────────────────────────────────────────────────
                _ev_css = f"""
<style>
.ev-wrap{{background:{_ev_page_bg};font-family:-apple-system,BlinkMacSystemFont,
  'Segoe UI',sans-serif;font-size:13px;color:{_ev_txt};border-radius:12px;
  overflow:hidden;border:1px solid {_ev_bord}}}
.ev-head{{background:{_ev_head_dark};color:#f1f5f9;padding:14px 20px;
  display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
.ev-head-left{{display:flex;flex-direction:column;gap:2px}}
.ev-area-name{{font-size:15px;font-weight:600;letter-spacing:.01em}}
.ev-area-sub{{font-size:9px;color:#94a3b8;letter-spacing:.1em;text-transform:uppercase}}
.ev-kpi-row{{display:flex;gap:16px;align-items:center}}
.ev-kpi{{text-align:center}}
.ev-kv{{font-size:19px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1}}
.ev-kl{{font-size:9px;letter-spacing:.06em;text-transform:uppercase;margin-top:2px;color:#64748b}}
.ev-sep{{width:1px;height:32px;background:#334155;flex-shrink:0}}
.ev-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;
  padding:14px;background:{_ev_page_bg}}}
.ev-card{{background:{_ev_card_bg};border:1px solid {_ev_bord};
  border-radius:10px;overflow:hidden}}
.ev-card-head{{background:{_ev_head_dark};padding:9px 14px;
  display:flex;justify-content:space-between;align-items:center;gap:8px}}
.ev-zone-name{{font-size:11px;font-weight:700;color:#f1f5f9;
  letter-spacing:.06em;text-transform:uppercase}}
.ev-zone-kpi{{font-size:10px;color:#94a3b8;white-space:nowrap}}
.ev-card-body{{padding:10px 12px}}
.ev-bot-badge{{font-size:9px;font-weight:700;color:#fff;background:#dc2626;
  border-radius:4px;padding:1px 7px;letter-spacing:.04em;white-space:nowrap;flex-shrink:0}}
.ev-mg{{border-radius:7px;border:1px solid {_ev_bord};padding:8px 10px;
  margin-bottom:6px;cursor:pointer;transition:box-shadow .12s}}
.ev-mg:hover{{box-shadow:0 2px 8px rgba(0,0,0,.1)}}
.ev-mg-on  {{border-left:4px solid #16a34a;background:{"#031a0c" if _is_dark_ev else "#f0fdf4"}}}
.ev-mg-off {{border-left:4px solid #dc2626;background:{"#1a0404" if _is_dark_ev else "#fff1f2"}}}
.ev-mg-mnt {{border-left:4px solid #d97706;background:{"#2a1a00" if _is_dark_ev else "#fffbeb"}}}
.ev-mg-part{{border-left:4px solid #f59e0b;background:{"#1a1200" if _is_dark_ev else "#fffbeb"}}}
.ev-mg-row1{{display:flex;justify-content:space-between;align-items:flex-start;
  gap:6px;margin-bottom:4px}}
.ev-mg-name{{font-size:12px;font-weight:600;color:{_ev_txt};line-height:1.25;flex:1;min-width:0}}
.ev-mg-cnt{{font-size:10px;font-weight:600;color:{_ev_muted};
  background:{_ev_card_bg2};border-radius:4px;padding:1px 6px;
  white-space:nowrap;flex-shrink:0}}
.dots-row{{display:flex;gap:3px;flex-wrap:wrap;margin:3px 0}}
.ed-on{{width:9px;height:9px;border-radius:2px;background:#16a34a;display:inline-block}}
.ed-off{{width:9px;height:9px;border-radius:2px;background:#dc2626;display:inline-block}}
.ed-mnt{{width:9px;height:9px;border-radius:2px;background:#d97706;display:inline-block}}
.ed-more{{font-size:9px;color:{_ev_muted};padding:0 2px;align-self:center}}
.ev-mg-row2{{display:flex;justify-content:space-between;align-items:center;
  gap:4px;margin-top:4px;flex-wrap:wrap}}
.ev-mg-stxt{{font-size:10px;color:{_ev_muted}}}
.ev-ops-pill{{font-size:10px;font-weight:500;color:{_ev_tag_ops[1]};
  background:{_ev_tag_ops[0]};border-radius:20px;padding:1px 8px;white-space:nowrap}}
.ep{{font-size:9px;font-weight:600;border-radius:4px;padding:1px 7px;letter-spacing:.04em}}
.ep-on  {{color:#14532d;background:{"#052e16" if _is_dark_ev else "#dcfce7"}}}
.ep-crit{{color:#fff;background:#dc2626}}
.ep-mnt {{color:#fff;background:#d97706}}
.ev-storage{{padding:10px 14px;border-top:1px solid {_ev_bord};
  background:{_ev_card_bg2}}}
.ev-chip{{display:inline-block;background:{_ev_card_bg};border:1px solid {_ev_bord};
  border-radius:5px;padding:3px 9px;font-size:10px;color:{_ev_muted};margin:2px}}
.ev-legend{{background:{_ev_card_bg};border-top:1px solid {_ev_bord};
  padding:8px 18px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}}
.ev-leg{{display:flex;align-items:center;gap:5px;font-size:11px;color:{_ev_muted}}}
.ev-ld{{width:13px;height:13px;border-radius:3px;flex-shrink:0}}
</style>"""

                # ── display name overrides ────────────────────────────────
                # "Mixer" in F5-A2 is a Hydraulic Press, not a mixing machine
                _EV_DISPLAY_NAMES = {
                    "Mixer":               "Hydraulic Press",
                    "Cup Frame Form Mixer": "Cup Frame Hydraulic Press",
                }
                def _ev_display(base_name):
                    return _EV_DISPLAY_NAMES.get(base_name, base_name)

                # ── build zone card HTML ───────────────────────────────────
                def _ev_zone_card(zname, zrows, is_bottleneck):
                    zt   = len(zrows)
                    z_on = sum(1 for r in zrows if str(r["Status"])=="ON")
                    z_off= sum(1 for r in zrows if str(r["Status"])=="OFF")
                    z_mnt= sum(1 for r in zrows if str(r["Status"])=="MAINTENANCE")
                    z_ops= sum(int(r.get("Operator_Count",0)) for r in zrows)
                    z_upt= round(z_on / max(zt, 1) * 100)
                    z_upc= ("#4ade80" if z_upt>=70 else
                            "#fb923c" if z_upt>=40 else "#f87171")

                    # machine groups by base name
                    _groups = {}
                    for r in zrows:
                        b = _ev_base(r["Machine"])
                        if b not in _groups:
                            _groups[b] = {"count":0,"on":0,"off":0,
                                          "mnt":0,"ops":0}
                        _groups[b]["count"] += 1
                        _groups[b]["ops"]   += int(r.get("Operator_Count",0))
                        st = str(r["Status"])
                        if st=="ON": _groups[b]["on"] += 1
                        elif st=="OFF": _groups[b]["off"] += 1
                        else: _groups[b]["mnt"] += 1

                    bot_html = ('<span class="ev-bot-badge">BOTTLENECK</span>'
                                if is_bottleneck else "")
                    kpi_txt  = (f'{z_on}/{zt} running'
                                if z_off+z_mnt > 0
                                else f'All {zt} operational')

                    blocks = ""
                    for gname, g in _groups.items():
                        gon  = g["on"]; goff = g["off"]; gmnt = g["mnt"]
                        gcnt = g["count"]; gops = g["ops"]
                        # block class
                        if goff > 0:    cls = "ev-mg-off" if gcnt==1 else "ev-mg-part"
                        elif gmnt > 0:  cls = "ev-mg-mnt"
                        else:           cls = "ev-mg-on"
                        if goff > 0 and gon == 0: cls = "ev-mg-off"

                        gname_disp = _tr(_ev_display(gname))
                        if len(gname_disp) > 24: gname_disp = gname_disp[:22] + "…"

                        cnt_badge = (f'<span class="ev-mg-cnt">×{gcnt}</span>'
                                     if gcnt > 1 else "")
                        dots_html = _ev_dots(gon, goff, gmnt)
                        st_parts  = []
                        if goff: st_parts.append(f'{goff} offline')
                        if gmnt: st_parts.append(f'{gmnt} maint')
                        if gon and (goff or gmnt): st_parts.append(f'{gon} running')
                        st_txt = " · ".join(st_parts) if st_parts else "Operational"

                        blocks += f"""
<div class="ev-mg {cls}">
  <div class="ev-mg-row1">
    <div class="ev-mg-name">{gname_disp}</div>{cnt_badge}
  </div>
  <div class="dots-row">{dots_html}</div>
  <div class="ev-mg-row2">
    <span class="ev-mg-stxt">{st_txt}</span>
    <span class="ev-ops-pill">👷 {gops}</span>
  </div>
</div>"""

                    return f"""
<div class="ev-card">
  <div class="ev-card-head">
    <span class="ev-zone-name">{zname}</span>
    <div style="display:flex;gap:6px;align-items:center">
      <span class="ev-zone-kpi">{kpi_txt} &nbsp;·&nbsp; 👷 {z_ops}</span>
      {bot_html}
    </div>
  </div>
  <div class="ev-card-body">{blocks}</div>
</div>"""

                # ── assemble full layout ───────────────────────────────────
                zone_cards_html = ""
                for _zn, _zrows in _ev_zone_data.items():
                    zone_cards_html += _ev_zone_card(
                        _zn, _zrows, _zn == _ev_bot_zone)

                _ev_upt_bar = (f'<span style="font-size:19px;font-weight:600;'
                               f'color:{_ev_upc}">{_ev_upt}%</span>')
                _ev_off_c   = "#f87171" if _ev_off > 0 else "#4ade80"

                # storage chips
                _ev_stor_html = ""
                if not _ev_zones_df.empty:
                    chips = "".join(
                        f'<span class="ev-chip">🗂 {_tr(r["Machine"])}</span>'
                        for _, r in _ev_zones_df.iterrows())
                    _ev_stor_html = (
                        f'<div class="ev-storage">'
                        f'<div style="font-size:9px;letter-spacing:.1em;'
                        f'text-transform:uppercase;color:{_ev_muted};'
                        f'font-weight:600;margin-bottom:6px">'
                        f'Storage & Zone Areas</div>'
                        f'{chips}</div>')

                _full_html = f"""
{_ev_css}
<div class="ev-wrap">
  <div class="ev-head">
    <div class="ev-head-left">
      <div class="ev-area-name">{_area_title}</div>
      <div class="ev-area-sub">Executive view &nbsp;·&nbsp; Process zone layout</div>
    </div>
    <div class="ev-kpi-row">
      <div class="ev-kpi">
        <div class="ev-kv" style="color:#e2e8f0">{_ev_total}</div>
        <div class="ev-kl">Machines</div>
      </div>
      <div class="ev-sep"></div>
      <div class="ev-kpi">
        <div class="ev-kv" style="color:#4ade80">{_ev_on}</div>
        <div class="ev-kl" style="color:#4ade80">Running</div>
      </div>
      <div class="ev-kpi">
        <div class="ev-kv" style="color:{_ev_off_c}">{_ev_off}</div>
        <div class="ev-kl" style="color:{_ev_off_c}">Offline</div>
      </div>
      <div class="ev-sep"></div>
      <div class="ev-kpi">
        <div class="ev-kv" style="color:#93c5fd">{_ev_ops}</div>
        <div class="ev-kl">Operators</div>
      </div>
      <div class="ev-kpi">
        <div class="ev-kv" style="color:{_ev_upc}">{_ev_upt}%</div>
        <div class="ev-kl">Uptime</div>
      </div>
    </div>
  </div>
  <div style="background:#dbeafe;border-bottom:2px solid #93c5fd;padding:7px 20px;
              text-align:center;font-size:10px;font-weight:700;color:#1d4ed8;
              letter-spacing:.12em">▼ RM ENTRANCE &nbsp;·&nbsp; RAW MATERIAL IN</div>
  <div class="ev-grid">{zone_cards_html}</div>
  {_ev_stor_html}
  <div style="background:#dcfce7;border-top:2px solid #86efac;padding:7px 20px;
              text-align:center;font-size:10px;font-weight:700;color:#15803d;
              letter-spacing:.12em">▲ FG EXIT &nbsp;·&nbsp; FINISHED GOODS OUT</div>
  <div class="ev-legend">
    <div class="ev-leg"><div class="ev-ld" style="background:#16a34a"></div>All operational</div>
    <div class="ev-leg"><div class="ev-ld" style="background:#f59e0b"></div>Partial — some offline</div>
    <div class="ev-leg"><div class="ev-ld" style="background:#dc2626"></div>Critical / all offline</div>
    <div class="ev-leg"><div class="ev-ld" style="background:#d97706"></div>Maintenance</div>
    <div style="display:flex;align-items:center;gap:4px;font-size:10px;
      background:#fee2e2;color:#991b1b;border-radius:4px;
      padding:2px 8px;font-weight:700">BOTTLENECK</div>
    <div style="margin-left:auto;font-size:10px;color:{_ev_muted}">
      Each ■ = 1 machine &nbsp;·&nbsp; Original AutoCAD layout: select "AutoCAD Original"
    </div>
  </div>
</div>"""

                # ── compute height for component iframe ────────────────
                _ev_n_zones  = len(_ev_zone_data)
                _ev_n_blocks = sum(
                    len({_ev_base(r["Machine"]) for r in rows})
                    for rows in _ev_zone_data.values()
                )
                _ev_height = (
                    90                                       # header
                    + 28                                     # grid padding
                    + ((_ev_n_zones + 1) // 2) * 62         # zone card headers per row
                    + _ev_n_blocks * 74                      # machine blocks
                    + (60 if not _ev_zones_df.empty else 0)  # storage row
                    + 56                                     # legend
                    + 60                                     # buffer
                )

                # ── wrap in full HTML document for component ──────────────
                _ev_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:{_ev_page_bg}">
{_ev_css}
{_full_html}
</body></html>"""

                import streamlit.components.v1 as _cmp_ev
                _cmp_ev.html(_ev_doc, height=_ev_height, scrolling=False)
                st.caption("🏭 Executive View · Process zones · ETO factory layout · "
                           "AutoCAD Original remains available in the layout selector")

            elif _is_exec_layout:
                # ══════════════════════════════════════════════════════════════
                # EXECUTIVE LAYOUT VIEW
                # Zone heights are 100% dynamic — calculated from actual machine
                # counts so content never clips. RM/FG gates centred on wall.
                # ══════════════════════════════════════════════════════════════
                import re as _re_el

                _ak_el = AREAS[st.session_state.active_area]["key"]
                _mc_el = df_display[df_display["Status"] != "-"]

                # ── abbreviation map ──────────────────────────────────────────
                _AB = {
                    "RASA Saw":"RASA","Manual Saw":"SAW","Auto Saw":"ASAW",
                    "Leadgers Welding":"LW","Welding Machine":"WM",
                    "Ring Vertical":"RV","Cup Vertical":"CV",
                    "Auto Welding":"AUTO","Assembly Station":"ASSY",
                    "Production Sorting Area":"SORT","Drill":"DR",
                    "Drrill":"DRL","Multi Drill":"MDR","Weld Cell":"WC",
                    "Cup Weld":"CW","Mixer":"HP","Cup Frame Form Mixer":"CFHP",
                    "Form & Tap":"F&T","Forming":"FRM","Tap":"TAP","Saw":"SAW",
                    "ECO Punch Press":"EPP","TECH Punch / Drill":"TPD",
                    "ECO Punch + TECH Press":"EP+TP","Presses":"PRS",
                    "Welding Package":"WP","Pre-Assembly Welding Robot":"PAWR",
                    "Welding Robot":"WR","Welding Station":"WS",
                    "9-Frame Assembly":"9FA","Grinding":"GRND",
                    "Delivery / QC":"QC","Saw Machine":"SAW",
                    "CNC Router Machine":"CNC","Manual Assembly Tools":"MAT",
                    "Pallet Assembly Spread":"PAS","Paint / Coating Station":"COAT",
                }
                def _el_base(n):
                    c = _re_el.sub(r'[\s\-_]*[#]?\s*\d+\s*$','',n.strip()).strip()
                    return c if c else n.strip()
                def _el_abbr(n):
                    b = _el_base(n)
                    ab = _AB.get(b, n[:4].upper())
                    m  = _re_el.search(r'\d+$', n.strip())
                    return f"{ab}{m.group()}" if m else ab
                def _el_clr(s):
                    return {"ON":"#16a34a","OFF":"#dc2626",
                            "MAINTENANCE":"#d97706"}.get(str(s).strip(),"#888888")
                def _el_get(bases):
                    r = []
                    for _, row in _mc_el.iterrows():
                        b = _el_base(row["Machine"])
                        if b in bases:
                            r.append({"a":_el_abbr(row["Machine"]),
                                      "b": b,
                                      "n": str(row["Machine"]).strip(),  # full name for tooltip
                                      "s":str(row["Status"]).strip(),
                                      "o":int(row.get("Operator_Count",0)),
                                      "nm": b in _EL_NON_MACHINES})
                    return r

                # ── non-machine work areas (white box, no icon) ──────────────
                _EL_NON_MACHINES = {
                    "Assembly Station","Production Sorting Area",
                    "9-Frame Assembly","Delivery / QC",
                    "Manual Assembly Tools","Pallet Assembly Spread",
                }

                # ── machine → icon type ───────────────────────────────────────
                _EL_IMAP = {
                    "Welding Machine":"weld","Leadgers Welding":"weld",
                    "Weld Cell":"weld","Cup Weld":"weld",
                    "Welding Package":"weld","Welding Station":"weld",
                    "Welding Robot":"robot","Pre-Assembly Welding Robot":"robot",
                    "Auto Welding":"robot",
                    "RASA Saw":"saw","Manual Saw":"saw","Auto Saw":"saw",
                    "Saw Machine":"saw","Saw":"saw","Grinding":"saw",
                    "Drill":"drill","Drrill":"drill","Multi Drill":"drill",
                    "CNC Router Machine":"drill","TECH Punch / Drill":"drill",
                    "Tap":"drill",
                    "Mixer":"press","Cup Frame Form Mixer":"press",
                    "Presses":"press","ECO Punch Press":"press",
                    "ECO Punch + TECH Press":"press","Ring Vertical":"press",
                    "Cup Vertical":"press","Form & Tap":"press","Forming":"press",
                }
                def _el_itype(b): return _EL_IMAP.get(b,"weld")

                # ── status colour palette ─────────────────────────────────────
                def _el_cmap(s):
                    if s=="ON":   return {"f":"#EAF3DE","p":"#C0DD97","s":"#3B6D11","d":"#639922"}
                    if s=="OFF":  return {"f":"#FCEBEB","p":"#F7C1C1","s":"#791F1F","d":"#A32D2D"}
                    return             {"f":"#FAEEDA","p":"#FAC775","s":"#633806","d":"#854F0B"}

                def _el_wclr(s):
                    if s=="ON":   return "#EAF3DE","#3B6D11","#173404"
                    if s=="OFF":  return "#FCEBEB","#791F1F","#501313"
                    return             "#FAEEDA","#633806","#412402"

                # ── machine icon SVG builders (52×55 canvas at bx, by) ────────
                def _icon_weld(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+12}" width="24" height="32" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.6"/>'
                        f'<rect x="{bx+8}" y="{by+17}" width="16" height="7" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width="0.9"/>'
                        f'<rect x="{bx+9}" y="{by+19}" width="10" height="4" rx="0.5" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="0.7"/>'
                        f'<rect x="{bx+8}" y="{by+27}" width="16" height="12" rx="1" fill="none" stroke="{c["d"]}" stroke-width="0.7"/>'
                        f'<circle cx="{bx+16}" cy="{by+33}" r="5" fill="none" stroke="{c["s"]}" stroke-width="1.1"/>'
                        f'<circle cx="{bx+16}" cy="{by+33}" r="1.5" fill="{c["s"]}"/>'
                        f'<circle cx="{bx+5}" cy="{by+21}" r="2.5" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="0.9"/>'
                        f'<rect x="{bx+4}" y="{by+43}" width="24" height="3.5" rx="1" fill="{c["s"]}" opacity="0.25"/>'
                        f'<circle cx="{bx+10}" cy="{by+47}" r="3.5" fill="none" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<circle cx="{bx+22}" cy="{by+47}" r="3.5" fill="none" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<path d="M {bx+28} {by+20} Q {bx+36} {by+16} {bx+42} {by+9}" fill="none" stroke="{c["d"]}" stroke-width="1.6" stroke-linecap="round"/>'
                        f'<ellipse cx="{bx+43}" cy="{by+8}" rx="5" ry="3" fill="{c["s"]}" transform="rotate(-30 {bx+43} {by+8})"/>'
                    )
                def _icon_saw(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+25}" width="44" height="8" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+6}" y="{by+33}" width="10" height="18" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+36}" y="{by+33}" width="10" height="18" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+16}" y="{by+33}" width="20" height="10" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width="1.1"/>'
                        f'<circle cx="{bx+26}" cy="{by+27}" r="14" fill="none" stroke="{c["s"]}" stroke-width="2"/>'
                        f'<circle cx="{bx+26}" cy="{by+27}" r="3.5" fill="{c["s"]}"/>'
                        f'<line x1="{bx+26}" y1="{by+13}" x2="{bx+26}" y2="{by+27}" stroke="{c["d"]}" stroke-width="0.8"/>'
                        f'<line x1="{bx+14}" y1="{by+20}" x2="{bx+26}" y2="{by+27}" stroke="{c["d"]}" stroke-width="0.8"/>'
                        f'<line x1="{bx+38}" y1="{by+20}" x2="{bx+26}" y2="{by+27}" stroke="{c["d"]}" stroke-width="0.8"/>'
                        f'<path d="M {bx+12} {by+24} Q {bx+26} {by+14} {bx+40} {by+24}" fill="none" stroke="{c["s"]}" stroke-width="1.5"/>'
                    )
                def _icon_drill(bx,by,c):
                    return (
                        f'<rect x="{bx+22}" y="{by+4}" width="8" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+9}" y="{by+6}" width="34" height="10" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+14}" y="{by+16}" width="24" height="15" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<polygon points="{bx+19},{by+31} {bx+33},{by+31} {bx+26},{by+47}" fill="{c["s"]}"/>'
                        f'<rect x="{bx+8}" y="{by+40}" width="36" height="6" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+34}" y1="{by+17}" x2="{bx+36}" y2="{by+23}" stroke="{c["d"]}" stroke-width="1"/>'
                    )
                def _icon_press(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+4}" width="9" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+39}" y="{by+4}" width="9" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+4}" y="{by+4}" width="44" height="9" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+4}" y="{by+45}" width="44" height="9" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+18}" y="{by+13}" width="16" height="18" rx="4" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+21}" y="{by+31}" width="10" height="15" rx="1" fill="{c["s"]}"/>'
                        f'<line x1="{bx+21}" y1="{by+18}" x2="{bx+31}" y2="{by+18}" stroke="{c["d"]}" stroke-width="0.75"/>'
                        f'<line x1="{bx+21}" y1="{by+22}" x2="{bx+31}" y2="{by+22}" stroke="{c["d"]}" stroke-width="0.75"/>'
                        f'<line x1="{bx+21}" y1="{by+26}" x2="{bx+31}" y2="{by+26}" stroke="{c["d"]}" stroke-width="0.75"/>'
                    )
                def _icon_assy(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+30}" width="44" height="8" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+6}" y="{by+38}" width="8" height="18" rx="1" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+38}" y="{by+38}" width="8" height="18" rx="1" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+14}" y="{by+17}" width="24" height="15" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<line x1="{bx+4}" y1="{by+25}" x2="{bx+14}" y2="{by+25}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+4}" y1="{by+25}" x2="{bx+4}" y2="{by+30}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+38}" y1="{by+25}" x2="{bx+48}" y2="{by+25}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+48}" y1="{by+25}" x2="{bx+48}" y2="{by+30}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<rect x="{bx+19}" y="{by+21}" width="14" height="7" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width="0.8"/>'
                    )
                def _icon_robot(bx,by,c):
                    return (
                        f'<rect x="{bx+10}" y="{by+48}" width="32" height="7" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<ellipse cx="{bx+26}" cy="{by+46}" rx="12" ry="6" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<rect x="{bx+23}" y="{by+24}" width="6" height="24" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<circle cx="{bx+26}" cy="{by+24}" r="4.5" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<rect x="{bx+26}" y="{by+10}" width="6" height="16" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5" transform="rotate(28 {bx+29} {by+24})"/>'
                        f'<circle cx="{bx+37}" cy="{by+13}" r="5" fill="{c["s"]}"/>'
                        f'<line x1="{bx+37}" y1="{by+8}" x2="{bx+41}" y2="{by+4}" stroke="{c["s"]}" stroke-width="2.5" stroke-linecap="round"/>'
                    )
                _ICON_FN = {
                    "weld":_icon_weld,"saw":_icon_saw,"drill":_icon_drill,
                    "press":_icon_press,"assy":_icon_assy,"robot":_icon_robot,
                }

                # ── worker circles: one per operator, colour follows status ───
                def _el_wcircles(n_ops, cx, cy, wf, ws, wp):
                    if n_ops <= 0: return ""
                    show = min(n_ops, 4)
                    r = 7.5; gap = 17
                    sx = cx - (show * gap) // 2 + r
                    svg = ""
                    for i in range(show):
                        px = int(sx + i * gap); py = cy
                        if i == 3 and n_ops > 4:
                            svg += (f'<circle cx="{px}" cy="{py}" r="{r}" fill="{ws}"/>'
                                    f'<text x="{px}" y="{py}" font-size="7" text-anchor="middle"'
                                    f' fill="white" font-family="Arial" font-weight="700"'
                                    f' dominant-baseline="central">+{n_ops-3}</text>')
                        else:
                            svg += (f'<circle cx="{px}" cy="{py}" r="{r}"'
                                    f' fill="{wf}" stroke="{ws}" stroke-width="1.2"/>'
                                    f'<circle cx="{px}" cy="{py-2.5}" r="2.2" fill="{wp}"/>'
                                    f'<rect x="{px-2.2}" y="{py}" width="4.4"'
                                    f' height="4" rx="1" fill="{wp}"/>')
                    return svg

                # ── layout constants ──────────────────────────────────────────
                _EL_IW   = 52    # icon canvas width
                _EL_IH   = 55    # icon canvas height
                _EL_WCR  = 7.5   # worker circle radius
                # Total height per machine unit: icon + abbrev label + circles
                _EL_UNIT = _EL_IH + 8 + 10 + 6 + int(_EL_WCR * 2)   # ≈ 94

                def _el_zone_h(n, zw, storage=False):
                    """Zone height sized for front-elevation icons + worker circles."""
                    if storage or n == 0:
                        return 130
                    cols = min(3, max(1, (zw - 16) // (_EL_IW + 10)))
                    rows = (n + cols - 1) // cols
                    return max(130, 48 + rows * (_EL_UNIT + 10) + 40 + 14)

                # ── non-machine dedicated icons (neutral gray palette) ────────
                def _nm_icon(b, bx, by):
                    """Dedicated front-elevation SVG for each non-machine work area type."""
                    _f="#e4e4e4"; _s="#555"; _d="#c4c4c4"; _h="#888"
                    bl = b.lower()
                    if "assembly" in bl and "9" not in bl and "pallet" not in bl and "manual" not in bl:
                        # Workbench with bench vice
                        return (
                            f'<rect x="{bx+4}" y="{by+19}" width="44" height="6" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<rect x="{bx+8}" y="{by+25}" width="6" height="24" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+38}" y="{by+25}" width="6" height="24" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+8}" y="{by+38}" width="36" height="4" rx="1" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<rect x="{bx+18}" y="{by+10}" width="18" height="10" rx="1.5" fill="{_d}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<line x1="{bx+36}" y1="{by+15}" x2="{bx+47}" y2="{by+15}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<circle cx="{bx+47}" cy="{by+15}" r="3" fill="none" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+6}" y="{by+11}" width="9" height="8" rx="1" fill="{_d}" stroke="{_s}" stroke-width=".9"/>'
                        )
                    elif "sort" in bl:
                        # Sorting table with labeled bins
                        return (
                            f'<rect x="{bx+3}" y="{by+21}" width="46" height="5" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<rect x="{bx+6}" y="{by+26}" width="5" height="22" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+41}" y="{by+26}" width="5" height="22" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+4}" y="{by+5}" width="14" height="17" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<rect x="{bx+20}" y="{by+5}" width="12" height="17" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<rect x="{bx+34}" y="{by+5}" width="14" height="17" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<text x="{bx+11}" y="{by+15}" font-size="6.5" text-anchor="middle" fill="{_h}" font-family="Arial" dominant-baseline="central">A</text>'
                            f'<text x="{bx+26}" y="{by+15}" font-size="6.5" text-anchor="middle" fill="{_h}" font-family="Arial" dominant-baseline="central">B</text>'
                            f'<text x="{bx+41}" y="{by+15}" font-size="6.5" text-anchor="middle" fill="{_h}" font-family="Arial" dominant-baseline="central">C</text>'
                        )
                    elif "9" in bl and "frame" in bl:
                        # 9-Frame rack with slot frames
                        return (
                            f'<rect x="{bx+4}" y="{by+4}" width="6" height="50" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<rect x="{bx+42}" y="{by+4}" width="6" height="50" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<rect x="{bx+10}" y="{by+6}" width="32" height="12" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<rect x="{bx+10}" y="{by+22}" width="32" height="12" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<rect x="{bx+10}" y="{by+38}" width="32" height="12" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<rect x="{bx+14}" y="{by+8}" width="24" height="8" rx=".7" fill="none" stroke="{_h}" stroke-width="1"/>'
                            f'<rect x="{bx+14}" y="{by+24}" width="24" height="8" rx=".7" fill="none" stroke="{_h}" stroke-width="1"/>'
                            f'<rect x="{bx+14}" y="{by+40}" width="24" height="8" rx=".7" fill="none" stroke="{_h}" stroke-width="1"/>'
                        )
                    elif "qc" in bl or "delivery" in bl:
                        # QC / inspection station with magnifier + checkmark
                        return (
                            f'<rect x="{bx+3}" y="{by+26}" width="46" height="6" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<rect x="{bx+7}" y="{by+32}" width="5" height="20" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+40}" y="{by+32}" width="5" height="20" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<circle cx="{bx+21}" cy="{by+14}" r="10" fill="none" stroke="{_s}" stroke-width="1.9"/>'
                            f'<circle cx="{bx+21}" cy="{by+14}" r="6" fill="#d4eedb" stroke="{_s}" stroke-width=".9"/>'
                            f'<line x1="{bx+29}" y1="{by+21}" x2="{bx+37}" y2="{by+29}" stroke="{_s}" stroke-width="3" stroke-linecap="round"/>'
                            f'<polyline points="{bx+17},{by+14} {bx+20},{by+17} {bx+25},{by+11}" fill="none" stroke="#22c55e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
                        )
                    elif "manual" in bl or "tool" in bl:
                        # Tool pegboard with hanging tools
                        return (
                            f'<rect x="{bx+3}" y="{by+3}" width="46" height="52" rx="2.5" fill="#e8e0cc" stroke="{_s}" stroke-width="1.5"/>'
                            f'<path d="M{bx+13} {by+14} L{bx+15} {by+30}" stroke="{_s}" stroke-width="3" stroke-linecap="round"/>'
                            f'<ellipse cx="{bx+13}" cy="{by+13}" rx="3.5" ry="3" fill="none" stroke="{_s}" stroke-width="1.6"/>'
                            f'<rect x="{bx+24}" y="{by+9}" width="7" height="5" rx="1" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                            f'<line x1="{bx+27}" y1="{by+14}" x2="{bx+27}" y2="{by+30}" stroke="{_s}" stroke-width="2.8" stroke-linecap="round"/>'
                            f'<line x1="{bx+39}" y1="{by+11}" x2="{bx+39}" y2="{by+30}" stroke="{_s}" stroke-width="2.2" stroke-linecap="round"/>'
                            f'<rect x="{bx+36}" y="{by+9}" width="6" height="4" rx=".5" fill="{_d}" stroke="{_s}" stroke-width=".9"/>'
                            f'<rect x="{bx+6}" y="{by+36}" width="40" height="14" rx="1.5" fill="{_d}" stroke="{_s}" stroke-width="1.2"/>'
                        )
                    elif "pallet" in bl:
                        # Wooden pallet with stacked boxes
                        return (
                            f'<rect x="{bx+4}" y="{by+18}" width="44" height="7" rx="1" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.5"/>'
                            f'<line x1="{bx+19}" y1="{by+18}" x2="{bx+19}" y2="{by+25}" stroke="#7b5e3a" stroke-width="1"/>'
                            f'<line x1="{bx+33}" y1="{by+18}" x2="{bx+33}" y2="{by+25}" stroke="#7b5e3a" stroke-width="1"/>'
                            f'<rect x="{bx+5}" y="{by+25}" width="10" height="10" rx=".5" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.1"/>'
                            f'<rect x="{bx+21}" y="{by+25}" width="10" height="10" rx=".5" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.1"/>'
                            f'<rect x="{bx+37}" y="{by+25}" width="10" height="10" rx=".5" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.1"/>'
                            f'<rect x="{bx+4}" y="{by+35}" width="44" height="5" rx="1" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.1"/>'
                            f'<rect x="{bx+8}" y="{by+4}" width="14" height="14" rx="1.5" fill="#c0d8f0" stroke="#5580a8" stroke-width="1.2"/>'
                            f'<rect x="{bx+24}" y="{by+4}" width="20" height="14" rx="1.5" fill="#c0d8f0" stroke="#5580a8" stroke-width="1.2"/>'
                            f'<rect x="{bx+12}" y="{by+6}" width="28" height="10" rx="1" fill="#b0c8e0" stroke="#5580a8" stroke-width="1"/>'
                        )
                    else:
                        # Generic workstation (computer terminal on desk)
                        return (
                            f'<rect x="{bx+5}" y="{by+22}" width="42" height="7" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                            f'<rect x="{bx+9}" y="{by+29}" width="5" height="22" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+38}" y="{by+29}" width="5" height="22" rx="1" fill="{_f}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+12}" y="{by+6}" width="28" height="17" rx="2" fill="{_d}" stroke="{_s}" stroke-width="1.2"/>'
                            f'<rect x="{bx+15}" y="{by+9}" width="22" height="11" rx="1" fill="#b0c0d4" stroke="{_s}" stroke-width=".8"/>'
                            f'<rect x="{bx+20}" y="{by+23}" width="12" height="3" rx=".5" fill="{_d}" stroke="{_s}" stroke-width=".8"/>'
                        )

                # ── machine icons + worker circles per zone ───────────────────
                def _el_boxes(ml, zx, zy, zw):
                    if not ml: return ""
                    _IW=_EL_IW; _IH=_EL_IH; _GAP_X=10; _GAP_Y=10
                    cols = min(3, max(1, (zw - 16) // (_IW + _GAP_X)))
                    row_w = cols * _IW + (cols - 1) * _GAP_X
                    sx = zx + max(8, (zw - row_w) // 2)
                    svg = ""
                    for i, m in enumerate(ml):
                        col = i % cols; row_i = i // cols
                        bx = int(sx + col * (_IW + _GAP_X))
                        by = int(zy + 48 + row_i * (_EL_UNIT + _GAP_Y))
                        # ── <g> wrapper for hover tooltip ──────────────────────
                        _mn = m.get("n", m.get("b","")).replace('"',"'")
                        _ms = m["s"] if not m.get("nm") else "WORK AREA"
                        _mo = m.get("o",0)
                        svg += f'<g data-mname="{_mn}" data-mstatus="{_ms}" data-mops="{_mo}" style="cursor:pointer">'
                        if m.get("nm"):
                            # Dedicated non-machine work-area icon + label
                            svg += _nm_icon(m.get("b",""), bx, by)
                            svg += (f'<text x="{bx+_IW//2}" y="{by+_IH+9}" font-size="8"'
                                    f' text-anchor="middle" fill="#666"'
                                    f' font-family="Arial" dominant-baseline="central"'
                                    f' font-style="italic">{m["a"]}</text>')
                        else:
                            c = _el_cmap(m["s"])
                            fn = _ICON_FN.get(_el_itype(m.get("b","")), _icon_weld)
                            svg += fn(bx, by, c)
                            # Abbreviation label below icon
                            svg += (f'<text x="{bx+_IW//2}" y="{by+_IH+9}" font-size="8"'
                                    f' text-anchor="middle" fill="#444"'
                                    f' font-family="Arial" dominant-baseline="central">'
                                    f'{m["a"]}</text>')
                            # Worker circles below label
                            n_ops = m.get("o", 0)
                            if n_ops > 0:
                                wf, ws, wp = _el_wclr(m["s"])
                                wcx = bx + _IW // 2
                                wcy = int(by + _IH + 8 + 10 + 6 + int(_EL_WCR))
                                svg += _el_wcircles(n_ops, wcx, wcy, wf, ws, wp)
                        svg += '</g>'  # close tooltip <g> wrapper
                    return svg

                def _el_stats(ml, zx, zy, zw):
                    if not ml: return ""
                    n   = len(ml)
                    ops = sum(m["o"] for m in ml)
                    cols = min(3, max(1, (zw - 16) // (_EL_IW + 10)))
                    rows = (n + cols - 1) // cols
                    sy  = zy + 48 + rows * (_EL_UNIT + 10) + 10
                    cx  = zx + zw // 2
                    _all_nm = all(m.get("nm") for m in ml)
                    if _all_nm:
                        return (f'<text x="{cx}" y="{sy}" font-size="8.5" text-anchor="middle"'
                                f' fill="#555" font-family="Arial">'
                                f'Work Area  \u00b7  {ops} operators</text>')
                    on  = sum(1 for m in ml if m["s"]=="ON"  and not m.get("nm"))
                    off = sum(1 for m in ml if m["s"]=="OFF" and not m.get("nm"))
                    mc  = sum(1 for m in ml if not m.get("nm"))
                    return (f'<text x="{cx}" y="{sy}" font-size="8.5" text-anchor="middle"'
                            f' fill="#333" font-family="Arial">'
                            f'{mc} M/C  \u00b7  {ops} operators</text>'
                            f'<text x="{cx}" y="{sy+16}" font-size="8.5" text-anchor="middle"'
                            f' fill="#666" font-family="Arial">'
                            f'{on} Running  \u00b7  {off} Offline</text>')

                def _el_zone_svg(name, sub, ml, zx, zy, zw, zh, storage=False):
                    fill="url(#el_dots)" if storage else "white"
                    cx=zx+zw//2
                    svg=(f'<rect x="{zx}" y="{zy}" width="{zw}" height="{zh}"'
                         f' fill="{fill}" stroke="#000" stroke-width="1.8"/>')
                    svg+=(f'<text x="{cx}" y="{zy+18}" font-size="10"'
                          f' font-weight="700" text-anchor="middle" fill="#000"'
                          f' font-family="Arial" letter-spacing=".4">{name}</text>')
                    if sub:
                        svg+=(f'<text x="{cx}" y="{zy+32}" font-size="7.5"'
                              f' text-anchor="middle" fill="#666"'
                              f' font-family="Arial">{sub}</text>')
                    if storage:
                        svg+=(f'<text x="{cx}" y="{zy+78}" font-size="8"'
                              f' text-anchor="middle" fill="#aaa"'
                              f' font-family="Arial" font-style="italic">'
                              f'No machines</text>')
                    svg+=_el_boxes(ml,zx,zy,zw)
                    svg+=_el_stats(ml,zx,zy,zw)
                    return svg

                # ── zone structure per area ───────────────────────────────────
                _ZS = {
                  "F5_A1": {
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("CUTTING & SAWING","RASA Saw \u00b7 Manual Saw \u00d72",
                          ["RASA Saw","Manual Saw"],False),
                    "left":[
                        ("LEDGER WELDING","Ledger Welding Station \u00d76",
                         ["Leadgers Welding"],False),
                        ("VERTICAL FORMING","Ring Vert. \u00d73 \u00b7 Cup Vert. \u00d74",
                         ["Ring Vertical","Cup Vertical"],False),
                    ],
                    "right":[
                        ("STRUCTURAL WELDING","Welding Machine \u00d75",
                         ["Welding Machine"],False),
                        ("ASSEMBLY","Assembly Station \u00b7 Sorting \u00d71",
                         ["Assembly Station"],False),
                        ("DRILLING","Drill \u00d72",["Drill"],False),
                    ],
                    "bl":("AUTO WELDING","",["Auto Welding"],False),
                    "br":("PROD. SORTING","",["Production Sorting Area"],False),
                  },
                  "F5_A2": {
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("DRILLING",
                          "Drrill \u00d73 \u00b7 Drill \u00d76 \u00b7 Multi Drill",
                          ["Drrill","Drill","Multi Drill"],False),
                    "left":[
                        ("HYDRAULIC PRESSING","Hydraulic Press \u00d76",
                         ["Mixer"],False),
                        ("WELDING CELLS","Weld Cell \u00d76",["Weld Cell"],False),
                    ],
                    "right":[
                        ("CUP FRAME PRESSING","Cup Frame Press \u00d72",
                         ["Cup Frame Form Mixer"],False),
                        ("CUP WELDING","Cup Weld \u00d72",["Cup Weld"],False),
                        ("FORMING & TAPPING",
                         "Form & Tap \u00b7 Forming \u00b7 Saw \u00b7 Tap",
                         ["Form & Tap","Forming","Saw","Tap"],False),
                    ],
                    "bl":("SORTING","",[], True),
                    "br":("OUTBOUND","",[], True),
                  },
                  "F4_A1": {
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("CUTTING & SAWING",
                          "Manual Saw \u00d72 \u00b7 Auto Saw \u00d71",
                          ["Manual Saw","Auto Saw"],False),
                    "left":[
                        ("PUNCHING & PRESSING",
                         "ECO Punch \u00b7 TECH Press \u00b7 Presses",
                         ["ECO Punch Press","TECH Punch / Drill",
                          "ECO Punch + TECH Press","Presses"],False),
                        ("FRAME ASSEMBLY","9-Frame Assembly",
                         ["9-Frame Assembly"],False),
                    ],
                    "right":[
                        ("WELDING","Pkg \u00b7 Robot \u00b7 Pre-Assy \u00b7 Station",
                         ["Welding Package","Pre-Assembly Welding Robot",
                          "Welding Robot","Welding Station"],False),
                        ("FINISHING & QC","Grinding \u00b7 Delivery / QC",
                         ["Grinding","Delivery / QC"],False),
                    ],
                    "bl":("STAGING","",[], True),
                    "br":("OUTBOUND","",[], True),
                  },
                  "F4_A2": {
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("CUTTING","Saw Machine \u00d71",["Saw Machine"],False),
                    "left":[
                        ("ASSEMBLY","Manual Assy \u00b7 Pallet Assembly",
                         ["Manual Assembly Tools","Pallet Assembly Spread"],False),
                    ],
                    "right":[
                        ("CNC MACHINING","CNC Router Machine \u00d71",
                         ["CNC Router Machine"],False),
                        ("SURFACE COATING","Paint / Coating Station \u00d71",
                         ["Paint / Coating Station"],False),
                    ],
                    "bl":("WIP STORAGE","",[], True),
                    "br":("OUTBOUND","",[], True),
                  },
                }

                _zs = _ZS.get(_ak_el, _ZS["F5_A1"])

                # ── machine lists ─────────────────────────────────────────────
                _tr_ml    = _el_get(_zs["tr"][2])
                _left_mls = [_el_get(z[2]) for z in _zs["left"]]
                _right_mls= [_el_get(z[2]) for z in _zs["right"]]
                _bl_ml    = _el_get(_zs["bl"][2])
                _br_ml    = _el_get(_zs["br"][2])

                # ── layout constants ──────────────────────────────────────────
                _FX=52; _FY=88
                _LW=240; _CW=25; _RW=365   # left / cross-aisle / right widths
                _FW=_LW+_CW+_RW            # = 630
                _AIL=22                     # aisle band height
                _FGH=50                     # FG exit band height
                _bl_w=195; _br_w=_FW-_bl_w # bottom zone widths (moved up)

                # ── compute dynamic heights ───────────────────────────────────
                _top_h  = max(120, _el_zone_h(len(_tr_ml), _RW, _zs["tr"][3]))
                _lhs    = [_el_zone_h(len(m), _LW, z[3])
                           for m,z in zip(_left_mls,  _zs["left"])]
                _rhs    = [_el_zone_h(len(m), _RW, z[3])
                           for m,z in zip(_right_mls, _zs["right"])]

                _mid_l = sum(_lhs); _mid_r = sum(_rhs)
                _mid_h = max(_mid_l, _mid_r, 100)

                # Stretch the shorter column's last zone to fill total mid height
                if _lhs and _mid_l < _mid_h:
                    _lhs[-1] += _mid_h - _mid_l
                if _rhs and _mid_r < _mid_h:
                    _rhs[-1] += _mid_h - _mid_r

                # Bottom zone height — fully dynamic, never hardcoded
                _BOT = max(
                    _el_zone_h(len(_bl_ml), _bl_w, _zs["bl"][3]),
                    _el_zone_h(len(_br_ml), _br_w, _zs["br"][3]),
                    100
                )
                _FH  = _top_h + _AIL + _mid_h + _AIL + _BOT + _FGH

                # ── absolute zone positions ───────────────────────────────────
                _y0   = _FY
                _ymid = _FY + _top_h + _AIL
                _ybot = _ymid + _mid_h + _AIL
                _yfg  = _ybot + _BOT

                _lpos=[]; _y=_ymid
                for h in _lhs: _lpos.append((_FX,_y,_LW,h)); _y+=h
                _rpos=[]; _y=_ymid
                for h in _rhs: _rpos.append((_FX+_LW+_CW,_y,_RW,h)); _y+=h

                _cross_y2 = _ymid + _mid_h

                # ── assemble zones SVG ────────────────────────────────────────
                _zsv = ""
                _zsv += _el_zone_svg(_zs["tl"][0],_zs["tl"][1],[],
                                     _FX,_y0,_LW,_top_h,True)
                _zsv += _el_zone_svg(_zs["tr"][0],_zs["tr"][1],_tr_ml,
                                     _FX+_LW+_CW,_y0,_RW,_top_h,_zs["tr"][3])
                for z,ml,p in zip(_zs["left"], _left_mls, _lpos):
                    _zsv+=_el_zone_svg(z[0],z[1],ml,*p,z[3])
                for z,ml,p in zip(_zs["right"],_right_mls,_rpos):
                    _zsv+=_el_zone_svg(z[0],z[1],ml,*p,z[3])
                _zsv+=_el_zone_svg(_zs["bl"][0],_zs["bl"][1],_bl_ml,
                                   _FX,_ybot,_bl_w,_BOT,_zs["bl"][3])
                _zsv+=_el_zone_svg(_zs["br"][0],_zs["br"][1],_br_ml,
                                   _FX+_bl_w,_ybot,_br_w,_BOT,_zs["br"][3])

                # ── global stats ──────────────────────────────────────────────
                _el_on =int((_mc_el["Status"]=="ON").sum())
                _el_off=int((_mc_el["Status"]=="OFF").sum())
                _el_tot=len(_mc_el)
                _el_ops=int(_mc_el["Operator_Count"].sum())
                _now   =pd.Timestamp.now().strftime("%d-%b-%Y").upper()

                # Gate: centred on factory wall
                _gcx  = _FX + _FW//2   # centre x = 52+315 = 367
                _gx   = _gcx - 45      # gate left edge
                _SVG_W= 740
                _SVG_H= _FY + _FH + 130  # factory + legend below

                _el_svg = f"""<svg viewBox="0 0 {_SVG_W} {_SVG_H}"
  xmlns="http://www.w3.org/2000/svg"
  style="width:100%;max-width:880px;display:block;margin:0 auto;background:white">
<defs>
  <pattern id="el_dots" width="7" height="7" patternUnits="userSpaceOnUse">
    <rect width="7" height="7" fill="#f9f9f9"/>
    <path d="M0,7L7,0" stroke="#ddd" stroke-width=".7"/>
  </pattern>
  <marker id="el_a" markerWidth="5" markerHeight="5" refX="2.5" refY="2.5" orient="auto">
    <path d="M0,0 L5,2.5 L0,5" fill="none" stroke="#444" stroke-width="1"/>
  </marker>
</defs>
<!-- TITLE BLOCK -->
<rect x="10" y="8" width="720" height="60" fill="none" stroke="#000" stroke-width="1.5"/>
<line x1="10" y1="28" x2="730" y2="28" stroke="#000" stroke-width=".5"/>
<text x="18" y="22" font-family="Arial" font-size="14" font-weight="700" letter-spacing=".5"
  fill="#000">{_area_title}</text>
<text x="18" y="57" font-family="Arial" font-size="9" fill="#555" letter-spacing=".5"
  >EXECUTIVE LAYOUT \u2014 MACHINE GROUPS</text>
<text x="18" y="42" font-family="Arial" font-size="8" fill="#666"
  >{_el_tot} M/C total \u00b7 {_el_on} running \u00b7 {_el_off} offline \u00b7 {_el_ops} operators</text>
<line x1="480" y1="8" x2="480" y2="68" stroke="#000" stroke-width=".8"/>
<line x1="570" y1="8" x2="570" y2="68" stroke="#000" stroke-width=".8"/>
<line x1="650" y1="8" x2="650" y2="68" stroke="#000" stroke-width=".8"/>
<text x="488" y="23" font-family="Arial" font-size="7.5" fill="#555">REV: A</text>
<text x="578" y="23" font-family="Arial" font-size="7.5" fill="#555">SCALE: NTS</text>
<text x="658" y="23" font-family="Arial" font-size="7.5" fill="#555">DATE: {_now}</text>
<!-- DIMENSION LINES -->
<line x1="{_FX}" y1="74" x2="{_FX+_FW}" y2="74" stroke="#444" stroke-width=".8"
  marker-start="url(#el_a)" marker-end="url(#el_a)"/>
<text x="{_FX+_FW//2}" y="72" font-family="Arial" font-size="7" text-anchor="middle" fill="#444">120'-0"</text>
<line x1="36" y1="{_FY}" x2="36" y2="{_FY+_FH}" stroke="#444" stroke-width=".8"
  marker-start="url(#el_a)" marker-end="url(#el_a)"/>
<text x="30" y="{_FY+_FH//2}" font-family="Arial" font-size="7" text-anchor="middle"
  fill="#444" transform="rotate(-90 30 {_FY+_FH//2})">110'-0"</text>
<!-- FACTORY BACKGROUND -->
<rect x="{_FX}" y="{_FY}" width="{_FW}" height="{_FH}" fill="white" stroke="none"/>
<!-- PRODUCTION ZONES -->
{_zsv}
<!-- MAIN AISLE -->
<rect x="{_FX}" y="{_FY+_top_h}" width="{_FW}" height="{_AIL}" fill="#f8f8f8" stroke="none"/>
<line x1="{_FX}" y1="{_FY+_top_h}" x2="{_FX+_FW}" y2="{_FY+_top_h}"
  stroke="#888" stroke-width=".9" stroke-dasharray="9,4"/>
<line x1="{_FX}" y1="{_ymid}" x2="{_FX+_FW}" y2="{_ymid}"
  stroke="#888" stroke-width=".9" stroke-dasharray="9,4"/>
<text x="{_FX+_FW//2}" y="{_FY+_top_h+15}" font-family="Arial" font-size="8"
  text-anchor="middle" fill="#999" font-weight="700" letter-spacing="2">MAIN AISLE</text>
<!-- CROSS AISLE -->
<rect x="{_FX+_LW}" y="{_ymid}" width="{_CW}" height="{_mid_h}" fill="#f8f8f8" stroke="none"/>
<line x1="{_FX+_LW}" y1="{_ymid}" x2="{_FX+_LW}" y2="{_cross_y2}"
  stroke="#888" stroke-width=".9" stroke-dasharray="5,3"/>
<line x1="{_FX+_LW+_CW}" y1="{_ymid}" x2="{_FX+_LW+_CW}" y2="{_cross_y2}"
  stroke="#888" stroke-width=".9" stroke-dasharray="5,3"/>
<text x="{_FX+_LW+_CW//2}" y="{(_ymid+_cross_y2)//2}"
  font-family="Arial" font-size="7" text-anchor="middle" fill="#ccc" font-weight="700"
  letter-spacing="1.5"
  transform="rotate(-90 {_FX+_LW+_CW//2} {(_ymid+_cross_y2)//2})">CROSS AISLE</text>
<!-- SERVICE AISLE -->
<rect x="{_FX}" y="{_ymid+_mid_h}" width="{_FW}" height="{_AIL}" fill="#f8f8f8" stroke="none"/>
<line x1="{_FX}" y1="{_ymid+_mid_h}" x2="{_FX+_FW}" y2="{_ymid+_mid_h}"
  stroke="#888" stroke-width=".9" stroke-dasharray="9,4"/>
<line x1="{_FX}" y1="{_ybot}" x2="{_FX+_FW}" y2="{_ybot}"
  stroke="#888" stroke-width=".9" stroke-dasharray="9,4"/>
<text x="{_FX+_FW//2}" y="{_ymid+_mid_h+15}" font-family="Arial" font-size="8"
  text-anchor="middle" fill="#999" font-weight="700" letter-spacing="2">SERVICE AISLE</text>
<!-- FG EXIT LOADING DOCK -->
<rect x="{_FX}" y="{_yfg}" width="{_FW}" height="{_FGH}" fill="white"
  stroke="#000" stroke-width="1.8"/>
<text x="{_FX+_FW//2}" y="{_yfg+20}" font-family="Arial" font-size="10.5"
  font-weight="700" text-anchor="middle" fill="#000" letter-spacing=".5"
  >FINISHED GOODS EXIT &amp; LOADING DOCK</text>
<text x="{_FX+_FW//2}" y="{_yfg+36}" font-family="Arial" font-size="9"
  text-anchor="middle" fill="#666">&#128666; \u00b7 OUTBOUND SHIPPING</text>
<!-- OUTER FACTORY WALL (drawn last, on top) -->
<rect x="{_FX}" y="{_FY}" width="{_FW}" height="{_FH}" fill="none"
  stroke="#000" stroke-width="5"/>
<!-- RM ENTRANCE — centred gate, no polygon -->
<rect x="{_gx}" y="{_FY-4}" width="90" height="7" fill="white" stroke="none"/>
<text x="{_gcx}" y="{_FY-7}" font-family="Arial" font-size="9" font-weight="700"
  text-anchor="middle" fill="#000" letter-spacing=".5">\u25bc RM ENTRANCE</text>
<!-- Door arc left wall -->
<rect x="{_FX-3}" y="{_FY+_top_h}" width="6" height="{_AIL}" fill="white" stroke="none"/>
<path d="M {_FX} {_FY+_top_h+_AIL} A 22 22 0 0 1 {_FX+22} {_FY+_top_h}"
  fill="none" stroke="#000" stroke-width="1.2"/>
<line x1="{_FX}" y1="{_FY+_top_h}" x2="{_FX}" y2="{_FY+_top_h+_AIL}"
  stroke="#000" stroke-width="1.2"/>
<!-- Door arc right wall -->
<rect x="{_FX+_FW-3}" y="{_ymid+_mid_h}" width="6" height="{_AIL}"
  fill="white" stroke="none"/>
<path d="M {_FX+_FW} {_ymid+_mid_h+_AIL} A 22 22 0 0 0 {_FX+_FW-22} {_ymid+_mid_h}"
  fill="none" stroke="#000" stroke-width="1.2"/>
<line x1="{_FX+_FW}" y1="{_ymid+_mid_h}" x2="{_FX+_FW}" y2="{_ymid+_mid_h+_AIL}"
  stroke="#000" stroke-width="1.2"/>
<!-- FG EXIT — centred gate, below wall -->
<rect x="{_gx}" y="{_FY+_FH-4}" width="90" height="7" fill="white" stroke="none"/>
<text x="{_gcx}" y="{_FY+_FH+18}" font-family="Arial" font-size="9" font-weight="700"
  text-anchor="middle" fill="#000" letter-spacing=".5">\u25bc FG EXIT</text>
<!-- LEGEND -->
<rect x="{_FX}" y="{_FY+_FH+32}" width="340" height="70" fill="white"
  stroke="#000" stroke-width="1"/>
<text x="{_FX+12}" y="{_FY+_FH+49}" font-family="Arial" font-size="9"
  font-weight="700" fill="#000" letter-spacing=".5">LEGEND</text>
<line x1="{_FX+12}" y1="{_FY+_FH+54}" x2="{_FX+328}" y2="{_FY+_FH+54}"
  stroke="#ccc" stroke-width=".5"/>
<rect x="{_FX+12}"  y="{_FY+_FH+61}" width="20" height="12" rx="3" fill="#16a34a"/>
<text x="{_FX+38}"  y="{_FY+_FH+72}" font-family="Arial" font-size="8.5" fill="#333">Machine \u2014 RUNNING</text>
<rect x="{_FX+175}" y="{_FY+_FH+61}" width="20" height="12" rx="3" fill="#dc2626"/>
<text x="{_FX+201}" y="{_FY+_FH+72}" font-family="Arial" font-size="8.5" fill="#333">Machine \u2014 OFFLINE</text>
<rect x="{_FX+12}"  y="{_FY+_FH+80}" width="20" height="12" rx="3" fill="#d97706"/>
<text x="{_FX+38}"  y="{_FY+_FH+91}" font-family="Arial" font-size="8.5" fill="#333">Machine \u2014 MAINTENANCE</text>
<!-- NOTES -->
<rect x="{_FX+350}" y="{_FY+_FH+32}" width="330" height="70" fill="white"
  stroke="#000" stroke-width="1"/>
<text x="{_FX+362}" y="{_FY+_FH+49}" font-family="Arial" font-size="9"
  font-weight="700" fill="#000" letter-spacing=".5">NOTES</text>
<line x1="{_FX+362}" y1="{_FY+_FH+54}" x2="{_FX+670}" y2="{_FY+_FH+54}"
  stroke="#ccc" stroke-width=".5"/>
<text x="{_FX+362}" y="{_FY+_FH+67}" font-family="Arial" font-size="7.5" fill="#555">\u2022 M/C = Machine</text>
<text x="{_FX+362}" y="{_FY+_FH+80}" font-family="Arial" font-size="7.5" fill="#555">\u2022 Layout not to scale</text>
<text x="{_FX+510}" y="{_FY+_FH+67}" font-family="Arial" font-size="7.5" fill="#555">\u2022 Machine groups in blocks</text>
<text x="{_FX+510}" y="{_FY+_FH+80}" font-family="Arial" font-size="7.5" fill="#555">\u2022 Color = machine status</text>
</svg>"""

                _el_tt_js = """
<div id="fmp-tt" style="position:fixed;display:none;background:#1a2035;color:white;
  padding:10px 14px;border-radius:8px;font-family:Arial,sans-serif;font-size:12.5px;
  pointer-events:none;z-index:9999;border-left:3px solid #22c55e;
  box-shadow:0 4px 18px rgba(0,0,0,0.45);min-width:170px;line-height:1.6"></div>
<script>
const _tt=document.getElementById('fmp-tt');
document.querySelectorAll('[data-mname]').forEach(el=>{
  el.addEventListener('mouseenter',()=>{
    const st=el.dataset.mstatus,n=parseInt(el.dataset.mops)||0;
    const sc=st==='ON'?'#22c55e':st==='OFF'?'#ef4444':st==='MAINTENANCE'?'#f59e0b':'#94a3b8';
    _tt.style.borderLeftColor=sc;
    _tt.innerHTML='<div style="font-weight:700;font-size:13.5px;margin-bottom:5px">'+el.dataset.mname+'</div>'
      +'<div style="margin-bottom:3px">Status\u00a0\u00a0<span style="color:'+sc+';font-weight:700">'+st+'</span></div>'
      +'<div style="color:#94a3b8">\U0001F477 '+n+' operator'+(n!==1?'s':'')+'</div>';
    _tt.style.display='block';
  });
  el.addEventListener('mousemove',e=>{
    _tt.style.left=(e.clientX+16)+'px';
    _tt.style.top=(e.clientY-12)+'px';
  });
  el.addEventListener('mouseleave',()=>_tt.style.display='none');
});
</script>"""
                _el_html = (
                    '<!DOCTYPE html><html><head><meta charset="utf-8">'
                    '<style>body{margin:0;padding:14px;background:#f5f5f5}'
                    f'</style></head><body>{_el_svg}{_el_tt_js}</body></html>')

                import streamlit.components.v1 as _cmp_el
                _cmp_h = max(900, _SVG_H + 60)
                _cmp_el.html(_el_html, height=_cmp_h, scrolling=False)
                st.caption("🏭 Executive Layout View · Engineering floor plan · "
                           "Green = Running · Red = Offline")

            elif _dz_view:
                # ══════════════════════════════════════════════════════════════
                # DRAW.IO VIEW — Style A (Swimlane) + Style C (Accent Grid)
                # Two Streamlit tabs; each tab generates a full SVG from live data.
                # Completely self-contained: no dependency on _el_* functions.
                # ══════════════════════════════════════════════════════════════
                import re as _re_dz
                import streamlit.components.v1 as _cmp_dz

                _dz_ak = AREAS[st.session_state.active_area]["key"]
                _dz_mc = df_display[df_display["Status"] != "-"].copy()

                def _dz_base(n): return _re_dz.sub(r'\s*\d+\s*$','',str(n).strip())
                _DZ_SHORT = {
                    "Leadgers Welding":"LW","Welding Machine":"WM",
                    "Ring Vertical":"RV","Cup Vertical":"CV",
                    "Weld Cell":"WC","Drrill":"DR","Drill":"DR",
                    "Auto Welding":"AW","RASA Saw":"SAW","Manual Saw":"SAW",
                    "Mixer":"HYD","Cup Frame Form Mixer":"CFM","Cup Weld":"CW",
                    "Multi Drill":"MD","Forming":"FRM","Form & Tap":"F&T",
                    "Saw":"SAW","Tap":"TAP","Presses":"PRS",
                    "ECO Punch Press":"ECO","TECH Punch / Drill":"TCH",
                    "Welding Robot":"WR","Pre-Assembly Welding Robot":"PAW",
                    "9-Frame Assembly":"9FA","Grinding":"GRD",
                    "Delivery / QC":"D/Q","Auto Saw":"SAW",
                    "Welding Package":"WPK","Welding Station":"WST",
                    "CNC Router Machine":"CNC","Saw Machine":"SAW",
                    "Manual Assembly Tools":"MAT","Pallet Assembly Spread":"PAS",
                    "Paint / Coating Station":"PNT","Assembly Station":"ASSY",
                    "Production Sorting Area":"SORT","ECO Punch + TECH Press":"E+T",
                }
                def _dz_abbr(n):
                    b = _dz_base(n)
                    return _DZ_SHORT.get(b, b[:4].upper())

                _DZ_NM = {
                    "Assembly Station","Production Sorting Area",
                    "9-Frame Assembly","Delivery / QC",
                    "Manual Assembly Tools","Pallet Assembly Spread",
                }
                _DZ_IMAP = {
                    "Welding Machine":"weld","Leadgers Welding":"weld",
                    "Weld Cell":"weld","Cup Weld":"weld",
                    "Welding Package":"weld","Welding Station":"weld",
                    "Welding Robot":"robot","Pre-Assembly Welding Robot":"robot",
                    "Auto Welding":"robot",
                    "RASA Saw":"saw","Manual Saw":"saw","Auto Saw":"saw",
                    "Saw Machine":"saw","Saw":"saw","Grinding":"saw",
                    "Drill":"drill","Drrill":"drill","Multi Drill":"drill",
                    "CNC Router Machine":"drill","TECH Punch / Drill":"drill",
                    "Tap":"drill",
                    "Mixer":"press","Cup Frame Form Mixer":"press",
                    "Presses":"press","ECO Punch Press":"press",
                    "ECO Punch + TECH Press":"press","Ring Vertical":"press",
                    "Cup Vertical":"press","Form & Tap":"press","Forming":"press",
                }
                def _dz_itype(b): return _DZ_IMAP.get(b, "weld")

                def _dz_get(bases):
                    r = []
                    for _, row in _dz_mc.iterrows():
                        b = _dz_base(row["Machine"])
                        if b in bases:
                            r.append({"a":_dz_abbr(row["Machine"]), "b":b,
                                      "n": str(row["Machine"]).strip(),
                                      "s":str(row["Status"]).strip(),
                                      "o":int(row.get("Operator_Count",0)),
                                      "nm": b in _DZ_NM})
                    return r

                _DZ_ZS = {
                  "F5_A1":{
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("CUTTING & SAWING","RASA Saw \u00b7 Manual Saw \u00d72",
                          ["RASA Saw","Manual Saw"],False),
                    "left":[("LEDGER WELDING","Ledger Station \u00d76",
                              ["Leadgers Welding"],False),
                             ("VERTICAL FORMING","Ring Vert. \u00d73 \u00b7 Cup Vert. \u00d74",
                              ["Ring Vertical","Cup Vertical"],False)],
                    "right":[("STRUCTURAL WELDING","Welding Machine \u00d75",
                               ["Welding Machine"],False),
                              ("ASSEMBLY","Assembly Station",["Assembly Station"],False),
                              ("DRILLING","Drill \u00d72",["Drill"],False)],
                    "bl":("AUTO WELDING","",["Auto Welding"],False),
                    "br":("PROD. SORTING","",["Production Sorting Area"],False),
                  },
                  "F5_A2":{
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("DRILLING","Drrill \u00d73 \u00b7 Drill \u00d76 \u00b7 Multi Drill",
                          ["Drrill","Drill","Multi Drill"],False),
                    "left":[("HYDRAULIC PRESSING","Hydraulic Press \u00d76",
                              ["Mixer"],False),
                             ("WELDING CELLS","Weld Cell \u00d76",["Weld Cell"],False)],
                    "right":[("CUP FRAME PRESSING","Cup Frame Press \u00d72",
                               ["Cup Frame Form Mixer"],False),
                              ("CUP WELDING","Cup Weld \u00d72",["Cup Weld"],False),
                              ("FORMING & TAPPING","Form \u00b7 Saw \u00b7 Tap",
                               ["Form & Tap","Forming","Saw","Tap"],False)],
                    "bl":("SORTING","",[], True),
                    "br":("OUTBOUND","",[], True),
                  },
                  "F4_A1":{
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("CUTTING & SAWING","Manual Saw \u00d72 \u00b7 Auto Saw",
                          ["Manual Saw","Auto Saw"],False),
                    "left":[("PUNCHING & PRESSING","ECO \u00b7 TECH \u00b7 Presses",
                              ["ECO Punch Press","TECH Punch / Drill",
                               "ECO Punch + TECH Press","Presses"],False),
                             ("FRAME ASSEMBLY","9-Frame",["9-Frame Assembly"],False)],
                    "right":[("WELDING","Pkg \u00b7 Robot \u00b7 Pre-Assy \u00b7 Stn",
                               ["Welding Package","Pre-Assembly Welding Robot",
                                "Welding Robot","Welding Station"],False),
                              ("FINISHING & QC","Grinding \u00b7 QC",
                               ["Grinding","Delivery / QC"],False)],
                    "bl":("STAGING","",[], True),
                    "br":("OUTBOUND","",[], True),
                  },
                  "F4_A2":{
                    "tl":("RAW MATERIAL STORAGE","Pipe / Sheet Buffer",[],True),
                    "tr":("CUTTING","Saw Machine \u00d71",["Saw Machine"],False),
                    "left":[("ASSEMBLY","Manual Assy \u00b7 Pallet",
                              ["Manual Assembly Tools","Pallet Assembly Spread"],False)],
                    "right":[("CNC MACHINING","CNC Router \u00d71",
                               ["CNC Router Machine"],False),
                              ("SURFACE COATING","Paint / Coating \u00d71",
                               ["Paint / Coating Station"],False)],
                    "bl":("WIP STORAGE","",[], True),
                    "br":("OUTBOUND","",[], True),
                  },
                }
                _dz_zs = _DZ_ZS.get(_dz_ak, _DZ_ZS["F5_A1"])

                # ── colour helpers ────────────────────────────────────────────
                def _dz_cmap(s):
                    if s=="ON":  return {"f":"#EAF3DE","p":"#C0DD97","s":"#3B6D11","d":"#639922"}
                    if s=="OFF": return {"f":"#FCEBEB","p":"#F7C1C1","s":"#791F1F","d":"#A32D2D"}
                    return           {"f":"#FAEEDA","p":"#FAC775","s":"#633806","d":"#854F0B"}
                def _dz_wclr(s):
                    if s=="ON":  return "#EAF3DE","#3B6D11","#173404"
                    if s=="OFF": return "#FCEBEB","#791F1F","#501313"
                    return           "#FAEEDA","#633806","#412402"

                # ── icon builders (52×55 canvas, same as Executive Layout) ───
                def _dz_icon_weld(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+12}" width="24" height="32" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.6"/>'
                        f'<rect x="{bx+8}" y="{by+17}" width="16" height="7" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width="0.9"/>'
                        f'<rect x="{bx+8}" y="{by+27}" width="16" height="12" rx="1" fill="none" stroke="{c["d"]}" stroke-width="0.7"/>'
                        f'<circle cx="{bx+16}" cy="{by+33}" r="5" fill="none" stroke="{c["s"]}" stroke-width="1.1"/>'
                        f'<circle cx="{bx+16}" cy="{by+33}" r="1.5" fill="{c["s"]}"/>'
                        f'<rect x="{bx+4}" y="{by+43}" width="24" height="3.5" rx="1" fill="{c["s"]}" opacity="0.25"/>'
                        f'<circle cx="{bx+10}" cy="{by+47}" r="3.5" fill="none" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<circle cx="{bx+22}" cy="{by+47}" r="3.5" fill="none" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<path d="M {bx+28} {by+20} Q {bx+36} {by+16} {bx+42} {by+9}" fill="none" stroke="{c["d"]}" stroke-width="1.6" stroke-linecap="round"/>'
                        f'<ellipse cx="{bx+43}" cy="{by+8}" rx="5" ry="3" fill="{c["s"]}" transform="rotate(-30 {bx+43} {by+8})"/>'
                    )
                def _dz_icon_saw(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+25}" width="44" height="8" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+6}" y="{by+33}" width="10" height="18" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+36}" y="{by+33}" width="10" height="18" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+16}" y="{by+33}" width="20" height="10" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width="1.1"/>'
                        f'<circle cx="{bx+26}" cy="{by+27}" r="14" fill="none" stroke="{c["s"]}" stroke-width="2"/>'
                        f'<circle cx="{bx+26}" cy="{by+27}" r="3.5" fill="{c["s"]}"/>'
                        f'<path d="M {bx+12} {by+24} Q {bx+26} {by+14} {bx+40} {by+24}" fill="none" stroke="{c["s"]}" stroke-width="1.5"/>'
                    )
                def _dz_icon_drill(bx,by,c):
                    return (
                        f'<rect x="{bx+22}" y="{by+4}" width="8" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+9}" y="{by+6}" width="34" height="10" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+14}" y="{by+16}" width="24" height="15" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<polygon points="{bx+19},{by+31} {bx+33},{by+31} {bx+26},{by+47}" fill="{c["s"]}"/>'
                        f'<rect x="{bx+8}" y="{by+40}" width="36" height="6" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                    )
                def _dz_icon_press(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+4}" width="9" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+39}" y="{by+4}" width="9" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+4}" y="{by+4}" width="44" height="9" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+4}" y="{by+45}" width="44" height="9" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+18}" y="{by+13}" width="16" height="18" rx="4" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+21}" y="{by+31}" width="10" height="15" rx="1" fill="{c["s"]}"/>'
                    )
                def _dz_icon_assy(bx,by,c):
                    return (
                        f'<rect x="{bx+4}" y="{by+30}" width="44" height="8" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<rect x="{bx+6}" y="{by+38}" width="8" height="18" rx="1" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+38}" y="{by+38}" width="8" height="18" rx="1" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                        f'<rect x="{bx+14}" y="{by+17}" width="24" height="15" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<line x1="{bx+4}" y1="{by+25}" x2="{bx+14}" y2="{by+25}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+4}" y1="{by+25}" x2="{bx+4}" y2="{by+30}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+38}" y1="{by+25}" x2="{bx+48}" y2="{by+25}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<line x1="{bx+48}" y1="{by+25}" x2="{bx+48}" y2="{by+30}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<rect x="{bx+19}" y="{by+21}" width="14" height="7" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width="0.8"/>'
                    )
                def _dz_icon_robot(bx,by,c):
                    return (
                        f'<rect x="{bx+10}" y="{by+48}" width="32" height="7" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.8"/>'
                        f'<ellipse cx="{bx+26}" cy="{by+46}" rx="12" ry="6" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<rect x="{bx+23}" y="{by+24}" width="6" height="24" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<circle cx="{bx+26}" cy="{by+24}" r="4.5" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                        f'<rect x="{bx+26}" y="{by+10}" width="6" height="16" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5" transform="rotate(28 {bx+29} {by+24})"/>'
                        f'<circle cx="{bx+37}" cy="{by+13}" r="5" fill="{c["s"]}"/>'
                        f'<line x1="{bx+37}" y1="{by+8}" x2="{bx+41}" y2="{by+4}" stroke="{c["s"]}" stroke-width="2.5" stroke-linecap="round"/>'
                    )
                _DZ_ICON_FN = {"weld":_dz_icon_weld,"saw":_dz_icon_saw,
                               "drill":_dz_icon_drill,"press":_dz_icon_press,
                               "assy":_dz_icon_assy,"robot":_dz_icon_robot}

                # ── worker circles ────────────────────────────────────────────
                def _dz_wcircles(n_ops, cx, cy, wf, ws, wp):
                    if n_ops <= 0: return ""
                    show=min(n_ops,4); r=7.5; gap=17
                    sx=cx-(show*gap)//2+r; svg=""
                    for i in range(show):
                        px=int(sx+i*gap); py=cy
                        if i==3 and n_ops>4:
                            svg+=(f'<circle cx="{px}" cy="{py}" r="{r}" fill="{ws}"/>'
                                  f'<text x="{px}" y="{py}" font-size="7" text-anchor="middle"'
                                  f' fill="white" font-family="Arial" font-weight="700"'
                                  f' dominant-baseline="central">+{n_ops-3}</text>')
                        else:
                            svg+=(f'<circle cx="{px}" cy="{py}" r="{r}"'
                                  f' fill="{wf}" stroke="{ws}" stroke-width="1.2"/>'
                                  f'<circle cx="{px}" cy="{py-2.5}" r="2.2" fill="{wp}"/>'
                                  f'<rect x="{px-2.2}" y="{py}" width="4.4"'
                                  f' height="4" rx="1" fill="{wp}"/>')
                    return svg

                # ── layout constants ──────────────────────────────────────────
                _DZ_IW=52; _DZ_IH=55; _DZ_WCR=7.5
                _DZ_UNIT = _DZ_IH + 8 + 10 + 6 + int(_DZ_WCR*2)   # ≈ 94

                def _dz_zone_h(n, zw, storage=False):
                    if storage or n==0: return 130
                    cols=min(3,max(1,(zw-16)//(_DZ_IW+10)))
                    rows=(n+cols-1)//cols
                    return max(130, 48+rows*(_DZ_UNIT+10)+40+14)

                # ── machine icon placement ────────────────────────────────────
                def _dz_boxes(ml, zx, zy, zw, hdr_h):
                    _IW=_DZ_IW; _IH=_DZ_IH; _GAP_X=10; _GAP_Y=10
                    cols=min(3,max(1,(zw-16)//(_IW+_GAP_X)))
                    rowW=cols*_IW+(cols-1)*_GAP_X
                    sx=zx+max(8,int((zw-rowW)/2)); svg=""
                    for i,m in enumerate(ml):
                        col=i%cols; row_i=i//cols
                        bx=int(sx+col*(_IW+_GAP_X))
                        by=int(zy+hdr_h+row_i*(_DZ_UNIT+_GAP_Y))
                        _mn=m.get("n",m.get("b","")).replace('"',"'")
                        _ms=m["s"] if not m["nm"] else "WORK AREA"
                        _mo=m.get("o",0)
                        svg+=f'<g data-mname="{_mn}" data-mstatus="{_ms}" data-mops="{_mo}" style="cursor:pointer">'
                        c=_dz_cmap(m["s"])
                        if m["nm"]:
                            # reuse the same _nm_icon logic (identical neutral SVG shapes)
                            _f2="#e4e4e4";_s2="#555";_d2="#c4c4c4";_h2="#888";bl2=m.get("b","").lower()
                            if "assembly" in bl2 and "9" not in bl2 and "pallet" not in bl2 and "manual" not in bl2:
                                svg+=(f'<rect x="{bx+4}" y="{by+19}" width="44" height="6" rx="1.5" fill="{_f2}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<rect x="{bx+8}" y="{by+25}" width="6" height="24" rx="1" fill="{_f2}" stroke="{_s2}" stroke-width="1.2"/>'
                                      f'<rect x="{bx+38}" y="{by+25}" width="6" height="24" rx="1" fill="{_f2}" stroke="{_s2}" stroke-width="1.2"/>'
                                      f'<rect x="{bx+8}" y="{by+38}" width="36" height="4" rx="1" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<rect x="{bx+18}" y="{by+10}" width="18" height="10" rx="1.5" fill="{_d2}" stroke="{_s2}" stroke-width="1.2"/>'
                                      f'<line x1="{bx+36}" y1="{by+15}" x2="{bx+47}" y2="{by+15}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<circle cx="{bx+47}" cy="{by+15}" r="3" fill="none" stroke="{_s2}" stroke-width="1.2"/>')
                            elif "sort" in bl2:
                                svg+=(f'<rect x="{bx+3}" y="{by+21}" width="46" height="5" rx="1.5" fill="{_f2}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<rect x="{bx+4}" y="{by+5}" width="14" height="17" rx="1.2" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<rect x="{bx+20}" y="{by+5}" width="12" height="17" rx="1.2" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<rect x="{bx+34}" y="{by+5}" width="14" height="17" rx="1.2" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<text x="{bx+11}" y="{by+15}" font-size="6.5" text-anchor="middle" fill="{_h2}" font-family="Arial" dominant-baseline="central">A</text>'
                                      f'<text x="{bx+26}" y="{by+15}" font-size="6.5" text-anchor="middle" fill="{_h2}" font-family="Arial" dominant-baseline="central">B</text>'
                                      f'<text x="{bx+41}" y="{by+15}" font-size="6.5" text-anchor="middle" fill="{_h2}" font-family="Arial" dominant-baseline="central">C</text>')
                            elif "9" in bl2 and "frame" in bl2:
                                svg+=(f'<rect x="{bx+4}" y="{by+4}" width="6" height="50" rx="1.5" fill="{_f2}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<rect x="{bx+42}" y="{by+4}" width="6" height="50" rx="1.5" fill="{_f2}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<rect x="{bx+10}" y="{by+6}" width="32" height="12" rx="1.2" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<rect x="{bx+10}" y="{by+22}" width="32" height="12" rx="1.2" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<rect x="{bx+10}" y="{by+38}" width="32" height="12" rx="1.2" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<rect x="{bx+14}" y="{by+8}" width="24" height="8" rx=".7" fill="none" stroke="{_h2}" stroke-width="1"/>'
                                      f'<rect x="{bx+14}" y="{by+24}" width="24" height="8" rx=".7" fill="none" stroke="{_h2}" stroke-width="1"/>'
                                      f'<rect x="{bx+14}" y="{by+40}" width="24" height="8" rx=".7" fill="none" stroke="{_h2}" stroke-width="1"/>')
                            elif "qc" in bl2 or "delivery" in bl2:
                                svg+=(f'<rect x="{bx+3}" y="{by+26}" width="46" height="6" rx="1.5" fill="{_f2}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<circle cx="{bx+21}" cy="{by+14}" r="10" fill="none" stroke="{_s2}" stroke-width="1.9"/>'
                                      f'<circle cx="{bx+21}" cy="{by+14}" r="6" fill="#d4eedb" stroke="{_s2}" stroke-width=".9"/>'
                                      f'<line x1="{bx+29}" y1="{by+21}" x2="{bx+37}" y2="{by+29}" stroke="{_s2}" stroke-width="3" stroke-linecap="round"/>'
                                      f'<polyline points="{bx+17},{by+14} {bx+20},{by+17} {bx+25},{by+11}" fill="none" stroke="#22c55e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
                            elif "manual" in bl2 or "tool" in bl2:
                                svg+=(f'<rect x="{bx+3}" y="{by+3}" width="46" height="52" rx="2.5" fill="#e8e0cc" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<path d="M{bx+13} {by+14} L{bx+15} {by+30}" stroke="{_s2}" stroke-width="3" stroke-linecap="round"/>'
                                      f'<ellipse cx="{bx+13}" cy="{by+13}" rx="3.5" ry="3" fill="none" stroke="{_s2}" stroke-width="1.6"/>'
                                      f'<rect x="{bx+24}" y="{by+9}" width="7" height="5" rx="1" fill="{_d2}" stroke="{_s2}" stroke-width="1"/>'
                                      f'<line x1="{bx+27}" y1="{by+14}" x2="{bx+27}" y2="{by+30}" stroke="{_s2}" stroke-width="2.8" stroke-linecap="round"/>'
                                      f'<rect x="{bx+6}" y="{by+36}" width="40" height="14" rx="1.5" fill="{_d2}" stroke="{_s2}" stroke-width="1.2"/>')
                            elif "pallet" in bl2:
                                svg+=(f'<rect x="{bx+4}" y="{by+18}" width="44" height="7" rx="1" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.5"/>'
                                      f'<rect x="{bx+4}" y="{by+35}" width="44" height="5" rx="1" fill="#d4b896" stroke="#7b5e3a" stroke-width="1.1"/>'
                                      f'<rect x="{bx+8}" y="{by+4}" width="14" height="14" rx="1.5" fill="#c0d8f0" stroke="#5580a8" stroke-width="1.2"/>'
                                      f'<rect x="{bx+24}" y="{by+4}" width="20" height="14" rx="1.5" fill="#c0d8f0" stroke="#5580a8" stroke-width="1.2"/>')
                            else:
                                svg+=(f'<rect x="{bx+5}" y="{by+22}" width="42" height="7" rx="1.5" fill="{_f2}" stroke="{_s2}" stroke-width="1.5"/>'
                                      f'<rect x="{bx+12}" y="{by+6}" width="28" height="17" rx="2" fill="{_d2}" stroke="{_s2}" stroke-width="1.2"/>'
                                      f'<rect x="{bx+15}" y="{by+9}" width="22" height="11" rx="1" fill="#b0c0d4" stroke="{_s2}" stroke-width=".8"/>')
                            svg+=(f'<text x="{bx+_IW//2}" y="{by+_IH+9}" font-size="8"'
                                  f' text-anchor="middle" fill="#666" font-family="Arial"'
                                  f' dominant-baseline="central" font-style="italic">{m["a"]}</text>')
                        else:
                            fn=_DZ_ICON_FN.get(_dz_itype(m["b"]),_dz_icon_weld)
                            svg+=fn(bx,by,c)
                            svg+=(f'<text x="{bx+_IW//2}" y="{by+_IH+9}" font-size="8"'
                                  f' text-anchor="middle" fill="#555" font-family="Arial"'
                                  f' dominant-baseline="central">{m["a"]}</text>')
                            if m["o"]>0:
                                wf,ws,wp=_dz_wclr(m["s"])
                                wcy=int(by+_IH+8+10+6+int(_DZ_WCR))
                                svg+=_dz_wcircles(m["o"],bx+_IW//2,wcy,wf,ws,wp)
                        svg+='</g>'
                    return svg

                def _dz_stats(ml, zx, zy, zw, hdr_h):
                    cols=min(3,max(1,(zw-16)//(_DZ_IW+10)))
                    rows=(len(ml)+cols-1)//cols if ml else 0
                    sy=int(zy+hdr_h+rows*(_DZ_UNIT+10)+10)
                    n_on =sum(1 for m in ml if m["s"]=="ON")
                    n_off=sum(1 for m in ml if m["s"]=="OFF")
                    ops  =sum(m["o"] for m in ml)
                    return (f'<text x="{zx+10}" y="{sy}" font-size="8.5" fill="#666"'
                            f' font-family="Arial" dominant-baseline="central">'
                            f'{len(ml)} M/C \u00b7 {ops} operators</text>'
                            f'<text x="{zx+10}" y="{sy+14}" font-size="8.5" fill="#999"'
                            f' font-family="Arial" dominant-baseline="central">'
                            f'{n_on} Running \u00b7 {n_off} Offline</text>')

                # ── draw.io category → colour ─────────────────────────────────
                _DZ_C = {
                    "stor": {"h":"#888888","b":"#F5F5F5"},
                    "weld": {"h":"#9673A6","b":"#EDE0F6"},
                    "cut":  {"h":"#6C8EBF","b":"#DAE8FC"},
                    "form": {"h":"#82B366","b":"#D5E8D4"},
                    "assy": {"h":"#D6B656","b":"#FFF2CC"},
                    "drill":{"h":"#6C8EBF","b":"#DAE8FC"},
                    "sort": {"h":"#888888","b":"#F5F5F5"},
                    "fg":   {"h":"#82B366","b":"#D5E8D4"},
                }
                def _dz_cat(name):
                    n=name.lower()
                    if any(k in n for k in ["storage","staging","wip","outbound","material"]): return "stor"
                    if "weld" in n:  return "weld"
                    if any(k in n for k in ["cut","saw"]): return "cut"
                    if any(k in n for k in ["form","press","vertical","punch","mix","cnc","coat"]): return "form"
                    if any(k in n for k in ["assembl","frame","pallet"]): return "assy"
                    if "drill" in n: return "drill"
                    if any(k in n for k in ["sort","finishing","qc","dispatch"]): return "sort"
                    return "stor"

                # ── layout sizing (same math as Executive Layout View) ────────
                _DZ_FX=52; _DZ_FY=88
                _DZ_LW=240; _DZ_CW=25; _DZ_RW=365
                _DZ_FW=_DZ_LW+_DZ_CW+_DZ_RW
                _DZ_AIL=22; _DZ_FGH=50
                _dz_bl_w=195; _dz_br_w=_DZ_FW-_dz_bl_w

                _dz_tr_ml    = _dz_get(_dz_zs["tr"][2])
                _dz_left_mls = [_dz_get(z[2]) for z in _dz_zs["left"]]
                _dz_right_mls= [_dz_get(z[2]) for z in _dz_zs["right"]]
                _dz_bl_ml    = _dz_get(_dz_zs["bl"][2])
                _dz_br_ml    = _dz_get(_dz_zs["br"][2])

                _dz_top_h  = max(120,_dz_zone_h(len(_dz_tr_ml),_DZ_RW,_dz_zs["tr"][3]))
                _dz_lhs    = [_dz_zone_h(len(m),_DZ_LW,z[3])
                              for m,z in zip(_dz_left_mls,_dz_zs["left"])]
                _dz_rhs    = [_dz_zone_h(len(m),_DZ_RW,z[3])
                              for m,z in zip(_dz_right_mls,_dz_zs["right"])]
                _dz_mid_l=sum(_dz_lhs); _dz_mid_r=sum(_dz_rhs)
                _dz_mid_h=max(_dz_mid_l,_dz_mid_r,100)
                if _dz_lhs and _dz_mid_l<_dz_mid_h: _dz_lhs[-1]+=_dz_mid_h-_dz_mid_l
                if _dz_rhs and _dz_mid_r<_dz_mid_h: _dz_rhs[-1]+=_dz_mid_h-_dz_mid_r
                _dz_BOT=max(_dz_zone_h(len(_dz_bl_ml),_dz_bl_w,_dz_zs["bl"][3]),
                            _dz_zone_h(len(_dz_br_ml),_dz_br_w,_dz_zs["br"][3]),100)
                _dz_FH =_dz_top_h+_DZ_AIL+_dz_mid_h+_DZ_AIL+_dz_BOT+_DZ_FGH
                _dz_ymid=_DZ_FY+_dz_top_h+_DZ_AIL
                _dz_ybot=_dz_ymid+_dz_mid_h+_DZ_AIL
                _dz_yfg =_dz_ybot+_dz_BOT
                _dz_lpos=[]; _y_=_dz_ymid
                for h in _dz_lhs: _dz_lpos.append((_DZ_FX,_y_,_DZ_LW,h)); _y_+=h
                _dz_rpos=[]; _y_=_dz_ymid
                for h in _dz_rhs: _dz_rpos.append((_DZ_FX+_DZ_LW+_DZ_CW,_y_,_DZ_RW,h)); _y_+=h
                _dz_SVG_W=_DZ_FX*2+_DZ_FW
                _dz_SVG_H=_DZ_FY+_dz_FH+130

                # ── SVG builder ───────────────────────────────────────────────
                def _dz_build(style):
                    HH=30 if style=="A" else 36   # header / top-offset height
                    p=[]

                    def _zone(x,y,w,h,name,sub,ml,storage=False):
                        cat=_dz_cat(name)
                        c=_DZ_C.get(cat,_DZ_C["stor"]); z=""
                        if style=="A":
                            z+=(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4"'
                                f' fill="{c["b"]}" stroke="{c["h"]}" stroke-width="1.5"/>'
                                f'<rect x="{x}" y="{y}" width="{w}" height="{HH}" rx="4" fill="{c["h"]}"/>'
                                f'<rect x="{x}" y="{y+HH-5}" width="{w}" height="5" fill="{c["h"]}"/>'
                                f'<text x="{x+9}" y="{y+HH//2}" font-size="10" font-weight="700"'
                                f' fill="white" font-family="Arial" dominant-baseline="central">{name}</text>')
                            if sub:
                                z+=(f'<text x="{x+w-8}" y="{y+HH//2}" font-size="7.5" fill="white"'
                                    f' font-family="Arial" text-anchor="end"'
                                    f' dominant-baseline="central" opacity=".9">{sub}</text>')
                        else:  # C
                            z+=(f'<rect x="{x}" y="{y}" width="{w}" height="{h}"'
                                f' fill="white" stroke="#ddd" stroke-width=".9" rx="3"/>'
                                f'<rect x="{x}" y="{y}" width="5" height="{h}" fill="{c["h"]}" rx="2"/>'
                                f'<rect x="{x+3}" y="{y}" width="2" height="{h}" fill="{c["h"]}"/>'
                                f'<text x="{x+14}" y="{y+15}" font-size="10" font-weight="700"'
                                f' fill="#222" font-family="Arial" dominant-baseline="central">{name}</text>')
                            if sub:
                                z+=(f'<text x="{x+14}" y="{y+28}" font-size="7.5" fill="#999"'
                                    f' font-family="Arial" dominant-baseline="central">{sub}</text>')
                        if storage or not ml:
                            z+=(f'<text x="{x+w//2}" y="{y+h//2}" font-size="9"'
                                f' text-anchor="middle" fill="#bbb" font-family="Arial"'
                                f' font-style="italic" dominant-baseline="central">No machines</text>')
                        else:
                            z+=_dz_boxes(ml,x,y,w,HH)
                            z+=_dz_stats(ml,x,y,w,HH)
                        return z

                    # background + title bar
                    _at=AREAS[st.session_state.active_area]["title"]
                    p.append(f'<rect width="{_dz_SVG_W}" height="{_dz_SVG_H}" fill="white"/>')
                    p.append(f'<rect x="0" y="0" width="{_dz_SVG_W}" height="58" fill="#1a2035"/>')
                    p.append(f'<rect x="0" y="56" width="{_dz_SVG_W}" height="3" fill="#3b82f6"/>')
                    _stag="Swimlane View (A)" if style=="A" else "Accent Grid View (C)"
                    p.append(f'<text x="18" y="24" font-size="15" font-weight="700"'
                             f' fill="white" font-family="Arial">{_at}</text>')
                    p.append(f'<text x="18" y="44" font-size="9.5" fill="#94a3b8"'
                             f' font-family="Arial">draw.io {_stag}</text>')
                    _dz_on =int((df_display["Status"]=="ON").sum())
                    _dz_off=int((df_display["Status"]=="OFF").sum())
                    _dz_tot=len(df_display[df_display["Status"]!="-"])
                    _dz_upt=round(_dz_on/_dz_tot*100) if _dz_tot else 0
                    p.append(f'<text x="{_dz_SVG_W-18}" y="24" font-size="11" fill="#22c55e"'
                             f' font-family="Arial" text-anchor="end" font-weight="700">'
                             f'{_dz_upt}% uptime</text>')
                    p.append(f'<text x="{_dz_SVG_W-18}" y="44" font-size="8.5" fill="#64748b"'
                             f' font-family="Arial" text-anchor="end">'
                             f'{_dz_on} ON \u00b7 {_dz_off} OFF \u00b7 {_dz_tot} total M/C</text>')

                    # factory outer wall (drawn first; redrawn on top later)
                    p.append(f'<rect x="{_DZ_FX}" y="{_DZ_FY}" width="{_DZ_FW}" height="{_dz_FH}"'
                             f' fill="none" stroke="#1a2035" stroke-width="4.5" rx="4"/>')

                    # RM entrance gate
                    _gcx=_DZ_FX+_DZ_FW//2
                    p.append(f'<rect x="{_gcx-45}" y="{_DZ_FY-3}" width="90" height="8"'
                             f' fill="white" stroke="none"/>')
                    p.append(f'<text x="{_gcx}" y="{_DZ_FY-10}" font-size="8.5" font-weight="700"'
                             f' text-anchor="middle" fill="#334155" font-family="Arial">'
                             f'\u25bc RM ENTRANCE</text>')

                    # top zones
                    _tl=_dz_zs["tl"]; _tr=_dz_zs["tr"]
                    p.append(_zone(_DZ_FX,_DZ_FY,_DZ_LW,_dz_top_h,_tl[0],_tl[1],[],_tl[3]))
                    p.append(_zone(_DZ_FX+_DZ_LW+_DZ_CW,_DZ_FY,_DZ_RW,_dz_top_h,
                                   _tr[0],_tr[1],_dz_tr_ml,_tr[3]))

                    # main aisle
                    _ay=_DZ_FY+_dz_top_h
                    p.append(f'<rect x="{_DZ_FX}" y="{_ay}" width="{_DZ_FW}" height="{_DZ_AIL}" fill="#f0f0f0"/>')
                    p.append(f'<line x1="{_DZ_FX}" y1="{_ay}" x2="{_DZ_FX+_DZ_FW}" y2="{_ay}"'
                             f' stroke="#bbb" stroke-width=".8" stroke-dasharray="8,4"/>')
                    p.append(f'<line x1="{_DZ_FX}" y1="{_ay+_DZ_AIL}" x2="{_DZ_FX+_DZ_FW}" y2="{_ay+_DZ_AIL}"'
                             f' stroke="#bbb" stroke-width=".8" stroke-dasharray="8,4"/>')
                    p.append(f'<text x="{_DZ_FX+_DZ_FW//2}" y="{_ay+_DZ_AIL//2}" font-size="7.5"'
                             f' text-anchor="middle" fill="#aaa" font-family="Arial" font-weight="700"'
                             f' dominant-baseline="central" letter-spacing="2">MAIN AISLE</text>')

                    # cross aisle divider
                    _cax=_DZ_FX+_DZ_LW
                    p.append(f'<rect x="{_cax}" y="{_dz_ymid}" width="{_DZ_CW}" height="{_dz_mid_h}" fill="#f9f9f9"/>')
                    p.append(f'<line x1="{_cax}" y1="{_dz_ymid}" x2="{_cax}" y2="{_dz_ymid+_dz_mid_h}"'
                             f' stroke="#ccc" stroke-width=".7" stroke-dasharray="4,3"/>')
                    p.append(f'<line x1="{_cax+_DZ_CW}" y1="{_dz_ymid}" x2="{_cax+_DZ_CW}" y2="{_dz_ymid+_dz_mid_h}"'
                             f' stroke="#ccc" stroke-width=".7" stroke-dasharray="4,3"/>')

                    # left & right column zones
                    for (_zx,_zy,_zw,_zh),(ml,zd) in zip(
                            _dz_lpos, zip(_dz_left_mls,_dz_zs["left"])):
                        p.append(_zone(_zx,_zy,_zw,_zh,zd[0],zd[1],ml,zd[3]))
                    for (_zx,_zy,_zw,_zh),(ml,zd) in zip(
                            _dz_rpos, zip(_dz_right_mls,_dz_zs["right"])):
                        p.append(_zone(_zx,_zy,_zw,_zh,zd[0],zd[1],ml,zd[3]))

                    # service aisle
                    _say=_dz_ybot-_DZ_AIL
                    p.append(f'<rect x="{_DZ_FX}" y="{_say}" width="{_DZ_FW}" height="{_DZ_AIL}" fill="#f0f0f0"/>')
                    p.append(f'<line x1="{_DZ_FX}" y1="{_say}" x2="{_DZ_FX+_DZ_FW}" y2="{_say}"'
                             f' stroke="#bbb" stroke-width=".8" stroke-dasharray="8,4"/>')
                    p.append(f'<line x1="{_DZ_FX}" y1="{_say+_DZ_AIL}" x2="{_DZ_FX+_DZ_FW}" y2="{_say+_DZ_AIL}"'
                             f' stroke="#bbb" stroke-width=".8" stroke-dasharray="8,4"/>')
                    p.append(f'<text x="{_DZ_FX+_DZ_FW//2}" y="{_say+_DZ_AIL//2}" font-size="7.5"'
                             f' text-anchor="middle" fill="#aaa" font-family="Arial" font-weight="700"'
                             f' dominant-baseline="central" letter-spacing="2">SERVICE AISLE</text>')

                    # bottom zones
                    _bl=_dz_zs["bl"]; _br=_dz_zs["br"]
                    p.append(_zone(_DZ_FX,_dz_ybot,_dz_bl_w,_dz_BOT,_bl[0],_bl[1],_dz_bl_ml,_bl[3]))
                    p.append(_zone(_DZ_FX+_dz_bl_w,_dz_ybot,_dz_br_w,_dz_BOT,_br[0],_br[1],_dz_br_ml,_br[3]))

                    # FG exit band
                    _fg_c=_DZ_C["fg"]
                    p.append(f'<rect x="{_DZ_FX}" y="{_dz_yfg}" width="{_DZ_FW}" height="{_DZ_FGH}"'
                             f' fill="{_fg_c["b"]}" stroke="{_fg_c["h"]}" stroke-width="1"/>')
                    p.append(f'<text x="{_DZ_FX+_DZ_FW//2}" y="{_dz_yfg+_DZ_FGH//2-6}" font-size="10.5"'
                             f' font-weight="700" text-anchor="middle" fill="{_fg_c["h"]}"'
                             f' font-family="Arial" dominant-baseline="central">'
                             f'FINISHED GOODS EXIT &amp; LOADING DOCK</text>')
                    p.append(f'<text x="{_DZ_FX+_DZ_FW//2}" y="{_dz_yfg+_DZ_FGH//2+10}" font-size="9"'
                             f' text-anchor="middle" fill="#888" font-family="Arial"'
                             f' dominant-baseline="central">\U0001f69b \u00b7 OUTBOUND SHIPPING</text>')

                    # factory outer wall redrawn on top
                    p.append(f'<rect x="{_DZ_FX}" y="{_DZ_FY}" width="{_DZ_FW}" height="{_dz_FH}"'
                             f' fill="none" stroke="#1a2035" stroke-width="4.5" rx="4"/>')

                    # FG gate
                    p.append(f'<rect x="{_gcx-45}" y="{_DZ_FY+_dz_FH-3}" width="90" height="7"'
                             f' fill="white" stroke="none"/>')
                    p.append(f'<text x="{_gcx}" y="{_DZ_FY+_dz_FH+14}" font-size="8.5"'
                             f' font-weight="700" text-anchor="middle" fill="#334155"'
                             f' font-family="Arial">\u25bc FG EXIT</text>')

                    # legend
                    _lx=_DZ_FX; _ly=_DZ_FY+_dz_FH+28
                    p.append(f'<rect x="{_lx}" y="{_ly}" width="320" height="68"'
                             f' fill="white" stroke="#ddd" stroke-width=".8" rx="4"/>')
                    p.append(f'<text x="{_lx+10}" y="{_ly+14}" font-size="9" font-weight="700"'
                             f' fill="#333" font-family="Arial">LEGEND</text>')
                    for _li,(_ls,_lf,_ls2) in enumerate([
                        ("ON","#EAF3DE","#3B6D11"),
                        ("OFF","#FCEBEB","#791F1F"),
                        ("MAINT","#FAEEDA","#633806")]):
                        _lbx=_lx+10+_li*100; _lby=_ly+34
                        p.append(f'<rect x="{_lbx}" y="{_lby-10}" width="28" height="20"'
                                 f' fill="{_lf}" stroke="{_ls2}" stroke-width="1" rx="2"/>')
                        p.append(f'<text x="{_lbx+33}" y="{_lby}" font-size="8.5"'
                                 f' fill="#555" font-family="Arial" dominant-baseline="central">{_ls}</text>')
                    p.append(f'<text x="{_lx+10}" y="{_ly+56}" font-size="7.5" fill="#bbb"'
                             f' font-family="Arial">'
                             f'\u25a0 = machine \u00b7 \u25ef\u25ef = workers \u00b7 dashed = work area</text>')

                    # notes
                    _nx=_DZ_FX+340; _ny=_ly
                    p.append(f'<rect x="{_nx}" y="{_ny}" width="{_DZ_FW-340}" height="68"'
                             f' fill="white" stroke="#ddd" stroke-width=".8" rx="4"/>')
                    p.append(f'<text x="{_nx+10}" y="{_ny+14}" font-size="9" font-weight="700"'
                             f' fill="#333" font-family="Arial">NOTES</text>')
                    for _ni,_nt in enumerate([
                        "1. Status and operators from live Excel data",
                        "2. Zone widths proportional to real floor plan",
                        "3. draw.io style \u2014 not a DXF-based layout"]):
                        p.append(f'<text x="{_nx+10}" y="{_ny+30+_ni*14}" font-size="8"'
                                 f' fill="#666" font-family="Arial">{_nt}</text>')

                    return (f'<svg viewBox="0 0 {_dz_SVG_W} {_dz_SVG_H}"'
                            f' xmlns="http://www.w3.org/2000/svg"'
                            f' style="width:100%;height:auto;display:block">'
                            + "".join(p) + "</svg>")

                # ── render two tabs ───────────────────────────────────────────
                _dz_tabA, _dz_tabC = st.tabs(
                    ["\U0001f3d7\ufe0f  Swimlane containers (A)",
                     "\U0001f4cb  Accent border grid (C)"])
                _dz_cmp_h = max(900, _dz_SVG_H + 60)

                _dz_tt = """<div id="dz-tt" style="position:fixed;display:none;background:#1a2035;color:white;
  padding:10px 14px;border-radius:8px;font-family:Arial,sans-serif;font-size:12.5px;
  pointer-events:none;z-index:9999;border-left:3px solid #22c55e;
  box-shadow:0 4px 18px rgba(0,0,0,0.45);min-width:170px;line-height:1.6"></div>
<script>
const _dtt=document.getElementById('dz-tt');
document.querySelectorAll('[data-mname]').forEach(el=>{
  el.addEventListener('mouseenter',()=>{
    const st=el.dataset.mstatus,n=parseInt(el.dataset.mops)||0;
    const sc=st==='ON'?'#22c55e':st==='OFF'?'#ef4444':st==='MAINTENANCE'?'#f59e0b':'#94a3b8';
    _dtt.style.borderLeftColor=sc;
    _dtt.innerHTML='<div style="font-weight:700;font-size:13.5px;margin-bottom:5px">'+el.dataset.mname+'</div>'
      +'<div style="margin-bottom:3px">Status\u00a0\u00a0<span style="color:'+sc+';font-weight:700">'+st+'</span></div>'
      +'<div style="color:#94a3b8">\U0001F477 '+n+' operator'+(n!==1?'s':'')+'</div>';
    _dtt.style.display='block';
  });
  el.addEventListener('mousemove',e=>{
    _dtt.style.left=(e.clientX+16)+'px';
    _dtt.style.top=(e.clientY-12)+'px';
  });
  el.addEventListener('mouseleave',()=>_dtt.style.display='none');
});
</script>"""
                with _dz_tabA:
                    _html_A = (f'<html><body style="margin:0;padding:0;background:white">'
                               f'{_dz_build("A")}{_dz_tt}</body></html>')
                    _cmp_dz.html(_html_A, height=_dz_cmp_h, scrolling=False)
                    st.caption("\U0001f3d7\ufe0f Style A \u00b7 Swimlane containers \u00b7 "
                               "Colored header band per zone type \u00b7 Hover any machine for details")

                with _dz_tabC:
                    _html_C = (f'<html><body style="margin:0;padding:0;background:white">'
                               f'{_dz_build("C")}{_dz_tt}</body></html>')
                    _cmp_dz.html(_html_C, height=_dz_cmp_h, scrolling=False)
                    st.caption("\U0001f4cb Style C \u00b7 Accent border grid \u00b7 "
                               "Clean white zones with colored left stripe \u00b7 Best for PDF export")

            else:
                # ── AUTOCAD ORIGINAL: DXF-rendered image with status dots ──

                _dark_path = _area_cfg["layout_dark"]
                if os.path.exists(_dark_path):
                    with open(_dark_path, "rb") as _f:
                        _map_img = Image.open(io.BytesIO(_f.read()))
                else:
                    _map_img = img

                # Theme-aware plotly bg
                _2d_bg = "#080808" if st.session_state.theme == "dark" else "#f5f5f5"
                _2d_legend_bg = "rgba(8,8,8,0.88)" if st.session_state.theme == "dark" else "rgba(245,245,245,0.92)"
                _2d_legend_border = "#2a2a2a" if st.session_state.theme == "dark" else "#d0d0d0"
                _2d_legend_txt = "#f0f0f0" if st.session_state.theme == "dark" else "#111111"
                _2d_hover_bg = "#1e1e1e" if st.session_state.theme == "dark" else "#ffffff"
                _2d_hover_border = "#2a2a2a" if st.session_state.theme == "dark" else "#d0d0d0"
                _2d_hover_txt = "#f0f0f0" if st.session_state.theme == "dark" else "#111111"
                _label_txt_col = "#ffffff" if st.session_state.theme == "dark" else "#111111"

                fig2d = go.Figure()
                fig2d.add_layout_image(dict(
                    source=_map_img, x=0, y=1, xref="paper", yref="paper",
                    sizex=1, sizey=1, xanchor="left", yanchor="top",
                    layer="below", sizing="stretch", opacity=1.0,
                ))
                _is_ar = st.session_state.get("display_lang") == "Arabic"
                for i, row in df_display.iterrows():
                    _row_status = str(row.get("Status","")).strip()
                    nx, ny = get_coords(row["Machine"], row.get("Zone",""), custom_coords)
                    _mname_display = _tr(row["Machine"])
                    # Shorten label so it fits beside the dot
                    _short_lbl = _mname_display if len(_mname_display) <= 16 else _mname_display[:14] + "…"

                    if _row_status == "-":
                        hover = (f"<b>{_mname_display}</b><br>"
                                 f"{'النوع: منطقة / مخزن' if _is_ar else 'Type: Zone / Storage'}<br>"
                                 f"{'المنطقة' if _is_ar else 'Zone'}: {_tr(row.get('Zone','—'))}")
                        fig2d.add_trace(go.Scatter(x=[nx], y=[1-ny], mode="markers+text",
                            marker=dict(size=10, color="#555555", opacity=0.55,
                                        symbol="square", line=dict(color="rgba(200,200,200,0.35)", width=1)),
                            text=[_short_lbl],
                            textposition="middle right",
                            textfont=dict(size=8, color=_label_txt_col, family="JetBrains Mono, monospace"),
                            hovertemplate=hover+"<extra></extra>",
                            name=_mname_display, showlegend=False))
                        continue

                    col = STATUS_COLORS.get(_row_status, "#94a3b8")
                    hover = (f"<b>{_mname_display}</b><br>"
                             f"{'الحالة' if _is_ar else 'Status'}: <b>{_tr(_row_status)}</b><br>"
                             f"{'المنطقة' if _is_ar else 'Zone'}: {_tr(row.get('Zone','—'))}<br>"
                             f"{'المشغلون' if _is_ar else 'Operators'}: {row.get('Operator_Count',0)}<br>"
                             f"{'ملاحظات' if _is_ar else 'Notes'}: {str(row.get('Notes','—'))}")

                    # Outer glow ring
                    fig2d.add_trace(go.Scatter(x=[nx], y=[1-ny], mode="markers",
                        marker=dict(size=28, color=col, opacity=0.10, line=dict(width=0)),
                        hoverinfo="skip", showlegend=False))
                    # Mid glow
                    fig2d.add_trace(go.Scatter(x=[nx], y=[1-ny], mode="markers",
                        marker=dict(size=18, color=col, opacity=0.18, line=dict(width=0)),
                        hoverinfo="skip", showlegend=False))
                    # Main dot — original 11px size, label always visible beside it
                    fig2d.add_trace(go.Scatter(x=[nx], y=[1-ny],
                        mode="markers+text",
                        marker=dict(size=11, color=col,
                                    line=dict(color="rgba(255,255,255,0.92)", width=1.5)),
                        text=[_short_lbl],
                        textposition="middle right",
                        textfont=dict(size=9, color=_label_txt_col,
                                      family="Inter, sans-serif"),
                        hovertemplate=hover+"<extra></extra>",
                        name=_mname_display, showlegend=False))

                # Legend traces
                for label, col in STATUS_COLORS.items():
                    fig2d.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                        marker=dict(size=12, color=col,
                                    line=dict(color="white", width=1.5)),
                        name=_tr(label), showlegend=True))
                fig2d.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                    marker=dict(size=12, color="#555555", symbol="square",
                                line=dict(color="rgba(200,200,200,0.4)", width=1)),
                    name="Zone / Storage", showlegend=True))

                fig2d.update_layout(
                    xaxis=dict(range=[0,1], showgrid=False, zeroline=False,
                               showticklabels=False, fixedrange=True),
                    yaxis=dict(range=[0,1], showgrid=False, zeroline=False,
                               showticklabels=False, fixedrange=True, scaleanchor="x"),
                    plot_bgcolor=_2d_bg, paper_bgcolor=_2d_bg,
                    margin=dict(l=0, r=0, t=0, b=0), height=680,
                    legend=dict(bgcolor=_2d_legend_bg, bordercolor=_2d_legend_border,
                                borderwidth=1, font=dict(color=_2d_legend_txt, size=12),
                                x=0.01, y=0.99, xanchor="left", yanchor="top",
                                title=dict(text="STATUS",
                                           font=dict(color=T["text_muted"], size=10))),
                    hoverlabel=dict(bgcolor=_2d_hover_bg, bordercolor=_2d_hover_border,
                                    font=dict(color=_2d_hover_txt, size=13)),
                )
                st.plotly_chart(fig2d, use_container_width=True,
                                config={"displayModeBar": False})
                st.caption("🏭 AutoCAD floor plan · Dot size 22px · Machine name always visible · Hover for full details")

        # ── 3D ISOMETRIC ───────────────────────────────────────────────────────────
        else:
            # Camera preset buttons
            st.markdown('<div class="sec-lbl">🎥 Camera Presets</div>', unsafe_allow_html=True)
            pc1, pc2, pc3, pc4 = st.columns(4)
            preset_clicked = None
            with pc1:
                if st.button("🌐 Overview",   key="cam_ov",    use_container_width=True): preset_clicked = "overview"
            with pc2:
                if st.button("◀ Left Zone",   key="cam_left",  use_container_width=True): preset_clicked = "left_zone"
            with pc3:
                if st.button("Right Zone ▶",  key="cam_right", use_container_width=True): preset_clicked = "right_zone"
            with pc4:
                if st.button("⬆ Aisle Top",   key="cam_aisle", use_container_width=True): preset_clicked = "aisle"
            if preset_clicked:
                st.session_state.cam_preset = preset_clicked

            # ── BRANCH: Factory Simulation view (Three.js WebGL) ────────────────
            if st.session_state.get("iso_style","Technical") == "Factory Simulation":
                import json as _json

                # Build machine data list for JavaScript
                _area_key = AREAS[st.session_state.active_area]["key"]
                _m_data   = []
                for _, _r in df_display.iterrows():
                    _m_data.append({
                        "name":      _r["Machine"],
                        "status":    _r["Status"],
                        "zone":      _r.get("Zone","—"),
                        "operators": int(_r.get("Operator_Count",1)),
                    })
                _machines_json = _json.dumps(_m_data)

                # Read template and inject data
                _tpl_path = os.path.join(BASE, "assets", "factory3d_template.html")
                with open(_tpl_path, encoding='utf-8') as _f:
                    _html = _f.read()
                _html = _html.replace("__MACHINES_JSON__", _machines_json)
                _html = _html.replace('"__AREA_KEY__"', f'"{_area_key}"')

                import streamlit.components.v1 as _comps
                _comps.html(_html, height=680, scrolling=False)
                st.caption("🏭 WebGL 3D Factory · Drag to orbit · Scroll to zoom · Hover machines for details")

            else:  # Technical 3D view
                cam = CAM_PRESETS[st.session_state.cam_preset]

                fig3d = go.Figure()

                # ── Floor surface ──────────────────────────────────────────────────────
                fx = np.linspace(0, 1, 12)
                fy = np.linspace(0, 1, 12)
                fxg, fyg = np.meshgrid(fx, fy)
                fig3d.add_trace(go.Surface(
                    x=fxg, y=fyg, z=np.zeros_like(fxg),
                    colorscale=[[0,"#0a0f1a"],[1,"#0f172a"]],
                    showscale=False, opacity=1.0,
                    contours=dict(
                        x=dict(show=True,color="#1e2d45",width=1),
                        y=dict(show=True,color="#1e2d45",width=1),
                    ),
                    hoverinfo="skip",
                ))

                # ── Factory walls ──────────────────────────────────────────────────────
                WH = 0.32
                wall_segs = [
                    ([0,1,1,0,0],[0,0,0,0,0],[0,0,WH,WH,0]),  # front wall
                    ([0,1,1,0,0],[1,1,1,1,1],[0,0,WH,WH,0]),  # back wall (entrance)
                    ([0,0,0,0,0],[0,1,1,0,0],[0,0,WH,WH,0]),  # left wall
                    ([1,1,1,1,1],[0,1,1,0,0],[0,0,WH,WH,0]),  # right wall
                ]
                for wx,wy,wz in wall_segs:
                    fig3d.add_trace(go.Scatter3d(
                        x=wx,y=wy,z=wz,mode="lines",
                        line=dict(color="#1e3a5f",width=2),
                        hoverinfo="skip",showlegend=False,
                    ))

                # ── Entrance / Exit labels ─────────────────────────────────────────────
                fig3d.add_trace(go.Scatter3d(
                    x=[0.42], y=[0.02], z=[WH+0.02], mode="text",
                    text=["⬇ RAW MATERIAL ENTRANCE"],
                    textfont=dict(size=9, color="#f59e0b"),
                    hoverinfo="skip", showlegend=False,
                ))
                fig3d.add_trace(go.Scatter3d(
                    x=[0.42], y=[0.98], z=[WH+0.02], mode="text",
                    text=["⬆ FINISHED GOODS EXIT"],
                    textfont=dict(size=9, color="#22c55e"),
                    hoverinfo="skip", showlegend=False,
                ))

                # ── Aisles on floor ────────────────────────────────────────────────────
                # Main horizontal aisle (y-direction centre line)
                aisle_ny = _n(0, 76.5)[1]
                fig3d.add_trace(go.Scatter3d(
                    x=[0.06, 0.94], y=[aisle_ny, aisle_ny], z=[0.001,0.001],
                    mode="lines", line=dict(color="#f59e0b", width=4),
                    hoverinfo="skip", showlegend=False,
                ))
                # Cross aisle (x-direction divider between zones)
                aisle_nx = _n(33, 0)[0]
                fig3d.add_trace(go.Scatter3d(
                    x=[aisle_nx, aisle_nx], y=[0.04, 0.96], z=[0.001,0.001],
                    mode="lines", line=dict(color="#3b82f6", width=2),
                    hoverinfo="skip", showlegend=False,
                ))

                # ── Zone boundary rectangles ───────────────────────────────────────────
                def hex_to_rgba(h, a=0.6):
                    h = h.lstrip("#")
                    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
                    return f"rgba({r},{g},{b},{a})"

                def mx(nx_raw):
                    """Mirror X so zones appear correct from RM entrance viewpoint.
                    Left zone (DXF x~14, nx~0.14) → swapped to right side visually.
                    Right zone (DXF x~46, nx~0.53) → swapped to left side visually.
                    Formula: 0.68 - nx  (mirrors around midpoint of the two zone centres)
                    """
                    return 0.68 - nx_raw

                # Mirrored aisle divider X
                aisle_nx_m = mx(aisle_nx)

                # Zone rectangles — swap label positions to match visual swap
                for zx_raw, zcolor, zlabel, ztx_raw, zty in [
                    # After mirror: DXF-left machines appear on visual RIGHT → label RIGHT ZONE
                    ([0.04, aisle_nx, aisle_nx, 0.04, 0.04], "#a855f7", "RIGHT ZONE ▶", 0.12, 0.50),
                    # After mirror: DXF-right machines appear on visual LEFT → label LEFT ZONE
                    ([aisle_nx, 0.96, 0.96, aisle_nx, aisle_nx], "#3b82f6", "◀ LEFT ZONE", 0.68, 0.50),
                ]:
                    # Mirror the X values of zone boundary
                    zx_m = [mx(x) if 0.02 < x < 0.98 else x for x in zx_raw]
                    ztx_m = mx(ztx_raw)
                    fig3d.add_trace(go.Scatter3d(
                        x=zx_m, y=[0.04,0.04,0.96,0.96,0.04], z=[0.002]*5,
                        mode="lines", line=dict(color=zcolor, width=2),
                        hoverinfo="skip", showlegend=False,
                    ))
                    fig3d.add_trace(go.Scatter3d(
                        x=[ztx_m], y=[zty], z=[0.003], mode="text",
                        text=[zlabel], textfont=dict(size=8, color=hex_to_rgba(zcolor, 0.55)),
                        hoverinfo="skip", showlegend=False,
                    ))

                # ── Material flow arrows ───────────────────────────────────────────────
                # Mirror X so flow follows the swapped zone layout
                flow_path = [
                    (mx(_n(29.0, 130.0)[0]), _n(29.0, 130.0)[1]),   # entrance
                    (mx(_n(14.0, 102.8)[0]), _n(14.0, 102.8)[1]),   # RASA Saw
                    (mx(_n(14.0,  93.2)[0]), _n(14.0,  93.2)[1]),   # Assembly Station
                    (mx(_n(15.0,  55.8)[0]), _n(15.0,  55.8)[1]),   # Welding (mid)
                    (mx(_n(29.0,  76.5)[0]), _n(29.0,  76.5)[1]),   # Main aisle cross
                    (mx(_n(46.0, 107.4)[0]), _n(46.0, 107.4)[1]),   # Right zone start
                    (mx(_n(46.0,  47.0)[0]), _n(46.0,  47.0)[1]),   # Auto Welding
                    (mx(_n(46.0,  36.7)[0]), _n(46.0,  36.7)[1]),   # Sorting
                    (mx(_n(29.0,  19.4)[0]), _n(29.0,  19.4)[1]),   # exit
                ]
                ARROW_Z = 0.004
                FLOW_COLOR = "#06b6d4"
                for k in range(len(flow_path)-1):
                    x0,y0 = flow_path[k]
                    x1,y1 = flow_path[k+1]
                    # Dashed line segment (3 sub-segments for dash effect)
                    for seg in range(3):
                        t0 = seg/3 + 0.02
                        t1 = (seg+1)/3 - 0.02
                        sx0,sy0 = x0+t0*(x1-x0), y0+t0*(y1-y0)
                        sx1,sy1 = x0+t1*(x1-x0), y0+t1*(y1-y0)
                        fig3d.add_trace(go.Scatter3d(
                            x=[sx0,sx1], y=[sy0,sy1], z=[ARROW_Z,ARROW_Z],
                            mode="lines", line=dict(color=FLOW_COLOR, width=3),
                            hoverinfo="skip", showlegend=False,
                        ))
                    # Arrowhead marker at end
                    fig3d.add_trace(go.Scatter3d(
                        x=[x1], y=[y1], z=[ARROW_Z+0.001],
                        mode="markers",
                        marker=dict(size=5, color=FLOW_COLOR, symbol="circle",
                                    line=dict(color="white", width=1)),
                        hoverinfo="skip", showlegend=False,
                    ))

                # ── Machines: shapes + status pins + workers ───────────────────────────
                # Scale factor: make machines bigger and compress floor to fill space
                SCALE = 1.9   # multiply all machine shape dimensions by this

                WORKER_OFFSETS = [
                    (-0.030, -0.028), (0.030, -0.028), (-0.030, 0.028), (0.030, 0.028),
                    (0.0,    -0.040), (0.0,   0.040),
                ]

                for i, row in df_display.iterrows():
                    nx_raw, ny = raw_coords(row["Machine"], row.get("Zone",""), custom_coords)
                    nx = mx(nx_raw)
                    mtype     = machine_type(row["Machine"])
                    color     = STATUS_COLORS.get(row["Status"], "#94a3b8")
                    ops       = int(row.get("Operator_Count", 0))
                    notes     = str(row.get("Notes","—"))
                    zone      = row.get("Zone","—")
                    hover     = (f"<b>{row['Machine']}</b><br>Status: {row['Status']}<br>"
                                 f"Zone: {zone}<br>Operators: {ops}<br>Notes: {notes}")

                    # Machine shape — colored by status
                    add_machine_shape(fig3d, nx, ny, mtype, color,
                                      row["Status"], hover, scale=SCALE)

                    # ── Floating name label above machine ─────────────────────────────
                    if st.session_state.show_labels:
                        box_top_label = get_box_top(mtype, SCALE)
                        pin_h_label   = {"ON": 0.14, "OFF": 0.045, "MAINTENANCE": 0.09}.get(row["Status"], 0.06) * SCALE
                        label_z       = box_top_label + pin_h_label + 0.045 * SCALE
                        # Shorten long names for cleaner display
                        short_name = row["Machine"]
                        if len(short_name) > 18:
                            # Abbreviate common words
                            short_name = (short_name
                                .replace("Machine", "M/C")
                                .replace("Station", "Stn")
                                .replace("Vertical", "Vert")
                                .replace("Welding", "Weld")
                                .replace("Production", "Prod")
                                .replace("Sorting Area", "Sort")
                                .replace("Leadgers", "Ldg"))
                            if len(short_name) > 18:
                                short_name = short_name[:16] + "…"
                        lbl_color = STATUS_COLORS.get(row["Status"], "#94a3b8")
                        fig3d.add_trace(go.Scatter3d(
                            x=[nx], y=[ny], z=[label_z],
                            mode="text",
                            text=[short_name],
                            textfont=dict(size=7, color=lbl_color),
                            hoverinfo="skip", showlegend=False,
                        ))

                    # Status pin above machine (scaled)
                    box_top  = get_box_top(mtype, SCALE)
                    pin_h    = {"ON": 0.14, "OFF": 0.045, "MAINTENANCE": 0.09}.get(row["Status"], 0.06) * SCALE

                    fig3d.add_trace(go.Scatter3d(
                        x=[nx,nx], y=[ny,ny], z=[box_top, box_top+pin_h],
                        mode="lines", line=dict(color=color, width=3),
                        hoverinfo="skip", showlegend=False,
                    ))
                    fig3d.add_trace(go.Scatter3d(
                        x=[nx], y=[ny], z=[box_top+pin_h+0.015*SCALE],
                        mode="markers",
                        marker=dict(size=9, color=color,
                                    line=dict(color="white", width=1.5)),
                        hovertemplate=hover+"<extra></extra>",
                        showlegend=False,
                    ))

                    # Pulse rings on floor
                    pr = np.linspace(0, 2*np.pi, 24)
                    if row["Status"] == "ON":
                        for r, w, op in [(0.030*SCALE, 2, 0.45), (0.050*SCALE, 1, 0.18)]:
                            fig3d.add_trace(go.Scatter3d(
                                x=nx+r*np.cos(pr), y=ny+r*np.sin(pr),
                                z=np.full_like(pr, 0.003),
                                mode="lines", line=dict(color="#22c55e", width=w),
                                opacity=op, hoverinfo="skip", showlegend=False,
                            ))
                    elif row["Status"] == "MAINTENANCE":
                        fig3d.add_trace(go.Scatter3d(
                            x=nx+0.034*SCALE*np.cos(pr), y=ny+0.034*SCALE*np.sin(pr),
                            z=np.full_like(pr, 0.003),
                            mode="lines", line=dict(color="#f59e0b", width=2, dash="dash"),
                            opacity=0.5, hoverinfo="skip", showlegend=False,
                        ))

                    # Worker figures
                    worker_color = "#94a3b8" if row["Status"] == "OFF" else "#e2e8f0"
                    for w in range(min(ops, 6)):
                        wx_off, wy_off = WORKER_OFFSETS[w]
                        add_worker(fig3d, nx+wx_off*SCALE, ny+wy_off*SCALE, 0.0, worker_color)

                # Legend
                for label, col in STATUS_COLORS.items():
                    fig3d.add_trace(go.Scatter3d(
                        x=[None],y=[None],z=[None],mode="markers",
                        marker=dict(size=7,color=col),name=label,showlegend=True,
                    ))
                # Flow arrow legend
                fig3d.add_trace(go.Scatter3d(
                    x=[None],y=[None],z=[None],mode="lines",
                    line=dict(color="#06b6d4",width=3),
                    name="Material Flow",showlegend=True,
                ))

                # ── Roof / ceiling (toggled by sidebar) ───────────────────────────────
                if st.session_state.show_roof:
                    # Main roof panel — semi-transparent mesh over factory footprint
                    roof_z = WH  # sits at wall height
                    rx = np.array([[0, 1], [0, 1]])
                    ry = np.array([[0, 0], [1, 1]])
                    rz = np.full((2, 2), roof_z)
                    fig3d.add_trace(go.Surface(
                        x=rx, y=ry, z=rz,
                        colorscale=[[0, "rgba(30,58,95,0.35)"], [1, "rgba(59,130,246,0.18)"]],
                        showscale=False,
                        opacity=0.38,
                        hoverinfo="skip",
                        showlegend=False,
                        lighting=dict(ambient=0.8, diffuse=0.5),
                    ))
                    # Roof edge outline (gives it a frame / structural feel)
                    roof_edges = [
                        ([0,1],[0,0],[roof_z,roof_z]),
                        ([1,1],[0,1],[roof_z,roof_z]),
                        ([1,0],[1,1],[roof_z,roof_z]),
                        ([0,0],[1,0],[roof_z,roof_z]),
                        # Ridge line across centre
                        ([0,1],[0.5,0.5],[roof_z+0.04,roof_z+0.04]),
                    ]
                    for ex, ey, ez in roof_edges:
                        fig3d.add_trace(go.Scatter3d(
                            x=ex, y=ey, z=ez, mode="lines",
                            line=dict(color="#3b82f6", width=2),
                            hoverinfo="skip", showlegend=False,
                        ))
                    # Roof support beams (cross the factory width at intervals)
                    for beam_y in [0.25, 0.5, 0.75]:
                        fig3d.add_trace(go.Scatter3d(
                            x=[0, 1], y=[beam_y, beam_y], z=[roof_z, roof_z],
                            mode="lines",
                            line=dict(color="#1e3a5f", width=3),
                            hoverinfo="skip", showlegend=False,
                        ))
                    # Skylights — four rectangular bright patches on roof
                    for slx, sly in [(0.2,0.3),(0.6,0.3),(0.2,0.65),(0.6,0.65)]:
                        slw, sld = 0.12, 0.08
                        sx = np.array([[slx-slw,slx+slw],[slx-slw,slx+slw]])
                        sy = np.array([[sly-sld,sly-sld],[sly+sld,sly+sld]])
                        sz = np.full((2,2), roof_z+0.001)
                        fig3d.add_trace(go.Surface(
                            x=sx, y=sy, z=sz,
                            colorscale=[[0,"rgba(186,230,253,0.6)"],[1,"rgba(224,242,254,0.8)"]],
                            showscale=False, opacity=0.65,
                            hoverinfo="skip", showlegend=False,
                        ))

                fig3d.update_layout(
                    scene=dict(
                        xaxis=dict(showgrid=True,gridcolor="#1e2d45",showticklabels=False,
                                   title="",backgroundcolor="#050a12",showbackground=True,zeroline=False),
                        yaxis=dict(showgrid=True,gridcolor="#1e2d45",showticklabels=False,
                                   title="",backgroundcolor="#050a12",showbackground=True,zeroline=False),
                        zaxis=dict(showgrid=False,showticklabels=False,title="",
                                   backgroundcolor="#050a12",showbackground=True,range=[0,0.75]),
                        camera=dict(**cam, up=dict(x=0,y=0,z=1)),
                        bgcolor="#050a12",
                        aspectmode="manual",
                        aspectratio=dict(x=1.6, y=2.8, z=0.65),
                    ),
                    paper_bgcolor="#0a0e17",
                    margin=dict(l=0,r=0,t=0,b=0), height=700,
                    legend=dict(
                        bgcolor="#111827", bordercolor="#1e2d45", borderwidth=1,
                        font=dict(color="#e2e8f0",size=11), x=0.01, y=0.99,
                        title=dict(text="LEGEND",font=dict(color="#64748b",size=10)),
                    ),
                    hoverlabel=dict(bgcolor="#1e293b",bordercolor="#334155",
                                    font=dict(color="#e2e8f0",size=13)),
                )
                st.plotly_chart(fig3d, use_container_width=True,
                                config={"displayModeBar": True, "displaylogo": False})
                st.caption("💡 Machine shapes vary by type · Green rings = ON · Amber dashed = MAINTENANCE · 👤 = workers · ── = material flow")

    # ══════════════════════════════════════════════════════════════════════════════
    # MACHINE LIST — Independent scrollable panel
    # ══════════════════════════════════════════════════════════════════════════════
    with col_list:
        st.markdown(
            '<div class="panel-header">'
            '<div class="panel-accent"></div>'
            '<div class="panel-title">Machine List</div>'
            '</div>',
            unsafe_allow_html=True)
        st.caption("All machines  |  Scrolls independently")

        import re as _re

        def base_name(name):
            return _re.sub(r'\s*\d+\s*$', '', name).strip()

        # Show ALL individual machines in the scrollable card list
        cards_html = '<div class="machine-scroll-wrapper">'
        for _, row in df_display.iterrows():
            status  = str(row.get("Status","")).strip()
            is_zone = (status == "-")   # non-machine classification
            emoji   = "🗂️" if is_zone else STATUS_EMOJI.get(status, "⚪")
            ops     = row.get("Operator_Count", 0)
            ops_str = "—" if is_zone else str(ops)
            zone    = _tr(row.get("Zone", "—"))
            machine = row["Machine"]
            machine_display = _tr(machine)
            is_sel  = st.session_state.selected_machine == base_name(machine)
            sel_cls = "sel" if is_sel else ""
            pill_cls= "p-ZONE" if is_zone else f"p-{status}"
            pill_lbl= ("منطقة" if st.session_state.get("display_lang")=="Arabic" else "ZONE") if is_zone else _tr(status)
            cards_html += (f'<div class="mcard {sel_cls}" style="{"opacity:0.7;" if is_zone else ""}">'
                           f'<div class="mname">{emoji} {machine_display}</div>'
                           f'<div class="mmeta">'
                           f'<span class="mpill {pill_cls}" '
                           f'style="{"background:rgba(100,116,139,0.15);color:#64748b;border-color:#64748b;" if is_zone else ""}">'
                           f'{pill_lbl}</span>'
                           f'<span class="mops">&#128119; {ops_str}</span>'
                           f'<span class="mops">{zone}</span>'
                           f'</div></div>')
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        # Selectbox — deduplicated base names (for report)
        unique_machine_names = list(dict.fromkeys(base_name(m) for m in df_display["Machine"].tolist()))
        st.markdown('<div class="sec-lbl" style="margin-top:8px">Select machine:</div>',
                    unsafe_allow_html=True)
        sel_choice = st.selectbox(
            "Select machine for detail",
            ["— none —"] + unique_machine_names,
            label_visibility="collapsed",
            key="machine_select_box",
        )
        if sel_choice and sel_choice != "— none —":
            st.session_state.selected_machine = sel_choice
        elif sel_choice == "— none —":
            st.session_state.selected_machine = None

        st.markdown('<hr class="s">', unsafe_allow_html=True)
        st.markdown(
            '<div class="panel-header">'
            '<div class="panel-accent" style="background:#8b5cf6"></div>'
            '<div class="panel-title">Zone Summary</div>'
            '</div>',
            unsafe_allow_html=True)
        # Exclude non-machine zones (Status='-') from the ON/OFF count table
        _zone_machines = df[df["Status"] != "-"]
        zone_df = _zone_machines.groupby("Zone")["Status"].value_counts().unstack(fill_value=0)
        # Count zone/storage entries separately
        _zone_storage = df[df["Status"] == "-"].groupby("Zone").size()
        if not _zone_storage.empty:
            zone_df["ZONE"] = _zone_storage.reindex(zone_df.index, fill_value=0)
        # Zone labels come directly from the Zone column in the Excel file
        # No remapping needed — show exactly what is in the data
        st.dataframe(zone_df, use_container_width=True, height=140)

    # ══════════════════════════════════════════════════════════════════════════════
    # MACHINE REPORT PANEL
    # ══════════════════════════════════════════════════════════════════════════════
    import re as _re2

    def _val(v, suffix="", fmt=None):
        if v is None or (isinstance(v, float) and pd.isna(v)): return "—"
        if fmt == "int":   return f"{int(v):,}{suffix}"
        if fmt == "float": return f"{v:.1f}{suffix}"
        return f"{v}{suffix}"

    sel_name = st.session_state.selected_machine
    if sel_name:
        base_pat = _re2.sub(r'\s*\d+\s*$', '', sel_name).strip()
        matched  = df[df["Machine"].apply(lambda m: _re2.sub(r'\s*\d+\s*$','',m).strip()) == base_pat]

        if not matched.empty:
            first_exact = sel_name if sel_name in df["Machine"].values else matched.iloc[0]["Machine"]
            report = get_machine_report(first_exact, df, st.session_state.rate_df)
            report["machines_same_type"] = len(matched)
            report["total_operators"]    = int(matched["Operator_Count"].sum())

            statuses = matched["Status"].tolist()
            if all(s == "ON" for s in statuses):           agg_st = "ON"
            elif any(s == "MAINTENANCE" for s in statuses): agg_st = "MAINTENANCE"
            elif all(s == "OFF" for s in statuses):         agg_st = "OFF"
            else:                                           agg_st = "ON"
            n_on_m  = sum(1 for s in statuses if s == "ON")
            n_off_m = sum(1 for s in statuses if s == "OFF")
            n_mn_m  = sum(1 for s in statuses if s == "MAINTENANCE")
            color   = STATUS_COLORS.get(agg_st, "#94a3b8")

            rate_val   = _val(report["rate"], " pcs/hr", "int")
            m_type_val = _val(report["machines_same_type"])
            ops_val    = _val(report["total_operators"])
            zone_val   = _val(report.get("zone") or (matched.iloc[0].get("Zone") if not matched.empty else None))
            notes_val  = report.get("notes") or "—"
            total_rate = report["rate"] * n_on_m if report.get("rate") and n_on_m else None
            total_rate_val = _val(total_rate, " pcs/hr", "int")
            status_bd  = f"🟢 {n_on_m} ON &nbsp;·&nbsp; 🔴 {n_off_m} OFF &nbsp;·&nbsp; 🟡 {n_mn_m} MAINT"

            # Build report HTML
            s  = T["surface"];  s2 = T["surface2"]; bd = T["border"]
            tx = T["text"];     tm = T["text_muted"]
            _is_ar = st.session_state.get("display_lang") == "Arabic"
            _dir   = 'direction:rtl;text-align:right;' if _is_ar else ''
            _lbl_rate   = "المعدل / وحدة" if _is_ar else "RATE / UNIT"
            _lbl_trate  = "المعدل الكلي (جاري)" if _is_ar else "TOTAL RATE (RUNNING)"
            _lbl_fleet  = "الأسطول والقوى العاملة" if _is_ar else "Fleet & Workforce"
            _lbl_prod   = "الإنتاج" if _is_ar else "Production"
            _lbl_count  = "عدد الماكينات" if _is_ar else "MACHINES"
            _lbl_ops    = "إجمالي المشغلين" if _is_ar else "TOTAL OPERATORS"
            _lbl_zone   = "المنطقة" if _is_ar else "ZONE"
            _lbl_notes  = "ملاحظات" if _is_ar else "NOTES"
            _lbl_report = "تقرير الماكينة" if _is_ar else "MACHINE REPORT"
            _display_name = _tr(sel_name)
            _display_st   = _tr(agg_st)
            h  = []
            h.append(f'<div style="background:{s};border:2px solid {color};border-radius:16px;padding:22px 26px;border-top:4px solid {color};box-shadow:0 8px 32px rgba(0,0,0,0.2);margin-bottom:10px">')
            h.append(f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid {bd}">')
            h.append(f'<div style="display:flex;align-items:center;gap:12px">')
            h.append(f'<div style="font-family:Rajdhani,sans-serif;font-size:22px;font-weight:700;color:{tx};{_dir}">{_display_name}</div>')
            h.append(f'<span style="font-size:10px;padding:3px 10px;border-radius:10px;background:rgba(0,0,0,0.25);color:{color};border:1px solid {color};font-family:Share Tech Mono,monospace;font-weight:700">{_display_st}</span>')
            h.append(f'</div><div style="font-family:Share Tech Mono,monospace;font-size:10px;color:{tm};letter-spacing:1px">{_lbl_report}</div></div>')
            h.append(f'<div style="font-size:11px;color:{tm};font-family:Share Tech Mono,monospace;margin-bottom:14px;padding:8px 12px;background:{s2};border-radius:8px">{status_bd}</div>')
            h.append(f'<div style="font-family:Share Tech Mono,monospace;font-size:9px;font-weight:600;letter-spacing:2px;color:{tm};text-transform:uppercase;margin-bottom:8px">⚡ {_lbl_prod}</div>')
            h.append(f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">')
            h.append(f'<div style="background:{s2};border:1px solid {bd};border-radius:10px;padding:14px 16px"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{tm};margin-bottom:6px">{_lbl_rate}</div><div style="font-family:Rajdhani,sans-serif;font-size:26px;font-weight:700;color:{tx}">{rate_val}</div></div>')
            h.append(f'<div style="background:{s2};border:1px solid {bd};border-radius:10px;padding:14px 16px"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{tm};margin-bottom:6px">{_lbl_trate}</div><div style="font-family:Rajdhani,sans-serif;font-size:26px;font-weight:700;color:{tx}">{total_rate_val}</div></div></div>')
            h.append(f'<div style="font-family:Share Tech Mono,monospace;font-size:9px;font-weight:600;letter-spacing:2px;color:{tm};text-transform:uppercase;margin-bottom:8px">👷 {_lbl_fleet}</div>')
            h.append(f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px">')
            h.append(f'<div style="background:{s2};border:1px solid {bd};border-radius:10px;padding:14px 16px"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{tm};margin-bottom:6px">{_lbl_count}</div><div style="font-family:Rajdhani,sans-serif;font-size:26px;font-weight:700;color:{tx}">{m_type_val}</div></div>')
            h.append(f'<div style="background:{s2};border:1px solid {bd};border-radius:10px;padding:14px 16px"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{tm};margin-bottom:6px">{_lbl_ops}</div><div style="font-family:Rajdhani,sans-serif;font-size:26px;font-weight:700;color:{tx}">{ops_val}</div></div>')
            h.append(f'<div style="background:{s2};border:1px solid {bd};border-radius:10px;padding:14px 16px"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{tm};margin-bottom:6px">{_lbl_zone}</div><div style="font-family:Rajdhani,sans-serif;font-size:26px;font-weight:700;color:{tx}">{_tr(zone_val)}</div></div></div>')
            h.append(f'<div style="background:{s2};border:1px solid {bd};border-radius:10px;padding:12px 16px;display:flex;gap:10px"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{tm};white-space:nowrap">📝 {_lbl_notes}</div><div style="font-size:12px;color:{tx}">{notes_val}</div></div>')
            h.append('</div>')
            report_html = "".join(h)

            st.markdown("---")
            st.markdown(report_html, unsafe_allow_html=True)
            if st.button("✖ Close Report", key="close_detail"):
                st.session_state.selected_machine = None
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════════
    # ANALYTICS
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-lbl">📈 Analytics Overview</div>', unsafe_allow_html=True)
    ca, cb, cc = st.columns(3)
    _lc = dict(plot_bgcolor=T["surface"],paper_bgcolor=T["paper_bg"],
               font=dict(color=T["text"],size=11),height=250,margin=dict(l=10,r=10,t=34,b=10))

    with ca:
        zc = df.groupby(["Zone","Status"]).size().reset_index(name="Count")
        bar = go.Figure()
        for s,c in STATUS_COLORS.items():
            sub=zc[zc["Status"]==s]
            bar.add_trace(go.Bar(x=sub["Zone"],y=sub["Count"],name=s,marker_color=c,
                                 opacity=0.85,text=sub["Count"],textposition="auto"))
        bar.update_layout(**_lc,barmode="group",
            legend=dict(bgcolor=T["surface"],bordercolor=T["border"],borderwidth=1,font=dict(size=10,color=T["text"])),
            xaxis=dict(gridcolor=T["grid"]),yaxis=dict(gridcolor=T["grid"]),
            title=dict(text="Zone Breakdown",font=dict(size=12,color=T["text_muted"])))
        st.plotly_chart(bar,use_container_width=True,config={"displayModeBar":False})

    with cb:
        sv=df["Status"].value_counts().reset_index(); sv.columns=["Status","Count"]
        pie=go.Figure(go.Pie(
            labels=sv["Status"],values=sv["Count"],
            marker=dict(colors=[STATUS_COLORS.get(s,"#94a3b8") for s in sv["Status"]],
                        line=dict(color=T["bg"],width=2)),
            hole=0.58,textinfo="label+percent",textfont=dict(color=T["text"],size=11)))
        pie.update_layout(**_lc,showlegend=False,
            title=dict(text="Fleet Distribution",font=dict(size=12,color=T["text_muted"])),
            annotations=[dict(text=f"<b>{uptime}%</b><br>Up",
                              font=dict(size=16,color="#22c55e"),showarrow=False)])
        st.plotly_chart(pie,use_container_width=True,config={"displayModeBar":False})

    with cc:
        od=df.groupby("Zone")["Operator_Count"].sum().reset_index(); od.columns=["Zone","Ops"]
        hb=go.Figure(go.Bar(x=od["Ops"],y=od["Zone"],orientation="h",
            marker=dict(color=od["Ops"],
                        colorscale=[[0,"#1e3a5f"],[0.5,"#3b82f6"],[1,"#06b6d4"]],
                        showscale=False),
            text=od["Ops"],textposition="auto"))
        hb.update_layout(**_lc,xaxis=dict(gridcolor=T["grid"]),yaxis=dict(gridcolor=T["grid"]),
            title=dict(text="Operators per Zone",font=dict(size=12,color=T["text_muted"])))
        st.plotly_chart(hb,use_container_width=True,config={"displayModeBar":False})

    # ══════════════════════════════════════════════════════════════════════════════
    # CELL INTELLIGENCE
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-lbl">🏭 Cell Intelligence — Capacity, BOM & Operations</div>', unsafe_allow_html=True)

    cell_df_ci  = st.session_state.cell_df
    bom_data_ci = st.session_state.bom_data

    if cell_df_ci is not None and not cell_df_ci.empty:

        LEVEL_COLORS = {4: "#22c55e", 3: "#8b5cf6", 2: "#0ea5e9", 1: "#64748b"}
        LEVEL_LABELS = {4: "600 Finished Good", 3: "500 Semi-Finished",
                        2: "400 Sub-Assembly",  1: "200 Raw Material"}

        cell_names_ci = cell_df_ci["Cell"].tolist()
        sel_cell = st.selectbox("Select Cell", cell_names_ci,
                                 key="sel_cell_intelligence", label_visibility="collapsed")

        cell_row  = cell_df_ci[cell_df_ci["Cell"] == sel_cell].iloc[0]
        capacity  = cell_row["Capacity"]
        top_item  = cell_row["Top_Item"]
        top_desc  = cell_row["Top_Desc"]
        cap_str   = f"{int(capacity):,}" if pd.notna(capacity) else "—"
        bom_nodes = bom_data_ci.get(sel_cell, [])

        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            st.markdown(f'<div style="background:{T["surface"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;border-left:4px solid #3b82f6"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{T["text_muted"]};margin-bottom:6px">CELL NAME</div><div style="font-family:Rajdhani,sans-serif;font-size:20px;font-weight:700;color:{T["text"]}">{sel_cell}</div></div>', unsafe_allow_html=True)
        with kc2:
            st.markdown(f'<div style="background:{T["surface"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;border-left:4px solid #22c55e"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{T["text_muted"]};margin-bottom:6px">DAILY CAPACITY</div><div style="font-family:Rajdhani,sans-serif;font-size:28px;font-weight:700;color:#22c55e">{cap_str} <span style="font-size:13px;font-weight:400">pcs/day</span></div></div>', unsafe_allow_html=True)
        with kc3:
            st.markdown(f'<div style="background:{T["surface"]};border:1px solid {T["border"]};border-radius:12px;padding:16px 20px;border-left:4px solid #f59e0b"><div style="font-family:Share Tech Mono,monospace;font-size:9px;letter-spacing:2px;color:{T["text_muted"]};margin-bottom:4px">TOP SELLING PRODUCT</div><div style="font-size:13px;font-weight:600;color:#f59e0b;line-height:1.3">{top_desc or "—"}</div><div style="font-size:10px;color:{T["text_muted"]};font-family:Share Tech Mono,monospace;margin-top:4px">{top_item}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        tab_bom, tab_ops = st.tabs(["📦 Bill of Materials", "⚙️ Operations Sequence"])

        with tab_bom:
            if not bom_nodes:
                st.info("No BOM data for this cell.")
            else:
                view_col, _ = st.columns([1, 3])
                with view_col:
                    bom_view = st.radio("Display", ["Codes only", "Descriptions only"],
                                         horizontal=True, key="bom_view_toggle",
                                         label_visibility="collapsed")
                show_desc = (bom_view == "Descriptions only")

                from collections import defaultdict
                by_level = defaultdict(list)
                for n in bom_nodes:
                    by_level[n["level"]].append(n)

                levels_present = sorted(by_level.keys(), reverse=True)
                bom_parts = ['<div style="overflow-x:auto;padding:8px 0">']

                for lvl_idx, lvl in enumerate(levels_present):
                    nodes_at_level = by_level[lvl]
                    color = LEVEL_COLORS.get(lvl, "#64748b")
                    label = LEVEL_LABELS.get(lvl, f"Level {lvl}")

                    bom_parts.append(
                        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">' +
                        f'<span style="font-family:Share Tech Mono,monospace;font-size:9px;font-weight:700;' +
                        f'letter-spacing:1.5px;color:{color};text-transform:uppercase;' +
                        f'background:{color}22;padding:3px 10px;border-radius:12px;white-space:nowrap">{label}</span>' +
                        f'<div style="flex:1;height:1px;background:{T["border"]}"></div></div>'
                    )
                    bom_parts.append('<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:6px">')
                    for node in nodes_at_level:
                        display_text = node["description"] if show_desc else node["item"]
                        font_size = "11px" if show_desc else "11px"
                        bom_parts.append(
                            f'<div style="background:{color}15;border:2px solid {color};' +
                            f'border-radius:10px;padding:12px 18px;min-width:130px;max-width:240px;' +
                            f'text-align:center">' +
                            f'<div style="font-family:Share Tech Mono,monospace;font-size:{font_size};' +
                            f'font-weight:700;color:{color};word-break:break-word;line-height:1.4">' +
                            f'{display_text}</div></div>'
                        )
                    bom_parts.append('</div>')
                    if lvl_idx < len(levels_present) - 1:
                        bom_parts.append(
                            f'<div style="display:flex;justify-content:flex-start;padding-left:20px;' +
                            f'margin:4px 0 10px;font-size:20px;color:{T["text_muted"]}">&#8595;</div>'
                        )

                bom_parts.append('</div>')
                st.markdown("".join(bom_parts), unsafe_allow_html=True)

        with tab_ops:
            if not bom_nodes:
                st.info("No operations data for this cell.")
            else:
                items_with_ops = [n for n in bom_nodes if any(o["op_seq"] != 9990 for o in n["operations"])]
                if not items_with_ops:
                    st.info("No operation sequences found for this cell.")
                else:
                    item_options = {f"{n['item']} — {n['description']}": n for n in items_with_ops}
                    sel_item_key = st.selectbox("Select item to view its operation sequence:",
                                                 list(item_options.keys()), key="sel_ops_item")
                    sel_node = item_options[sel_item_key]
                    lvl   = sel_node["level"]
                    color = LEVEL_COLORS.get(lvl, "#64748b")
                    ops_real = [o for o in sel_node["operations"] if o["op_seq"] != 9990]
                    ops_real.sort(key=lambda o: o["op_seq"])

                    st.markdown(
                        f'<div style="background:{color}12;border:1px solid {color}44;border-radius:10px;' +
                        f'padding:12px 16px;margin:10px 0 16px"><div style="font-family:Share Tech Mono,monospace;' +
                        f'font-size:10px;color:{color};font-weight:700">{LEVEL_LABELS.get(lvl,"")}</div>' +
                        f'<div style="font-family:Rajdhani,sans-serif;font-size:16px;font-weight:700;' +
                        f'color:{T["text"]};margin-top:2px">{sel_node["description"]}</div>' +
                        f'<div style="font-size:10px;color:{T["text_muted"]};font-family:Share Tech Mono,monospace">' +
                        f'{sel_node["item"]}</div></div>',
                        unsafe_allow_html=True)

                    if not ops_real:
                        st.info("No operations defined for this item.")
                    else:
                        ops_parts = ['<div style="display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:4px 0">']
                        for k, op in enumerate(ops_real):
                            is_last = k == len(ops_real) - 1
                            ops_parts.append(
                                f'<div style="background:{T["surface"]};border:2px solid {color};' +
                                f'border-radius:10px;padding:14px 18px;min-width:120px;text-align:center">' +
                                f'<div style="font-family:Share Tech Mono,monospace;font-size:9px;' +
                                f'color:{T["text_muted"]};margin-bottom:6px">STEP {k+1}</div>' +
                                f'<div style="font-size:14px;font-weight:700;color:{color}">{op["op_desc"]}</div>' +
                                f'<div style="font-size:9px;color:{T["text_muted"]};font-family:Share Tech Mono,monospace;' +
                                f'margin-top:4px">Seq: {op["op_seq"]}</div></div>'
                            )
                            if not is_last:
                                ops_parts.append(f'<div style="font-size:22px;color:{T["text_muted"]}">&#8594;</div>')
                        ops_parts.append('</div>')
                        st.markdown("".join(ops_parts), unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)
                        ops_tbl = pd.DataFrame([
                            {"Step": k+1, "Operation": o["op_desc"], "Sequence No.": o["op_seq"]}
                            for k, o in enumerate(ops_real)
                        ])
                        st.dataframe(ops_tbl, use_container_width=True,
                                      hide_index=True, height=min(200, 40+35*len(ops_real)))

    else:
        st.info("Upload an Excel file with a 'Cell Details' sheet to see cell intelligence.")

    # Footer
    st.markdown(f"""
    <div style="text-align:center;color:{T['text_muted']};font-size:10px;margin-top:28px;
                border-top:1px solid {T['border']};padding-top:14px;
                font-family:'Share Tech Mono',monospace;letter-spacing:1.2px">
      FACTORY 5 · AREA 1 &nbsp;|&nbsp; PRODUCTION PLANNING DEPT &nbsp;|&nbsp;
      DWG NO: F5-S5-MAP-001 REV A
    </div>""", unsafe_allow_html=True)
