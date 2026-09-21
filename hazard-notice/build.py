"""Build the Searle Forestry Hazard Notice / Inspection Acknowledgement PDF.

    python3 build.py             # writes hazard_notice.html + Hazard Notice ... .pdf
    python3 build.py --html-only

Two A4 portrait pages: the hazard notice, and the inspection acknowledgement
and registration form the visitor signs. Brand follows the Searle Forestry
marketing template - olive #1D2308 on cream #FBFAF8, Cormorant Garamond
headings, Inter body. Fonts and logo are inlined as data URIs so the HTML is
self-contained and the PDF embeds them.

The REA Act licence line sits in the footer of both pages: Forestry Sales
Limited is the licensed agent, Searle Forestry the trading style, and s 121
requires both on every page of a set.
"""
import base64, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

LICENCE = "Forestry Sales Limited, Licensed Agent REA Act 2008"
AGENT = "Forestry Sales Limited (trading as Searle Forestry)"

HAZARDS = (
    "Active harvesting and silviculture operations, Felling, hung-up and wind-thrown "
    "trees, falling branches, Hauler ropes, guy ropes and breaking-out areas, Skid sites "
    "and landings, Log stacks, log trucks and logging traffic, Narrow one-lane forestry "
    "roads, blind corners and RT-controlled roads, Slash, stumps, windrows and debris, "
    "Cutover and recently planted land, Uneven ground including steep slopes, banks, "
    "bluffs and slips, Slippery ground surfaces, Holes in the ground, old stumps and "
    "tomos, Streams, culverts, fords and water crossings, Drains and ponds, Quarries, "
    "metal pits and unfenced excavations, Fire risk in dry slash and cutover, Chemicals, "
    "fertilisers and spray operations (ground and aerial), Electric fences, Livestock, "
    "stock yards and gates, Animals (including dogs), hunters and firearms, Buildings, "
    "disused structures, old wire rope and abandoned equipment, Workers and contractors, "
    "Chainsaws and other hand-held equipment, Forestry machinery (harvesters, "
    "fellerbunchers, skidders, haulers, loaders, excavators, bulldozers, graders, etc.), "
    "do not approach, climb on or operate machinery!"
)

