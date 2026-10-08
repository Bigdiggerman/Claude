#!/usr/bin/env python3
"""Commission Pipeline workbook helper.

The pipeline lives in an .xlsx with ONE main sheet laid out as:

  A1  title            A2  "As at <date>. Blue = inputs; black = formulas; yellow = assumption to confirm."
  A4  section title    A5  header row       A6..  data rows      "Total" row
  (blank rows)
  A12 section title    A13 header row       ...   "Total" row
  (blank row)
  "Notes" heading then one free-text note per row

Columns: A Property | B Status | C Price ($) | D Rate - first $500k | E Rate - balance |
         F Searle share | G Gross commission ($) | H George % | I George ($) | J James % |
         K James ($) | L Net to Searle ($) | M Notes
G, I, K, L and the Total row are formulas; everything else is an input.

Sub-commands (all JSON in / JSON out, so the run is deterministic):

  parse-xlsx  --xlsx FILE --out data.json        read a real workbook (binary) into data.json
  parse-dump  --dump FILE --out data.json        read the Microsoft 365 connector's text dump of the
                                                 workbook (tab-separated rows) into data.json (lossy: % rounded)
  merge-dump  --data data.json --dump FILE       overlay hand edits seen in the dump onto the authoritative
                                                 data.json (the normal weekly path; prints what changed)
  build       --data data.json --out FILE [--asat "12 October 2026"] [--recalc]
                                                 write a fresh, fully formatted workbook from data.json
  add         --data data.json --section "under contract"|"possibles" --property NAME --status TEXT
              --price N --rate-first 0.04 --rate-balance 0.025 [--share 1] [--george 0] [--james 0.15]
              [--notes TEXT] [--assume price,rate_first,rate_balance,share] [--source-id ID]
                                                 append a row (refuses a duplicate property name)
  set         --data data.json --property NAME [--status ..] [--price ..] [--notes ..] [--section ..]
                                                 update an existing row (moves it if --section given)
  commission  --price N [--rate-first 0.04] [--rate-balance 0.025] [--share 1] [--min-fee 10000]
                                                 print the gross commission for a price
  summary     --data data.json                   markdown table of every row with computed $ figures
  seen        --data data.json [--add ID --property NAME --source SRC] [--check ID]
                                                 the "Seen" register of listing ids already handled

data.json shape:
{
  "title": "...", "asat": "8 October 2026", "legend": "...",
  "sections": [{"name": "Under contract", "rows": [ROW, ...]},
               {"name": "Possibles - not yet under contract", "rows": [ROW, ...]}],
  "notes": ["...", ...],
  "seen": [{"id": "searleagri:lm-farms", "property": "LM Farms", "source": "searleagri", "first_seen": "2026-10-12"}]
}
ROW = {"property","status","price" (number or null),"rate_first","rate_balance","share","george","james",
       "notes","assumptions": [field names whose cell is yellow]}
"""
import argparse, json, re, sys, os, subprocess, shutil, tempfile, datetime

DEFAULTS = dict(rate_first=0.04, rate_balance=0.025, share=1.0, george=0.0, james=0.15, min_fee=10000)
SECTION_UNDER = "Under contract"
SECTION_POSS = "Possibles - not yet under contract"
HEADERS = ["Property", "Status", "Price ($)", "Rate - first $500k", "Rate - balance", "Searle share",
           "Gross commission ($)", "George %", "George ($)", "James %", "James ($)", "Net to Searle ($)", "Notes"]
MONEY_FMT = '\\$#,##0;"($"#,##0\\);\\-'
PCT_FMT = '0.0%;\\(0.0%\\);\\-'
INPUT_COLS = {"price": "C", "rate_first": "D", "rate_balance": "E", "share": "F", "george": "H", "james": "J"}


# ----------------------------------------------------------------------------- maths
def gross_commission(price, rate_first=0.04, rate_balance=0.025, share=1.0, min_fee=None):
    """Tiered fee: rate_first on the first $500k, rate_balance on the balance, times Searle's share."""
    if price in (None, ""):
        return None
    price = float(price)
    g = (min(price, 500000) * rate_first + max(price - 500000, 0) * rate_balance)
    if min_fee is not None:
        g = max(g, float(min_fee))
    return round(g * share, 2)


