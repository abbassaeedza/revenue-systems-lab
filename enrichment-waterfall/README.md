# Enrichment Waterfall

Pattern: ordered multi-provider enrichment chain with two hard invariants:

1. **Never overwrite a populated field.** A cheaper/later provider must not clobber a
   better/earlier result — once a field is filled, every subsequent provider skips it.
2. **A rate-limited provider is skipped, not fatal.** One provider hitting quota on one lead
   must not stop the rest of the chain, or the rest of the batch.

This pattern was independently built twice in production, in two different stacks (a low-code
orchestrator against Postgres, and a from-scratch Python service against Postgres) — same shape
both times, which is why it's here as a standalone reusable module rather than folded into a
specific pipeline.

Run: `python3 waterfall.py`
