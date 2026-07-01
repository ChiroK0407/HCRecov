"""
generate_pdf.py  —  HCRecov PDF Report Generator
=================================================
Generates a professional engineering PDF report.

Usage:
    python generate_pdf.py                    # outputs to outputs/
    python generate_pdf.py --out my_report.pdf

All content comes from generate_report_data.py.
Any JSON or engine change is automatically reflected.
"""

import argparse
import io
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ---------------------------------------------------------------------------
# Import shared data module
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_report_data import build_report_payload

# ---------------------------------------------------------------------------
# Brand palette  (change here; everything updates)
# ---------------------------------------------------------------------------
NAVY     = colors.HexColor("#1e3a8a")
RED      = colors.HexColor("#b91c1c")
GREEN    = colors.HexColor("#047857")
SLATE    = colors.HexColor("#334155")
MUTED    = colors.HexColor("#64748b")
BG_LIGHT = colors.HexColor("#f8fafc")
WHITE    = colors.white
BLACK    = colors.black

MPL_NAVY  = "#1e3a8a"
MPL_RED   = "#b91c1c"
MPL_GREEN = "#047857"

PAGE_W, PAGE_H = A4


# ===========================================================================
# CHART BUILDERS  (matplotlib → in-memory PNG → ReportLab Image)
# ===========================================================================