def row_figures(r):
    g = gross_commission(r.get("price"), r.get("rate_first", DEFAULTS["rate_first"]),
                         r.get("rate_balance", DEFAULTS["rate_balance"]), r.get("share", 1.0))
    if g is None:
        return dict(gross=None, george=None, james=None, net=None)
    ge = round(g * float(r.get("george") or 0), 2)
    ja = round(g * float(r.get("james") or 0), 2)
    return dict(gross=g, george=ge, james=ja, net=round(g - ge - ja, 2))


# ----------------------------------------------------------------------------- helpers
def norm_name(s):
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    stop = {"forest", "forests", "farm", "farms", "limited", "ltd", "the", "and", "of", "station", "block", "road", "rd"}
    toks = [t for t in s.split() if t not in stop]
    return " ".join(toks)


def find_row(data, name):
    key = norm_name(name)
    for sec in data["sections"]:
        for r in sec["rows"]:
            if norm_name(r["property"]) == key:
                return sec, r
    # loose match: all tokens of the shorter name inside the longer one
    for sec in data["sections"]:
        for r in sec["rows"]:
            a, b = set(norm_name(r["property"]).split()), set(key.split())
            if a and b and (a <= b or b <= a):
                return sec, r
    return None, None


def section_by_name(data, name):
    n = name.lower()
    for sec in data["sections"]:
        if sec["name"].lower().startswith(n) or n in sec["name"].lower():
            return sec
    raise SystemExit(f"unknown section {name!r}; have {[s['name'] for s in data['sections']]}")


def load(path):
    with open(path) as f:
        d = json.load(f)
    d.setdefault("seen", [])
    d.setdefault("notes", [])
    return d


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def to_number(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ("", "-", "—"):
        return None
    neg = s.startswith("(") or s.startswith("-")
    pct = s.endswith("%")
    s = re.sub(r"[^0-9.]", "", s)
    if not s:
        return None
    n = float(s)
    if pct:
        n = n / 100.0
    return -n if neg else n


# ----------------------------------------------------------------------------- parse-xlsx
def parse_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path)  # formulas kept
    ws = wb.worksheets[0]
    data = {"title": ws["A1"].value, "asat": "", "legend": "", "sections": [], "notes": [], "seen": []}
    a2 = ws["A2"].value or ""
    m = re.match(r"As at (.+?)\.\s*(.*)", a2)
    if m:
        data["asat"], data["legend"] = m.group(1), m.group(2)
    rows = list(ws.iter_rows(min_row=1, max_row=ws.max_row))
    i = 0
    cur = None
    in_notes = False
    while i < len(rows):
        row = rows[i]
        a = row[0].value
        b = row[1].value if len(row) > 1 else None
        if isinstance(a, str) and a.strip() == "Notes" and b is None:
            in_notes = True
            i += 1
            continue
        if in_notes:
            if isinstance(a, str) and a.strip():
                data["notes"].append(a.strip())
            i += 1
            continue
        if isinstance(a, str) and a.strip() == "Property" and b == "Status":
            i += 1
            continue
        if isinstance(a, str) and a.strip() and b is None and i > 2 and a.strip() != "Total":
            cur = {"name": a.strip(), "rows": []}
            data["sections"].append(cur)
            i += 1
            continue
        if isinstance(a, str) and a.strip() == "Total":
            cur = None
            i += 1
            continue
        if cur is not None and isinstance(a, str) and a.strip():
            r = {"property": a.strip(), "status": (b or "").strip() if isinstance(b, str) else (b or ""),
                 "price": to_number(row[2].value) if not str(row[2].value or "").startswith("=") else None,
                 "rate_first": to_number(row[3].value), "rate_balance": to_number(row[4].value),
                 "share": to_number(row[5].value), "george": to_number(row[7].value), "james": to_number(row[9].value),
                 "notes": (row[12].value or "") if len(row) > 12 else "", "assumptions": []}
            for field, col in INPUT_COLS.items():
                c = ws[f"{col}{row[0].row}"]
                if c.fill is not None and c.fill.fill_type == "solid" and str(c.fill.fgColor.rgb).upper().endswith("FFFF00"):
                    r["assumptions"].append(field)
            cur["rows"].append(r)
        i += 1
    if "Seen" in wb.sheetnames:
        s = wb["Seen"]
        for row in s.iter_rows(min_row=2, values_only=True):
            if row and row[0]:
                data["seen"].append({"id": row[0], "property": row[1], "source": row[2], "first_seen": str(row[3] or "")})
    return data


