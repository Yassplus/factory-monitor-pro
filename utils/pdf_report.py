"""
PDF Report Generator — Factory 5 Production Monitor.
Light-background professional report with proper BOM tree visualization.
"""

import io
import datetime
import pandas as pd
from PIL import Image as PILImage
from collections import defaultdict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, PageBreak, KeepTogether, Flowable,
)

# ── Color palette (light background — colors must be visible on white) ─────────
C_WHITE   = colors.white
C_OFFWHITE= colors.HexColor("#f8fafc")
C_LIGHT   = colors.HexColor("#f1f5f9")
C_BORDER  = colors.HexColor("#cbd5e1")
C_TEXT    = colors.HexColor("#1e293b")
C_MUTED   = colors.HexColor("#64748b")
C_BLUE    = colors.HexColor("#1d4ed8")
C_BLUE_LT = colors.HexColor("#dbeafe")
C_GREEN   = colors.HexColor("#15803d")
C_GREEN_LT= colors.HexColor("#dcfce7")
C_RED     = colors.HexColor("#b91c1c")
C_RED_LT  = colors.HexColor("#fee2e2")
C_AMBER   = colors.HexColor("#b45309")
C_AMBER_LT= colors.HexColor("#fef3c7")
C_PURPLE  = colors.HexColor("#7c3aed")
C_PURPLE_LT=colors.HexColor("#ede9fe")
C_CYAN    = colors.HexColor("#0e7490")
C_CYAN_LT = colors.HexColor("#cffafe")
C_GREY    = colors.HexColor("#475569")
C_GREY_LT = colors.HexColor("#f1f5f9")
C_ACCENT  = colors.HexColor("#0f172a")  # header bar

STATUS_COLORS    = {"ON": C_GREEN,  "OFF": C_RED,    "MAINTENANCE": C_AMBER}
STATUS_BG        = {"ON": C_GREEN_LT,"OFF": C_RED_LT, "MAINTENANCE": C_AMBER_LT}
LEVEL_COLORS     = {4: C_GREEN,  3: C_PURPLE,  2: C_BLUE,  1: C_GREY}
LEVEL_BG         = {4: C_GREEN_LT, 3: C_PURPLE_LT, 2: C_BLUE_LT, 1: C_GREY_LT}
LEVEL_LABELS_SHORT = {4: "600 Finished Good", 3: "500 Semi-Finished",
                      2: "400 Sub-Assembly",  1: "200 Raw Material"}


def _styles():
    s = {
        "title": ParagraphStyle("title", fontSize=20, fontName="Helvetica-Bold",
                                textColor=C_WHITE, alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", fontSize=9, fontName="Helvetica",
                                   textColor=colors.HexColor("#94a3b8"),
                                   alignment=TA_CENTER, spaceAfter=2),
        "section": ParagraphStyle("section", fontSize=11, fontName="Helvetica-Bold",
                                  textColor=C_ACCENT, spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", fontSize=9, fontName="Helvetica",
                               textColor=C_TEXT, spaceAfter=3),
        "small": ParagraphStyle("small", fontSize=8, fontName="Helvetica",
                                textColor=C_MUTED, spaceAfter=2),
        "cell_header": ParagraphStyle("cell_header", fontSize=12, fontName="Helvetica-Bold",
                                      textColor=C_ACCENT, spaceBefore=10, spaceAfter=4),
        "bom_node": ParagraphStyle("bom_node", fontSize=8.5, fontName="Helvetica",
                                   textColor=C_TEXT, spaceAfter=2),
    }
    return s


