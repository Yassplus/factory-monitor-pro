"""
Factory Monitor Pro — Mobile View
Streamlit page optimised for phone screens (portrait, touch-first).
Run alongside app.py:  streamlit run mobile.py --server.port 8502
or add to .streamlit/pages/ for multi-page navigation.
"""

import streamlit as st
import pandas as pd
import os, re

st.set_page_config(
    page_title="Factory Monitor · Mobile",
    page_icon="🏭",
    layout="centered",
    initial_sidebar_state="collapsed",
)

BASE = os.path.dirname(os.path.abspath(__file__))
# If running from pages/ subfolder, go up one level to project root
if os.path.basename(BASE).lower() == "pages":
    BASE = os.path.dirname(BASE)

_F4_EXCEL = os.path.join(BASE, "data", "F4_A1_A2_machine_status.xlsx")
AREAS = {
    "F5 – Area 1": os.path.join(BASE, "data", "F5_A1_machine_status.xlsx"),
    "F5 – Area 2": os.path.join(BASE, "data", "F5_A2_machine_status.xlsx"),
    "F4 – Area 1": _F4_EXCEL,
    "F4 – Area 2": _F4_EXCEL,
}
# Row slices for F4 areas (shared excel)
AREA_ROWS = {
    "F4 – Area 1": (0, 15),
    "F4 – Area 2": (15, 26),
}

STATUS_COLOR = {"ON": "#22c55e", "OFF": "#ef4444", "MAINTENANCE": "#f59e0b"}
STATUS_BG    = {"ON": "#052e16", "OFF": "#450a0a", "MAINTENANCE": "#431407"}

# ── Mobile CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #070b12 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    color: #e2e8f0 !important;
}
[data-testid="stAppViewContainer"] > .main > div { padding: 0 0 80px !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stHeader"]  { display: none !important; }
footer { display: none !important; }

/* ── Top bar ── */
.mob-topbar {
    background: linear-gradient(180deg, #0d1526 0%, #070b12 100%);
    padding: 16px 20px 12px;
    border-bottom: 1px solid #1e2d45;
    position: sticky; top: 0; z-index: 100;
}
.mob-title {
    font-size: 18px; font-weight: 700; letter-spacing: 0.5px;
    color: #e2e8f0;
}
.mob-subtitle {
    font-size: 10px; color: #64748b; letter-spacing: 2px;
    text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
    margin-top: 2px;
}
.mob-live {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.3);
    border-radius: 20px; padding: 3px 10px; font-size: 10px;
    color: #22c55e; font-family: 'JetBrains Mono', monospace;
    float: right; margin-top: -22px;
}
.mob-live-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #22c55e;
    animation: blink 1.4s infinite;
}
@keyframes blink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.3;transform:scale(1.5)} }

/* ── KPI strip ── */
.mob-kpi-strip {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 8px; padding: 14px 16px;
}
.mob-kpi {
    background: #0d1526; border: 1px solid #1e2d45;
    border-radius: 12px; padding: 12px 10px; text-align: center;
}
.mob-kpi-val {
    font-size: 28px; font-weight: 700; line-height: 1;
    font-family: 'JetBrains Mono', monospace;
}
.mob-kpi-lbl {
    font-size: 9px; color: #64748b; text-transform: uppercase;
    letter-spacing: 1px; margin-top: 4px;
}

/* ── Operator alert ── */
.mob-alert {
    margin: 0 16px 8px;
    background: rgba(245,158,11,0.1);
    border: 1px solid rgba(245,158,11,0.4);
    border-radius: 10px; padding: 10px 14px;
    font-size: 11px; color: #fbbf24;
    display: flex; gap: 8px; align-items: flex-start;
}

/* ── Section header ── */
.mob-sec {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase; color: #334155;
    border-left: 3px solid #3b82f6; padding-left: 10px;
    margin: 16px 16px 8px;
}

/* ── Machine cards ── */
.mob-machine-grid {
    display: flex; flex-direction: column; gap: 6px;
    padding: 0 16px;
}
.mob-mcard {
    background: #0d1526; border: 1px solid #1e2d45;
    border-radius: 12px; padding: 13px 15px;
    display: flex; align-items: center; gap: 12px;
    transition: all 0.15s;
}
.mob-mcard:active { transform: scale(0.98); }
.mob-status-dot {
    width: 12px; height: 12px; border-radius: 50%;
    flex-shrink: 0; box-shadow: 0 0 8px currentColor;
}
.mob-mname {
    font-size: 13px; font-weight: 600; color: #e2e8f0;
    flex: 1; min-width: 0;
}
.mob-mmeta {
    display: flex; flex-direction: column;
    align-items: flex-end; gap: 3px;
}
.mob-mpill {
    font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
    padding: 2px 7px; border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
}
.mob-ops {
    font-size: 10px; color: #64748b;
    font-family: 'JetBrains Mono', monospace;
}
.mob-zone-badge {
    font-size: 8px; color: #475569; font-family: 'JetBrains Mono', monospace;
}

