# CRM <-> Outbound Sync

Pattern: CRM qualification → outbound send → outbound event (reply/bounce) → CRM state update.
Bidirectional, idempotent in both directions.

Two invariants that mattered in production:

1. **CRM → outbound must not double-send.** A lead already sent to the outbound platform is a
   no-op on the next sync pass, not a duplicate send.
2. **Outbound → CRM must not double-apply.** An already-applied reply/bounce event is a no-op,
   not a state flip-flop — this matters because a real event poll can return the same event more
   than once across retries/pagination.

Run: `python3 sync.py`