def _header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4

    # Top bar — dark navy
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, h - 1.6*cm, w, 1.6*cm, fill=1, stroke=0)
    # Blue accent stripe
    canvas.setFillColor(C_BLUE)
    canvas.rect(0, h - 0.10*cm, w, 0.10*cm, fill=1, stroke=0)

    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(1*cm, h - 1.05*cm, "FACTORY 5 — PRODUCTION MONITOR")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(1*cm, h - 1.38*cm, "Area 1 · Section 5 · Confidential")
    now = datetime.datetime.now().strftime("%d %b %Y  %H:%M")
    canvas.drawRightString(w - 1*cm, h - 1.05*cm, now)

    # Bottom bar
    canvas.setFillColor(C_LIGHT)
    canvas.rect(0, 0, w, 0.85*cm, fill=1, stroke=0)
    canvas.setStrokeColor(C_BORDER)
    canvas.line(0, 0.85*cm, w, 0.85*cm)
    canvas.setFillColor(C_MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(1*cm, 0.3*cm,
                      "DWG: F5-S5-MAP-001  |  Production Planning Dept")
    canvas.drawRightString(w - 1*cm, 0.3*cm, f"Page {doc.page}")

    canvas.restoreState()


def _kpi_table(total, n_on, n_off, n_mnt, uptime):
    pct = lambda n: f"{round(n/total*100) if total else 0}%"
    data = [
        ["TOTAL\nMACHINES", "RUNNING\n(ON)", "STOPPED\n(OFF)", "MAINTENANCE", "UPTIME\nRATE"],
        [str(total), str(n_on), str(n_off), str(n_mnt), f"{uptime}%"],
        ["in this section", pct(n_on), pct(n_off), pct(n_mnt), "machines running"],
    ]
    cw = [3.0*cm] * 5
    t  = Table(data, colWidths=cw, rowHeights=[0.65*cm, 1.1*cm, 0.45*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), C_ACCENT),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.HexColor("#94a3b8")),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), 7),
        ("BACKGROUND", (0,1), (-1,1), C_WHITE),
        ("FONTNAME",   (0,1), (-1,1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,1), (-1,1), 18),
        ("BACKGROUND", (0,2), (-1,2), C_LIGHT),
        ("FONTNAME",   (0,2), (-1,2), "Helvetica"),
        ("FONTSIZE",   (0,2), (-1,2), 7.5),
        ("TEXTCOLOR",  (0,2), (-1,2), C_MUTED),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR",  (0,1), (0,1), C_BLUE),
        ("TEXTCOLOR",  (1,1), (1,1), C_GREEN),
        ("TEXTCOLOR",  (2,1), (2,1), C_RED),
        ("TEXTCOLOR",  (3,1), (3,1), C_AMBER),
        ("TEXTCOLOR",  (4,1), (4,1), C_GREEN),
        ("BOX",        (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",  (0,0), (-1,-1), 0.5, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    return t


def _machine_table(df, styles):
    import re
    def base(n): return re.sub(r'\s*\d+\s*$', '', n).strip()

    # Deduplicate by base name
    agg = {}
    for _, row in df.iterrows():
        b = base(row["Machine"])
        if b not in agg:
            agg[b] = {"statuses": [], "ops": 0, "zone": row["Zone"], "count": 0}
        agg[b]["statuses"].append(row["Status"])
        agg[b]["ops"] += row.get("Operator_Count", 0)
        agg[b]["count"] += 1

    header = ["Machine Type", "Qty", "Status", "Zone", "Operators"]
    rows   = [header]
    for name, info in agg.items():
        sts = info["statuses"]
        if all(s == "ON" for s in sts):            ag = "ON"
        elif any(s == "MAINTENANCE" for s in sts): ag = "MAINTENANCE"
        elif all(s == "OFF" for s in sts):         ag = "OFF"
        else:
            n_on = sum(1 for s in sts if s == "ON")
            ag   = f"{n_on}/{len(sts)} ON"
        rows.append([name, str(info["count"]), ag, info["zone"], str(info["ops"])])

    cw = [5.5*cm, 1.3*cm, 3.0*cm, 2.0*cm, 2.2*cm]
    t  = Table(rows, colWidths=cw, repeatRows=1)
    style = [
        ("BACKGROUND", (0,0), (-1,0), C_ACCENT),
        ("TEXTCOLOR",  (0,0), (-1,0), C_WHITE),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,0), 8),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("ALIGN",      (0,0), (0,-1), "LEFT"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("FONTNAME",   (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,1), (-1,-1), 8.5),
        ("TEXTCOLOR",  (0,1), (-1,-1), C_TEXT),
        ("BOX",        (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(0,-1),8),
    ]
    for i, row in enumerate(rows[1:], 1):
        st = row[2].split()[0]
        fg = STATUS_COLORS.get(st, C_MUTED)
        bg = STATUS_BG.get(st, C_LIGHT)
        style += [
            ("TEXTCOLOR",  (2, i), (2, i), fg),
            ("FONTNAME",   (2, i), (2, i), "Helvetica-Bold"),
            ("BACKGROUND", (2, i), (2, i), bg),
        ]
        if i % 2 == 0:
            style.append(("BACKGROUND", (0,i), (1,i), C_LIGHT))
            style.append(("BACKGROUND", (3,i), (-1,i), C_LIGHT))
    t.setStyle(TableStyle(style))
    return t


def _cell_table(cell_df, styles):
    if cell_df is None or cell_df.empty:
        return Paragraph("No cell data available.", styles["body"])
    header = ["Cell Name", "Daily Capacity", "Top Selling Product", "Item Code"]
    rows   = [header]
    for _, r in cell_df.iterrows():
        cap = f"{int(r['Capacity']):,} pcs/day" if pd.notna(r.get('Capacity')) else "—"
        rows.append([r.get("Cell","—"), cap,
                     r.get("Top_Desc","—") or "—",
                     r.get("Top_Item","—") or "—"])
    cw = [4.5*cm, 3.0*cm, 6.0*cm, 3.5*cm]
    t  = Table(rows, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), C_ACCENT),
        ("TEXTCOLOR",    (0,0), (-1,0), C_WHITE),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0), 8),
        ("BACKGROUND",   (0,1), (-1,-1), C_WHITE),
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,1), (-1,-1), 8.5),
        ("TEXTCOLOR",    (0,1), (-1,-1), C_TEXT),
        ("TEXTCOLOR",    (1,1), (1,-1), C_BLUE),
        ("FONTNAME",     (1,1), (1,-1), "Helvetica-Bold"),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("ALIGN",        (0,0), (0,-1), "LEFT"),
        ("ALIGN",        (2,0), (2,-1), "LEFT"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("BOX",          (0,0), (-1,-1), 0.5, C_BORDER),
        ("INNERGRID",    (0,0), (-1,-1), 0.3, C_BORDER),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (0,-1), 8),
        ("LEFTPADDING",  (2,0), (2,-1), 8),
    ]))
    return t


