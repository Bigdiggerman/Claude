# Working context for Warwick — Searle Forestry

This file is shared context for Claude. It lives in git so every machine
(work computer, laptop, web sessions) reads the same instructions.

## Who / what

- Warwick, Searle Forestry — NZ forestry and rural property sales.
- Work covers listings, vendor reporting, tenders/EOIs, buyer enquiries,
  ETS/carbon, and the usual forestry market context (log prices, NZU, NES-CF).

## Where things live

Keep working files in cloud storage, not on a local drive — anything on a
single machine's disk is invisible to the other machine and to Claude.

- **SharePoint / OneDrive** (Microsoft 365 connector) — enquiry sheets,
  listing folders, vendor correspondence.
- **Dropbox** (Dropbox connector) — <fill in what you keep here>
- **Xero** (Xero connector) — invoices, bills, financial reporting.
- **GitHub** (`Bigdiggerman/Claude`) — this repo: shared Claude config,
  and the published pages under `docs/`.

## Conventions

- NZ English and NZ date format (e.g. 18/09/2026).
- NZ$ for all figures unless stated otherwise.
- Areas in hectares; log prices per tonne; carbon in NZU.
- Vendor-facing writing is plain and factual — no filler, no hype.

## Skills

These are account-level skills, so they work on any machine once signed in:

| Skill | Use |
| --- | --- |
| `daily-briefing` / `morning-briefing` | Calendar, emails needing a reply, forestry/log/carbon news |
| `property-enquiry-logger` | Sweep Outlook for Trade Me / realestate.co.nz enquiries, log to the property's enquiry sheet |
| `tender-report` | Branded tender / EOI report to the vendor when bids close |
| `property-map` | Interactive listing map — LINZ boundary, carbon areas, ESC, LUC, data room |

## Notes for Claude

- Prefer the connectors over asking Warwick to upload a file — the file is
  usually already in SharePoint, OneDrive or Dropbox.
- Don't assume a file path exists on this machine; check first.
- Recurring work should be a cloud Routine, not a task tied to one computer,
  so it runs whether or not that machine is on.