/* ── Cell cards ── */
.mob-cell-cards {
    display: flex; flex-direction: column; gap: 8px;
    padding: 0 16px;
}
.mob-cell {
    background: #0d1526; border: 1px solid #1e2d45;
    border-radius: 14px; padding: 16px;
}
.mob-cell-name {
    font-size: 14px; font-weight: 700; color: #e2e8f0;
    margin-bottom: 10px;
}
.mob-cell-row {
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 6px;
}
.mob-cell-lbl { font-size: 10px; color: #64748b; font-family: 'JetBrains Mono', monospace; }
.mob-cell-val { font-size: 14px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

/* ── Bottom nav ── */
.mob-nav {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 200;
    background: #0d1526; border-top: 1px solid #1e2d45;
    display: flex; padding: 8px 0 12px;
}
.mob-nav-btn {
    flex: 1; text-align: center;
    font-size: 9px; color: #475569;
    text-transform: uppercase; letter-spacing: 1px;
    font-family: 'JetBrains Mono', monospace;
    display: flex; flex-direction: column; align-items: center; gap: 3px;
}
.mob-nav-btn.active { color: #3b82f6; }
.mob-nav-icon { font-size: 20px; }

/* ── Streamlit widget overrides ── */
.stSelectbox label { display: none !important; }
.stSelectbox > div > div {
    background: #0d1526 !important;
    border: 1px solid #1e2d45 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.stRadio label { color: #94a3b8 !important; font-size: 12px !important; }
.stRadio [data-testid="stMarkdownContainer"] p { font-size: 12px !important; }
div[data-testid="stTabs"] button {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 12px !important; font-weight: 600 !important;
    color: #64748b !important; padding: 8px 16px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #3b82f6 !important;
    border-bottom: 2px solid #3b82f6 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "mob_area"  not in st.session_state: st.session_state.mob_area  = "F5 – Area 1"
if "mob_tab"   not in st.session_state: st.session_state.mob_tab   = "machines"
if "mob_filter"not in st.session_state: st.session_state.mob_filter= "ALL"

# ── Load data ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_area_data(path, area_name=""):
    row_slice = AREA_ROWS.get(area_name)
    df = pd.read_excel(path, sheet_name="Machine_Status")
    if row_slice:
        df = df.iloc[row_slice[0]:row_slice[1]].reset_index(drop=True)
    df.columns = [c.strip() for c in df.columns]
    df["Status"] = df["Status"].fillna("ON").astype(str).str.strip().str.upper()
    df["Zone"]   = df["Zone"].fillna("—").astype(str).str.strip()
    df["Operator_Count"] = df["Operator_Count"].apply(
        lambda x: int(float(x)) if str(x).replace('.','').isdigit() else 0)
    df["Notes"]  = df["Notes"].fillna("").astype(str)
    df["Machine"]= df["Machine"].astype(str).str.strip().str.replace(r'^\xa0','',regex=True)
    df = df[df["Machine"].str.strip() != ""].reset_index(drop=True)
    return df

@st.cache_data(ttl=30)
def load_cells(path):
    try:
        cd = pd.read_excel(path, sheet_name="Cell Details").dropna(subset=["Cell"])
        cd["Cell"] = cd["Cell"].astype(str).str.strip()
        cap_col = [c for c in cd.columns if "cap" in c.lower()]
        if cap_col: cd["Capacity"] = pd.to_numeric(cd[cap_col[0]], errors="coerce")
        desc_col = [c for c in cd.columns if "desc" in c.lower()]
        if desc_col: cd["TopDesc"] = cd[desc_col[0]].fillna("—").astype(str)
        item_col = [c for c in cd.columns if "item" in c.lower() or "sell" in c.lower()]
        if item_col:
            cd["TopItem"] = cd[item_col[0]].apply(
                lambda x: f"{x:.0f}" if isinstance(x,float) and not pd.isna(x) else str(x) if pd.notna(x) else "—")
        return cd[["Cell"] + (["Capacity"] if "Capacity" in cd.columns else [])
                           + (["TopDesc"]  if "TopDesc"  in cd.columns else [])
                           + (["TopItem"]  if "TopItem"  in cd.columns else [])].reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["Cell"])

active_path = AREAS[st.session_state.mob_area]
df_raw = load_area_data(active_path, st.session_state.mob_area)
df_cells = load_cells(active_path)

# KPI calc — exclude non-machine zones (Status='-')
_df_machines = df_raw[df_raw["Status"] != "-"]
total  = len(df_raw)
n_on   = (_df_machines["Status"]=="ON").sum()
n_off  = (_df_machines["Status"]=="OFF").sum()
n_mnt  = (_df_machines["Status"]=="MAINTENANCE").sum()
n_zone = (df_raw["Status"]=="-").sum()
uptime = round(n_on/max(len(_df_machines),1)*100) if len(_df_machines) else 0

# Operator alerts — only for actual machines (not '-' status zones)
orig_df = load_area_data(active_path, st.session_state.mob_area)
std_map = dict(zip(orig_df["Machine"], orig_df["Operator_Count"]))
op_alerts = [(r["Machine"], std_map.get(r["Machine"], r["Operator_Count"]), r["Operator_Count"])
             for _, r in df_raw.iterrows()
             if str(r.get("Status","")).strip() not in ("-", "OFF")
             and r["Operator_Count"] < std_map.get(r["Machine"], r["Operator_Count"])]

# ── TOP BAR ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="mob-topbar">
  <div class="mob-live"><div class="mob-live-dot"></div>LIVE</div>
  <div class="mob-title">🏭 Factory Monitor</div>
  <div class="mob-subtitle">{st.session_state.mob_area}</div>
</div>
""", unsafe_allow_html=True)

# ── Area selector ─────────────────────────────────────────────────────────────
sel_area = st.selectbox("Area", list(AREAS.keys()),
                         index=list(AREAS.keys()).index(st.session_state.mob_area),
                         key="mob_area_sel")
if sel_area != st.session_state.mob_area:
    st.session_state.mob_area = sel_area
    st.cache_data.clear()
    st.rerun()

# ── KPI STRIP ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="mob-kpi-strip">
  <div class="mob-kpi">
    <div class="mob-kpi-val" style="color:#3b82f6">{total}</div>
    <div class="mob-kpi-lbl">Total</div>
  </div>
  <div class="mob-kpi">
    <div class="mob-kpi-val" style="color:#22c55e">{n_on}</div>
    <div class="mob-kpi-lbl">ON</div>
  </div>
  <div class="mob-kpi">
    <div class="mob-kpi-val" style="color:#ef4444">{n_off}</div>
    <div class="mob-kpi-lbl">OFF</div>
  </div>
  <div class="mob-kpi">
    <div class="mob-kpi-val" style="color:{'#22c55e' if uptime>=70 else '#ef4444'}">{uptime}%</div>
    <div class="mob-kpi-lbl">Uptime</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── OPERATOR ALERT ────────────────────────────────────────────────────────────
if op_alerts:
    alert_txt = " · ".join(f"{m}: {act}/{std}" for m,std,act in op_alerts[:4])
    if len(op_alerts) > 4: alert_txt += f" +{len(op_alerts)-4} more"
    st.markdown(f"""
<div class="mob-alert">
  <span>⚠️</span>
  <div><b>Manpower below standard</b><br>{alert_txt}</div>
</div>""", unsafe_allow_html=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_machines, tab_zones, tab_cells, tab_layout = st.tabs(["🏭 Machines", "📊 Zones", "⚡ Cells", "🗺️ Layout"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — MACHINE LIST
# ─────────────────────────────────────────────────────────────────────────────
with tab_machines:
    # Status filter pills (radio as horizontal)
    filt = st.radio("Filter", ["ALL","ON","OFF","MAINTENANCE"],
                    horizontal=True, key="mob_status_filter",
                    label_visibility="collapsed")

    df_show = df_raw if filt == "ALL" else (
        df_raw[df_raw["Status"] == filt] if filt != "ALL"
        else df_raw
    )

    st.markdown('<div class="mob-sec">Machines</div>', unsafe_allow_html=True)

    cards = '<div class="mob-machine-grid">'
    for _, row in df_show.iterrows():
        st_val = str(row.get("Status","")).strip()
        is_zone = (st_val == "-")
        sc = "#64748b" if is_zone else STATUS_COLOR.get(st_val,"#94a3b8")
        sb = "#1e293b" if is_zone else STATUS_BG.get(st_val,"#1e293b")
        name  = row["Machine"]
        ops   = row["Operator_Count"]
        zone  = row["Zone"]
        std_o = std_map.get(name, ops)
        ops_warn = "⚠️ " if (not is_zone and ops < std_o and st_val != "OFF") else ""
        ops_disp = "—" if is_zone else f"{ops}"
        pill_lbl = "ZONE" if is_zone else st_val
        icon = "🗂️" if is_zone else ""
        cards += (
            f'<div class="mob-mcard" style="border-left:3px solid {sc};{"opacity:0.75;" if is_zone else ""}">'
            f'<div class="mob-status-dot" style="background:{sc};color:{sc}"></div>'
            f'<div class="mob-mname">{icon}{name}</div>'
            f'<div class="mob-mmeta">'
            f'<span class="mob-mpill" style="background:{sb};color:{sc}">{pill_lbl}</span>'
            f'<span class="mob-ops">{ops_warn}👷 {ops_disp}</span>'
            f'<span class="mob-zone-badge">{zone}</span>'
            f'</div></div>'
        )
    cards += '</div>'
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:10px;color:#334155;text-align:center;margin-top:12px">{len(df_show)} entries</p>',
                unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ZONE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
with tab_zones:
    st.markdown('<div class="mob-sec">Zone Breakdown</div>', unsafe_allow_html=True)
    zones = df_raw["Zone"].unique()
    zone_html = '<div class="mob-cell-cards">'
    for z in sorted(zones):
        zdf = df_raw[df_raw["Zone"]==z]
        z_on  = (zdf["Status"]=="ON").sum()
        z_off = (zdf["Status"]=="OFF").sum()
        z_mnt = (zdf["Status"]=="MAINTENANCE").sum()
        z_tot = len(zdf)
        z_upt = round(z_on/z_tot*100) if z_tot else 0
        z_col = "#22c55e" if z_upt>=70 else ("#ef4444" if z_upt<40 else "#f59e0b")
        zone_html += f"""<div class="mob-cell" style="border-left:4px solid {z_col}">
<div class="mob-cell-name">{z} Zone</div>
<div class="mob-cell-row">
  <span class="mob-cell-lbl">MACHINES</span><span class="mob-cell-val">{z_tot}</span>
</div>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:10px 0">
  <div style="background:#052e16;border-radius:8px;padding:8px;text-align:center">
    <div style="font-size:20px;font-weight:700;color:#22c55e;font-family:JetBrains Mono,monospace">{z_on}</div>
    <div style="font-size:9px;color:#64748b">ON</div>
  </div>
  <div style="background:#450a0a;border-radius:8px;padding:8px;text-align:center">
    <div style="font-size:20px;font-weight:700;color:#ef4444;font-family:JetBrains Mono,monospace">{z_off}</div>
    <div style="font-size:9px;color:#64748b">OFF</div>
  </div>
  <div style="background:#431407;border-radius:8px;padding:8px;text-align:center">
    <div style="font-size:20px;font-weight:700;color:#f59e0b;font-family:JetBrains Mono,monospace">{z_mnt}</div>
    <div style="font-size:9px;color:#64748b">MAINT</div>
  </div>
</div>
<div style="background:#0a0e17;border-radius:8px;height:8px;overflow:hidden">
  <div style="background:{z_col};height:100%;width:{z_upt}%;transition:width .5s;border-radius:8px"></div>
</div>
<div style="font-size:10px;color:{z_col};text-align:right;margin-top:4px;font-family:JetBrains Mono,monospace">{z_upt}% uptime</div>
</div>"""
    zone_html += '</div>'
    st.markdown(zone_html, unsafe_allow_html=True)

    # Machines in each zone
    for z in sorted(zones):
        st.markdown(f'<div class="mob-sec">{z} Zone — All Machines</div>', unsafe_allow_html=True)
        zdf = df_raw[df_raw["Zone"]==z]
        cards2 = '<div class="mob-machine-grid">'
        for _, row in zdf.iterrows():
            sc = STATUS_COLOR.get(row["Status"],"#94a3b8")
            sb = STATUS_BG.get(row["Status"],"#1e293b")
            cards2 += (
                f'<div class="mob-mcard" style="border-left:3px solid {sc}">'
                f'<div class="mob-status-dot" style="background:{sc};color:{sc}"></div>'
                f'<div class="mob-mname">{row["Machine"]}</div>'
                f'<div class="mob-mmeta">'
                f'<span class="mob-mpill" style="background:{sb};color:{sc}">{row["Status"]}</span>'
                f'<span class="mob-ops">👷 {row["Operator_Count"]}</span>'
                f'</div></div>'
            )
        cards2 += '</div>'
        st.markdown(cards2, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — CELL INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────
with tab_cells:
    st.markdown('<div class="mob-sec">Cell Capacity</div>', unsafe_allow_html=True)

    if df_cells.empty:
        st.info("No cell data found.")
    else:
        cell_html = '<div class="mob-cell-cards">'
        CELL_COLORS = ["#3b82f6","#8b5cf6","#22c55e","#f59e0b","#0ea5e9"]
        for ci, (_, cr) in enumerate(df_cells.iterrows()):
            cc = CELL_COLORS[ci % len(CELL_COLORS)]
            cap_str = f"{int(cr['Capacity']):,}" if "Capacity" in cr and pd.notna(cr.get("Capacity")) else "—"
            desc_str = cr.get("TopDesc","—") or "—"
            item_str = cr.get("TopItem","—") or "—"
            cell_html += f"""<div class="mob-cell" style="border-left:4px solid {cc}">
<div class="mob-cell-name" style="color:{cc}">{cr['Cell']}</div>
<div class="mob-cell-row">
  <span class="mob-cell-lbl">DAILY CAPACITY</span>
  <span class="mob-cell-val" style="color:{cc}">{cap_str} pcs/day</span>
</div>
<div style="height:1px;background:#1e2d45;margin:8px 0"></div>
<div style="font-size:10px;color:#64748b;font-family:JetBrains Mono,monospace;margin-bottom:3px">TOP PRODUCT</div>
<div style="font-size:13px;font-weight:600;color:#e2e8f0;line-height:1.4">{desc_str}</div>
<div style="font-size:10px;color:#475569;font-family:JetBrains Mono,monospace;margin-top:3px">{item_str}</div>
</div>"""
        cell_html += '</div>'
        st.markdown(cell_html, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — EXECUTIVE LAYOUT VIEW (mobile-optimised SVG)
# ─────────────────────────────────────────────────────────────────────────────
with tab_layout:
    import re as _re_mob
    import streamlit.components.v1 as _mob_cmp

    _mob_area_key = {
        "F5 – Area 1":"F5_A1","F5 – Area 2":"F5_A2",
        "F4 – Area 1":"F4_A1","F4 – Area 2":"F4_A2",
    }.get(st.session_state.mob_area,"F5_A1")

    _mob_df = df_raw[df_raw["Status"] != "-"].copy()

    def _mb(n): return _re_mob.sub(r'\s*\d+\s*$','',str(n).strip())
    _MS = {"Leadgers Welding":"LW","Welding Machine":"WM","Ring Vertical":"RV",
           "Cup Vertical":"CV","Weld Cell":"WC","Drrill":"DR","Drill":"DR",
           "Auto Welding":"AW","RASA Saw":"SAW","Manual Saw":"SAW","Mixer":"HYD",
           "Cup Frame Form Mixer":"CFM","Cup Weld":"CW","Multi Drill":"MD",
           "Forming":"FRM","Form & Tap":"F&T","Saw":"SAW","Tap":"TAP",
           "Presses":"PRS","ECO Punch Press":"ECO","TECH Punch / Drill":"TCH",
           "Welding Robot":"WR","Pre-Assembly Welding Robot":"PAW","9-Frame Assembly":"9FA",
           "Grinding":"GRD","Delivery / QC":"D/Q","Auto Saw":"SAW",
           "Welding Package":"WPK","Welding Station":"WST","CNC Router Machine":"CNC",
           "Saw Machine":"SAW","Manual Assembly Tools":"MAT","Pallet Assembly Spread":"PAS",
           "Paint / Coating Station":"PNT","Assembly Station":"ASSY",
           "Production Sorting Area":"SORT","ECO Punch + TECH Press":"E+T"}
    def _mabb(n): b=_mb(n); return _MS.get(b,b[:4].upper())

    _MNM={"Assembly Station","Production Sorting Area","9-Frame Assembly",
          "Delivery / QC","Manual Assembly Tools","Pallet Assembly Spread"}
    _MIMAP={"Welding Machine":"weld","Leadgers Welding":"weld","Weld Cell":"weld",
            "Cup Weld":"weld","Welding Package":"weld","Welding Station":"weld",
            "Welding Robot":"robot","Pre-Assembly Welding Robot":"robot","Auto Welding":"robot",
            "RASA Saw":"saw","Manual Saw":"saw","Auto Saw":"saw","Saw Machine":"saw",
            "Saw":"saw","Grinding":"saw","Drill":"drill","Drrill":"drill",
            "Multi Drill":"drill","CNC Router Machine":"drill","TECH Punch / Drill":"drill",
            "Tap":"drill","Mixer":"press","Cup Frame Form Mixer":"press","Presses":"press",
            "ECO Punch Press":"press","ECO Punch + TECH Press":"press",
            "Ring Vertical":"press","Cup Vertical":"press","Form & Tap":"press","Forming":"press"}
    def _mit(b): return _MIMAP.get(b,"weld")

    _MZS = {
      "F5_A1":{"tl":("RAW MATERIAL STORAGE",[],True),"tr":("CUTTING & SAWING",["RASA Saw","Manual Saw"],False),
               "left":[("LEDGER WELDING",["Leadgers Welding"],False),("VERTICAL FORMING",["Ring Vertical","Cup Vertical"],False)],
               "right":[("STRUCTURAL WELDING",["Welding Machine"],False),("ASSEMBLY",["Assembly Station"],False),("DRILLING",["Drill"],False)],
               "bl":("AUTO WELDING",["Auto Welding"],False),"br":("PROD. SORTING",["Production Sorting Area"],False)},
      "F5_A2":{"tl":("RAW MATERIAL STORAGE",[],True),"tr":("DRILLING",["Drrill","Drill","Multi Drill"],False),
               "left":[("HYDRAULIC PRESSING",["Mixer"],False),("WELDING CELLS",["Weld Cell"],False)],
               "right":[("CUP FRAME PRESSING",["Cup Frame Form Mixer"],False),("CUP WELDING",["Cup Weld"],False),("FORMING & TAPPING",["Form & Tap","Forming","Saw","Tap"],False)],
               "bl":("SORTING",[],True),"br":("OUTBOUND",[],True)},
      "F4_A1":{"tl":("RAW MATERIAL STORAGE",[],True),"tr":("CUTTING & SAWING",["Manual Saw","Auto Saw"],False),
               "left":[("PUNCHING & PRESSING",["ECO Punch Press","TECH Punch / Drill","ECO Punch + TECH Press","Presses"],False),("FRAME ASSEMBLY",["9-Frame Assembly"],False)],
               "right":[("WELDING",["Welding Package","Pre-Assembly Welding Robot","Welding Robot","Welding Station"],False),("FINISHING & QC",["Grinding","Delivery / QC"],False)],
               "bl":("STAGING",[],True),"br":("OUTBOUND",[],True)},
      "F4_A2":{"tl":("RAW MATERIAL STORAGE",[],True),"tr":("CUTTING",["Saw Machine"],False),
               "left":[("ASSEMBLY",["Manual Assembly Tools","Pallet Assembly Spread"],False)],
               "right":[("CNC MACHINING",["CNC Router Machine"],False),("SURFACE COATING",["Paint / Coating Station"],False)],
               "bl":("WIP STORAGE",[],True),"br":("OUTBOUND",[],True)},
    }
    _mzs = _MZS.get(_mob_area_key, _MZS["F5_A1"])

    def _mg(bases):
        r=[]
        for _,row in _mob_df.iterrows():
            b=_mb(row["Machine"])
            if b in bases:
                r.append({"a":_mabb(row["Machine"]),"b":b,"n":str(row["Machine"]).strip(),
                          "s":str(row["Status"]).strip(),"o":int(row.get("Operator_Count",0)),
                          "nm":b in _MNM})
        return r

    def _mcmap(s):
        if s=="ON":  return {"f":"#EAF3DE","p":"#C0DD97","s":"#3B6D11","d":"#639922"}
        if s=="OFF": return {"f":"#FCEBEB","p":"#F7C1C1","s":"#791F1F","d":"#A32D2D"}
        return               {"f":"#FAEEDA","p":"#FAC775","s":"#633806","d":"#854F0B"}
    def _mwclr(s):
        if s=="ON":  return "#EAF3DE","#3B6D11","#173404"
        if s=="OFF": return "#FCEBEB","#791F1F","#501313"
        return               "#FAEEDA","#633806","#412402"

    # compact icon set for mobile (same shapes, same 52x55 canvas)
    def _mi_weld(bx,by,c):
        return (f'<rect x="{bx+4}" y="{by+12}" width="24" height="32" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.5"/>'
                f'<rect x="{bx+8}" y="{by+17}" width="16" height="7" rx="1" fill="{c["p"]}" stroke="{c["s"]}" stroke-width=".9"/>'
                f'<circle cx="{bx+16}" cy="{by+33}" r="5" fill="none" stroke="{c["s"]}" stroke-width="1.1"/>'
                f'<circle cx="{bx+10}" cy="{by+47}" r="3.5" fill="none" stroke="{c["s"]}" stroke-width="1.3"/>'
                f'<circle cx="{bx+22}" cy="{by+47}" r="3.5" fill="none" stroke="{c["s"]}" stroke-width="1.3"/>'
                f'<path d="M{bx+28} {by+20} Q{bx+36} {by+16} {bx+42} {by+9}" fill="none" stroke="{c["d"]}" stroke-width="1.5" stroke-linecap="round"/>'
                f'<ellipse cx="{bx+43}" cy="{by+8}" rx="5" ry="3" fill="{c["s"]}" transform="rotate(-30 {bx+43} {by+8})"/>')
    def _mi_saw(bx,by,c):
        return (f'<rect x="{bx+4}" y="{by+25}" width="44" height="8" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+6}" y="{by+33}" width="10" height="18" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.3"/>'
                f'<rect x="{bx+36}" y="{by+33}" width="10" height="18" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.3"/>'
                f'<circle cx="{bx+26}" cy="{by+27}" r="14" fill="none" stroke="{c["s"]}" stroke-width="2"/>'
                f'<circle cx="{bx+26}" cy="{by+27}" r="3.5" fill="{c["s"]}"/>'
                f'<path d="M{bx+12} {by+24} Q{bx+26} {by+14} {bx+40} {by+24}" fill="none" stroke="{c["s"]}" stroke-width="1.4"/>') 
    def _mi_drill(bx,by,c):
        return (f'<rect x="{bx+22}" y="{by+4}" width="8" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+9}" y="{by+6}" width="34" height="10" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+14}" y="{by+16}" width="24" height="15" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<polygon points="{bx+19},{by+31} {bx+33},{by+31} {bx+26},{by+47}" fill="{c["s"]}"/>'
                f'<rect x="{bx+8}" y="{by+40}" width="36" height="6" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>')
    def _mi_press(bx,by,c):
        return (f'<rect x="{bx+4}" y="{by+4}" width="9" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+39}" y="{by+4}" width="9" height="50" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+4}" y="{by+4}" width="44" height="9" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+4}" y="{by+45}" width="44" height="9" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<rect x="{bx+18}" y="{by+13}" width="16" height="18" rx="4" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.3"/>'
                f'<rect x="{bx+21}" y="{by+31}" width="10" height="15" rx="1" fill="{c["s"]}"/>')
    def _mi_robot(bx,by,c):
        return (f'<rect x="{bx+10}" y="{by+48}" width="32" height="7" rx="2" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.7"/>'
                f'<ellipse cx="{bx+26}" cy="{by+46}" rx="12" ry="6" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                f'<rect x="{bx+23}" y="{by+24}" width="6" height="24" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                f'<circle cx="{bx+26}" cy="{by+24}" r="4.5" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4"/>'
                f'<rect x="{bx+26}" y="{by+10}" width="6" height="16" rx="3" fill="{c["f"]}" stroke="{c["s"]}" stroke-width="1.4" transform="rotate(28 {bx+29} {by+24})"/>'
                f'<circle cx="{bx+37}" cy="{by+13}" r="5" fill="{c["s"]}"/>'
                f'<line x1="{bx+37}" y1="{by+8}" x2="{bx+41}" y2="{by+4}" stroke="{c["s"]}" stroke-width="2.5" stroke-linecap="round"/>')
    def _mi_nm(b,bx,by):
        _f="#e4e4e4";_s="#555";_d="#c4c4c4";bl=b.lower()
        if "sort" in bl:
            return (f'<rect x="{bx+3}" y="{by+21}" width="46" height="5" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                    f'<rect x="{bx+4}" y="{by+5}" width="14" height="17" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                    f'<rect x="{bx+20}" y="{by+5}" width="12" height="17" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>'
                    f'<rect x="{bx+34}" y="{by+5}" width="14" height="17" rx="1.2" fill="{_d}" stroke="{_s}" stroke-width="1"/>')
        if "qc" in bl or "delivery" in bl:
            return (f'<circle cx="{bx+21}" cy="{by+16}" r="10" fill="none" stroke="{_s}" stroke-width="1.9"/>'
                    f'<circle cx="{bx+21}" cy="{by+16}" r="6" fill="#d4eedb" stroke="{_s}" stroke-width=".9"/>'
                    f'<line x1="{bx+29}" y1="{by+23}" x2="{bx+37}" y2="{by+31}" stroke="{_s}" stroke-width="3" stroke-linecap="round"/>'
                    f'<polyline points="{bx+17},{by+16} {bx+20},{by+19} {bx+25},{by+13}" fill="none" stroke="#22c55e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>')
        return (f'<rect x="{bx+5}" y="{by+22}" width="42" height="7" rx="1.5" fill="{_f}" stroke="{_s}" stroke-width="1.5"/>'
                f'<rect x="{bx+12}" y="{by+6}" width="28" height="17" rx="2" fill="{_d}" stroke="{_s}" stroke-width="1.2"/>'
                f'<rect x="{bx+15}" y="{by+9}" width="22" height="11" rx="1" fill="#b0c0d4" stroke="{_s}" stroke-width=".8"/>')
    _MIFN={"weld":_mi_weld,"saw":_mi_saw,"drill":_mi_drill,"press":_mi_press,"robot":_mi_robot}

    def _mwc(n,cx,cy,wf,ws,wp):
        if not n: return ""
        show=min(n,4);r=7.5;gap=17;sx=cx-(show*gap)//2+r;svg=""
        for i in range(show):
            px=int(sx+i*gap)
            if i==3 and n>4:
                svg+=f'<circle cx="{px}" cy="{cy}" r="{r}" fill="{ws}"/><text x="{px}" y="{cy}" font-size="7" text-anchor="middle" fill="white" font-family="Arial" font-weight="700" dominant-baseline="central">+{n-3}</text>'
            else:
                svg+=(f'<circle cx="{px}" cy="{cy}" r="{r}" fill="{wf}" stroke="{ws}" stroke-width="1.2"/>'
                      f'<circle cx="{px}" cy="{cy-2.5}" r="2.2" fill="{wp}"/>'
                      f'<rect x="{px-2.2}" y="{cy}" width="4.4" height="4" rx="1" fill="{wp}"/>')
        return svg

    _IW=52;_IH=55;_WCR=7.5;_UNIT=_IH+8+10+6+int(_WCR*2)
    def _mzh(n,zw,stor=False):
        if stor or n==0: return 130
        cols=min(3,max(1,(zw-16)//(_IW+10)))
        rows=(n+cols-1)//cols
        return max(130,48+rows*(_UNIT+10)+40+14)
    def _mboxes(ml,zx,zy,zw):
        if not ml: return ""
        _GAP_X=10;_GAP_Y=10
        cols=min(3,max(1,(zw-16)//(_IW+_GAP_X)))
        rwW=cols*_IW+(cols-1)*_GAP_X;sx=zx+max(8,(zw-rwW)//2);svg=""
        for i,m in enumerate(ml):
            col=i%cols;ri=i//cols
            bx=int(sx+col*(_IW+_GAP_X));by=int(zy+48+ri*(_UNIT+_GAP_Y))
            mn=m.get("n",m.get("b","")).replace('"',"'");ms=m["s"] if not m["nm"] else "WORK AREA"
            svg+=f'<g data-mname="{mn}" data-mstatus="{ms}" data-mops="{m["o"]}" style="cursor:pointer">'
            if m["nm"]:
                svg+=_mi_nm(m.get("b",""),bx,by)
                svg+=f'<text x="{bx+_IW//2}" y="{by+_IH+9}" font-size="8" text-anchor="middle" fill="#666" font-family="Arial" dominant-baseline="central" font-style="italic">{m["a"]}</text>'
            else:
                c=_mcmap(m["s"]);fn=_MIFN.get(_mit(m.get("b","")),_mi_weld);svg+=fn(bx,by,c)
                svg+=f'<text x="{bx+_IW//2}" y="{by+_IH+9}" font-size="8" text-anchor="middle" fill="#444" font-family="Arial" dominant-baseline="central">{m["a"]}</text>'
                if m["o"]>0:
                    wf,ws,wp=_mwclr(m["s"]);wcy=int(by+_IH+8+10+6+int(_WCR))
                    svg+=_mwc(m["o"],bx+_IW//2,wcy,wf,ws,wp)
            svg+='</g>'
        return svg
    def _mstats(ml,zx,zy,zw):
        if not ml: return ""
        cols=min(3,max(1,(zw-16)//(_IW+10)));rows=(len(ml)+cols-1)//cols
        sy=zy+48+rows*(_UNIT+10)+10;cx=zx+zw//2
        nOn=sum(1 for m in ml if m["s"]=="ON" and not m["nm"])
        nOf=sum(1 for m in ml if m["s"]=="OFF" and not m["nm"])
        ops=sum(m["o"] for m in ml)
        return (f'<text x="{cx}" y="{sy}" font-size="8.5" text-anchor="middle" fill="#666" font-family="Arial" dominant-baseline="central">{len(ml)} M/C · {ops} operators</text>'
                f'<text x="{cx}" y="{sy+14}" font-size="8.5" text-anchor="middle" fill="#999" font-family="Arial" dominant-baseline="central">{nOn} Running · {nOf} Offline</text>')

    # layout
    _FX=52;_FY=88;_LW=240;_CW=25;_RW=365;_FW=_LW+_CW+_RW;_AIL=22;_FGH=50
    _bl_w=195;_br_w=_FW-_bl_w
    _trl=_mg(_mzs["tr"][1]); _lmls=[_mg(z[1]) for z in _mzs["left"]]
    _rmls=[_mg(z[1]) for z in _mzs["right"]]
    _blml=_mg(_mzs["bl"][1]); _brml=_mg(_mzs["br"][1])
    _toph=max(120,_mzh(len(_trl),_RW,_mzs["tr"][2]))
    _lhs2=[_mzh(len(m),_LW,z[2]) for m,z in zip(_lmls,_mzs["left"])]
    _rhs2=[_mzh(len(m),_RW,z[2]) for m,z in zip(_rmls,_mzs["right"])]
    _ml2=sum(_lhs2);_mr2=sum(_rhs2);_midh=max(_ml2,_mr2,100)
    if _lhs2 and _ml2<_midh: _lhs2[-1]+=_midh-_ml2
    if _rhs2 and _mr2<_midh: _rhs2[-1]+=_midh-_mr2
    _BOT2=max(_mzh(len(_blml),_bl_w,_mzs["bl"][2]),_mzh(len(_brml),_br_w,_mzs["br"][2]),100)
    _FH2=_toph+_AIL+_midh+_AIL+_BOT2+_FGH
    _ymid2=_FY+_toph+_AIL;_ybot2=_ymid2+_midh+_AIL;_yfg2=_ybot2+_BOT2
    _lpx2=[];_y_=_ymid2
    for h in _lhs2: _lpx2.append((_FX,_y_,_LW,h));_y_+=h
    _rpx2=[];_y_=_ymid2
    for h in _rhs2: _rpx2.append((_FX+_LW+_CW,_y_,_RW,h));_y_+=h
    _SVGW2=_FX*2+_FW;_SVGH2=_FY+_FH2+130

    # zone SVG builder
    def _mzone(zx,zy,zw,zh,name,ml,stor=False):
        z=f'<rect x="{zx}" y="{zy}" width="{zw}" height="{zh}" fill="white" stroke="#ccc" stroke-width=".9"/>'
        z+=f'<rect x="{zx}" y="{zy}" width="{zw}" height="30" fill="#1a2035"/>'
        z+=f'<text x="{zx+9}" y="{zy+15}" font-size="9.5" font-weight="700" fill="white" font-family="Arial" dominant-baseline="central">{name}</text>'
        if stor or not ml:
            z+=f'<text x="{zx+zw//2}" y="{zy+zh//2}" font-size="9" text-anchor="middle" fill="#ccc" font-family="Arial" dominant-baseline="central" font-style="italic">No machines</text>'
        else:
            z+=_mboxes(ml,zx,zy,zw)+_mstats(ml,zx,zy,zw)
        return z

    _sp=[]
    _sp.append(f'<rect width="{_SVGW2}" height="{_SVGH2}" fill="#f8f9fb"/>')
    _sp.append(f'<rect x="{_FX}" y="{_FY}" width="{_FW}" height="{_FH2}" fill="white" stroke="#1a2035" stroke-width="4" rx="3"/>')
    # RM entrance
    _gcx2=_FX+_FW//2
    _sp.append(f'<rect x="{_gcx2-45}" y="{_FY-3}" width="90" height="7" fill="#f8f9fb"/>')
    _sp.append(f'<text x="{_gcx2}" y="{_FY-11}" font-size="8.5" font-weight="700" text-anchor="middle" fill="#334155" font-family="Arial">▼ RM ENTRANCE</text>')
    # top zones
    _sp.append(_mzone(_FX,_FY,_LW,_toph,_mzs["tl"][0],[],True))
    _sp.append(_mzone(_FX+_LW+_CW,_FY,_RW,_toph,_mzs["tr"][0],_trl,_mzs["tr"][2]))
    # main aisle
    _ay2=_FY+_toph
    _sp.append(f'<rect x="{_FX}" y="{_ay2}" width="{_FW}" height="{_AIL}" fill="#f0f0f0"/>')
    _sp.append(f'<text x="{_FX+_FW//2}" y="{_ay2+_AIL//2}" font-size="7.5" text-anchor="middle" fill="#aaa" font-family="Arial" font-weight="700" dominant-baseline="central" letter-spacing="2">MAIN AISLE</text>')
    # cross aisle
    _sp.append(f'<rect x="{_FX+_LW}" y="{_ymid2}" width="{_CW}" height="{_midh}" fill="#f9f9f9"/>')
    # zones
    for (_zx,_zy,_zw,_zh),(ml,zd) in zip(_lpx2,zip(_lmls,_mzs["left"])):
        _sp.append(_mzone(_zx,_zy,_zw,_zh,zd[0],ml,zd[2]))
    for (_zx,_zy,_zw,_zh),(ml,zd) in zip(_rpx2,zip(_rmls,_mzs["right"])):
        _sp.append(_mzone(_zx,_zy,_zw,_zh,zd[0],ml,zd[2]))
    # service aisle
    _say2=_ybot2-_AIL
    _sp.append(f'<rect x="{_FX}" y="{_say2}" width="{_FW}" height="{_AIL}" fill="#f0f0f0"/>')
    _sp.append(f'<text x="{_FX+_FW//2}" y="{_say2+_AIL//2}" font-size="7.5" text-anchor="middle" fill="#aaa" font-family="Arial" font-weight="700" dominant-baseline="central" letter-spacing="2">SERVICE AISLE</text>')
    # bottom zones
    _sp.append(_mzone(_FX,_ybot2,_bl_w,_BOT2,_mzs["bl"][0],_blml,_mzs["bl"][2]))
    _sp.append(_mzone(_FX+_bl_w,_ybot2,_br_w,_BOT2,_mzs["br"][0],_brml,_mzs["br"][2]))
    # FG band
    _sp.append(f'<rect x="{_FX}" y="{_yfg2}" width="{_FW}" height="{_FGH}" fill="#f0fdf4" stroke="#82B366" stroke-width="1"/>')
    _sp.append(f'<text x="{_FX+_FW//2}" y="{_yfg2+_FGH//2}" font-size="10" font-weight="700" text-anchor="middle" fill="#2C5A1E" font-family="Arial" dominant-baseline="central">FINISHED GOODS EXIT & LOADING DOCK</text>')
    # outer wall redrawn on top
    _sp.append(f'<rect x="{_FX}" y="{_FY}" width="{_FW}" height="{_FH2}" fill="none" stroke="#1a2035" stroke-width="4" rx="3"/>')
    _sp.append(f'<rect x="{_gcx2-45}" y="{_FY+_FH2-3}" width="90" height="7" fill="#f8f9fb"/>')
    _sp.append(f'<text x="{_gcx2}" y="{_FY+_FH2+14}" font-size="8.5" font-weight="700" text-anchor="middle" fill="#334155" font-family="Arial">▼ FG EXIT</text>')
    # KPI bar
    _m_on=int((_mob_df["Status"]=="ON").sum());_m_off=int((_mob_df["Status"]=="OFF").sum())
    _m_tot=len(_mob_df);_m_upt=round(_m_on/_m_tot*100) if _m_tot else 0
    _sp.append(f'<text x="{_FX+8}" y="{_FY-28}" font-size="11" font-weight="700" fill="#1a2035" font-family="Arial">{st.session_state.mob_area}</text>')
    _sp.append(f'<text x="{_SVGW2-8}" y="{_FY-28}" font-size="10" font-weight="700" fill="#22c55e" font-family="Arial" text-anchor="end">{_m_upt}% uptime</text>')
    _sp.append(f'<text x="{_SVGW2-8}" y="{_FY-14}" font-size="8.5" fill="#64748b" font-family="Arial" text-anchor="end">{_m_on} ON · {_m_off} OFF · {_m_tot} M/C</text>')

    _mob_svg=f'<svg viewBox="0 0 {_SVGW2} {_SVGH2}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">'+"".join(_sp)+"</svg>"
    _mob_tt="""<div id="mob-tt" style="position:fixed;display:none;background:#1a2035;color:white;padding:9px 13px;border-radius:7px;font-family:Arial,sans-serif;font-size:12px;pointer-events:none;z-index:9999;border-left:3px solid #22c55e;box-shadow:0 4px 16px rgba(0,0,0,0.5);min-width:160px;line-height:1.6"></div>
<script>const _mt=document.getElementById('mob-tt');document.querySelectorAll('[data-mname]').forEach(el=>{el.addEventListener('mouseenter',()=>{const st=el.dataset.mstatus,n=parseInt(el.dataset.mops)||0;const sc=st==='ON'?'#22c55e':st==='OFF'?'#ef4444':st==='MAINTENANCE'?'#f59e0b':'#94a3b8';_mt.style.borderLeftColor=sc;_mt.innerHTML='<div style="font-weight:700;font-size:13px;margin-bottom:5px">'+el.dataset.mname+'</div><div style="margin-bottom:3px">Status&nbsp;&nbsp;<span style="color:'+sc+';font-weight:700">'+st+'</span></div><div style="color:#94a3b8">👷 '+n+' operator'+(n!==1?'s':'')+'</div>';_mt.style.display='block';});el.addEventListener('mousemove',e=>{_mt.style.left=(e.clientX+14)+'px';_mt.style.top=(e.clientY-10)+'px';});el.addEventListener('mouseleave',()=>_mt.style.display='none');});</script>"""
    _mob_cmp_h=max(900,_SVGH2+60)
    _mob_html=f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{{margin:0;padding:8px;background:#f8f9fb}}</style></head><body>{_mob_svg}{_mob_tt}</body></html>'
    _mob_cmp.html(_mob_html,height=_mob_cmp_h,scrolling=False)

# ── BOTTOM SPACER ─────────────────────────────────────────────────────────────
st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
