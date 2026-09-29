# RB2B ICP Router

A de-anonymized-visitor scoring and routing system: RB2B identifies an anonymous website visitor, this workflow decides in real time whether they're worth a sales touch, scores and resolves them, and routes qualified visitors into an outbound campaign - everyone else gets logged (not dropped) to a tracking sheet with the reason.

> Sanitized real workflow. Credentials, API keys, spreadsheet IDs, and the ICP-classification system prompt's company name are replaced with placeholders in `workflow.json`. Disqualification rules, the scoring formula, and segment definitions are unchanged from production.

## What it does

1. **Cheap disqualify before any paid call.** Visitors on career/job pages (job seekers) or whose company/industry text matches a competitor-category denylist are filtered out on free signals alone - the expensive enrichment step never wastes a lookup on structurally-never-going-to-convert traffic.
2. **Dedup on identity, not session.** A repeat visitor just gets a last-seen timestamp bump in the tracking sheet and skips the entire scoring/enrichment path.
3. **Enrich via a contact-enrichment API** (firmographic + person data) once a visitor clears the disqualify filter.
4. **Score: rule-based first, LLM only for genuinely ambiguous cases.** Most visitor events have enough signal (a specific page path, a filled-in industry field) to score deterministically. Root-domain visits or blank-industry cases fall through to an LLM classification call that returns a structured verdict (qualified, ICP sub-segment, intent score, reason) - the model is a fallback for real uncertainty, not the primary classifier.
5. **Route qualified visitors to an outbound campaign**, segmented by the ICP sub-segment the scoring step assigned. Everyone else is logged to a "not ICP" tracking sheet with the disqualification/score reason attached, not silently dropped.

## Why it's built this way

- **Two independent scores (intent from URL path, fit from firmographic/title data), not one blended number.** Keeping them separate makes the routing decision auditable - a high-fit-low-intent visitor and a low-fit-high-intent visitor reach a threshold differently and can be routed differently, which one combined score would hide.
- **The LLM is a narrow fallback, not the primary classifier.** Rule-based scoring handles the common, high-signal cases directly (cheap, deterministic, no model-call latency); the LLM only sees the minority of events where the rules genuinely don't have enough to go on.
- **Never silently drop a visitor.** Disqualified and below-threshold visitors are both logged with their reason, not just discarded - the tracking sheet is the record of what the router decided and why.

## Reliability

- Every stage writes to a durable store (tracking sheet) before the next stage reads it - the dedup lookup itself depends on this.
- Disqualification is deliberately conservative - biased toward letting a few noisy visitors through rather than risking a false-positive drop, since a real lead silently killed by an over-aggressive filter is a much harder failure mode to catch than one that costs a bit more enrichment budget.

## Tech stack

n8n (orchestration) · a visitor de-anonymization webhook source (RB2B) · a contact-enrichment API · an LLM for ambiguous-case classification · Google Sheets (tracking/audit log) · an outbound sending platform

## What this proves

A real-time visitor-scoring decision built as a small set of composable, auditable stages (disqualify -> dedup -> enrich -> score -> route) instead of one opaque scoring blob, with a bias toward "never silently drop a qualified lead" as a default engineering posture.
