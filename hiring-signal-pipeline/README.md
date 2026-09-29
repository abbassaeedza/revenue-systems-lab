# Hiring Signal Pipeline

The real production hiring-source chain: five separately-deployed n8n workflows, chained through shared database state (not direct workflow-to-workflow calls), that turn a raw job posting into a real decision-maker's contact info. This is one source out of ~10 independent discovery sources feeding the same overall system (see "Where this fits" below) - but it's the one with a complete, working path all the way to a resolved contact, so it's documented here in full.

> Sanitized real workflows, not a clean-room demo. Credentials, the database hostname, and internal alert addresses are replaced with placeholders in all five files; the node graphs, logic, and API call shapes are real.

## Pipeline order (and the bug this ordering fixed)

```
1-theirstack-discovery  (weekly, Mon 6am)  -> seeds companies + job_postings + which ATS boards to poll
2-ats-poller            (daily, 5am)       -> keeps job_postings fresh daily (new/still-open/closed) instead of waiting a week
3-staleness-recheck     (daily, 4am)       -> confirms closed_at on postings the ATS poller doesn't cover directly
4-scoring               (daily, 7am)       -> computes signals + scores companies, DB-side
5-find-hiring-contacts  (daily, 8am, cap 200/run) -> resolves a real contact for score-gated companies only
```

**Scoring runs at 7am, contact resolution at 8am - this exact ordering was a real production bug fix.** It used to be the other way round: contact resolution ran before scoring had computed that day's signals, so a company discovered same-morning had zero signals yet and silently failed the score gate for a full day. Root-caused by cross-referencing execution history against real backlog counts (the default query view was quietly capping results and hiding the true backlog size), not by watching the pipeline run. Fixed by swapping the two schedules. The lesson generalizes: the *expensive* stage (contact resolution costs real per-lookup credits) has to be scheduled strictly behind the *cheap* qualifying stage (scoring is pure DB computation, no external calls) - and that ordering has to be enforced by the schedule itself, not assumed from the code being "correct."

## Stage 1: TheirStack Discovery

Searches job postings via a hiring-intent API, normalizes results, recognizes which applicant-tracking-system a posting uses by its board URL pattern (Greenhouse/Lever/Ashby/Recruitee/Workable), and upserts companies + job_postings + an ATS registry row (which board to poll going forward). This is the seed stage for everything downstream - it's also the shape shared by the ~9 other independent discovery sources in the wider system (see below), just with a different search API at the front each time.

**Dedup by normalized domain, not raw company name** - two variants of the same domain from two different sources have to merge into one company record, or the pipeline double-counts and double-contacts.

## Stage 2: ATS Poller

Runs daily specifically because the weekly discovery pass alone leaves job_postings up to a week stale. Polls every board in the ATS registry, diffs the board's current listing against what the database already thinks is open, and reconciles: new postings inserted, still-open postings get a freshness bump, postings that vanished from the board get closed. Per-board batching means one board's API hiccup can't abort the poll for the rest.

## Stage 3: Staleness Recheck

Confirms `closed_at` on the roughly 90% of postings that ATS Poller doesn't cover directly (non-ATS-board postings), using a targeted, low-cost recheck call rather than re-running full discovery. Corrects the record before Scoring runs, so a posting that's actually closed doesn't keep earning "stale posting" points it no longer deserves.

## Stage 4: Scoring

Two DB-side stored-procedure calls, no external API traffic at all:
1. `compute_hiring_signals()` - stale posting (+30, open >= 45 days), multi-role (+25, >= 3 open relevant postings at once), lone-engineer (+30, exactly 1 posting at a <= 50-employee company), contract-language (+15, contract-to-hire/staff-aug wording detected). All four signals expire in 30 days and self-renew while the posting stays open.
2. `score_hiring_contacts()` - sums a company's active signal points plus an employee-band bonus into a final score.

**Scoring logic lives in the database, not in workflow code** - deliberate, since scoring rules change often as targeting sharpens, and a stored procedure is one place to change instead of hunting through workflow nodes. Zero external API calls also means this stage is cheap to re-run daily with no rate-limit exposure.

## Stage 5: Find Hiring Contacts

Reads companies with `score >= 35`, best-scored first, capped at 200/run. For each: Apollo person search across 8 target titles (Founder/Co-Founder/CEO/Owner/President/CTO/Head of Product/Studio Head) -> if matched, Apollo reveal (real name + email, or a LeadMagic email-finder fallback if Apollo has no email) -> if no Apollo match at all, LeadMagic role-finder tries the same 8 titles one at a time before falling back further. Every "not found" branch on the LeadMagic side costs 0 credits - only a real match spends credit (2 for role-finder, 1 for email-finder) - which is exactly why the waterfall still tries LeadMagic even after Apollo comes up empty: worst case it costs nothing more to also try. A company with no match anywhere stays in the backlog rather than getting a fabricated contact.

**Two-tier waterfall, not three flat providers.** Apollo is checked first because it returns richer person data in one call; LeadMagic is specifically the fallback for cases Apollo can't fully answer - a flat "try every provider" design would burn LeadMagic credits on companies Apollo could already answer for less.

## Where this fits (the bigger system)

This 5-workflow chain is one source inside a larger real pipeline covering ~9 other independent discovery sources (directory listings, funding filings, accelerator/community signals, hiring-intent APIs, etc.), 3 separate resolution sweeps for sources that write a signal but not yet a contact, and one shared error handler every workflow reports to. The other sources follow the same discovery shape as Stage 1 with a different search step at the front, but most stop earlier than this chain does - this hiring source is the one with a complete, working path all the way from a raw signal to a resolved contact, which is why it's the one documented here in full rather than representatively.

## Reliability (all five stages)

- Every stage writes to durable storage before the next stage reads it - any stage can be re-run independently without reprocessing the whole chain.
- Per-row/per-company batching isolates failures at every stage - one bad record can't abort a run.
- All five report to the same shared error handler (`shared-error-handler` module, same repo) rather than five separate ad-hoc failure paths.
- Stats are logged even when nothing changed, so a human reviewing the tracking sheet can tell "ran and found nothing new" apart from "didn't run."

## Tech stack

n8n (orchestration) · PostgreSQL via PostgREST (stored-procedure-based scoring, shared signal/company state) · a hiring-intent discovery API · direct ATS board polling (Greenhouse/Lever/Ashby/Recruitee/Workable) · a two-tier contact-enrichment waterfall

## What this proves

A real, complete multi-stage pipeline where a genuine production bug (wrong schedule ordering, expensive stage running ahead of its own qualifying gate) got root-caused from execution data and fixed, where each of five independently-deployed workflows does exactly one job, and where the expensive step is structurally impossible to reach without first clearing the cheap one.
