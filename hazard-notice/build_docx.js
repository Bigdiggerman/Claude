/**
 * Build the Word version of the Searle Forestry Hazard Notice and Visitor
 * Register. Wording comes from content.py via content.json, so the Word and
 * PDF versions cannot drift:
 *
 *   python3 export_content.py && node build_docx.js
 *
 * Headings are Cormorant Garamond and body text Inter, matching the PDF. Word
 * substitutes if those are not installed locally; the PDF remains the print
 * master.
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, HeadingLevel, LevelFormat,
  PageBreak, Footer, VerticalAlign,
} = require("docx");

const HERE = __dirname;
const C = JSON.parse(fs.readFileSync(path.join(HERE, "content.json"), "utf8"));

const OLIVE = "1D2308", INK = "22211D", MUTE = "6B6A64",
      LINE = "D0CDC2", BAND = "F1F0E8";
const SERIF = "Cormorant Garamond", SANS = "Inter";

// A4 less 14mm margins, in DXA (1440 = 1 inch).
const MARGIN = 794;
const CONTENT_W = 11906 - MARGIN * 2;

const hair = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const cellBorders = { top: hair, bottom: hair, left: hair, right: hair };

const body = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after ?? 120, line: 264 },
  ...opts.paragraph,
  children: [new TextRun({ text, font: SANS, size: 18, color: INK, ...opts.run })],
});

const sectionHead = (text) => new Paragraph({
  spacing: { before: 320, after: 140 },
  keepNext: true,
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 6 } },
  children: [new TextRun({
    text: text.toUpperCase(), font: SANS, size: 17, bold: true,
    color: OLIVE, characterSpacing: 40,
  })],
});

const groupHead = (text) => new Paragraph({
  spacing: { before: 200, after: 80 },
  keepNext: true,
  children: [new TextRun({ text, font: SERIF, size: 26, color: OLIVE })],
});

const bullet = (text) => new Paragraph({
  numbering: { reference: "haz", level: 0 },
  spacing: { after: 60, line: 264 },
  children: [new TextRun({ text, font: SANS, size: 17, color: INK })],
});

/** "Bold lead-in.  Body" -> a numbered paragraph with the lead-in bold. */
const condition = (text) => {
  const i = text.indexOf(".  ");
  const head = i < 0 ? null : text.slice(0, i + 1);
  const rest = i < 0 ? text : text.slice(i + 3);
  return new Paragraph({
    numbering: { reference: "cond", level: 0 },
    spacing: { after: 110, line: 264 },
    children: [
      ...(head ? [new TextRun({ text: head + " ", font: SANS, size: 17, bold: true, color: OLIVE })] : []),
      new TextRun({ text: rest, font: SANS, size: 17, color: INK }),
    ],
  });
};

const cell = (children, opts = {}) => new TableCell({
  width: { size: opts.width, type: WidthType.DXA },
  borders: cellBorders,
  shading: opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill, color: "auto" } : undefined,
  margins: { top: 90, bottom: 90, left: 120, right: 120 },
  verticalAlign: VerticalAlign.CENTER,
  children,
});

const textCell = (text, width, opts = {}) => cell(
  [new Paragraph({
    spacing: { after: 0, line: 240 },
    children: [new TextRun({
      text, font: SANS, size: 17,
      color: opts.head ? "FFFFFF" : INK,
      bold: opts.head || opts.label || false,
      ...(opts.head ? { characterSpacing: 20 } : {}),
    })],
  })],
  { width, fill: opts.head ? OLIVE : opts.fill },
);

/** Two-column label / blank-value table. */
const fieldTable = (labels) => new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [3700, CONTENT_W - 3700],
  rows: labels.map((l) => new TableRow({
    children: [
      textCell(l, 3700, { fill: BAND, label: true }),
      cell([new Paragraph({ spacing: { after: 0 }, children: [] })], { width: CONTENT_W - 3700 }),
    ],
  })),
});

const gridTable = (head, widths, rows) => new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: widths,
  rows: [
    new TableRow({
      tableHeader: true,
      children: head.map((h, i) => textCell(h, widths[i], { head: true })),
    }),
    ...rows.map((r) => new TableRow({
      children: r.map((v, i) => textCell(v, widths[i])),
    })),
  ],
});

const logo = (widthMm) => {
  const w = Math.round((widthMm / 25.4) * 96);
  return new ImageRun({
    type: "png",
    data: fs.readFileSync(path.join(HERE, "assets", "logo_light_bg.png")),
    transformation: { width: w, height: Math.round((w * 96) / 295) },
  });
};