# ----------------------------------------------------------------------------- parse-dump
def parse_dump(path):
    """Parse the Microsoft 365 connector's read_resource output for an .xlsx.

    That output is: a header line per sheet ("## Sheet: <name> — N rows × M columns (A1:M26)") followed by
    tab-separated cell rows, then optionally a "Formulas" section. Formula cells show their last cached value
    (or nothing); we ignore them and recompute. Yellow-cell assumptions are not visible in the dump, so they are
    carried over from a previous data.json via --merge-assumptions-from if given.
    """
    text = open(path, encoding="utf-8").read()
    sheets = re.split(r"^## Sheet: ", text, flags=re.M)
    main, seen_txt = None, None
    for s in sheets[1:]:
        name = s.split("—")[0].split("\n")[0].strip()
        body = s.split("\n", 1)[1] if "\n" in s else ""
        body = re.split(r"^(?:Formulas|## Formulas)\b.*$", body, flags=re.M)[0]
        if name.lower() == "seen":
            seen_txt = body
        elif main is None:
            main = body
    if main is None:
        raise SystemExit("no sheet found in dump")
    lines = [l.rstrip("\n") for l in main.split("\n")]
    data = {"title": "", "asat": "", "legend": "", "sections": [], "notes": [], "seen": []}
    cur, in_notes = None, False
    for idx, line in enumerate(lines):
        if re.match(r"^\[\d+ empty rows?\]\s*$", line):
            line = ""
        cells = line.split("\t")
        a = cells[0].strip() if cells else ""
        b = cells[1].strip() if len(cells) > 1 else ""
        rest_empty = all(not c.strip() for c in cells[1:])
        if idx == 0 and a:
            data["title"] = a
            continue
        m = re.match(r"As at (.+?)\.\s*(.*)", a)
        if m and not data["asat"]:
            data["asat"], data["legend"] = m.group(1), m.group(2)
            continue
        if a == "Notes" and rest_empty:
            in_notes = True
            continue
        if in_notes:
            if a:
                data["notes"].append(a)
            continue
        if a == "Property" and b == "Status":
            continue
        if a == "Total":
            cur = None
            continue
        if a and rest_empty and cur is None:
            cur = {"name": a, "rows": []}
            data["sections"].append(cur)
            continue
        if cur is not None and a:
            cells += [""] * (13 - len(cells))
            cur["rows"].append({"property": a, "status": b, "price": to_number(cells[2]),
                                "rate_first": to_number(cells[3]), "rate_balance": to_number(cells[4]),
                                "share": to_number(cells[5]), "george": to_number(cells[7]), "james": to_number(cells[9]),
                                "notes": cells[12].strip(), "assumptions": []})
    if seen_txt:
        for line in seen_txt.split("\n")[1:]:
            c = line.split("\t")
            if c and c[0].strip() and c[0].strip() != "id":
                c += [""] * (4 - len(c))
                data["seen"].append({"id": c[0].strip(), "property": c[1].strip(), "source": c[2].strip(), "first_seen": c[3].strip()})
    return data