RULES = [
    f"You enter the property at your own risk and you will not hold the landowner or {AGENT} "
    "or its licensees liable for any loss and/or harm and/or damage suffered.",

    "Do not venture off the track with your vehicle under any circumstances \u2013 there are "
    "dangerous hazards which may include steep sidings, bluffs and holes which could cause "
    "serious injury to you and/or your passengers.",

    "You will comply with all instructions given by the licensee/s or our vendors at any time.",

    "You are responsible for all people who accompany you. All children are to be supervised "
    "by an adult while on the property.",

    "If you take any vehicle onto the property, it must hold a current WoF, be in good working "
    "condition and suitable for use in the conditions. You must hold a current drivers licence "
    "and have sufficient driver training and/or experience to operate the vehicle.",

    "In the event that such a vehicle is an ATV, it is to be operated strictly in accordance "
    "with the conditions set out in the \u201cAgriculture Guideline \u2013 Safe Use of ATVs on "
    "New Zealand Farms\u201d and the manufacturer.",

    "Please keep your vehicle to the obvious tracks and away from all slopes and apparent "
    "hazardous areas.",

    "Keep your speed below 30km/hr maximum. Please be courteous at all times.",

    "Caution is required with any livestock.",

    "Smoking and setting fires is prohibited in all buildings and anywhere on the property.",

    "You will not trespass onto neighbouring land.",

    "You use best endeavours and not cause any damage to the property. If any damage does "
    "occur, you will notify the licensee/s or vendors immediately.",

    "Parts of the tracks may be steep, and/or the surface may be slippery, particularly during "
    "or immediately after rain, therefore you should operate your vehicle in four wheel drive "
    "during the time you are on the property and/or avoid such problem areas.",

    "You will take care to keep yourself safe and avoid the hazards noted above, as well as "
    "any other hazards.",

    "You will leave all gates and fences as you find them. Please treat all fences as being "
    "electric, and that they are \u201clive\u201d.",

    "When you leave the property, you will report back to the licensee to confirm that you and "
    "all people accompanying you have left the property.",

    "Your pets must stay in your vehicle at all times while on the property.",

    "Do not drink any water from taps unless advised.",
]


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def css():
    fonts = (ASSETS / "fonts.css").read_text(encoding="utf-8")
    return fonts + """
:root { --olive:#1D2308; --cream:#FBFAF8; --ink:#22211D; --mute:#6b6a64;
        --line:#d9d6cc; --band:#f1f0e8; }
@page { size:A4 portrait; margin:0; }
html, body { margin:0; padding:0; background:var(--cream); color:var(--ink);
  font-family:'Inter','Segoe UI',Arial,sans-serif; font-size:9.1pt; line-height:1.42;
  -webkit-print-color-adjust:exact; print-color-adjust:exact; }
.page { position:relative; width:210mm; height:297mm; overflow:hidden;
  background:var(--cream); padding:14mm 14mm 20mm; box-sizing:border-box;
  page-break-after:always; }
.page:last-child { page-break-after:auto; }
h1 { font-family:'Cormorant Garamond',Georgia,serif; font-weight:600; color:var(--olive);
  margin:0; letter-spacing:.5px; text-transform:uppercase; }

/* masthead */
.mast { display:flex; align-items:center; gap:7mm; }
.mast .tri { width:17mm; flex:none; }
.mast h1 { font-size:37pt; line-height:.95; }
.mast.form h1 { text-transform:none; font-weight:500; letter-spacing:0; }
.mast .brand { margin-left:auto; text-align:right; flex:none; }
.mast .brand img { width:41mm; display:block; }
.mast.form h1 { font-size:25pt; line-height:1.06; }
.rule { height:1.6pt; background:var(--olive); margin:5mm 0 0; }

.intro { color:var(--olive); font-size:9.5pt; font-weight:300; line-height:1.45;
  margin:5.5mm 0 0; }
.intro + .intro { margin-top:3mm; }
.comply { font-weight:600; font-size:9.2pt; color:var(--ink); margin:5mm 0 0;
  text-align:center; }
.hr { height:.8pt; background:var(--line); margin:3mm 0 3.5mm; }

/* numbered requirements */
ol.rules { list-style:none; margin:0; padding:0; counter-reset:r; }
ol.rules li { counter-increment:r; position:relative; padding:0 0 1.8mm 11mm;
  font-size:8.5pt; line-height:1.38; }
ol.rules li::before { content:counter(r); position:absolute; left:0; top:.2mm;
  width:6.4mm; height:4.4mm; background:var(--olive); color:#fff; border-radius:1pt;
  font-size:6.6pt; font-weight:600; display:flex; align-items:center;
  justify-content:center; }
.closing { font-size:8.5pt; margin:2.5mm 0 0; padding-left:11mm; }

/* form tables */
.band { background:var(--olive); color:#fff; font-weight:600; font-size:9.2pt;
  letter-spacing:.3px; padding:2.1mm 4mm; margin:4mm 0 0; }
.band.first { margin-top:6mm; }
.rows { border:.6pt solid var(--line); border-top:none; }
.rows .row { padding:2.3mm 4mm; font-size:8.9pt; color:var(--ink);
  border-bottom:.6pt solid var(--line); }
.rows .row:last-child { border-bottom:none; }
.rows .row:nth-child(odd) { background:var(--band); }
.rows .row.tall { padding:3.6mm 4mm; }
.ack p { font-size:8.9pt; margin:3.2mm 0 0; }
.sig { margin:5.5mm 0 0; font-size:8.9pt; display:flex; align-items:flex-end; gap:5mm; }
.sig .line { flex:1; max-width:95mm; border-bottom:.8pt solid var(--olive);
  height:7mm; }
.thanks { font-size:8.9pt; margin:4mm 0 0; }

/* footer */
.foot { position:absolute; left:14mm; right:14mm; bottom:9mm;
  display:flex; align-items:flex-end; justify-content:space-between;
  border-top:.6pt solid var(--line); padding-top:2.6mm; }
.foot .lic { font-size:7.4pt; color:var(--mute); letter-spacing:.2px; }
.foot .lic b { color:var(--olive); font-weight:600; }
.foot img { width:31mm; display:block; }
"""


