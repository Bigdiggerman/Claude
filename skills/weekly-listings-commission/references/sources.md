# Where new listings and contracts show up

Checked on 8 Oct 2026 from the Claude cloud environment. Re-verify a source the first time a run reports it empty.

## 1. Searle Agribusiness website — primary, machine-readable

WordPress site with a public REST feed for the `property` post type (Easy Property Listings plugin).

```
GET https://www.searleagri.co.nz/wp-json/wp/v2/property?per_page=50&status=publish&_fields=id,slug,title,date,modified,link,status,class_list,meta
```

- One object per listing. `title.rendered` = property name (HTML entities possible: `&#038;` → `&`).
- `date` = first published (NZ local), `modified` = last edit, `link` = public page.
- `class_list` contains `epl-status-current` while the listing is live, `location-<region>`.
- `meta.property_status` (`current` / `sold` / `withdrawn`), `meta.property_agent`, `meta.property_second_agent`,
  `meta.property_land_area` + `meta.property_land_area_unit`, `meta.property_category`, `meta.property_heading`.
- Treat `status == "publish"` **and** `epl-status-current` in `class_list` as *active*.
- Listing id for the Seen register: `searleagri:<slug>`.
- Forestry listings also appear here (Jelldale, Tokomaru) — the Agribusiness site is now the shared shopfront.
- Fetch with `curl -sS` (works through the environment proxy) or `WebFetch`. If the REST feed ever 404s, fall back
  to `WebFetch https://www.searleagri.co.nz/property/` and read the cards (title, hectares, "View Details" link).
- Public page per listing gives: address, region, sale method and close date ("Tender closes Wednesday, 4 November 2026"),
  agents. Use it to fill Status.

## 2. OneDrive `Properties/` folders — the office's own record (works even before launch)

Drive: Warwick's OneDrive (`warwick@forestrysales.co.nz`), driveId `b!ZUP3CS6LvkqSE85fs7eMXrUW9GsayUZLshhWRv3ArfDBvKOSh7dKTq5QfuTdETKs`,
root folder `Properties` (itemId `01QRNQVLA27GKTETGJM5AIC5EGDCV776VD`). One sub-folder per property.
`Properties/AA Sold or Withdrawn Listings/` holds the dead ones — never list from there.

Signals, found with `sharepoint_search`:

| Signal | Search | Means |
|---|---|---|
| New agency agreement | `query: "agency agreement"`, `afterDateTime: <8 weeks ago>` | a new listing (or re-listing); folder name = property |
| Signed contract | `query: "sale and purchase agreement"` / `"tender agreement"` / `"acceptance of tender"`, `afterDateTime` | the property is under contract; purchase price inside |
| Tender report / offers summary | `query: "tender report"` / `"offers summary"` | EOI/tender stage — status text, no price change |
| Enquiry sheet | `ENQUIRY SHEET - <Name>.xlsx` | listing is live and being marketed |

Read any hit with `read_resource` on its `file:///{driveId}/{itemId}` URI (PDF and DOCX come back as text; use
`startPage`/`endPage` for long PDFs — clause 5.3 is usually on page 5 or 6).

Listing id for the Seen register: `onedrive:<itemId of the agency agreement>`.

## 3. Searle Forestry website — currently unreachable from the cloud

`www.searleforestry.co.nz` resets the connection from the Claude environment and from external fetchers
(checked 8 Oct 2026). Do **not** retry it in a loop or route around the proxy. Forestry listings are covered by
sources 1, 2 and 4.

## 4. Portals — fallback only

- Trade Me: `WebSearch` for `"Searle Forestry" OR "Searle Agribusiness" tender site:trademe.co.nz` and read the
  listing pages the search returns (`/a/property/rural/.../listing/<id>`). Listing id: `trademe:<id>`.
- realestate.co.nz: rarely indexed; try `site:realestate.co.nz "Forestry Sales Limited"` only if the others are empty.
- Trade Me listings by **NZ Forest Sales / George Searle** are a different company — ignore them.

## 5. Dropbox (Searle Agribusiness shared folders)

Some agribusiness vendor files live in Dropbox under `/<Address> (<Vendor>)/2. Listing agreements, AML/`.
`Dropbox search "Agency Agreement"` → `Dropbox fetch` on the id. Only consult if OneDrive has no agreement for
an Agribusiness listing.

## Matching a listing to a pipeline row / folder

Normalise names before comparing: lower-case, drop anything in brackets, drop the words
forest(s)/farm(s)/limited/ltd/station/block/road/rd. `pipeline.py` does this in `find_row`. Known aliases:

| Website / folder | Pipeline row |
|---|---|
| Nicklin Farms (site), Puhoi (folder) | Puhoi (Nicklin Farms) |
| LM Farms (site), Dargaville Dairy (folder), 455 West Coast Road | — not yet on the pipeline |
| Jelldale Forest (site), Jelldale (folder) | Jelldale |
| Tokomaru Forests (site), Tokomarua East & West (folder) | — not yet on the pipeline |
| Nirvana (folder), Nirvana Farm Limited (In Receivership) | Nirvana Farm (receivership) |
| Hinerua / Pineview Forest (folders) | Hinerua & Pineview |

When a name could match two rows or two folders, HOLD it (summary email, *Needs your input*) rather than guess.
