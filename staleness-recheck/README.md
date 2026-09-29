# Staleness Recheck

`workflow.json` is a **sanitized export of a real production workflow** (n8n). Credentials, the
database hostname, and the alert email have been replaced with placeholders; the node graph and
logic are real.

## What it does

Runs daily. Computes a 45-day cutoff, then finds every job posting that's crossed it — postings old
enough that they might have quietly closed without the pipeline noticing. Rechecks each one
against the original source API (batched, one at a time), and updates the posting's status based
on what comes back.

## Why it exists

A hiring signal (an open job posting) has a shelf life. Without this workflow, a posting that
closed the day after it was first discovered would sit in the database looking like an active
signal indefinitely — every downstream stage (scoring, contact resolution) would keep treating a
filled role as an open one. The 45-day cutoff isn't "recheck everything constantly" (wasteful, most
postings that are still open at day 10 are still open at day 20) or "never recheck" (signals rot
silently) — it's a middle point picked to catch staleness before it meaningfully skews scoring,
without re-querying every posting on every run.

## Production context

Keeps the same `job_postings` table that `hiring-signal-pipeline` populates and `lead-scoring`
reads from honest over time — a decay mechanism for the whole pipeline, not just this workflow.
