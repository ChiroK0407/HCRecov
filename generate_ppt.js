#!/usr/bin/env node
/**
 * generate_ppt.js  —  HCRecov PowerPoint Generator
 * ==================================================
 * Reads report_payload.json (produced by generate_report_data.py)
 * and builds a polished 7-slide engineering presentation.
 *
 * Usage (from HCRecov/ directory):
 *   python -c "from generate_report_data import build_report_payload; import json; open('_payload.json','w').write(json.dumps(build_report_payload()))"
 *   node generate_ppt.js
 *
 * OR use the orchestrator:
 *   python generate_outputs.py --ppt
 *
 * Palette: Midnight Executive (navy / ice-blue / white)
 */

"use strict";
const pptxgen = require("pptxgenjs");
const path    = require("path");
const fs      = require("fs");

// ---------------------------------------------------------------------------
// Load payload from Python-generated JSON bridge
// ---------------------------------------------------------------------------
const PAYLOAD_PATH = path.resolve(__dirname, "_payload.json");
if (!fs.existsSync(PAYLOAD_PATH)) {
  console.error("❌  _payload.json not found. Run generate_outputs.py first.");
  process.exit(1);
}
const D = JSON.parse(fs.readFileSync(PAYLOAD_PATH, "utf8"));
const { summary, feed, chart_data, matrix, ledgers } = D;

// ---------------------------------------------------------------------------
// Output path
// ---------------------------------------------------------------------------
const OUT_DIR = path.resolve(__dirname, "outputs");
fs.mkdirSync(OUT_DIR, { recursive: true });
const OUT_FILE = path.join(OUT_DIR, "HCRecov_Presentation.pptx");

// ---------------------------------------------------------------------------
// Palette & constants  (edit here; all slides update)
// ---------------------------------------------------------------------------
const C = {
  navy:    "1E3A8A",
  ice:     "BFDBFE",
  slate:   "334155",
  muted:   "64748B",
  green:   "047857",
  red:     "B91C1C",
  white:   "FFFFFF",
  offwhite:"F8FAFC",
  mid:     "1D4ED8",
};

const FONT_TITLE  = "Cambria";
const FONT_BODY   = "Calibri";
const SLIDE_W     = 10;   // inches (LAYOUT_16x9)
const SLIDE_H     = 5.625;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeShadow() {
  return { type: "outer", color: "000000", blur: 6, offset: 2, angle: 45, opacity: 0.12 };
}

function addHeader(slide, leftText, rightText = summary.date) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: SLIDE_W, h: 0.52,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText(leftText, {
    x: 0.25, y: 0, w: 7.5, h: 0.52,
    fontFace: FONT_BODY, fontSize: 9, color: C.ice, bold: false,
    valign: "middle", margin: 0
  });
  slide.addText(rightText, {
    x: 7.75, y: 0, w: 2, h: 0.52,
    fontFace: FONT_BODY, fontSize: 9, color: C.ice,
    align: "right", valign: "middle", margin: 0
  });
}

function addFooter(slide, pageNum, total) {
  slide.addText(
    `${summary.plant}  ·  ${summary.prepared_by}  ·  Slide ${pageNum} / ${total}`,
    {
      x: 0, y: 5.35, w: SLIDE_W, h: 0.27,
      fontFace: FONT_BODY, fontSize: 7.5, color: C.muted,
      align: "center", valign: "middle", margin: 0
    }
  );
}

function cardBg(slide, x, y, w, h, fillColor = C.offwhite) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: fillColor },
    line: { color: "E2E8F0", width: 0.5 },
    rectRadius: 0.08,
    shadow: makeShadow()
  });
}

// ---------------------------------------------------------------------------
// Presentation setup
// ---------------------------------------------------------------------------
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = summary.prepared_by;
pres.title  = summary.title;
pres.subject = "Hydrocarbon Recovery Technology Assessment";

const TOTAL_SLIDES = 10;