// ---- emergency panel: single shaded cell with a heavy olive left edge -------
const emergencyPanel = () => new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [CONTENT_W],
  rows: [new TableRow({
    children: [new TableCell({
      width: { size: CONTENT_W, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: BAND, color: "auto" },
      borders: {
        top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
        right: { style: BorderStyle.NONE },
        left: { style: BorderStyle.SINGLE, size: 18, color: OLIVE },
      },
      margins: { top: 200, bottom: 120, left: 240, right: 240 },
      children: C.EMERGENCY.map((t, i) => {
        if (i === 0 && t.startsWith("Call 111.")) {
          return new Paragraph({
            spacing: { after: 120, line: 264 },
            children: [
              new TextRun({ text: "Call 111.", font: SANS, size: 18, bold: true, color: OLIVE }),
              new TextRun({ text: t.slice(9), font: SANS, size: 17, color: INK }),
            ],
          });
        }
        return body(t, { after: 120, run: { size: 17 } });
      }),
    })],
  })],
});

const signatureTable = () => new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [CONTENT_W / 2, CONTENT_W / 2],
  rows: [new TableRow({
    children: C.SIGNATURES.map((s) => new TableCell({
      width: { size: CONTENT_W / 2, type: WidthType.DXA },
      borders: cellBorders,
      margins: { top: 900, bottom: 120, left: 120, right: 120 },
      children: [new Paragraph({
        spacing: { after: 0 },
        children: [new TextRun({ text: s, font: SANS, size: 15, color: MUTE })],
      })],
    })),
  })],
});

// ---- document --------------------------------------------------------------
const children = [
  new Paragraph({
    alignment: AlignmentType.RIGHT,
    spacing: { after: 60 },
    children: [logo(38)],
  }),
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { after: 40 },
    children: [new TextRun({ text: C.TITLE, font: SERIF, size: 54, bold: true, color: OLIVE })],
  }),
  new Paragraph({
    spacing: { after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 14, color: OLIVE, space: 8 } },
    children: [new TextRun({
      text: C.SUBTITLE.toUpperCase(), font: SANS, size: 17, color: MUTE, characterSpacing: 40,
    })],
  }),
  ...C.INTRO.map((t) => body(t, { after: 160 })),

  sectionHead("Hazards you may encounter"),
  body("These include, but are not limited to:", { after: 60 }),
  ...C.HAZARD_GROUPS.flatMap(([name, items]) => [groupHead(name), ...items.map(bullet)]),

  sectionHead("Conditions of entry"),
  body(C.CONDITIONS_INTRO, { after: 140 }),
  ...C.CONDITIONS.map(condition),

  sectionHead("In an emergency"),
  emergencyPanel(),

  new Paragraph({ children: [new PageBreak()] }),

  new Paragraph({
    alignment: AlignmentType.RIGHT,
    spacing: { after: 60 },
    children: [logo(38)],
  }),
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { after: 60 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 14, color: OLIVE, space: 8 } },
    children: [new TextRun({ text: C.REGISTER_TITLE, font: SERIF, size: 44, color: OLIVE })],
  }),
  body(C.REGISTER_LEAD, { after: 80, run: { color: MUTE } }),

  sectionHead("Property and site information"),
  fieldTable(C.SITE_FIELDS),
  sectionHead("Visitor details"),
  fieldTable(C.VISITOR_FIELDS),
  sectionHead("People accompanying you"),
  gridTable(C.ACCOMPANYING_HEAD, [5518, 2400, 2400],
            Array.from({ length: C.ACCOMPANYING_ROWS }, () => ["", "", ""])),
  sectionHead("Pre-entry briefing"),
  gridTable(C.BRIEFING_HEAD, [6318, 1600, 2400],
            C.BRIEFING_ROWS.map(([item, detail]) => [item, "", detail])),
  sectionHead("Acknowledgement"),
  ...C.ACKNOWLEDGEMENT.map((t) => body(t, { after: 140 })),
  new Paragraph({ spacing: { after: 100 }, children: [] }),
  signatureTable(),
  new Paragraph({ spacing: { after: 100 }, children: [] }),
  ...C.CLOSING.map((t) => body(t, { after: 100 })),
];

const doc = new Document({
  creator: "Searle Forestry",
  title: `${C.TITLE} — Searle Forestry`,
  description: "Visitor hazard notice, conditions of entry and visitor register.",
  numbering: {
    config: [
      {
        reference: "haz",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 284, hanging: 227 } },
                   run: { color: OLIVE, font: SANS } },
        }],
      },
      {
        reference: "cond",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 454, hanging: 454 } },
                   run: { color: OLIVE, bold: true, font: SANS } },
        }],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: MARGIN, right: MARGIN, bottom: 1000, left: MARGIN },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          border: { top: { style: BorderStyle.SINGLE, size: 6, color: LINE, space: 6 } },
          spacing: { before: 60 },
          children: [new TextRun({
            text: C.LICENCE, font: SANS, size: 14, bold: true, color: MUTE,
          })],
        })],
      }),
    },
    children,
  }],
});

const out = path.join(HERE, "Hazard Notice and Visitor Register - Searle Forestry.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(out, buf);
  console.log("DOCX ->", out, `(${(buf.length / 1e3).toFixed(0)} KB)`);
});
