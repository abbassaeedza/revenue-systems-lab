# Reply Classification Router

`workflow.json` is a **sanitized export of a real production workflow** (n8n). Credentials and the
alert email have been replaced with placeholders; the node graph, logic, and a real production
debugging note (kept in the JSON's own sticky-note/comments) are unchanged.

## What it does

A webhook receives every event from the outbound-sending platform for the whole account (not
per-campaign) — sends, opens, clicks, replies, bounces, unsubscribes, and lead-category changes.
Most event types are dropped on purpose; only `EMAIL_SENT`, `EMAIL_REPLIED`, `EMAIL_BOUNCED`, and
`LEAD_CATEGORY_UPDATED` get logged. The rest (opens, clicks, unsubscribes) are noise for this
particular log's purpose and would just inflate it without adding anything actionable.

## Hard part: the vendor's own docs were wrong

The event-parsing code was originally written against the sending platform's documented payload
shape. It shipped, then broke — the documented field paths didn't match what the platform actually
sent. The fix (same day) was to pull a **real webhook payload from a real event** and rewrite the
parser against the actual shape instead of the docs. This is a recurring theme across this pipeline
(the same lesson shows up in the `intent-based-outbound-pipeline` case study, from a different
vendor) — trust the payload you actually received over what a vendor's docs say you'll receive.

## Why it's built this way

- **Filter at the door, not downstream.** The `Should Log?` gate drops uninteresting events before
  they ever reach the log, keeping the append-only sheet meaningful instead of needing a second
  filtering pass every time someone reads it.
- **Account-wide, not per-campaign.** One webhook covers every campaign, which means adding a new
  campaign never requires touching this workflow.

## Production context

Feeds a reporting sheet with daily/monthly/category rollups, read by a human, not by another
automated stage — the log's job is to make outbound performance visible at a glance, not to drive
further automation.
