# Hazard Notice — Searle Forestry

The Searle Forestry visitor Hazard Notice and Inspection Acknowledgement /
Visitor Register. Four A4 portrait pages: the hazard notice and conditions of
entry (pages 1–2), and the register the visitor and salesperson complete
together before entry (pages 3–4).

| File | |
|---|---|
| `Hazard Notice and Visitor Register - Searle Forestry.pdf` | the document to print or email |
| `content.py` | all wording — edit here |
| `build.py` | layout; regenerates the HTML and PDF |
| `hazard_notice.html` | generated, self-contained (fonts and logo inlined) |
| `assets/` | Searle Forestry logo, Cormorant Garamond + Inter web fonts |

## Rebuilding

```
python3 build.py              # HTML + PDF
python3 build.py --html-only  # HTML only
```

Rendering the PDF needs Chrome, Chromium or Edge; `build.py` looks in the
usual install locations.

Pages are fixed A4 boxes, not reflowing text, so content does **not** move
between them on its own. After editing `content.py`, rebuild and look at every
page. If a page overruns, move the split with `PAGE_1_CONDITIONS` in
`build.py`, shift a section to the next page, or trim the spacing. Rendering
each page to PNG is the quickest check:

```
python3 -c "import pypdfium2 as p; d=p.PdfDocument('Hazard Notice and Visitor Register - Searle Forestry.pdf'); [d[i].render(scale=1.5).to_pil().save(f'page{i+1}.png') for i in range(len(d))]"
```

## Brand and compliance

Olive `#1D2308` on cream `#FBFAF8`, Cormorant Garamond headings, Inter body —
the same system as the marketing report and tender report templates.

The footer of every page carries **Forestry Sales Limited trading as Searle
Forestry · Licensed Agent REA Act 2008 · searleforestry.co.nz**. Forestry Sales
Limited is the licensed agent and Searle Forestry the trading style, so s 121
needs both, on every page of the set. Keep that line on any page added here.
