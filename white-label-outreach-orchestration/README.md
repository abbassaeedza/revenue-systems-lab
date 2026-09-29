# White-Label Outreach Orchestration

The n8n orchestration layer tying together the scraper, enrichment, send, and event-tracking stages of the White-Label Outreach Pipeline (full write-up: [`systems-case-studies/white-label-outreach-pipeline`](https://github.com/abbassaeedza/systems-case-studies/tree/main/white-label-outreach-pipeline)). The scraper itself and the unsubscribe/reply edge worker are separate Node.js/Cloudflare Workers components documented in that case study; this module is the n8n side - ingest, nightly enrichment, gated daily send, and event tracking.

> Sanitized real workflow. Company name, address, sender identity, infrastructure URLs, and third-party names used as social proof in the outreach copy are all replaced with placeholders. See `_note` and `sanitization_notes` in the JSON for exactly what was changed and why.

## What it does

1. **Ingest** - receives a batch of scraped company records from the external scraper, explodes it, upserts into a tracking sheet keyed by domain.
2. **Enrichment (nightly, capped batch)** - resolves each un-enriched company to a decision-maker via a contact-enrichment API search-then-reveal pattern, restricted to relevant seniority titles. A company with no findable decision-maker is marked terminal, not retried forever - some companies genuinely don't have one reachable through this method, and treating that as a fact rather than a bug avoids an infinite retry loop.
3. **Send (working-hours-gated, small daily cap)** - builds a personalized pitch, generates an HMAC-signed one-click unsubscribe link using the same signing scheme as the edge worker, sends via a transactional email API with a proper `List-Unsubscribe` header (not just a footer link), logs the full send for audit.
4. **Event tracking** - receives forwarded reply/unsubscribe events from the edge worker and updates the tracking sheet so the send stage's own filter excludes anyone who's replied or opted out on every subsequent run.

## Why this design

- **Enrichment and sending are separate scheduled stages, not one long pipeline.** A company can sit "enriched, not yet sent" for a while - decoupling the two means a slow enrichment day never delays sends to companies already resolved, and a paused send schedule never blocks enrichment from keeping the backlog warm.
- **Terminal failure states are explicit.** "No decision-maker found" and "no valid email revealed" both mark a company `enriched: none` rather than leaving it in limbo to be retried indefinitely - an honest dead-end is more useful than a silent infinite retry.
- **Compliance is structural, not a checklist item.** The unsubscribe link and the `List-Unsubscribe` header are generated as part of every send, not bolted on after - the same HMAC scheme documented in the case study is reused here rather than inventing a second one.

## What this proves

The n8n half of a system whose other half (scraper + edge worker) is Node.js/Cloudflare Workers - same "assume failure is normal, make terminal states explicit, keep compliance structural not incidental" engineering posture, expressed in the orchestration layer rather than the edge service.