def _chart_to_image(fig, width_cm=16, height_cm=7):
    """Convert a matplotlib figure to a ReportLab Image flowable (in-memory)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                facecolor="white")
    buf.seek(0)
    plt.close(fig)
    return Image(buf, width=width_cm * cm, height=height_cm * cm)


def build_efficiency_chart(chart_data: dict):
    """Bar chart: recovery efficiency by technology."""
    techs = chart_data["technologies"]
    effs  = chart_data["efficiencies"]
    target = chart_data["target_pct"]

    short = ["Membrane", "PSA\n(Adsorption)", "Absorption"]
    colors_bar = [MPL_NAVY, MPL_RED, MPL_GREEN]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    bars = ax.bar(short, effs, color=colors_bar, width=0.5,
                  edgecolor="white", linewidth=1.5, zorder=3)
    ax.axhline(y=target, color="#ef4444", linestyle="--", linewidth=1.8,
               label=f"Min. Plant Target ({target:.0f}%)", zorder=4)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Monomer Recovery Efficiency (%)", fontsize=10, color="#334155")
    ax.set_title("Net Separation Efficiency by Technology\n"
                 "[Feed: 1.20 bar(a) · 64 °C · 5 mol% C3H6]",
                 fontsize=11, fontweight="bold", color="#1e3a8a", pad=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, color="#cbd5e1", zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors="#475569")

    for bar, val in zip(bars, effs):
        label = f"{val:.1f}%"
        if val < target:
            label += "  FAIL"
        ax.text(bar.get_x() + bar.get_width() / 2, val + 2, label,
                ha="center", va="bottom", fontsize=9.5, fontweight="bold",
                color="#1e293b")

    ax.legend(fontsize=9, framealpha=0.6)
    return _chart_to_image(fig, width_cm=16, height_cm=7)


def build_capex_chart(chart_data: dict):
    """Bar chart: CAPEX comparison."""
    techs = ["Membrane", "PSA\n(Adsorption)", "Absorption"]
    capex_lakhs = [v / 100000 for v in chart_data["capex_inr"]]
    colors_bar = [MPL_NAVY, MPL_RED, MPL_GREEN]

    fig, ax = plt.subplots(figsize=(9, 4))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    bars = ax.bar(techs, capex_lakhs, color=colors_bar, width=0.5,
                  edgecolor="white", linewidth=1.5, zorder=3)
    ax.set_ylabel("CAPEX (₹ Lakhs)", fontsize=10, color="#334155")
    ax.set_title("Package Installed Capital Expenditure (CAPEX)\n"
                 "[Standard Catalog Equipment — 2026 Cost Index]",
                 fontsize=11, fontweight="bold", color="#1e3a8a", pad=10)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4, color="#cbd5e1", zorder=0)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors="#475569")
    ax.set_ylim(0, max(capex_lakhs) * 1.25)

    for bar, val in zip(bars, capex_lakhs):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 8,
                f"₹{val:,.1f}L", ha="center", va="bottom",
                fontsize=9.5, fontweight="bold", color="#1e293b")

    return _chart_to_image(fig, width_cm=16, height_cm=6.5)


# ===========================================================================
# STYLES
# ===========================================================================

def build_styles():
    base = getSampleStyleSheet()
    S = {}

    def add(name, parent="Normal", **kw):
        S[name] = ParagraphStyle(name, parent=base[parent], **kw)

    add("cover_title",   "Title",  fontSize=26, textColor=WHITE,
        fontName="Helvetica-Bold", spaceAfter=6, leading=32)
    add("cover_sub",     "Normal", fontSize=13, textColor=colors.HexColor("#bfdbfe"),
        fontName="Helvetica", spaceAfter=4, leading=18)
    add("cover_meta",    "Normal", fontSize=10, textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica")

    add("section_head",  "Normal", fontSize=14, textColor=NAVY,
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=4, leading=18)
    add("body",          "Normal", fontSize=10, textColor=SLATE,
        fontName="Helvetica", leading=14, spaceAfter=4)
    add("body_j",        "Normal", fontSize=10, textColor=SLATE,
        fontName="Helvetica", leading=14, spaceAfter=4, alignment=TA_JUSTIFY)
    add("caption",       "Normal", fontSize=8.5, textColor=MUTED,
        fontName="Helvetica-Oblique", spaceAfter=8, alignment=TA_CENTER)
    add("bullet_item",   "Normal", fontSize=10, textColor=SLATE,
        fontName="Helvetica", leading=14, spaceAfter=3,
        leftIndent=12, bulletIndent=0)
    add("rec_box",       "Normal", fontSize=10, textColor=WHITE,
        fontName="Helvetica-Bold", leading=14, alignment=TA_CENTER)
    add("footer",        "Normal", fontSize=8, textColor=MUTED,
        fontName="Helvetica", alignment=TA_CENTER)
    add("table_cell",    "Normal", fontSize=8, textColor=SLATE,
        fontName="Helvetica", leading=10)

    return S


# ===========================================================================
# FLOWABLE BUILDERS
# ===========================================================================

def cover_page(data: dict, styles: dict) -> list:
    """Dark navy cover block built as a table for reliable background."""
    summary = data["summary"]

    cover_table = Table(
        [[
            Paragraph(summary["title"],   styles["cover_title"]),
            Paragraph(""),
            Paragraph(summary["subtitle"], styles["cover_sub"]),
            Paragraph(""),
            Paragraph(f"{summary['plant']}", styles["cover_meta"]),
            Paragraph(f"{summary['prepared_by']}  ·  {summary['date']}", styles["cover_meta"]),
            Paragraph(f"Project: {data['project']}  ·  {data['version']}", styles["cover_meta"]),
        ]],
        colWidths=[PAGE_W - 4 * cm],
        rowHeights=[PAGE_H - 6 * cm],
    )
    cover_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), NAVY),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 40),
        ("RIGHTPADDING", (0, 0), (-1, -1), 40),
        ("TOPPADDING",   (0, 0), (-1, -1), 60),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 40),
    ]))
    return [cover_table, PageBreak()]


def section_header(title: str, styles: dict) -> list:
    rule = HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=4)
    return [Paragraph(title, styles["section_head"]), rule]


def scope_section(data: dict, styles: dict) -> list:
    summary = data["summary"]
    feed    = data["feed"]
    items = [
        *section_header("1.  Scope & Feed Conditions", styles),
        Paragraph(summary["scope"], styles["body_j"]),
        Spacer(1, 6),
    ]

    feed_rows = [
        ["Parameter", "Value"],
        ["Feed mass flow",          f"{feed['feed_mass_kg_hr']:.1f} kg/hr"],
        ["Feed pressure",           f"{feed['p_feed_bar']:.2f} bar (absolute)"],
        ["Feed temperature",        f"{feed['t_feed_k'] - 273.15:.1f} °C"],
        ["N2 mole fraction",        f"{feed['y_n2']*100:.0f} mol%"],
        ["HC mole fraction (C3H6)", f"{feed['y_hc']*100:.0f} mol%"],
    ]
    t = Table(feed_rows, colWidths=[9 * cm, 7.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_LIGHT, WHITE]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("TEXTCOLOR",    (0, 1), (-1, -1), SLATE),
    ]))
    items.append(t)
    items.append(Spacer(1, 8))
    return items


def efficiency_section(data: dict, styles: dict) -> list:
    chart_data = data["chart_data"]
    items = [
        *section_header("2.  Recovery Efficiency Comparison", styles),
        Paragraph(
            "The chart below shows the net monomer recovery efficiency for each "
            "technology under the stated feed conditions. The dashed red line marks "
            "the minimum plant target of 90%.",
            styles["body_j"]
        ),
        Spacer(1, 6),
        build_efficiency_chart(chart_data),
        Paragraph(
            "Figure 1  —  Net Separation Efficiency (η<sub>global</sub>) by Technology",
            styles["caption"]
        ),
    ]
    return items


def capex_section(data: dict, styles: dict) -> list:
    chart_data = data["chart_data"]
    items = [
        *section_header("3.  Capital Expenditure (CAPEX) Comparison", styles),
        Paragraph(
            "CAPEX estimates are derived from standard catalog equipment using "
            "published scaling exponents (cost index year 2026). "
            "Membrane cost is dominated by the feed gas booster compressor "
            "required to raise the 1.2 bar feed to 16.2 bar permeate differential.",
            styles["body_j"]
        ),
        Spacer(1, 6),
        build_capex_chart(chart_data),
        Paragraph(
            "Figure 2  —  Installed Package CAPEX (INR). Feed compression excluded for PSA and Absorption.",
            styles["caption"]
        ),
    ]
    return items


def matrix_section(data: dict, styles: dict) -> list:
    matrix = data["matrix"]
    headers = matrix["headers"]
    rows    = matrix["rows"]

    # Build table rows
    short_headers = ["Criterion", "Membrane", "PSA", "Absorption"]
    table_data = [short_headers]

    for row in rows:
        table_row = [row["criterion"]] + row["values"]
        table_data.append(table_row)

    col_w = [5.5 * cm, 4 * cm, 4 * cm, 4 * cm]
    t = Table(table_data, colWidths=col_w)

    style_cmds = [
        ("BACKGROUND",   (0, 0), (-1, 0),   NAVY),
        ("TEXTCOLOR",    (0, 0), (-1, 0),   WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),   "Helvetica-Bold"),
        ("FONTNAME",     (0, 1), (0, -1),   "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1),  9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [BG_LIGHT, WHITE]),
        ("GRID",         (0, 0), (-1, -1),  0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN",        (1, 0), (-1, -1),  "CENTER"),
        ("ALIGN",        (0, 0), (0, -1),   "LEFT"),
        ("VALIGN",       (0, 0), (-1, -1),  "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1),  7),
        ("RIGHTPADDING", (0, 0), (-1, -1),  7),
        ("TOPPADDING",   (0, 0), (-1, -1),  5),
        ("BOTTOMPADDING",(0, 0), (-1, -1),  5),
        ("TEXTCOLOR",    (0, 1), (-1, -2),  SLATE),
    ]

    # Highlight best cells in last row (Recommended)
    for col_idx, val in enumerate(table_data[-1][1:], start=1):
        if "YES" in str(val):
            style_cmds.append(("TEXTCOLOR", (col_idx, len(table_data)-1),
                               (col_idx, len(table_data)-1), GREEN))
            style_cmds.append(("FONTNAME",  (col_idx, len(table_data)-1),
                               (col_idx, len(table_data)-1), "Helvetica-Bold"))
        elif "NO" in str(val):
            style_cmds.append(("TEXTCOLOR", (col_idx, len(table_data)-1),
                               (col_idx, len(table_data)-1), RED))

    t.setStyle(TableStyle(style_cmds))

    return [
        *section_header("7.  Technology Comparison Matrix", styles),
        Paragraph(
            "Qualitative and quantitative comparison across key engineering criteria.",
            styles["body"]
        ),
        Spacer(1, 6),
        t,
        Spacer(1, 8),
    ]


def _sanitize_text(text: str) -> str:
    """Replace characters that don't render in ReportLab's base-14 fonts."""
    return (text.replace("Δ", "delta-")
                .replace("η", "eta")
                .replace("≈", "~"))


def ledger_table_for_tech(tech_key: str, ledger: dict, styles: dict) -> list:
    """
    Builds the full per-technology breakdown: component table (rating,
    max/used capacity, CAPEX, OPEX) followed by a separation-efficiency
    statement, exactly mirroring run_assessment.py's printed ledger.
    """
    rows = ledger["rows"]

    items = []

    header = ["Component", "Rating", "Max Capacity", "Used Capacity", "Flow Rate", "ΔP", "CAPEX (INR)", "OPEX (₹/hr)"]
    table_data = [header]
    for row in rows:
        table_data.append([
            Paragraph(_sanitize_text(row["component"]), styles["table_cell"]),
            Paragraph(_sanitize_text(row["rating"]), styles["table_cell"]),
            Paragraph(_sanitize_text(row["max_capacity"]), styles["table_cell"]),
            Paragraph(_sanitize_text(row["used_capacity"]), styles["table_cell"]),
            Paragraph(_sanitize_text(str(row.get("flow_rate", "n/a"))), styles["table_cell"]),
            Paragraph(_sanitize_text(str(row.get("pressure_drop", "n/a"))), styles["table_cell"]),
            Paragraph(f"₹{row['capex']:,.0f}", styles["table_cell"]),
            Paragraph(f"₹{row['opex']:,.2f}", styles["table_cell"]),
        ])

    # Totals row
    table_data.append([
        Paragraph("<b>TOTAL</b>", styles["table_cell"]),
        "", "", "", "", "",
        Paragraph(f"<b>₹{ledger['capex_total']:,.0f}</b>", styles["table_cell"]),
        Paragraph(f"<b>₹{ledger['opex_total']:,.2f}</b>", styles["table_cell"]),
    ])

    col_w = [2.8*cm, 3.2*cm, 2.2*cm, 2.3*cm, 2.0*cm, 1.6*cm, 1.7*cm, 1.5*cm]
    t = Table(table_data, colWidths=col_w, repeatRows=1)
    style_cmds = [
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [BG_LIGHT, WHITE]),
        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#dbeafe")),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style_cmds))
    items.append(t)
    items.append(Spacer(1, 5))

    # Separation efficiency statement(s) — one per component, directly under the table
    for row in rows:
        items.append(Paragraph(
            f"<b>{row['component'].split(' ')[0]}:</b> {_sanitize_text(row['efficiency'])}",
            ParagraphStyle("eff_note", parent=styles["body"], fontSize=8.5,
                          textColor=SLATE, leading=11, spaceAfter=3,
                          fontName="Helvetica-Oblique")
        ))

    items.append(Spacer(1, 6))
    items.append(Paragraph(
        f"<b>Net Recovery Efficiency: {ledger['recovery_pct']:.1f}%</b>  ·  "
        f"Total Package CAPEX: ₹{ledger['capex_total']:,.0f}  ·  "
        f"Total OPEX: ₹{ledger['opex_total']:,.2f}/hr",
        ParagraphStyle("eff_summary", parent=styles["body"], fontSize=9.5,
                      textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=10)
    ))

    return items


def technology_sections(data: dict, styles: dict) -> list:
    """Builds the three per-technology component breakdown sections."""
    ledgers = data["ledgers"]
    items = []
    section_num = 6
    for i, key in enumerate(["membrane", "adsorption", "absorption"]):
        block = section_header(f"{section_num}.{i+1}  Component Breakdown — {ledgers[key]['title']}", styles)
        block += ledger_table_for_tech(key, ledgers[key], styles)
        items.append(KeepTogether(block))
        items.append(Spacer(1, 14))
    return items


def findings_section(data: dict, styles: dict) -> list:
    summary = data["summary"]
    items = [*section_header("8.  Key Findings & Recommendation", styles)]

    for i, finding in enumerate(summary["findings"], 1):
        items.append(Paragraph(f"<b>{i}.</b>  {finding}", styles["bullet_item"]))
        items.append(Spacer(1, 3))

    items.append(Spacer(1, 8))

    # Recommendation box
    rec_table = Table(
        [[Paragraph(
            f"<b>ENGINEERING RECOMMENDATION</b><br/>{summary['recommendation']}",
            styles["rec_box"]
        )]],
        colWidths=[PAGE_W - 4 * cm],
    )
    rec_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), GREEN),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", (0, 0), (-1, -1), [4, 4, 4, 4]),
    ]))
    items.append(rec_table)
    items.append(Spacer(1, 10))
    return items


# ===========================================================================
# PAGE TEMPLATE  (header / footer)
# ===========================================================================

def _make_page_template(data: dict):
    summary = data["summary"]

    def on_page(canvas, doc):
        canvas.saveState()
        w, h = A4

        # Header strip
        canvas.setFillColor(NAVY)
        canvas.rect(0, h - 1.1 * cm, w, 1.1 * cm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(WHITE)
        canvas.drawString(1.5 * cm, h - 0.75 * cm, summary["title"])
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(w - 1.5 * cm, h - 0.75 * cm, summary["date"])

        # Footer
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(
            w / 2, 0.6 * cm,
            f"{summary['plant']}  ·  {summary['prepared_by']}  ·  Page {doc.page}"
        )
        canvas.restoreState()

    return on_page


# ===========================================================================
# MAIN BUILDER
# ===========================================================================

def generate_pdf(output_path: str | Path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data    = build_report_payload()
    styles  = build_styles()
    on_page = _make_page_template(data)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=1.8 * cm,
        title=data["summary"]["title"],
        author=data["summary"]["prepared_by"],
        subject="Hydrocarbon Recovery Technology Assessment",
    )

    story = []
    story += cover_page(data, styles)
    story += scope_section(data, styles)
    story.append(Spacer(1, 6))
    story += efficiency_section(data, styles)
    story.append(Spacer(1, 6))
    story += capex_section(data, styles)
    story.append(PageBreak())
    story += technology_sections(data, styles)
    story += matrix_section(data, styles)
    story += findings_section(data, styles)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅  PDF written → {output_path}")
    return str(output_path)


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate HCRecov PDF report")
    parser.add_argument("--out", default="outputs/HCRecov_Report.pdf",
                        help="Output PDF path (default: outputs/HCRecov_Report.pdf)")
    args = parser.parse_args()

    out = Path(__file__).resolve().parent / args.out
    generate_pdf(out)