def _hex(c) -> str:
    """Safe hex string from reportlab color — always returns 6-char RRGGBB."""
    try:
        h = c.hexval()          # returns '0xRRGGBB'
        return h.replace('0x','').replace('0X','').upper().zfill(6)
    except Exception:
        return "000000"


def _safe_text(s: str) -> str:
    """Strip non-latin1 characters (Arabic etc.) for Helvetica compatibility."""
    return "".join(c if ord(c) < 256 else "?" for c in str(s))


def _bom_tree_section(bom_data, styles) -> list:
    """
    Render BOM as a proper visual tree per cell.
    Layout: each BOM level = a row of colored boxes side by side.
    Levels connected by downward arrow rows (drawn as a Table with arrow text).
    Colors: dark text on light background — fully visible on white paper.
    Arabic text stripped (Helvetica does not support Arabic glyphs).
    """
    elements = []
    if not bom_data:
        elements.append(Paragraph("No BOM data available.", styles["body"]))
        return elements

    # Explicit dark-on-light color pairs for maximum visibility
    LEVEL_FG  = {4: "#15803d", 3: "#6d28d9", 2: "#1d4ed8", 1: "#374151"}
    LEVEL_BG  = {4: "#dcfce7", 3: "#ede9fe", 2: "#dbeafe", 1: "#f3f4f6"}
    LEVEL_BD  = {4: "#15803d", 3: "#6d28d9", 2: "#1d4ed8", 1: "#9ca3af"}
    LEVEL_LBL = {4: "600  FINISHED GOOD", 3: "500  SEMI-FINISHED",
                 2: "400  SUB-ASSEMBLY",  1: "200  RAW MATERIAL"}

    PAGE_W = A4[0] - 2.4*cm   # usable width

    for cell_name, nodes in bom_data.items():
        if not nodes:
            continue

        elements.append(KeepTogether([
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f172a"),
                       spaceAfter=5),
            Paragraph(_safe_text(f"  {cell_name}"), styles["cell_header"]),
        ]))

        # Group by level
        from collections import defaultdict as _dd
        by_level = _dd(list)
        for n in nodes:
            by_level[n["level"]].append(n)
        levels = sorted(by_level.keys(), reverse=True)   # 4 → 3 → 2 → 1

        for li, lvl in enumerate(levels):
            lvl_nodes = by_level[lvl]
            fg  = LEVEL_FG.get(lvl, "#374151")
            bg  = LEVEL_BG.get(lvl, "#f3f4f6")
            bd  = LEVEL_BD.get(lvl, "#9ca3af")
            lbl = LEVEL_LBL.get(lvl, f"Level {lvl}")

            # ── Level badge ──────────────────────────────────────────────────
            badge_style = ParagraphStyle(
                "badge", fontSize=7.5, fontName="Helvetica-Bold",
                textColor=colors.HexColor(fg),
                backColor=colors.HexColor(bg),
                borderPadding=(3, 6, 3, 6),
                spaceBefore=4, spaceAfter=4,
            )
            elements.append(Paragraph(f"  {lbl}  ", badge_style))

            # ── Node boxes — 4 per row maximum ───────────────────────────────
            MAX_COLS = 4
            chunks = [lvl_nodes[i:i+MAX_COLS]
                      for i in range(0, len(lvl_nodes), MAX_COLS)]

            for chunk in chunks:
                padded = chunk + [None] * (MAX_COLS - len(chunk))
                col_w  = [PAGE_W / MAX_COLS] * MAX_COLS

                # Two-row table: code row + description row
                row_codes = []
                row_descs = []
                for node in padded:
                    if node is None:
                        row_codes.append("")
                        row_descs.append("")
                    else:
                        row_codes.append(_safe_text(node["item"]))
                        desc = _safe_text(node["description"])
                        if len(desc) > 32: desc = desc[:30] + "…"
                        row_descs.append(desc)

                tbl = Table([row_codes, row_descs], colWidths=col_w,
                             rowHeights=[0.70*cm, 0.55*cm])

                ts = [
                    # Code row
                    ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",    (0,0), (-1,0), 8),
                    ("TEXTCOLOR",   (0,0), (-1,0), colors.HexColor(fg)),
                    ("BACKGROUND",  (0,0), (-1,0), colors.HexColor(bg)),
                    # Description row
                    ("FONTNAME",    (0,1), (-1,1), "Helvetica"),
                    ("FONTSIZE",    (0,1), (-1,1), 6.5),
                    ("TEXTCOLOR",   (0,1), (-1,1), colors.HexColor("#374151")),
                    ("BACKGROUND",  (0,1), (-1,1), colors.white),
                    # Borders
                    ("BOX",         (0,0), (-1,-1), 1.2, colors.HexColor(bd)),
                    ("INNERGRID",   (0,0), (-1,-1), 0.4, colors.HexColor("#e5e7eb")),
                    ("LINEABOVE",   (0,1), (-1,1), 0.4, colors.HexColor("#e5e7eb")),
                    # Alignment
                    ("ALIGN",       (0,0), (-1,-1), "CENTER"),
                    ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
                    ("TOPPADDING",  (0,0), (-1,-1), 3),
                    ("BOTTOMPADDING",(0,0),(-1,-1), 3),
                ]
                # Blank out empty cells
                for ci, node in enumerate(padded):
                    if node is None:
                        ts += [
                            ("BACKGROUND", (ci,0), (ci,-1), colors.white),
                            ("BOX",        (ci,0), (ci,-1), 0,  colors.white),
                            ("INNERGRID",  (ci,0), (ci,-1), 0,  colors.white),
                        ]
                tbl.setStyle(TableStyle(ts))
                elements.append(tbl)
                elements.append(Spacer(1, 0.08*cm))

            # ── Arrow connector ───────────────────────────────────────────────
            if li < len(levels) - 1:
                next_fg  = LEVEL_FG.get(levels[li+1], "#374151")
                arrow_style = ParagraphStyle(
                    "arrow", fontSize=16, fontName="Helvetica",
                    textColor=colors.HexColor(next_fg),
                    alignment=TA_CENTER, spaceBefore=2, spaceAfter=2,
                )
                elements.append(Paragraph("v", arrow_style))   # plain v as arrow

        elements.append(Spacer(1, 0.6*cm))

    return elements

