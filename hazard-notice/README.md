# Hazard Notice — Searle Forestry

Searle Forestry rebrand of the two-page visitor Hazard Notice and Inspection
Acknowledgement, rebuilt from the CRTGA Ltd original.

| File | |
|---|---|
| `Hazard Notice and Acknowledgement - Searle Forestry.pdf` | the document to print or email |
| `build.py` | regenerates the HTML and PDF |
| `hazard_notice.html` | generated, self-contained (fonts and logo inlined) |
| `assets/` | Searle Forestry logo, Cormorant Garamond + Inter web fonts |

## Rebuilding

```
python3 build.py              # HTML + PDF
python3 build.py --html-only  # HTML only
```

Rendering the PDF needs Chrome, Chromium or Edge; `build.py` looks in the
usual install locations.

## Brand and compliance

Olive `#1D2308` on cream `#FBFAF8`, Cormorant Garamond headings, Inter body —
the same system as the marketing report and tender report templates.

The REA Act licence line reads **Forestry Sales Limited, Licensed Agent REA
Act 2008** and sits in the footer of both pages. Forestry Sales Limited is the
licensed agent and Searle Forestry the trading style, so s 121 needs both, on
every page of the set. Keep that line on any new page added here.
