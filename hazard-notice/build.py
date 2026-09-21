"""Build the Searle Forestry Hazard Notice and Visitor Register PDF.

    python3 build.py             # writes hazard_notice.html + the PDF
    python3 build.py --html-only

Wording lives in content.py; this file is layout only. Brand follows the
Searle Forestry marketing template - olive #1D2308 on cream #FBFAF8,
Cormorant Garamond headings, Inter body. Fonts and logo are inlined as data
URIs so the HTML is self-contained and the PDF embeds them.

Pages are fixed A4 boxes, each carrying its own footer, so the REA Act
licence line lands on every page as s 121 requires (Chromium does not repeat
a position:fixed footer reliably). Content does not reflow between them: if
content.py grows, move the split with PAGE_1_CONDITIONS or add a page, then
re-render and check every page.
"""
import base64, os, subprocess, sys
from pathlib import Path

import content as C

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def css():
    return (ASSETS / "fonts.css").read_text(encoding="utf-8") + """
:root { --olive:#1D2308; --cream:#FBFAF8; --ink:#22211D; --mute:#6b6a64;
        --line:#d0cdc2; --band:#f1f0e8; }
@page { size:A4 portrait; margin:0; }
html, body { margin:0; padding:0; background:var(--cream); color:var(--ink);
  font-family:'Inter','Segoe UI',Arial,sans-serif; font-size:8.7pt; line-height:1.4;
  -webkit-print-color-adjust:exact; print-color-adjust:exact; }
p { margin:0 0 2.6mm; }
.page { position:relative; width:210mm; height:297mm; overflow:hidden;
  background:var(--cream); padding:13mm 14mm 19mm; box-sizing:border-box;
  page-break-after:always; }
.page:last-child { page-break-after:auto; }
.page > :first-child { margin-top:0; }
h1, h2, h3 { font-family:'Cormorant Garamond',Georgia,serif; color:var(--olive); margin:0; }

/* masthead */
.mast { display:flex; align-items:center; gap:6mm; margin-bottom:1mm; }
.mast .tri { width:15mm; flex:none; }
.mast h1 { font-size:27pt; font-weight:600; line-height:1.02; letter-spacing:.3px; }
.mast .sub { font-family:'Inter'; font-size:8.6pt; font-weight:300; color:var(--mute);
  letter-spacing:1.6px; text-transform:uppercase; margin-top:1.4mm; }
.mast .brand { margin-left:auto; flex:none; }
.mast .brand img { width:38mm; display:block; }
.rule { height:1.5pt; background:var(--olive); margin:3.5mm 0 4mm; }

/* section heads */
.sec { font-family:'Inter'; font-size:8.4pt; font-weight:600; letter-spacing:1.9px;
  text-transform:uppercase; color:var(--olive); margin:4.5mm 0 0;
  padding-bottom:1.6mm; border-bottom:.8pt solid var(--line); }
.sec + p, .sec + .cols, .sec + .grp { margin-top:3mm; }
h3.grp { font-size:13pt; font-weight:500; margin:3.5mm 0 1.5mm; }

/* hazard bullets: one group per column, so no bullet is split by a column
   break and each heading sits at the top of its own column */
.cols { display:grid; grid-template-columns:1fr 1fr; column-gap:7mm; align-items:start; }
.cols > div > h3.grp:first-child { margin-top:0; }
ul.haz { list-style:none; margin:0 0 1mm; padding:0; }
ul.haz li { position:relative; padding:0 0 1.2mm 4mm; font-size:8.3pt; line-height:1.34; }
ul.haz li::before { content:''; position:absolute; left:0; top:1.5mm; width:1.7mm;
  height:1.7mm; background:var(--olive); border-radius:50%; }

/* conditions of entry */
ol.rules { list-style:none; margin:0; padding:0; counter-reset:r; }
ol.rules li { counter-increment:r; position:relative; padding:0 0 1.7mm 10mm;
  font-size:8.2pt; line-height:1.35; }
ol.rules li::before { content:counter(r); position:absolute; left:0; top:.2mm;
  width:6.2mm; height:4.3mm; background:var(--olive); color:#fff; border-radius:1pt;
  font-size:6.5pt; font-weight:600; display:flex; align-items:center;
  justify-content:center; }
ol.rules b { color:var(--olive); }

/* emergency callout */
.emerg { background:var(--band); border-left:3pt solid var(--olive); padding:3.4mm 5mm 1mm;
  margin-top:2.5mm; }
.emerg p { font-size:8.2pt; margin-bottom:2.2mm; }
.emerg p:first-child b { font-size:9.2pt; }

/* register */
.lead { color:var(--mute); margin-bottom:1mm; }
table { width:100%; border-collapse:collapse; margin-top:3mm; }
td, th { border:.6pt solid var(--line); padding:2.1mm 3mm; font-size:8.4pt;
  vertical-align:top; text-align:left; }
th { background:var(--olive); color:#fff; font-family:'Inter'; font-weight:600;
  font-size:7.3pt; letter-spacing:.7px; text-transform:uppercase; padding:2.2mm 3mm; }
td.lbl { width:64mm; background:var(--band); font-weight:500; }
td.fill { height:4.2mm; }
.sigrow { display:flex; gap:6mm; margin-top:5mm; }
.sigbox { flex:1; border:.6pt solid var(--line); border-top:none; padding:11mm 3mm 2.2mm;
  font-size:7.8pt; color:var(--mute); border-top:.6pt solid var(--line); }
.closing { margin-top:4.5mm; }
.closing p { font-size:8.4pt; }

/* footer, one per page */
.foot { position:absolute; left:14mm; right:14mm; bottom:8mm; display:flex; align-items:flex-end;
  justify-content:space-between; border-top:.6pt solid var(--line); padding-top:2.4mm; }
.foot .lic { font-size:7.2pt; color:var(--mute); letter-spacing:.2px; font-weight:500; }
.foot img { width:28mm; display:block; }
"""


