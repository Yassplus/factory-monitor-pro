"""
Factory Monitor Pro — Mobile View
Optimized for small screens. Served on port 8502.
"""

import os
import sys
from datetime import date

import pandas as pd
import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
# Handle being loaded from pages/ subdirectory
_here = os.path.dirname(os.path.abspath(__file__))
BASE = _here if os.path.exists(os.path.join(_here, "data")) else os.path.dirname(_here)
sys.path.insert(0, BASE)

from utils.themes import PREMIUM_DARK_CSS, LIGHT_CSS

st.set_page_config(
    page_title="Factory Monitor — Mobile",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Session defaults ──────────────────────────────────────────────────────────
for k, v in {
    "theme_mode": "Pro Dark",
    "display_lang": "English",
    "mobile_area": "F5 – Area 1",
    "mobile_tab": "Machines",
    "mobile_filter": "All",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Inject theme ──────────────────────────────────────────────────────────────
if st.session_state.theme_mode == "Pro Dark":
    st.markdown(PREMIUM_DARK_CSS, unsafe_allow_html=True)
else:
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

# ── Config ────────────────────────────────────────────────────────────────────
AREA_ROWS = {
    "F5 – Area 1": (os.path.join(BASE, "data", "F5_A1_machine_status.xlsx"), None),
    "F5 – Area 2": (os.path.join(BASE, "data", "F5_A2_machine_status.xlsx"), None),
    "F4 – Area 1": (os.path.join(BASE, "data", "F4_A1_A2_machine_status.xlsx"), (0, 15)),
    "F4 – Area 2": (os.path.join(BASE, "data", "F4_A1_A2_machine_status.xlsx"), (15, 26)),
}

STATUS_COLORS = {
    "ON": "#5DCAA5",
    "OFF": "#F09595",
    "MAINTENANCE": "#FAC775",
    "-": "#888888",
}

ARABIC_NAMES = {
    "ON": "تشغيل", "OFF": "إيقاف", "MAINTENANCE": "صيانة",
    "Machines": "الماكينات", "Zones": "المناطق", "Analytics": "التحليل",
}


def _tr(text):
    if st.session_state.display_lang == "Arabic":
        return ARABIC_NAMES.get(str(text), str(text))
    return str(text)


@st.cache_data(ttl=30)
def _load(path, rows):
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception:
        return pd.DataFrame(columns=["Machine", "Status", "Zone", "Notes", "Operator_Count"])
    if rows:
        df = df.iloc[rows[0]:rows[1]].reset_index(drop=True)
    for col in ["Status", "Zone", "Notes", "Operator_Count"]:
        if col not in df.columns:
            df[col] = None
    if "Status" in df.columns:
        df["Status"] = df["Status"].fillna("-")
    if "Machine" not in df.columns:
        return pd.DataFrame(columns=["Machine", "Status", "Zone", "Notes", "Operator_Count"])
    return df


# ── Header bar ────────────────────────────────────────────────────────────────
is_dark = st.session_state.theme_mode == "Pro Dark"
hdr_bg  = "rgba(255,255,255,0.04)" if is_dark else "#ffffff"
hdr_bd  = "rgba(255,255,255,0.09)" if is_dark else "#e0e0e0"
tc      = "rgba(255,255,255,0.88)" if is_dark else "#222"

st.markdown(f"""
<div style="background:{hdr_bg};border:0.5px solid {hdr_bd};border-radius:12px;
            padding:12px 16px;margin-bottom:12px;display:flex;
            justify-content:space-between;align-items:center;">
  <span style="font-size:15px;font-weight:500;color:{tc};">🏭 Factory Monitor</span>
  <span style="font-size:12px;color:rgba(255,255,255,0.40);">{date.today().strftime('%d %b %Y')}</span>
</div>
""", unsafe_allow_html=True)

# ── Top controls ──────────────────────────────────────────────────────────────
col_a, col_b, col_c = st.columns([3, 1, 1])
with col_a:
    area = st.selectbox("Area", list(AREA_ROWS.keys()), label_visibility="collapsed",
                        key="mobile_area_sel",
                        index=list(AREA_ROWS.keys()).index(st.session_state.mobile_area))
    st.session_state.mobile_area = area

with col_b:
    if st.button("🇬🇧" if st.session_state.display_lang == "Arabic" else "🇸🇦", use_container_width=True):
        st.session_state.display_lang = "Arabic" if st.session_state.display_lang == "English" else "English"
        st.rerun()

with col_c:
    if st.button("🌙" if st.session_state.theme_mode == "Light" else "☀️", use_container_width=True):
        st.session_state.theme_mode = "Light" if st.session_state.theme_mode == "Pro Dark" else "Pro Dark"
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
path, rows = AREA_ROWS[st.session_state.mobile_area]
df = _load(path, rows)
active = df[df["Status"] != "-"]

# ── KPI strip ─────────────────────────────────────────────────────────────────
total = len(active)
on    = int((active["Status"] == "ON").sum())
off   = int((active["Status"] == "OFF").sum())
maint = int((active["Status"] == "MAINTENANCE").sum())
uptime = round((on / total * 100) if total else 0, 1)

card_bg = "rgba(255,255,255,0.04)" if is_dark else "#fff"
bd      = "rgba(255,255,255,0.09)" if is_dark else "#e0e0e0"
sub_c   = "rgba(255,255,255,0.40)" if is_dark else "#888"

kpi_html = f"""
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:12px;">
"""
for label, value, color in [
    ("Total", total, tc),
    ("ON", on, "#5DCAA5"),
    ("OFF", off, "#F09595"),
    ("Maint", maint, "#FAC775"),
    ("Uptime", f"{uptime}%", "#85B7EB"),
]:
    kpi_html += f"""
  <div style="background:{card_bg};border:0.5px solid {bd};border-radius:10px;
              padding:10px 6px;text-align:center;">
    <div style="font-size:16px;font-weight:500;color:{color};">{value}</div>
    <div style="font-size:10px;color:{sub_c};">{label}</div>
  </div>"""
kpi_html += "</div>"
st.markdown(kpi_html, unsafe_allow_html=True)

# ── Tab selector ──────────────────────────────────────────────────────────────
tab_labels = ["Machines", "Zones", "Analytics"]
tab_cols = st.columns(3)
for i, tl in enumerate(tab_labels):
    active_tab = st.session_state.mobile_tab == tl
    bg_t  = "rgba(255,255,255,0.10)" if (is_dark and active_tab) else ("#f0f0f0" if (not is_dark and active_tab) else "transparent")
    col_t = (tc if active_tab else sub_c)
    if tab_cols[i].button(
        _tr(tl),
        use_container_width=True,
        key=f"tab_{tl}",
        type="primary" if active_tab else "secondary",
    ):
        st.session_state.mobile_tab = tl
        st.rerun()

st.divider()

# ── Status filter pills ───────────────────────────────────────────────────────
if st.session_state.mobile_tab == "Machines":
    filter_opts = ["All", "ON", "OFF", "MAINTENANCE"]
    f_cols = st.columns(len(filter_opts))
    for i, fo in enumerate(filter_opts):
        is_sel = st.session_state.mobile_filter == fo
        if f_cols[i].button(
            fo,
            use_container_width=True,
            key=f"filt_{fo}",
            type="primary" if is_sel else "secondary",
        ):
            st.session_state.mobile_filter = fo
            st.rerun()
    st.markdown("")

# ════════════════════════════════════════════════════════════════════════
# TAB: MACHINES
# ════════════════════════════════════════════════════════════════════════
if st.session_state.mobile_tab == "Machines":
    filt = st.session_state.mobile_filter
    for _, row in df.iterrows():
        status = str(row.get("Status", "-")).strip()
        if status == "-":
            continue
        if filt != "All" and status != filt:
            continue

        machine = str(row.get("Machine", "?"))
        ops     = row.get("Operator_Count", None)
        zone    = row.get("Zone", None)
        dot_c   = STATUS_COLORS.get(status, "#888")
        bg_s    = f"rgba({','.join(str(int(int(dot_c.lstrip('#')[i:i+2], 16))) for i in (0,2,4))},0.10)"

        ops_text  = str(int(ops)) if ops is not None and str(ops).replace(".", "").isdigit() else "—"
        zone_text = str(zone) if zone and str(zone) != "nan" else "—"

        st.markdown(f"""
<div style="background:{card_bg};border:0.5px solid {bd};border-left:3px solid {dot_c};
            border-radius:10px;padding:10px 14px;margin-bottom:6px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-size:13px;font-weight:500;color:{tc};">{machine}</span>
    <span style="background:{bg_s};color:{dot_c};border:0.5px solid {dot_c}44;
                 border-radius:20px;padding:2px 9px;font-size:11px;">{_tr(status)}</span>
  </div>
  <div style="margin-top:5px;display:flex;gap:14px;">
    <span style="font-size:11px;color:{sub_c};">👷 {ops_text}</span>
    <span style="font-size:11px;color:{sub_c};">📍 {zone_text}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════
# TAB: ZONES
# ════════════════════════════════════════════════════════════════════════
elif st.session_state.mobile_tab == "Zones":
    zone_entries = df[df["Status"] == "-"]
    if zone_entries.empty:
        st.info("No zone/storage entries in this area.")
    else:
        for _, row in zone_entries.iterrows():
            machine = str(row.get("Machine", "?"))
            st.markdown(f"""
<div style="background:{card_bg};border:0.5px solid {bd};border-radius:10px;
            padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px;">
  <span style="font-size:18px;">🗂️</span>
  <div>
    <div style="font-size:13px;font-weight:500;color:{tc};">{machine}</div>
    <div style="font-size:11px;color:{sub_c};">Storage / Zone area</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════
# TAB: ANALYTICS
# ════════════════════════════════════════════════════════════════════════
elif st.session_state.mobile_tab == "Analytics":
    import plotly.graph_objects as go

    plot_bg  = "rgba(0,0,0,0)"
    font_col = "rgba(255,255,255,0.65)" if is_dark else "#444"

    counts = active["Status"].value_counts()
    fig = go.Figure(go.Pie(
        labels=[_tr(s) for s in counts.index],
        values=counts.values,
        hole=0.55,
        marker_colors=[STATUS_COLORS.get(s, "#888") for s in counts.index],
        textinfo="percent",
        textfont_color=font_col,
    ))
    fig.update_layout(
        plot_bgcolor=plot_bg,
        paper_bgcolor=plot_bg,
        font=dict(color=font_col, size=11),
        margin=dict(t=20, b=10, l=0, r=0),
        height=250,
        showlegend=True,
        legend=dict(font=dict(color=font_col, size=10)),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Zone breakdown
    if "Zone" in active.columns and active["Zone"].notna().any():
        import plotly.express as px
        zone_df = active.groupby("Zone")["Status"].count().reset_index()
        zone_df.columns = ["Zone", "Count"]
        fig2 = px.bar(zone_df, x="Zone", y="Count",
                      color_discrete_sequence=["#378ADD"])
        fig2.update_layout(
            plot_bgcolor=plot_bg, paper_bgcolor=plot_bg,
            font=dict(color=font_col, size=11),
            margin=dict(t=10, b=30, l=10, r=10),
            height=200,
            xaxis=dict(color=font_col, gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(color=font_col, gridcolor="rgba(255,255,255,0.06)"),
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