// ===========================================================================
// SLIDE 1 — Cover
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.navy };

  // Accent shape — right diagonal band
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.8, y: 0, w: 3.2, h: SLIDE_H,
    fill: { color: C.mid, transparency: 55 },
    line: { color: C.mid, transparency: 55 }
  });

  // Main title
  slide.addText(summary.title, {
    x: 0.5, y: 1.2, w: 6.2, h: 1.3,
    fontFace: FONT_TITLE, fontSize: 32, color: C.white, bold: true,
    align: "left", valign: "middle"
  });

  // Subtitle
  slide.addText(summary.subtitle, {
    x: 0.5, y: 2.55, w: 6.2, h: 0.6,
    fontFace: FONT_BODY, fontSize: 13, color: C.ice,
    align: "left", valign: "middle"
  });

  // Meta line
  slide.addText(`${summary.plant}\n${summary.prepared_by}  ·  ${summary.date}`, {
    x: 0.5, y: 3.55, w: 6.2, h: 0.8,
    fontFace: FONT_BODY, fontSize: 10.5, color: "94A3B8",
    align: "left", valign: "top"
  });

  // Version badge
  slide.addText(`Project: ${D.project}  ·  ${D.version}`, {
    x: 0.5, y: 4.8, w: 4, h: 0.3,
    fontFace: FONT_BODY, fontSize: 8.5, color: "64748B",
    align: "left"
  });

  addFooter(slide, 1, TOTAL_SLIDES);
}

// ===========================================================================
// SLIDE 2 — Scope & Feed Conditions
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "Scope & Feed Conditions  |  HCRecov Assessment");
  addFooter(slide, 2, TOTAL_SLIDES);

  // Section title
  slide.addText("Process Scope & Boundary Conditions", {
    x: 0.4, y: 0.65, w: 9.2, h: 0.55,
    fontFace: FONT_TITLE, fontSize: 22, color: C.navy, bold: true
  });

  // Scope text left column
  const scopeText = summary.scope;
  cardBg(slide, 0.4, 1.3, 4.7, 2.5);
  slide.addText("Assessment Scope", {
    x: 0.55, y: 1.35, w: 4.4, h: 0.35,
    fontFace: FONT_BODY, fontSize: 11, color: C.navy, bold: true
  });
  slide.addText(scopeText, {
    x: 0.55, y: 1.72, w: 4.4, h: 1.95,
    fontFace: FONT_BODY, fontSize: 10, color: C.slate, valign: "top"
  });

  // Feed conditions — right column as KPI cards
  const kpis = [
    { label: "Feed Flow",     value: `${feed.feed_mass_kg_hr} kg/hr` },
    { label: "Pressure",      value: `${feed.p_feed_bar.toFixed(2)} bar(a)` },
    { label: "Temperature",   value: `${(feed.t_feed_k - 273.15).toFixed(0)} °C` },
    { label: "HC (C3H6)",     value: `${(feed.y_hc * 100).toFixed(0)} mol%` },
  ];

  kpis.forEach((kpi, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 5.4 + col * 2.3;
    const y = 1.28 + row * 1.3;
    cardBg(slide, x, y, 2.1, 1.1, C.navy);
    slide.addText(kpi.value, {
      x, y: y + 0.1, w: 2.1, h: 0.65,
      fontFace: FONT_TITLE, fontSize: 22, color: C.white,
      bold: true, align: "center", valign: "middle"
    });
    slide.addText(kpi.label, {
      x, y: y + 0.72, w: 2.1, h: 0.32,
      fontFace: FONT_BODY, fontSize: 9, color: C.ice,
      align: "center"
    });
  });

  // Technologies assessed
  cardBg(slide, 0.4, 3.9, 9.2, 1.1);
  slide.addText("Technologies Assessed", {
    x: 0.55, y: 3.92, w: 2.5, h: 0.32,
    fontFace: FONT_BODY, fontSize: 9.5, color: C.navy, bold: true
  });
  const techs = [
    "① Hollow-Fiber Polymeric Membrane Skid",
    "② Twin-Bed Pressure Swing Adsorption (PSA)",
    "③ Heavy Hydrocarbon Gas Absorption Loop",
  ];
  techs.forEach((t, i) => {
    slide.addText(t, {
      x: 0.4 + i * 3.1, y: 4.28, w: 3.0, h: 0.55,
      fontFace: FONT_BODY, fontSize: 10, color: C.slate,
      align: "center", valign: "middle"
    });
  });
}