def triangle():
    return ("<svg class='tri' viewBox='0 0 100 88' xmlns='http://www.w3.org/2000/svg'>"
            "<path d='M50 2 97 84H3Z' fill='#1D2308'/>"
            "<rect x='44.5' y='27' width='11' height='31' rx='5.5' fill='#FBFAF8'/>"
            "<circle cx='50' cy='69' r='6.2' fill='#FBFAF8'/></svg>")


def condition(text):
    """Split "Bold lead-in.  Body" into its two parts."""
    head, _, body = text.partition(".  ")
    return f"<b>{head}.</b> {body}" if body else text


# Where the conditions list splits between page one and page two. Move it if
# the wording in content.py changes length, then re-render and check.
PAGE_1_CONDITIONS = 4


def notice_page(logo, foot):
    groups = "".join(
        f"<div><h3 class='grp'>{name}</h3><ul class='haz'>"
        + "".join(f"<li>{h}</li>" for h in items) + "</ul></div>"
        for name, items in C.HAZARD_GROUPS)
    first = C.CONDITIONS[:PAGE_1_CONDITIONS]
    return f"""<div class="page">
  <div class="mast">{triangle()}
    <div><h1>{C.TITLE}</h1><div class="sub">{C.SUBTITLE}</div></div>
    <div class="brand"><img src="{logo}" alt="Searle Forestry"></div></div>
  <div class="rule"></div>
  {''.join(f'<p>{t}</p>' for t in C.INTRO)}

  <div class="sec">Hazards you may encounter</div>
  <p>These include, but are not limited to:</p>
  <div class="cols">{groups}</div>

  <div class="sec">Conditions of entry</div>
  <p>{C.CONDITIONS_INTRO}</p>
  <ol class="rules">{''.join(f'<li>{condition(c)}</li>' for c in first)}</ol>
  {foot}
</div>"""


def conditions_page(foot):
    rest = C.CONDITIONS[PAGE_1_CONDITIONS:]
    return f"""<div class="page">
  <ol class="rules" start="{PAGE_1_CONDITIONS + 1}"
      style="counter-reset:r {PAGE_1_CONDITIONS}">
    {''.join(f'<li>{condition(c)}</li>' for c in rest)}</ol>

  <div class="sec">In an emergency</div>
  <div class="emerg">{''.join(f'<p>{t}</p>' for t in C.EMERGENCY).replace(
      "Call 111.", "<b>Call 111.</b>", 1)}</div>
  {foot}
</div>"""


