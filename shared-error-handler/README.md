# Shared Error Handler

Pattern: error trigger → structured payload → alert dispatch. Mirrors a real production
3-node shape (error trigger → build payload → send alert) confirmed in an active pipeline
handling 18 scheduled workflows sharing one alert path instead of each workflow rolling
its own error handling.

The point isn't the code (it's deliberately small) — it's the shape: every workflow in a
pipeline routes failures through the same handler, so there's one place that defines what
"failed" looks like and one place that decides where the alert goes, instead of N slightly
different try/except blocks drifting apart over time.

## Real production reference

`workflow.json` is a **sanitized export of the actual 3-node handler** this pattern is based on —
not a reconstruction, the real thing with the alert email replaced by a placeholder. Every
scheduled workflow in the pipeline points its "Error Workflow" setting at this one, so a failure
anywhere routes through the same three nodes: catch → build a structured message (workflow name,
failed node, error text, timestamp) → email it.
