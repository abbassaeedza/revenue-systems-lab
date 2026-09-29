# Lead Scoring

`workflow.json` is a **sanitized export of a real production workflow** (n8n), not a clean-room
reimplementation like the other modules in this repo — see the top-level README for the
distinction. Credentials, the database hostname, and the alert email have been replaced with
placeholders; the node graph, logic, and API shapes are real.

## What it does

Runs daily. Computes hiring-intent signals directly in the database (stale job postings, multiple
open roles at once, a lone-engineer signal, contract-language detection in postings) via a single
RPC call, then scores every contact tied to those signals into a tier, via a second RPC call. Logs
tier counts and per-source stats to a tracking sheet for a human to glance at without opening the
database.

## Why it's built this way

- **Scoring lives in the database, not in workflow code.** The two `httpRequest` nodes calling
  `rpc/compute_hiring_signals` and `rpc/score_hiring_contacts` are thin triggers — the actual
  signal/scoring logic is a stored procedure. That's a deliberate choice: scoring rules change
  often as targeting sharpens (see the `hiring-signal-pipeline` module's README for the same point),
  and a DB function is one place to change instead of hunting through workflow nodes.
- **No external API calls at all.** Everything needed to score a contact was already ingested by
  earlier pipeline stages — this workflow is pure computation over data that already exists,
  which makes it cheap to re-run and safe to run daily without rate-limit concerns.
- **Stats logged even when nothing changed** (`Get Updated Source Stats` → sheet row), so a human
  reviewing the tracking sheet can tell "ran and found nothing new" apart from "didn't run."

## Production context

One of several daily/weekly scheduled workflows feeding a shared contact database — see
`hiring-signal-pipeline` (discovery), `contact-resolution` (resolves contact info once a company
scores high enough), and `staleness-recheck` (decays stale signals) for the surrounding pipeline.