# ----------------------------------------------------------------------------- build
def build(data, out, asat=None, recalc=False):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Commission Pipeline"
    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill("solid", fgColor="FF2F4F2F")
    tot_fill = PatternFill("solid", fgColor="FFE2EFDA")
    yellow = PatternFill("solid", fgColor="FFFFFF00")
    blue = Font(name="Arial", size=11, color="FF0000FF")
    black = Font(name="Arial", size=11)
    formula_font = Font(name="Calibri", size=11)
    wrap = Alignment(wrap_text=True, vertical="top")

    for col, w in zip("ABCDEFGHIJKLM", [24, 38, 14, 12, 12, 10, 16, 10, 12, 10, 12, 16, 60]):
        ws.column_dimensions[col].width = w

    asat = asat or data.get("asat") or datetime.date.today().strftime("%-d %B %Y")
    ws["A1"] = data.get("title") or "Searle Forestry - Commission Pipeline (excl. GST)"
    ws["A1"].font = Font(name="Arial", size=14, bold=True)
    ws["A2"] = f"As at {asat}. {data.get('legend') or 'Blue = inputs; black = formulas; yellow = assumption to confirm.'}"
    ws["A2"].font = Font(name="Arial", size=9)
    ws.row_dimensions[1].height = 17.25
    ws.row_dimensions[2].height = 15

    r = 4
    for sec in data["sections"]:
        ws.cell(r, 1, sec["name"]).font = Font(name="Arial", size=12, bold=True)
        ws.row_dimensions[r].height = 15
        r += 1
        for ci, h in enumerate(HEADERS, 1):
            c = ws.cell(r, ci, h)
            c.font = Font(name="Arial", size=11, bold=True, color="FFFFFFFF")
            c.fill = hdr_fill
            c.border = border
            c.alignment = Alignment(wrap_text=True)
        ws.row_dimensions[r].height = 26.25
        r += 1
        first = r
        for row in sec["rows"]:
            vals = {1: row["property"], 2: row.get("status", ""), 3: row.get("price"),
                    4: row.get("rate_first", DEFAULTS["rate_first"]), 5: row.get("rate_balance", DEFAULTS["rate_balance"]),
                    6: row.get("share", 1.0) if row.get("share") is not None else 1.0,
                    8: row.get("george") or 0.0, 10: row.get("james") if row.get("james") is not None else DEFAULTS["james"],
                    13: row.get("notes", "")}
            for ci in range(1, 14):
                c = ws.cell(r, ci)
                c.border = border
                c.alignment = wrap
                c.font = black
            for ci, v in vals.items():
                ws.cell(r, ci, v)
            for ci in (3, 4, 5, 6, 8, 10):
                ws.cell(r, ci).font = blue
            ws.cell(r, 3).number_format = MONEY_FMT
            for ci in (4, 5, 6, 8, 10):
                ws.cell(r, ci).number_format = PCT_FMT
            ws.cell(r, 7, f'=IF(C{r}="","",(MIN(C{r},500000)*D{r}+MAX(C{r}-500000,0)*E{r})*F{r})')
            ws.cell(r, 9, f'=IF(G{r}="","",G{r}*H{r})')
            ws.cell(r, 11, f'=IF(G{r}="","",G{r}*J{r})')
            ws.cell(r, 12, f'=IF(G{r}="","",G{r}-I{r}-K{r})')
            for ci in (7, 9, 11, 12):
                ws.cell(r, ci).number_format = MONEY_FMT
                ws.cell(r, ci).font = formula_font
            for field in row.get("assumptions", []):
                col = INPUT_COLS.get(field)
                if col:
                    ws[f"{col}{r}"].fill = yellow
            longest = max(len(str(row.get("status", ""))) / 36.0, len(str(row.get("notes", ""))) / 58.0, 1.0)
            ws.row_dimensions[r].height = 15 if longest <= 1.0 else (26.25 if longest <= 2.0 else 39)
            r += 1
        last = r - 1
        ws.cell(r, 1, "Total")
        for ci in range(1, 14):
            c = ws.cell(r, ci)
            c.border = border
            c.font = Font(name="Arial", size=11, bold=True)
            c.fill = tot_fill
        if last >= first:
            for col in "CGIKL":
                ws[f"{col}{r}"] = f"=SUM({col}{first}:{col}{last})"
                ws[f"{col}{r}"].number_format = MONEY_FMT
        ws.row_dimensions[r].height = 15
        r += 3
    r -= 1  # two blank rows before Notes, three between sections (matches the original layout)

    ws.cell(r, 1, "Notes").font = Font(name="Arial", size=11, bold=True)
    r += 1
    for n in data.get("notes", []):
        ws.cell(r, 1, n).font = Font(name="Arial", size=9)
        r += 1
    ws.freeze_panes = "B6"

    s = wb.create_sheet("Seen")
    for ci, h in enumerate(["id", "property", "source", "first_seen"], 1):
        s.cell(1, ci, h).font = Font(bold=True)
    for i, item in enumerate(data.get("seen", []), 2):
        s.cell(i, 1, item.get("id")); s.cell(i, 2, item.get("property")); s.cell(i, 3, item.get("source")); s.cell(i, 4, item.get("first_seen"))
    s.column_dimensions["A"].width = 40; s.column_dimensions["B"].width = 30; s.column_dimensions["C"].width = 16; s.column_dimensions["D"].width = 14

    wb.calculation.fullCalcOnLoad = True
    wb.save(out)
    if recalc:
        recalc_with_libreoffice(out)
    return out