def generate_pdf(df: pd.DataFrame, cell_df, bom_data: dict,
                 layout_img_bytes: bytes,
                 total: int, n_on: int, n_off: int, n_mnt: int,
                 uptime: int) -> bytes:
    buf    = io.BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.2*cm, rightMargin=1.2*cm,
        topMargin=2.0*cm,  bottomMargin=1.2*cm,
        title="Factory 5 Production Report",
        author="Production Planning Dept",
    )

    story = []

    # ── Cover block ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("FACTORY 5", styles["title"]))
    story.append(Paragraph("PRODUCTION FLOOR MONITOR — STATUS REPORT", styles["subtitle"]))
    story.append(Paragraph(
        f"Area 1  ·  Section 5  ·  {datetime.datetime.now().strftime('%d %B %Y  %H:%M')}",
        styles["subtitle"]
    ))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=C_BLUE, spaceAfter=12))

    # ── Floor plan ─────────────────────────────────────────────────────────────
    if layout_img_bytes:
        try:
            pil_img = PILImage.open(io.BytesIO(layout_img_bytes)).convert("RGB")
            img_buf = io.BytesIO()
            pil_img.save(img_buf, format="PNG")
            img_buf.seek(0)
            max_w  = 17.0*cm
            aspect = pil_img.height / pil_img.width
            story.append(RLImage(img_buf, width=max_w, height=max_w * aspect * 0.55))
            story.append(Spacer(1, 0.3*cm))
        except Exception:
            pass

    # ── KPIs ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("📊  KEY PERFORMANCE INDICATORS", styles["section"]))
    story.append(_kpi_table(total, n_on, n_off, n_mnt, uptime))
    story.append(Spacer(1, 0.5*cm))

    # ── Machine table ──────────────────────────────────────────────────────────
    story.append(Paragraph("🏭  MACHINE STATUS — GROUPED BY TYPE", styles["section"]))
    story.append(_machine_table(df, styles))
    story.append(Spacer(1, 0.4*cm))

    # ── Cell capacity ──────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("⚡  CELL CAPACITY OVERVIEW", styles["section"]))
    story.append(_cell_table(cell_df, styles))
    story.append(Spacer(1, 0.6*cm))

    # ── BOM Tree ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=4))
    story.append(Paragraph("📦  BILL OF MATERIALS — TREE PER CELL", styles["section"]))
    story.extend(_bom_tree_section(bom_data or {}, styles))

    # ── Footer note ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Paragraph(
        "Generated automatically by Factory 5 Production Monitor  |  "
        "Production Planning Dept  |  Confidential",
        styles["small"]
    ))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buf.seek(0)
    return buf.read()