// ===========================================================================
// SLIDE 3 — Efficiency Chart (native bar chart)
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "Recovery Efficiency Comparison");
  addFooter(slide, 3, TOTAL_SLIDES);

  slide.addText("Net Monomer Recovery Efficiency by Technology", {
    x: 0.4, y: 0.65, w: 9.2, h: 0.5,
    fontFace: FONT_TITLE, fontSize: 20, color: C.navy, bold: true
  });
  slide.addText(
    `Feed: ${feed.p_feed_bar.toFixed(2)} bar(a)  ·  ${(feed.t_feed_k - 273.15).toFixed(0)} °C  ·  ${(feed.y_hc * 100).toFixed(0)} mol% C3H6  ·  Target ≥ ${chart_data.target_pct}%`,
    {
      x: 0.4, y: 1.15, w: 9.2, h: 0.3,
      fontFace: FONT_BODY, fontSize: 10, color: C.muted
    }
  );

  // Native BAR chart
  slide.addChart(pres.charts.BAR, [
    {
      name: "Recovery Efficiency (%)",
      labels: ["Membrane", "PSA (Adsorption)", "Absorption"],
      values: chart_data.efficiencies
    }
  ], {
    x: 0.4, y: 1.5, w: 8, h: 3.6,
    barDir: "col",
    chartColors: [C.navy, C.red, C.green],
    chartArea: { fill: { color: C.offwhite }, roundedCorners: false },
    catAxisLabelColor: C.slate,
    valAxisLabelColor: C.slate,
    valAxisMaxVal: 110,
    valAxisMinVal: 0,
    valGridLine: { color: "E2E8F0", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: "1E293B",
    dataLabelFontFace: FONT_BODY,
    dataLabelFontSize: 11,
    showLegend: false,
  });

  // Manual target line annotation
  slide.addShape(pres.shapes.LINE, {
    x: 0.55, y: 2.77, w: 7.7, h: 0,
    line: { color: "EF4444", width: 1.8, dashType: "dash" }
  });
  slide.addText("Min. Target 90%", {
    x: 8.25, y: 2.65, w: 1.65, h: 0.35,
    fontFace: FONT_BODY, fontSize: 8.5, color: "EF4444", bold: true
  });
}

// ===========================================================================
// SLIDE 4 — CAPEX Chart
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "Capital Expenditure (CAPEX) Comparison");
  addFooter(slide, 4, TOTAL_SLIDES);

  slide.addText("Package Installed CAPEX by Technology", {
    x: 0.4, y: 0.65, w: 9.2, h: 0.5,
    fontFace: FONT_TITLE, fontSize: 20, color: C.navy, bold: true
  });
  slide.addText("Standard Catalog Equipment  ·  2026 Cost Index  (INR × 1 000)", {
    x: 0.4, y: 1.15, w: 9.2, h: 0.3,
    fontFace: FONT_BODY, fontSize: 10, color: C.muted
  });

  slide.addChart(pres.charts.BAR, [
    {
      name: "CAPEX (× ₹1000)",
      labels: ["Membrane", "PSA (Adsorption)", "Absorption"],
      values: chart_data.capex_inr.map(v => Math.round(v / 1000))
    }
  ], {
    x: 0.4, y: 1.5, w: 8, h: 3.6,
    barDir: "col",
    chartColors: [C.navy, C.red, C.green],
    chartArea: { fill: { color: C.offwhite }, roundedCorners: false },
    catAxisLabelColor: C.slate,
    valAxisLabelColor: C.slate,
    valGridLine: { color: "E2E8F0", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: "1E293B",
    dataLabelFontFace: FONT_BODY,
    dataLabelFontSize: 11,
    showLegend: false,
  });

  // Annotation: why membrane is expensive
  slide.addText(
    "Note: Membrane CAPEX includes K-301 feed gas booster\ncompressor (1.2 → 16.2 bar)",
    {
      x: 8.45, y: 1.65, w: 1.4, h: 1.1,
      fontFace: FONT_BODY, fontSize: 7.5, color: C.muted, italic: true
    }
  );
}

