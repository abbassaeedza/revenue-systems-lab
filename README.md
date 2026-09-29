# Revenue Systems Lab

Reusable revenue-ops / GTM engineering patterns. Most modules here are sanitized exports of real production n8n workflows - actual node graphs and business logic, with credentials, database hostnames, internal emails, and workflow/campaign IDs replaced by placeholders. One module (`enrichment-waterfall`) is a clean-room demo instead, because that specific pattern was independently built twice in two different stacks (a low-code orchestrator + Postgres, and a from-scratch Python service) and converged on the same shape - a decent signal it's a real pattern worth demonstrating generically, rather than tied to either single real export.

Each module's README says which kind it is and what's been replaced.

## Modules

| Module | Pattern | Kind |
|---|---|---|
| [`hiring-signal-pipeline/`](hiring-signal-pipeline/) | 5-workflow real chain: discovery → daily ATS poll → staleness recheck → DB-side scoring → two-tier contact resolution | Real (sanitized), 5 workflows |
| [`crm-outbound-sync/`](crm-outbound-sync/) | Visitor-intent webhook → cheap disqualify → dedup → enrich → LLM-assisted scoring → segment-routed outbound | Real (sanitized) |
| [`shared-error-handler/`](shared-error-handler/) | Standardized error capture → structured payload → alert dispatch, shared across every workflow in the pipeline | Real (sanitized) |
| [`reply-classification-router/`](reply-classification-router/) | Account-wide webhook event filter + structured activity log | Real (sanitized) |
| [`guest-post-prospecting-pipeline/`](guest-post-prospecting-pipeline/) | Search-discovery fan-out → two-tier email resolution → verify-then-send with dual-mailbox rotation | Real (sanitized) |
| [`white-label-outreach-orchestration/`](white-label-outreach-orchestration/) | Scraper ingest → nightly enrichment → gated compliant send → event tracking | Real (sanitized) |
| [`enrichment-waterfall/`](enrichment-waterfall/) | Ordered multi-provider enrichment chain, non-destructive writes, rate-limit fallback | Demo (pattern proven twice in production, shown clean-room) |

Every module is self-contained and has its own README. The one demo module is runnable (`python3 waterfall.py`, stdlib-only, no install step) with a self-check proving the core invariant it exists to protect. The real-workflow modules are n8n exports meant to be read, not run standalone - import into a local n8n instance if you want to inspect a graph visually.

## Why these seven

Production automation systems that ingest external signals and turn them into qualified outbound contact tend to hit the same handful of problems regardless of stack: a multi-stage chain needs its expensive step structurally gated behind a cheap qualifying one (`hiring-signal-pipeline`), CRM and outbound-platform state drifts apart without an explicit sync contract (`crm-outbound-sync`), silent failures in a scheduled pipeline are worse than loud ones (`shared-error-handler`), noisy reply/event streams need filtering before they're useful (`reply-classification-router`), a multi-stage outreach system needs each stage's distinct failure mode handled on its own terms (`guest-post-prospecting-pipeline`), compliance has to be structural not incidental (`white-label-outreach-orchestration`), and enrichment/resolution providers are unreliable and shouldn't clobber good data with bad (`enrichment-waterfall`). Seven modules, one answer each.

## Scale note

`hiring-signal-pipeline` documents one real source in full (5 chained workflows, start to finish). It's one of roughly 10 independent discovery sources feeding the same overall production system, plus several dedicated resolution sweeps and one shared error handler - around 18 real workflows total in that system alone. The other sources follow the same discovery shape with a different search API at the front each time; `hiring-signal-pipeline`'s README documents the one with a complete working path all the way to a resolved contact, rather than duplicating nine more folders that mostly repeat the same pattern.
