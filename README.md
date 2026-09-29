# Revenue Systems Lab

Reusable revenue-ops / GTM engineering patterns, in two forms:

- **Clean-room demos** (`enrichment-waterfall`, `crm-outbound-sync`) — reimplemented from scratch
  against synthetic data. No real API keys, client data, company names, or production logic.
  Production-specific tuning (credit budgets, real provider list, real scoring weights) is
  intentionally omitted.
- **Sanitized real workflows** (`lead-scoring`, `contact-resolution`, `hiring-signal-pipeline`,
  `staleness-recheck`, `shared-error-handler`, `reply-classification-router`) — actual production
  n8n workflow exports, with credentials, database hostnames, internal emails, and workflow IDs
  replaced by placeholders. The node graph and business logic are unmodified.

Each module's README says which kind it is. The enrichment-waterfall pattern specifically was
built twice from scratch in two different stacks (a low-code orchestrator + Postgres, and a
from-scratch Python service) and converged on the same shape — a decent signal it's a real pattern
and not a one-off, which is why that one stayed a demo rather than a single sanitized export.

## Modules

| Module | Pattern | Kind |
|---|---|---|
| [`hiring-signal-pipeline/`](hiring-signal-pipeline/) | Multi-source signal ingestion → normalize → dedup → score → resolve → outbound-eligibility gate | Demo + real reference |
| [`enrichment-waterfall/`](enrichment-waterfall/) | Ordered multi-provider enrichment chain, non-destructive writes, rate-limit fallback | Demo |
| [`crm-outbound-sync/`](crm-outbound-sync/) | Bidirectional, idempotent CRM ↔ outbound-platform state sync | Demo |
| [`shared-error-handler/`](shared-error-handler/) | Standardized error capture → structured payload → alert dispatch | Demo + real reference |
| [`lead-scoring/`](lead-scoring/) | DB-side signal computation + tiered contact scoring | Real (sanitized) |
| [`contact-resolution/`](contact-resolution/) | Two-tier paid-lookup waterfall gated behind a score threshold | Real (sanitized) |
| [`staleness-recheck/`](staleness-recheck/) | Time-boxed signal decay — rechecks aging records instead of trusting them forever | Real (sanitized) |
| [`reply-classification-router/`](reply-classification-router/) | Account-wide webhook event filter + structured activity log | Real (sanitized) |

Every module is self-contained and has its own README. The demo modules are runnable
(`python3 <module>.py`, stdlib-only, no install step) with a self-check proving the core invariant
they exist to protect. The real-workflow modules are n8n exports meant to be read, not run
standalone — import into a local n8n instance if you want to inspect the graph visually.

## Why these eight

Production automation systems that ingest external signals and turn them into qualified outbound
contact tend to hit the same handful of problems regardless of stack: signals arrive from sources
that disagree with each other, enrichment/resolution providers are unreliable and shouldn't clobber
good data with bad (or get called before a signal's proven worth the cost), CRM and
outbound-platform state drifts apart without an explicit sync contract, stale signals rot silently
without an active recheck, noisy event streams need filtering before they're useful, and silent
failures in a scheduled pipeline are worse than loud ones. These eight modules are the reusable
answer to each — four demonstrated clean-room, four shown as the real, sanitized thing.
