# Commission rules — Forestry Sales Limited (Searle Forestry / Searle Agribusiness)

Everything below was read from the office's own agency agreements in OneDrive
(`Properties/<Name>/Agency/Agency Agreement*.pdf|docx`, Oct 2023 and Aug 2026 editions).
Re-read the actual agreement for the property before relying on any number here.

## Where the numbers live in an agency agreement

| What | Where in the agreement |
|---|---|
| Property name, address, sale method, listing price / internet search range | Executive Summary (page 2) |
| Commission rates | Clause **5.3 "The Agent's commission is calculated as follows"** |
| Appraised value | Same clause: "We have appraised your property … in the range $X to $Y" |
| Agreement's own estimate | Same clause: "A sale price of $Y would mean an estimated commission of $Z plus GST" (always at the **top** of the range) |
| Minimum fee | Same clause, in brackets: "(Minimum fee of $10,000.00 plus GST)" |
| Marketing budget | Clause 5.4 / "APPROVED MARKETING BUDGET $… (plus GST)" — not commission, ignore for the pipeline |
| Salespersons acting | Parties, item 3 — tells you who may be owed a split |
| Co-agency / conjunctional | Look for another agency named in the Executive Summary, clause 3.2, or the proposal; Searle share < 100% |

## Standard structure (seen on Jelldale, LM Farms/Dargaville Dairy, Menin Reiki, Hagan, Awaroa, Takapu …)

- **4% on the first $500,000** of total consideration
- **2.5% on the balance**
- **Minimum fee $10,000 + GST**
- "Consideration" = everything passing from purchaser to client (money, stock, plant, equipment, other compensation).

Gross (excl. GST) = `min(price, 500000) × 4% + max(price − 500000, 0) × 2.5%`, floored at the minimum fee,
× Searle's share.

Variants that exist on the current pipeline — always take the agreement's wording over the default:

| Property | Structure | Pipeline encoding (rate_first / rate_balance / share) |
|---|---|---|
| Waingaro | 1.99% flat | 0.0199 / 0.0199 / 1 |
| Woodlands | 2.5% flat | 0.025 / 0.025 / 1 |
| Nirvana Farm | 1.5% success fee | 0.015 / 0.015 / 1 |
| Hinerua & Pineview | 2% assumed (1.5–2.5%) — yellow | 0.02 / 0.02 / 1 |
| Puhoi (Nicklin Farms) | 50/50 co-agency with Colliers Tauranga | 0.04 / 0.025 / 0.5 |

A flat rate is encoded by putting the same rate in both rate columns. A share below 1 is Searle's slice of
the gross after the co-agent takes theirs.

## Which price to use

1. **Under contract** (a signed Sale & Purchase Agreement, accepted Tender, or signed Acceptance of Tender in
   `Properties/<Name>/Legal/` or `Tenders Received/`): use the **purchase price** in that contract, excluding GST
   (if the contract says "inclusive of GST (if any)" and the vendor is GST-registered, divide by 1.15 and say so
   in Notes). Section = *Under contract*. Price cell is black-on-white (a fact), not yellow.
2. **Listed but no contract**: use the **midpoint of the appraisal range** in clause 5.3 of the agency agreement.
   Section = *Possibles*. Mark the price cell yellow (`--assume price`) and put the full range and the
   agreement's own top-of-range estimate in Notes, e.g.
   `Appraised $4.8m–$5.3m (agreement est. $140,000 at $5.3m); midpoint used.`
   If the agreement gives a single appraised figure, use it. If the Executive Summary carries a listing price
   or an asking price instead, prefer the appraisal for the pipeline and mention the asking price in Notes.
3. **Nothing to go on** (no agreement found, or the agreement has the range blank): leave the price empty,
   add the row with Notes `No price guide - enter expected price.`, and list it under *Needs your input* in
   the summary email. Never invent a figure.

## Splits

Per the pipeline's own Notes block (keep it authoritative; re-read it each run):

- **James**: 15% of gross on every *Possibles* row and on Waingaro / Wakamarina. Default `--james 0.15` for new rows.
- **George**: 0% on new rows (paid on Woodlands only after his 19 Oct 2026 termination). Default `--george 0`.
- Net to Searle = gross − George − James.

If the agreement's "Salesperson(s) Acting" names someone other than Warwick / George / James, do not invent a
column — note it in the email under *Needs your input*.

## Worked examples

| Price | Structure | Gross excl. GST |
|---|---|---|
| $5,300,000 | 4% / 2.5% | 20,000 + 120,000 = **$140,000** (matches the LM Farms agreement) |
| $4,587,232 | 4% / 2.5% | 20,000 + 102,180.80 = **$122,180.80** (matches the Jelldale agreement) |
| $3,630,000 | 1.99% flat | **$72,237** |
| $5,000,000 | 4% / 2.5%, share 50% | (20,000 + 112,500) × 0.5 = **$66,250** |
| $200,000 | 4% / 2.5% | 8,000 → floored to **$10,000** minimum fee |

Check any figure with:

```bash
python3 scripts/pipeline.py commission --price 5300000 --rate-first 0.04 --rate-balance 0.025 --share 1
```

GST: the pipeline is **excl. GST** throughout. Quote incl. GST only when asked (× 1.15).
