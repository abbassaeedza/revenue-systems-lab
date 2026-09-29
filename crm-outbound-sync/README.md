# CRM <-> Outbound Sync

Pattern: de-anonymized visitor event -> cheap disqualify -> dedup -> enrich -> score (rule-based, with an LLM fallback for ambiguous cases) -> segment-routed outbound send -> reply event -> CRM state update. Bidirectional, idempotent in both directions.

> Sanitized real workflows (three files: visitor-intent scoring/routing, CRM-to-outbound lead creation, outbound-reply-to-CRM update). Credentials, API keys, campaign IDs, and the ICP-classification prompt company name are placeholders.

Two invariants that mattered in production:

1. **CRM -> outbound must not double-send.** A visitor already seen (deduped on a stable identity key, checked before any paid enrichment call) is a no-op on the next pass, not a duplicate enrichment spend or a duplicate outbound add.
2. **Outbound -> CRM must not double-apply.** An already-applied reply/bounce event is a no-op, not a state flip-flop - this matters because a real event poll or webhook retry can redeliver the same event more than once.

## What it does

1. **Cheap disqualify before any paid call.** Filters out visitors on career/job pages (job seekers) or whose company/industry text matches a competitor-category denylist - all on free, already-available signals, so the expensive enrichment step never wastes a lookup on structurally-never-going-to-convert traffic.
2. **Dedup on identity, not session.** A repeat visitor just gets a last-seen timestamp bump and skips the entire scoring/enrichment path - no re-spend on someone already processed.
3. **Enrich, then score.** A contact-enrichment API resolves firmographic + person data; a rule-based score combines URL-path intent (a pricing/contact page scores near-max, a blog/about page scores low) with a rule-based fit score (title seniority, company size, revenue, tag boosts). Only genuinely ambiguous cases (root-domain visit, or no industry data at all) fall through to an LLM classification call - the model is a fallback for real uncertainty, not the primary classifier.
4. **Segment-routed send.** Qualified visitors route into one of several outbound campaigns by segment, not one generic sequence.
5. **Reply-triggered CRM update.** An inbound reply gets classified (interested / not interested / out of office) and written back onto the CRM contact, advancing or completing its sequence status - closing the loop without a human having to notice and act on the reply manually.

Files: steps 1-3 are the scoring/routing workflow; step 4's CRM-triggered half (a deal reaching a qualifying stage) is the CRM-to-outbound-lead workflow; step 5 is the outbound-reply-to-CRM workflow.

## Why it's built this way

- **Rule-based scoring first, LLM only for ambiguous cases.** Most visitor events have enough signal (a specific page path, a filled-in industry field) to score deterministically and cheaply. Reserving the LLM call for the genuinely unclear minority keeps the common path fast and free of model-call latency/cost, while still handling the edge cases that a fixed rule set can't.
- **Two independent scores (intent, fit), not one blended number.** Keeping them separate makes the routing decision auditable - a high-fit-low-intent visitor and a low-fit-high-intent visitor reach a threshold differently and can be routed differently, which a single combined score would hide.
- **Never silently drop a qualified lead.** A visitor with no resolvable email doesn't get discarded - it's logged as a LinkedIn-only outreach candidate on a separate channel instead of disappearing.

## Reliability

- Every stage writes to a durable store before the next stage reads it - any stage can be re-run independently without reprocessing the whole flow.
- The disqualify stage is deliberately conservative (biased toward letting a few noisy visitors through rather than risking a false-positive drop) - a real lead silently killed by an over-aggressive filter is a much harder failure mode to catch than one that costs a bit more enrichment budget.

## Tech stack

n8n (orchestration) · a visitor de-anonymization webhook source · a contact-enrichment API · an LLM for ambiguous-case classification · a CRM/outbound sending platform