def recalc_with_libreoffice(path):
    """Round-trip through LibreOffice so formula cells carry cached values (nice for previews). Best effort."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return False
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run([soffice, "--headless", "--calc", "--convert-to", "xlsx", "--outdir", tmp, path],
                       check=True, capture_output=True, timeout=180)
        produced = os.path.join(tmp, os.path.basename(path))
        if os.path.exists(produced):
            # keep our styling: copy only cached values back into our workbook
            import openpyxl
            src = openpyxl.load_workbook(produced, data_only=True)
            dst = openpyxl.load_workbook(path)
            # openpyxl cannot write cached values alongside formulas; so instead replace the file wholesale
            # only if LibreOffice preserved the number formats we care about.
            ok = src.worksheets[0]["C6"].number_format.startswith("\\$") or src.worksheets[0]["C6"].number_format.startswith('"$') or "$" in src.worksheets[0]["C6"].number_format
            if ok:
                shutil.copy(produced, path)
                return True
    except Exception as e:  # noqa
        sys.stderr.write(f"recalc skipped: {e}\n")
    return False


# ----------------------------------------------------------------------------- commands
def cmd_add(a):
    data = load(a.data)
    sec, existing = find_row(data, a.property)
    if existing:
        raise SystemExit(f"REFUSED: '{a.property}' already on the pipeline as '{existing['property']}' in section '{sec['name']}'. Use `set` instead.")
    sec = section_by_name(data, a.section)
    row = {"property": a.property, "status": a.status or "", "price": to_number(a.price),
           "rate_first": a.rate_first, "rate_balance": a.rate_balance, "share": a.share,
           "george": a.george, "james": a.james, "notes": a.notes or "",
           "assumptions": [x.strip() for x in (a.assume or "").split(",") if x.strip()]}
    sec["rows"].append(row)
    if a.source_id:
        data["seen"].append({"id": a.source_id, "property": a.property, "source": a.source_id.split(":")[0],
                             "first_seen": datetime.date.today().isoformat()})
    save(a.data, data)
    print(json.dumps({"added": row, "figures": row_figures(row), "section": sec["name"]}, indent=1))


def cmd_set(a):
    data = load(a.data)
    sec, row = find_row(data, a.property)
    if not row:
        raise SystemExit(f"no row matching {a.property!r}")
    for field in ("status", "notes"):
        v = getattr(a, field)
        if v is not None:
            row[field] = v
    for field in ("price", "rate_first", "rate_balance", "share", "george", "james"):
        v = getattr(a, field)
        if v is not None:
            row[field] = to_number(v)
    if a.assume is not None:
        row["assumptions"] = [x.strip() for x in a.assume.split(",") if x.strip()]
    if a.section:
        target = section_by_name(data, a.section)
        if target is not sec:
            sec["rows"].remove(row)
            target["rows"].append(row)
    save(a.data, data)
    print(json.dumps({"updated": row, "figures": row_figures(row)}, indent=1))


def cmd_summary(a):
    data = load(a.data)
    out = [f"**{data.get('title')}** — as at {data.get('asat')}", ""]
    grand = 0.0
    for sec in data["sections"]:
        out += [f"### {sec['name']}", "", "| Property | Status | Price | Gross | George | James | Net to Searle |", "|---|---|---:|---:|---:|---:|---:|"]
        tot = dict(price=0.0, gross=0.0, george=0.0, james=0.0, net=0.0)
        for r in sec["rows"]:
            f = row_figures(r)
            def m(v):
                return "" if v is None else f"${v:,.0f}"
            flag = " ⚠" if r.get("assumptions") else ""
            out.append(f"| {r['property']}{flag} | {r.get('status','')} | {m(r.get('price'))} | {m(f['gross'])} | {m(f['george'])} | {m(f['james'])} | {m(f['net'])} |")
            if f["gross"] is not None:
                tot["price"] += r.get("price") or 0; tot["gross"] += f["gross"]; tot["george"] += f["george"]; tot["james"] += f["james"]; tot["net"] += f["net"]
        out.append(f"| **Total** | | **${tot['price']:,.0f}** | **${tot['gross']:,.0f}** | **${tot['george']:,.0f}** | **${tot['james']:,.0f}** | **${tot['net']:,.0f}** |")
        out.append("")
        grand += tot["net"]
    out.append(f"Net to Searle across all sections: **${grand:,.0f}** (excl. GST). ⚠ = contains a yellow assumption cell.")
    print("\n".join(out))


def cmd_seen(a):
    data = load(a.data)
    if a.add:
        if any(s["id"] == a.add for s in data["seen"]):
            print(json.dumps({"already": a.add}))
        else:
            data["seen"].append({"id": a.add, "property": a.property or "", "source": a.source or a.add.split(":")[0],
                                 "first_seen": datetime.date.today().isoformat()})
            save(a.data, data)
            print(json.dumps({"added": a.add}))
    elif a.check:
        print(json.dumps({"seen": any(s["id"] == a.check for s in data["seen"])}))
    else:
        print(json.dumps(data["seen"], indent=1))


def merge_dump(data, dumped):
    """Overlay edits made by hand in Excel (visible in the connector dump) onto the authoritative data.json.

    The dump rounds percentages to one decimal (1.99% shows as 2.0%), so a rate is only taken from the dump when it
    differs from the stored value by more than rounding. Rows deleted in Excel are dropped; rows added by hand are
    kept (with no assumption flags). Returns a list of human-readable change descriptions.
    """
    changes = []
    seen_keys = set()
    for dsec in dumped["sections"]:
        tsec = None
        for sec in data["sections"]:
            if sec["name"].lower() == dsec["name"].lower():
                tsec = sec
        if tsec is None:
            tsec = {"name": dsec["name"], "rows": []}
            data["sections"].append(tsec)
            changes.append(f"new section '{dsec['name']}' added by hand")
        for dr in dsec["rows"]:
            seen_keys.add(norm_name(dr["property"]))
            osec, orow = find_row(data, dr["property"])
            if orow is None:
                dr["assumptions"] = []
                tsec["rows"].append(dr)
                changes.append(f"row '{dr['property']}' added by hand in '{dsec['name']}'")
                continue
            if osec is not tsec:
                osec["rows"].remove(orow); tsec["rows"].append(orow)
                changes.append(f"'{orow['property']}' moved to '{tsec['name']}' by hand")
            for field in ("status", "notes"):
                if (dr.get(field) or "") != (orow.get(field) or ""):
                    changes.append(f"'{orow['property']}' {field}: '{orow.get(field)}' -> '{dr.get(field)}'")
                    orow[field] = dr.get(field) or ""
            if dr.get("price") != orow.get("price"):
                changes.append(f"'{orow['property']}' price: {orow.get('price')} -> {dr.get('price')}")
                orow["price"] = dr.get("price")
                if dr.get("price") is not None and "price" in orow.get("assumptions", []):
                    pass  # leave the yellow flag; Warwick clears it by telling us or editing the notes
            for field in ("rate_first", "rate_balance", "share", "george", "james"):
                dv, ov = dr.get(field), orow.get(field)
                dv = 0.0 if dv is None else dv
                ov = 0.0 if ov is None else ov
                if abs(dv - ov) > 0.0006:
                    changes.append(f"'{orow['property']}' {field}: {ov} -> {dv}")
                    orow[field] = dv
    for sec in data["sections"]:
        for r in list(sec["rows"]):
            if norm_name(r["property"]) not in seen_keys and not any(norm_name(r["property"]) == norm_name(x) for x in seen_keys):
                sec["rows"].remove(r)
                changes.append(f"row '{r['property']}' deleted by hand - dropped")
    if dumped.get("notes"):
        if dumped["notes"] != data.get("notes"):
            changes.append("Notes block edited by hand")
        data["notes"] = dumped["notes"]
    for item in dumped.get("seen", []):
        if not any(x["id"] == item["id"] for x in data["seen"]):
            data["seen"].append(item)
    return changes


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("parse-xlsx"); s.add_argument("--xlsx", required=True); s.add_argument("--out", required=True)
    s = sub.add_parser("parse-dump"); s.add_argument("--dump", required=True); s.add_argument("--out", required=True)
    s.add_argument("--merge-assumptions-from", help="previous data.json whose yellow-cell flags should carry over")
    s = sub.add_parser("merge-dump"); s.add_argument("--data", required=True); s.add_argument("--dump", required=True)
    s = sub.add_parser("build"); s.add_argument("--data", required=True); s.add_argument("--out", required=True)
    s.add_argument("--asat"); s.add_argument("--recalc", action="store_true")
    s = sub.add_parser("add"); s.add_argument("--data", required=True); s.add_argument("--section", required=True)
    s.add_argument("--property", required=True); s.add_argument("--status", default="")
    s.add_argument("--price"); s.add_argument("--rate-first", type=float, default=DEFAULTS["rate_first"])
    s.add_argument("--rate-balance", type=float, default=DEFAULTS["rate_balance"]); s.add_argument("--share", type=float, default=1.0)
    s.add_argument("--george", type=float, default=0.0); s.add_argument("--james", type=float, default=DEFAULTS["james"])
    s.add_argument("--notes", default=""); s.add_argument("--assume"); s.add_argument("--source-id")
    s = sub.add_parser("set"); s.add_argument("--data", required=True); s.add_argument("--property", required=True)
    for f in ("status", "notes", "price", "rate_first", "rate_balance", "share", "george", "james", "section", "assume"):
        s.add_argument("--" + f.replace("_", "-"), dest=f)
    s = sub.add_parser("commission"); s.add_argument("--price", required=True)
    s.add_argument("--rate-first", type=float, default=DEFAULTS["rate_first"]); s.add_argument("--rate-balance", type=float, default=DEFAULTS["rate_balance"])
    s.add_argument("--share", type=float, default=1.0); s.add_argument("--min-fee", type=float, default=DEFAULTS["min_fee"])
    s.add_argument("--george", type=float, default=0.0); s.add_argument("--james", type=float, default=DEFAULTS["james"])
    s = sub.add_parser("summary"); s.add_argument("--data", required=True)
    s = sub.add_parser("seen"); s.add_argument("--data", required=True); s.add_argument("--add"); s.add_argument("--check")
    s.add_argument("--property"); s.add_argument("--source")
    a = p.parse_args(argv)

    if a.cmd == "parse-xlsx":
        save(a.out, parse_xlsx(a.xlsx)); print(f"wrote {a.out}")
    elif a.cmd == "parse-dump":
        d = parse_dump(a.dump)
        if a.merge_assumptions_from and os.path.exists(a.merge_assumptions_from):
            prev = load(a.merge_assumptions_from)
            for sec in d["sections"]:
                for r in sec["rows"]:
                    _, pr = find_row(prev, r["property"])
                    if pr:
                        r["assumptions"] = pr.get("assumptions", [])
        save(a.out, d); print(f"wrote {a.out}: {sum(len(s['rows']) for s in d['sections'])} rows, {len(d['seen'])} seen")
    elif a.cmd == "merge-dump":
        d = load(a.data)
        ch = merge_dump(d, parse_dump(a.dump))
        save(a.data, d)
        print(json.dumps({"changes": ch}, indent=1))
    elif a.cmd == "build":
        build(load(a.data), a.out, a.asat, a.recalc); print(f"wrote {a.out} ({os.path.getsize(a.out)} bytes)")
    elif a.cmd == "add":
        cmd_add(a)
    elif a.cmd == "set":
        cmd_set(a)
    elif a.cmd == "commission":
        price = to_number(a.price)
        g = gross_commission(price, a.rate_first, a.rate_balance, a.share, a.min_fee)
        print(json.dumps({"price": price, "gross_excl_gst": g, "george": round(g * a.george, 2), "james": round(g * a.james, 2),
                          "net_to_searle": round(g - g * a.george - g * a.james, 2), "gross_incl_gst": round(g * 1.15, 2)}, indent=1))
    elif a.cmd == "summary":
        cmd_summary(a)
    elif a.cmd == "seen":
        cmd_seen(a)


if __name__ == "__main__":
    main()
