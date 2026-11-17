# Factory Monitor Pro

A shop floor monitoring dashboard for a metal formwork and scaffolding manufacturer. It shows the live status of every machine on the real AutoCAD floor layout, checks operator coverage against the standard crew, and rolls up uptime across factories and areas.

**Live app:** _link added after deployment_

## What it does

- **Multi-factory, multi-area.** Four production areas across two factories, each with its own AutoCAD (DXF) layout and coordinate mapping.
- **2D floor plans.** AutoCAD original with status overlay, plus Executive Layout, draw.io-style, Process Ribbon, Node Map and Resource views.
- **3D views.** A technical Plotly 3D scene and a Three.js factory simulation with machines, workers and zones.
- **Operator alerts.** Flags running machines with fewer operators than standard, and can send the alert by email (SMTP) or WhatsApp (Twilio).
- **Executive dashboard.** Fleet uptime, running and offline counts, and per-area and per-process health ranked worst first.
- **Daily history.** Auto-saves a snapshot per area each day so past days can be reloaded and compared.
- **Bilingual.** English and Arabic display, including machine names.
- **Mobile view.** A phone-friendly page with KPIs, machine and zone lists, and the layout view.
- **PDF export.** A one-click status report.

## How it works

Supervisors keep updating one Excel status sheet per area (machine, status, zone, operator count). The app reads those sheets, maps each machine onto its position in the DXF layout, and renders the views above. Rows with status `-` are storage or WIP zones: they appear on the plan but are excluded from uptime and alerts.

## Stack

Python · Streamlit · pandas · Plotly · ezdxf · Pillow · ReportLab · Three.js · SMTP · Twilio

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501. On Windows you can also use `1_INSTALL_FIRST.bat` and `2_RUN_DASHBOARD.bat`.

## Project layout

```
app.py                  main dashboard
pages/2_Mobile_View.py  mobile page
mobile.py               standalone mobile app (port 8502)
utils/                  history, PDF report, alerts, themes, DXF parsing
assets/                 layout images, DXF files, 3D template
data/                   Excel status sheets and daily history snapshots
```