def fields(rows):
    return ("<table>" + "".join(
        f"<tr><td class='lbl'>{f}</td><td class='fill'></td></tr>" for f in rows)
        + "</table>")


def register_page_one(logo, foot):
    return f"""<div class="page">
  <div class="mast">
    <div><h1 style="font-size:23pt;font-weight:500">{C.REGISTER_TITLE}</h1></div>
    <div class="brand"><img src="{logo}" alt="Searle Forestry"></div></div>
  <div class="rule"></div>
  <p class="lead">{C.REGISTER_LEAD}</p>

  <div class="sec">Property and site information</div>{fields(C.SITE_FIELDS)}
  <div class="sec">Visitor details</div>{fields(C.VISITOR_FIELDS)}
  {foot}
</div>"""


def register_page_two(foot):
    acc = ("<table><tr>" + "".join(f"<th>{h}</th>" for h in C.ACCOMPANYING_HEAD) + "</tr>"
           + "<tr><td class='fill'></td><td class='fill'></td><td class='fill'></td></tr>"
           * C.ACCOMPANYING_ROWS + "</table>")
    brief = ("<table><tr>" + "".join(f"<th>{h}</th>" for h in C.BRIEFING_HEAD) + "</tr>"
             + "".join(f"<tr><td>{item}</td><td class='fill'></td><td>{detail}</td></tr>"
                       for item, detail in C.BRIEFING_ROWS) + "</table>")
    sig = "".join(f"<div class='sigbox'>{s}</div>" for s in C.SIGNATURES)
    return f"""<div class="page">
  <div class="sec" style="margin-top:0">People accompanying you</div>{acc}
  <div class="sec">Pre-entry briefing</div>{brief}
  <div class="sec">Acknowledgement</div>
  {''.join(f'<p>{t}</p>' for t in C.ACKNOWLEDGEMENT)}
  <div class="sigrow">{sig}</div>
  <div class="closing">{''.join(f'<p>{t}</p>' for t in C.CLOSING)}</div>
  {foot}
</div>"""


def build():
    logo = data_uri(ASSETS / "logo_light_bg.png", "image/png")
    foot = (f"<div class='foot'><div class='lic'>{C.LICENCE}</div>"
            f"<img src='{logo}' alt='Searle Forestry'></div>")
    doc = ("<!doctype html><html lang='en-NZ'><head><meta charset='utf-8'>"
           f"<title>{C.TITLE} \u2014 Searle Forestry</title>"
           f"<style>{css()}</style></head><body>"
           + notice_page(logo, foot) + conditions_page(foot)
           + register_page_one(logo, foot) + register_page_two(foot)
           + "</body></html>")
    out = HERE / "hazard_notice.html"
    out.write_text(doc, encoding="utf-8")
    print("HTML ->", out)
    return out


def to_pdf(html):
    chrome = next((c for c in ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
                               "/usr/bin/chromium", "/usr/bin/google-chrome",
                               r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
                   if os.path.exists(c)), None)
    if not chrome:
        sys.exit("No Chrome/Edge found for PDF rendering")
    out = HERE / "Hazard Notice and Visitor Register - Searle Forestry.pdf"
    tmp = HERE / "_print.pdf"
    tmp.unlink(missing_ok=True)
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                    "--virtual-time-budget=15000", f"--print-to-pdf={tmp}",
                    html.resolve().as_uri()], check=True, capture_output=True)
    if not tmp.exists() or tmp.stat().st_size < 5000:
        sys.exit("Chrome did not produce a PDF - check the HTML renders in a browser")
    os.replace(tmp, out)
    print("PDF  ->", out, f"({out.stat().st_size/1e3:.0f} KB)")
    return out


if __name__ == "__main__":
    h = build()
    if "--html-only" not in sys.argv:
        to_pdf(h)
