# CRM Outbound Sync

Pattern: CRM qualification event -> outbound send -> outbound reply event -> CRM state update. Bidirectional, idempotent in both directions. Two separately-deployed real n8n workflows, chained through shared state (the CRM contact ID, carried as a custom field on the outbound lead), not direct workflow-to-workflow calls.

> Sanitized real workflows. Credentials, API keys, and campaign IDs are replaced with placeholders in both files. Node logic and status-transition rules are unchanged from production.

**Lead qualification itself happens upstream, in the CRM's own automation** (a separate workflow inside the CRM platform managing lead lifecycle states - e.g. a lead moves to "qualified," or to "lost - recheck in 60 days" if it doesn't convert). This module starts at the point the CRM fires a webhook because a lead just became qualified - it isn't the qualification logic itself.

## What it does

1. **`1-crm-qualified-lead-to-outbound.workflow.json`** - triggered by a CRM webhook on a qualified-lead event. Pulls the lead's contact details from the CRM, creates the corresponding lead in the outbound platform with the CRM contact ID carried through as a custom field, and marks the CRM contact synced. A contact with no email yet, or a deal with no associated contact yet, is logged to a side table rather than dropped - both are common, real states, not errors.
2. **`2-outbound-reply-to-crm-update.workflow.json`** - triggered by an outbound-platform event webhook. On a genuine reply (not opens/clicks/bounces), classifies the reply body via a lightweight LLM call into INTERESTED / NOT INTERESTED / OUT OF OFFICE, then writes the sequence step, classification, and both raw email addresses back onto the matching CRM contact. A NOT INTERESTED verdict, or a reply landing on the final sequence step without an INTERESTED verdict, marks the CRM record COMPLETED; anything else stays IN PROGRESS.

## Two invariants that mattered in production

1. **CRM -> outbound must not double-send.** A lead already marked synced is a no-op on a retried/redelivered webhook, not a duplicate outbound lead.
2. **Outbound -> CRM must not double-apply.** An already-applied reply/bounce event is a no-op, not a state flip-flop - this matters because a real webhook can redeliver the same event more than once.

## Why it's built this way

- **Two small, single-purpose workflows instead of one bidirectional monolith.** The CRM-to-outbound direction and the outbound-to-CRM direction have genuinely different triggers, payloads, and failure modes - keeping them separate means a change to reply-classification logic can't accidentally affect lead-creation logic, and vice versa.
- **Never silently drop a lead.** No-contact and no-email states are logged to dedicated side tables specifically so nothing just vanishes - the same "never silently drop" posture used throughout the other modules in this repo.
- **Status transitions are explicit terminal states**, not inferred - COMPLETED vs IN PROGRESS is set directly by rule, not left for a human to infer from raw event history.

## Tech stack

n8n (orchestration) · a CRM's webhook + REST API · an LLM for reply classification · an outbound sending platform's REST API

## What this proves

A real bidirectional sync where each direction is its own small workflow with its own idempotency guarantee, triggered by real lifecycle events (qualification, reply) rather than a polling loop - and where every edge case (no contact, no email, redelivered event) has an explicit, non-dropping outcome.