// ===========================================================================
// SLIDES 5-7 — Per-Technology Component Breakdown
// ===========================================================================
{
  const techKeys = ["membrane", "adsorption", "absorption"];
  const techColors = [C.navy, C.red, C.green];
  const slideTitles = {
    membrane:   "Membrane Skid — Component Breakdown",
    adsorption: "PSA Skid — Component Breakdown",
    absorption: "Absorption Loop — Component Breakdown",
  };

  techKeys.forEach((key, idx) => {
    const ledger = ledgers[key];
    const slide = pres.addSlide();
    slide.background = { color: C.white };
    addHeader(slide, `${ledger.title}`);
    addFooter(slide, 5 + idx, TOTAL_SLIDES);

    slide.addText(slideTitles[key], {
      x: 0.4, y: 0.62, w: 9.2, h: 0.45,
      fontFace: FONT_TITLE, fontSize: 19, color: techColors[idx], bold: true
    });

    // Build table: header + one row per component + totals row
    const headerRow = ["Component", "Rating", "Max Capacity", "Used Capacity", "Flow Rate", "ΔP", "CAPEX", "OPEX/hr"].map(h => ({
      text: h, options: { bold: true, color: C.white, fill: { color: techColors[idx] }, fontFace: FONT_BODY, fontSize: 9 }
    }));

    const dataRows = ledger.rows.map((row, ri) => {
      const bg = ri % 2 === 0 ? C.offwhite : C.white;
      return [
        { text: row.component,    options: { bold: true, color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 7.5 } },
        { text: row.rating,       options: { color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 7 } },
        { text: row.max_capacity, options: { color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 7 } },
        { text: row.used_capacity,options: { color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 7 } },
        { text: row.flow_rate || "n/a", options: { color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 7 } },
        { text: row.pressure_drop || "n/a", options: { color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 7 } },
        { text: `₹${row.capex.toLocaleString()}`, options: { align: "right", color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 8 } },
        { text: `₹${row.opex.toFixed(2)}`,         options: { align: "right", color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 8 } },
      ];
    });

    const totalRow = [
      { text: "TOTAL", options: { bold: true, color: C.navy, fill: { color: "DBEAFE" }, fontFace: FONT_BODY, fontSize: 8.5 } },
      { text: "", options: { fill: { color: "DBEAFE" } } },
      { text: "", options: { fill: { color: "DBEAFE" } } },
      { text: "", options: { fill: { color: "DBEAFE" } } },
      { text: "", options: { fill: { color: "DBEAFE" } } },
      { text: "", options: { fill: { color: "DBEAFE" } } },
      { text: `₹${ledger.capex_total.toLocaleString()}`, options: { align: "right", bold: true, color: C.navy, fill: { color: "DBEAFE" }, fontFace: FONT_BODY, fontSize: 8.5 } },
      { text: `₹${ledger.opex_total.toFixed(2)}`,         options: { align: "right", bold: true, color: C.navy, fill: { color: "DBEAFE" }, fontFace: FONT_BODY, fontSize: 8.5 } },
    ];

    slide.addTable([headerRow, ...dataRows, totalRow], {
      x: 0.4, y: 1.15, w: 9.2,
      colW: [1.7, 2.0, 1.35, 1.35, 1.0, 0.85, 0.8, 0.8],
      border: { pt: 0.5, color: "E2E8F0" },
      autoPage: false,
    });

    // Efficiency statement card below the table
    const tableHeight = 0.32 * (ledger.rows.length + 2);
    const statY = 1.15 + tableHeight + 0.15;
    cardBg(slide, 0.4, statY, 9.2, 5.15 - statY, C.offwhite);
    slide.addText(
      `Net Recovery Efficiency: ${ledger.recovery_pct.toFixed(1)}%   ·   Total Package CAPEX: ₹${ledger.capex_total.toLocaleString()}   ·   Total OPEX: ₹${ledger.opex_total.toFixed(2)}/hr`,
      {
        x: 0.55, y: statY + 0.08, w: 8.9, h: 0.35,
        fontFace: FONT_BODY, fontSize: 11, color: techColors[idx], bold: true
      }
    );

    // Per-component efficiency note (sanitize delta symbol for safety)
    const effLines = ledger.rows.map(row => {
      const tag = row.component.split(" ")[0];
      const clean = row.efficiency.replace(/Δ/g, "d-");
      return `${tag}: ${clean}`;
    }).join("\n");

    slide.addText(effLines, {
      x: 0.55, y: statY + 0.45, w: 8.9, h: (5.15 - statY) - 0.55,
      fontFace: FONT_BODY, fontSize: 8, color: C.muted, valign: "top",
      italic: true, lineSpacingMultiple: 1.15
    });
  });
}

