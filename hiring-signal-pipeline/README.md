# Hiring Signal Pipeline

Pattern: multi-source signal ingestion → normalize/dedup → score by freshness+relevance →
contact-resolution gate → outbound-eligibility decision.

In production this pattern ran across 11 independent signal sources (job boards, funding
filings, hiring-intent APIs, community engagement) feeding a shared company/contact store,
with contact resolution behind a paid-lookup waterfall that's only called for companies that
already cleared the score gate — resolution is the expensive step, so nothing reaches it
without first proving it's worth the cost.

This demo collapses that to two synthetic sources and one scoring function, but keeps the two
decisions that mattered in production:

1. **Dedup by normalized domain, not raw company name** — `www.acmerobotics.io` and
   `acmerobotics.io` from two different sources must merge into one company record, or the
   pipeline double-counts and double-contacts.
2. **Score before resolve** — contact resolution costs money per lookup; only score-eligible
   companies get resolved.

Run: `python3 pipeline.py`

## Real production reference

`workflow.json` is a **sanitized export of one of the 11 real signal sources** (n8n) — job-board
discovery via a hiring-intent API, representative of the shape all 11 sources share: search →
flatten paginated results → normalize → extract which applicant-tracking-system a posting uses
(recognizing known board URL patterns) → upsert company/posting records → track discovery stats.
The other 10 sources (funding filings, community engagement, accelerator/directory listings, etc.)
follow the same shape with a different search step at the front — this one file stands in for the
pattern repeated across all of them, not just for itself.

Credentials and the database hostname have been replaced with placeholders; the node graph and
logic are real.
