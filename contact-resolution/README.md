# Contact Resolution

`workflow.json` is a **sanitized export of a real production workflow** (n8n) — the largest one in
this repo (34 nodes). Credentials, the database hostname, and the alert email have been replaced
with placeholders; the node graph, logic, and API call shapes are real.

## What it does

Takes companies that already cleared the hiring-signal score gate (see `lead-scoring`) and resolves
an actual decision-maker's contact info for each one, batched via `splitInBatches` so one bad
company can't take the whole run down with it. For each company:

1. **Apollo first** — search for a matching person, then reveal their contact record.
2. **If Apollo has no email**, two parallel LeadMagic fallback paths run depending on what Apollo
   *did* return: path A re-tries email-finding directly from the Apollo person match; path B starts
   from a role-finder call (using a list of target role titles) when Apollo didn't return a usable
   person match at all, then chains into a second email-finder call.
3. Whichever path succeeds first builds a contact payload and inserts it; if nothing resolves, the
   iteration ends without a contact rather than blocking the batch.

## Why it's built this way

- **Two-tier waterfall, not three flat providers.** Apollo is checked first because it returns
  richer person data in one call; LeadMagic is the fallback specifically for cases where Apollo has
  the company/person but not a verified email — going straight to a flat "try every provider"
  design would burn LeadMagic credits on companies Apollo could already answer for cheaper.
- **Per-company batching isolates failures.** A single company with malformed data (see the
  `intent-based-outbound-pipeline` case study in `systems-case-studies` for a real example of this
  exact failure mode elsewhere in the pipeline) can't abort the other 49 in the batch.
- **Resolution only runs on score-gated companies** — this is the expensive step (per-lookup paid
  APIs), so nothing reaches it without already proving it's worth the cost. Same design principle
  as `hiring-signal-pipeline`'s "score before resolve" rule, here in its real implementation.

## Production context

Feeds the same shared contact database `lead-scoring` and `staleness-recheck` operate on.