// ===========================================================================
// SLIDE 8 — Comparison Matrix
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "Technology Comparison Matrix");
  addFooter(slide, 8, TOTAL_SLIDES);

  slide.addText("Multi-Criteria Technology Comparison", {
    x: 0.4, y: 0.65, w: 9.2, h: 0.5,
    fontFace: FONT_TITLE, fontSize: 20, color: C.navy, bold: true
  });

  const rows  = matrix.rows;
  const hdrs  = ["Criterion", "Membrane", "PSA", "Absorption"];

  // Build table data
  const tableData = [
    hdrs.map(h => ({ text: h, options: { bold: true, color: C.white, fill: { color: C.navy }, fontFace: FONT_BODY, fontSize: 10 } })),
    ...rows.map((row, ri) => {
      const bg = ri % 2 === 0 ? C.offwhite : C.white;
      return [
        { text: row.criterion, options: { bold: true, color: C.slate, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 9.5 } },
        ...row.values.map((v, ci) => {
          let color = C.slate;
          if (row.criterion === "Recommended") {
            color = v.includes("YES") ? C.green : C.red;
          }
          if (v.includes("FAIL") || v.includes("No ❌")) color = C.red;
          return { text: v, options: { align: "center", color, fill: { color: bg }, fontFace: FONT_BODY, fontSize: 9.5 } };
        })
      ];
    })
  ];

  slide.addTable(tableData, {
    x: 0.4, y: 1.25, w: 9.2, h: 3.9,
    border: { pt: 0.5, color: "E2E8F0" },
    colW: [2.8, 2.1, 2.1, 2.2],
    rowH: 0.42,
  });
}

