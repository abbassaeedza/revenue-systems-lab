# Guest-Post Prospecting Pipeline

A small-scale, real production system for SEO link-building outreach: find blogs that accept guest posts, resolve a contact email per domain, and send a personalized pitch through a compliance-aware sending stage.

## Problem

Guest-post link building has three separable hard parts that most simple scrapers conflate into one script: finding *candidate* blogs (search-engine discovery, not a fixed list), resolving an actual *contact email* per domain (most sites don't publish one obviously), and *sending* without either annoying everyone with an identical template or tripping spam filters. Each stage has a different failure mode, so each is its own workflow.

## Architecture

```
Launcher (query sets)
   |
   v  (parallel, one worker invocation per query set)
Worker: SERP search -> extract URLs -> filter/dedupe domains -> save to prospect sheet
   |
   v  (scheduled poll of the prospect sheet)
Email extraction: fetch homepage -> extract email (regex + junk filter)
                      |-- found --> done
                      '-- not found --> fetch /contact-us/ -> extract again -> done/no-email/error
   |
   v  (daily scheduled run, reads sheets fresh each time)
Outreach: filter to unsent prospects -> daily send cap -> verify email (NeverBounce)
             -> deliverable? -> personalize (fixed copy OR LLM-drafted, alternating mailboxes)
             -> send -> log to tracking sheet
```

## What I built

- **Parallel worker fan-out for search discovery.** The launcher doesn't loop through query sets sequentially — it executes a sub-workflow once per set via n8n's Execute Workflow node in `each` mode, so ~20+ query sets run concurrently instead of one at a time. Each set intentionally varies phrasing ("guest post X", "write for us X", "submit article X", "contribute X blog", "guest post guidelines X") because search engines rank these patterns differently — a single phrasing misses real prospects.
- **A real junk-filtering pass on email extraction**, not just a regex match: strips script/style tags before matching, rejects file-extension false positives (`.png`/`.css`/etc. that a naive regex reads as a TLD), rejects placeholder domains and local parts (`example.com`, `noreply@`, `johndoe@`), rejects 32-char hex strings (tracking-pixel IDs that look like emails), and fixes a specific encoding artifact where obfuscated mailto links decode with a stray unicode-escape prefix glued onto the front of the address.
- **Two-tier email resolution**: homepage first, `/contact-us/` only as a fallback if the homepage yields nothing — avoids a second HTTP request per domain in the common case where the homepage already has it.
- **Retry-with-cap on the extraction stage**: an `Error` status (fetch itself failed) is eligible for retry up to a fixed attempt cap; a `No Email` status (both pages fetched cleanly, genuinely nothing there) is terminal and never retried. The two failure modes are handled differently on purpose.
- **Daily send cap split across two mailboxes**, alternated evenly across the whole send history (not reset per run) so neither mailbox gets disproportionately loaded — a real deliverability/reputation-management decision, not an arbitrary number.
- **Email verification before every send**, not before every scrape: NeverBounce runs at send-time, right before the message goes out, so a domain that stops resolving between discovery and send doesn't waste a mailbox's daily cap on a bounce. `catchall` domains (common for blog platforms) are accepted by default; a stricter deployment could drop that from the accept-list at the cost of volume.
- **Dual-path personalization**: one mailbox always sends a fixed, pre-approved template (predictable, reviewable copy); the other sends an LLM-drafted pitch constrained by an explicit style contract (word count, sentence count, sentence length, subject-line character count, exactly one ask) enforced by a real compliance-stats pass after generation — the system checks its own output against the prompt's own limits rather than trusting the model to have followed them.
- **Personalization that knows when to stay generic.** The scraped page title is only referenced in the outreach email if it looks like an actual article (rejects nav/category-page titles, "write for us" pages, and anything under 4 words) — naming a category index instead of a real post reads worse than not personalizing at all, so the system detects that case and falls back to a generic open.

## Hard parts

- **Search-engine query phrasing genuinely changes result composition.** The same underlying topic returns a different set of candidate blogs depending on whether the query is phrased "guest post X" vs. "write for us X" vs. "submit article X" — this is why the query-set generator deliberately varies phrasing per topic rather than using one canonical query per topic.
- **The encoding-artifact bug**: some sites' obfuscated `mailto:` links decode through the extraction pipeline with a stray unicode-escape prefix stuck to the front of the local part (e.g. an address reads as garbage-prefix-plus-real-address). Fixed with a targeted regex once identified, rather than a rewrite of the extraction approach.
- **Reply/bounce data lives in a separate real system** (Smartlead-based reply classification, covered in the `reply-classification-router` module) — this pipeline's own tracking sheet only records send events, not response outcomes, by design; response handling is a shared concern with the rest of the outbound stack, not duplicated here.

## Reliability

- `onError: continueRegularOutput` on every outbound HTTP fetch — one unreachable site's timeout never halts the batch.
- Google Sheets writes use `retryOnFail` with multiple attempts — a transient Sheets API hiccup doesn't lose a result.
- The daily send job re-reads both source sheets fresh on every run rather than holding stale in-memory state, so a manual edit to either sheet between runs is always respected.

## Tech stack

n8n (orchestration, parallel sub-workflow execution) · a search-engine results API · Google Sheets (as a lightweight queue/database) · NeverBounce (email verification) · an LLM via Groq (constrained-style copy generation) · SMTP send

## What this proves

A real multi-stage pipeline where each stage has its own distinct failure mode and each is handled on its own terms — parallel fan-out for discovery throughput, a two-tier fallback with a real junk filter for extraction accuracy, and a verify-then-send-with-caps discipline for deliverability. Small in scale, but every design choice here is defensible on its own, not cargo-culted from a tutorial.
