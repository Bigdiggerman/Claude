# Daily Briefing — scheduled routine

The `daily-briefing` skill in this directory is run unattended each weekday morning by a
Claude Code Remote **Routine** (scheduled trigger).

## Schedule

| | |
|---|---|
| **Local time** | 07:00 NZT, Monday–Friday |
| **Cron (UTC)** | `0 19 * * 0-4` while NZ is on **NZST** (UTC+12) |
| | `0 18 * * 0-4` while NZ is on **NZDT** (UTC+13) |
| **Mode** | Fresh session per firing |
| **Connectors** | Microsoft 365 (Outlook calendar + mail) |
| **Notification** | Push to phone on completion |
| **Trigger ID** | `trig_01431fy95Fm1NumYcevtwSSj` |

Cron is evaluated in UTC, so 07:00 NZT falls on the **previous** UTC day — hence day-of-week
`0-4` (Sun–Thu) rather than `1-5`.

### Daylight saving

New Zealand switches at 02:00 on the last Sunday in September and the first Sunday in April.
The cron expression does **not** follow this automatically, so the routine's `cron_expression`
must be flipped between `0 19 * * 0-4` and `0 18 * * 0-4` at each transition, or the briefing
arrives an hour late (or early) for six months.

Upcoming transitions:

| Date | NZ goes to | Set cron to |
|---|---|---|
| 2026-09-27 | NZDT (UTC+13) | `0 18 * * 0-4` |
| 2027-04-04 | NZST (UTC+12) | `0 19 * * 0-4` |
| 2027-09-26 | NZDT (UTC+13) | `0 18 * * 0-4` |

Use `update_trigger` with the new `cron_expression` — do not delete and recreate the routine,
as that loses its run history.

A one-shot routine (`trig_01WD4KRGLGuuxoYX6G4C3Y6u`, fires 2026-09-25 21:00 UTC) performs the
2026-09-27 flip automatically and then disables itself. Later transitions are manual unless a
new one-shot is created each time.

## Outstanding: connectors are not attached

`create_trigger` returned:

> this trigger stores no MCP connectors, so the sessions it fires will run without connector
> (mcp__<server>__*) tools

Routines created through the meta-MCP tool can only pass through connector grants the calling
session itself holds, and this session had none to pass. **Until Microsoft 365 is attached to
the routine, sections 1 and 2 (calendar and email) will fail at every firing** — the fired
session will have no `outlook_calendar_search` or `outlook_email_search`. Sections 3–5 (log
prices, carbon price, news) run on `WebSearch` and are unaffected.

Fix: open the routine at claude.ai → Routines → "Daily Briefing — forestry, logs & carbon" and
add the **Microsoft 365** connector. The existing "Property Enquiry" routine was created
through that UI and carries its connectors correctly, which is why it works.

## Known environment constraint

`www.neon.markets` and `nz.pfolsen.com` are **blocked by the network egress proxy** in the
Default remote environment. `WebFetch` against them returns `EGRESS_BLOCKED` (HTTP 403 from
the policy proxy), which must not be retried or routed around.

`WebSearch` is unaffected and reaches these publishers' content, so the skill falls back to it
and footnotes the substitution. To restore the direct `neon.markets` read as the primary
carbon source, add the domain to the environment's network policy allowlist — see
https://code.claude.com/docs/en/claude-code-on-the-web

## Skill precedence

This copy lives in the repo as a **project skill**, so it only loads for sessions that have
this repository checked out on a branch where it exists. The account-level `daily-briefing`
skill synced from claude.ai is what unattended firings load by default. Keep the two in step:
paste this file's contents into the account skill at claude.ai → Settings → Capabilities →
Skills whenever it changes here.

As a backstop, the routine's own prompt restates the log-price and carbon-price requirements
inline, so the briefing is still correct if only the older account-level skill is loaded.