def triangle():
    """Hazard triangle in brand olive."""
    return ("<svg class='tri' viewBox='0 0 100 88' xmlns='http://www.w3.org/2000/svg'>"
            "<path d='M50 2 97 84H3Z' fill='#1D2308'/>"
            "<rect x='44.5' y='27' width='11' height='31' rx='5.5' fill='#FBFAF8'/>"
            "<circle cx='50' cy='69' r='6.2' fill='#FBFAF8'/></svg>")


def foot(logo):
    return (f"<div class='foot'><div class='lic'><b>{LICENCE}</b></div>"
            f"<img src='{logo}' alt='Searle Forestry'></div>")


def page_one(logo):
    rules = "".join(f"<li>{r}</li>" for r in RULES)
    return f"""<div class="page">
  <div class="mast">{triangle()}<h1>Hazard Notice</h1></div>
  <div class="rule"></div>
  <p class="intro">This is a work place, and a number of hazards exist which cannot be
    eliminated. Forestry and rural property hazards that may be encountered include but
    are not limited to:</p>
  <p class="intro">{HAZARDS}</p>
  <p class="comply">To minimise the effect of hazards during your visit we ask that you
    comply with the following requirements:</p>
  <div class="hr"></div>
  <ol class="rules">{rules}</ol>
  <p class="closing">If you have any questions or concerns please advise the licensee
    immediately.</p>
  {foot(logo)}
</div>"""


def page_two(logo):
    blank = "<div class='row tall'>&nbsp;</div>"
    visitor = "".join(
        f"<div class='row'>{f}</div>"
        for f in ["Name:", "Address:", "Email:", "Vehicle Registration:", "Date:",
                  "Phone Number:"])
    accompanying = "".join("<div class='row'>Name:</div>" for _ in range(4))
    return f"""<div class="page">
  <div class="mast form"><h1>Inspection Acknowledgement<br>and Registration</h1></div>
  <div class="rule"></div>

  <div class="band first">Property Name/Address:</div>
  <div class="rows">{blank}{blank}</div>

  <div class="band">Visitor Details:</div>
  <div class="rows">{visitor}</div>

  <div class="band">Accompanying People:</div>
  <div class="rows">{accompanying}</div>

  <div class="band">Hazard Notice:</div>
  <div class="ack">
    <p>I/we acknowledge that I/we have received a copy and have read the Hazard Notice and
      are aware of our obligations under the Health and Safety at Work Act 2015 to comply
      with the direction of such notice and of the Licensee and Staff of the Vendor.
      (Please ensure all people in our party read the Hazard Notice).</p>
    <p>I/we voluntarily accept all the risks known and unknown of visiting and inspecting
      this property.</p>
    <p>I/we indemnify the landowners, lessees, management and {AGENT} as licensees against
      all damage, loss and liability arising from my access to this property.</p>
  </div>
  <div class="sig"><span>Signature:</span><span class="line"></span></div>
  <p class="thanks">Thank you for your attention to these matters. Enjoy your visit, and
    have a safe journey home.</p>
  <p class="thanks">Please ensure all visitors report to the salesperson upon exiting the
    property.</p>
  {foot(logo)}
</div>"""


def build():
    logo = data_uri(ASSETS / "logo_light_bg.png", "image/png")
    doc = ("<!doctype html><html lang='en-NZ'><head><meta charset='utf-8'>"
           "<title>Hazard Notice and Acknowledgement \u2014 Searle Forestry</title>"
           f"<style>{css()}</style></head><body>"
           f"{page_one(logo)}{page_two(logo)}</body></html>")
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
    out = HERE / "Hazard Notice and Acknowledgement - Searle Forestry.pdf"
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