// ===========================================================================
// SLIDE 6 — Findings & Recommendation
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.white };
  addHeader(slide, "Key Findings & Engineering Recommendation");
  addFooter(slide, 9, TOTAL_SLIDES);

  slide.addText("Key Findings", {
    x: 0.4, y: 0.65, w: 9.2, h: 0.45,
    fontFace: FONT_TITLE, fontSize: 20, color: C.navy, bold: true
  });

  // Finding cards
  summary.findings.forEach((finding, i) => {
    const y = 1.18 + i * 1.12;
    const dotColor = [C.navy, C.red, C.green][i];
    cardBg(slide, 0.4, y, 9.2, 1.0);

    // Numbered dot
    slide.addShape(pres.shapes.OVAL, {
      x: 0.52, y: y + 0.25, w: 0.45, h: 0.45,
      fill: { color: dotColor }, line: { color: dotColor }
    });
    slide.addText(`${i + 1}`, {
      x: 0.52, y: y + 0.25, w: 0.45, h: 0.45,
      fontFace: FONT_BODY, fontSize: 11, color: C.white,
      bold: true, align: "center", valign: "middle"
    });

    slide.addText(finding, {
      x: 1.1, y: y + 0.08, w: 8.2, h: 0.82,
      fontFace: FONT_BODY, fontSize: 10, color: C.slate, valign: "middle"
    });
  });

  // Recommendation block
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.4, y: 4.52, w: 9.2, h: 0.75,
    fill: { color: C.green }, line: { color: C.green }, rectRadius: 0.08
  });
  slide.addText(`RECOMMENDATION  ·  ${summary.recommendation}`, {
    x: 0.55, y: 4.52, w: 8.9, h: 0.75,
    fontFace: FONT_BODY, fontSize: 9.5, color: C.white,
    bold: false, valign: "middle", align: "left"
  });
}

// ===========================================================================
// SLIDE 7 — Summary / Thank You
// ===========================================================================
{
  const slide = pres.addSlide();
  slide.background = { color: C.navy };

  slide.addText("Summary", {
    x: 0.5, y: 1.0, w: 9, h: 0.7,
    fontFace: FONT_TITLE, fontSize: 28, color: C.white, bold: true, align: "center"
  });

  const passingNames = chart_data.technologies
    .map((t, i) => ({ name: t, eff: chart_data.efficiencies[i], capex: chart_data.capex_inr[i] }))
    .filter(t => t.eff >= chart_data.target_pct);
  const cheapestPassing = passingNames.length
    ? passingNames.reduce((a, b) => (a.capex < b.capex ? a : b))
    : null;

  const techShortNames = ["Membrane", "PSA", "Absorption"];
  const bullets = [
    `Feed: ${feed.feed_mass_kg_hr} kg/hr  ·  ${feed.p_feed_bar} bar(a)  ·  ${(feed.t_feed_k-273.15).toFixed(0)} °C  ·  5 mol% C3H6`,
    ...techShortNames.map((name, i) => {
      const eff = chart_data.efficiencies[i];
      const capex = chart_data.capex_inr[i];
      const status = eff >= chart_data.target_pct ? "Meets target" : "Below 90% minimum";
      return `${name}: ${eff.toFixed(1)}% recovery  |  CAPEX ₹${(capex/100000).toFixed(1)}L  ·  ${status}`;
    }),
    cheapestPassing
      ? `Primary Recommendation: ${cheapestPassing.name}  (lowest CAPEX among options meeting target)`
      : `No technology currently meets the ${chart_data.target_pct}% recovery target`,
  ];

  slide.addText(
    bullets.map((b, i) => ({
      text: b,
      options: { bullet: true, breakLine: i < bullets.length - 1, color: i === bullets.length - 1 ? "86EFAC" : C.ice }
    })),
    { x: 1.0, y: 1.9, w: 8.0, h: 2.6, fontFace: FONT_BODY, fontSize: 11, valign: "top" }
  );

  slide.addText(`Generated: ${D.generated}  ·  ${D.project} ${D.version}`, {
    x: 0, y: 5.25, w: SLIDE_W, h: 0.3,
    fontFace: FONT_BODY, fontSize: 8, color: "475569", align: "center"
  });
}

// ===========================================================================
// Write file
// ===========================================================================
try {
  if (fs.existsSync(OUT_FILE)) {
    fs.rmSync(OUT_FILE, { force: true });
  }
} catch (cleanupErr) {
  console.warn("⚠️  Could not remove existing PPT file before write:", cleanupErr);
}

pres.writeFile({ fileName: OUT_FILE })
  .then(() => console.log(`✅  PPT written → ${OUT_FILE}`))
  .catch(err => { console.error("❌  PPT generation failed:", err); process.exit(1); });
