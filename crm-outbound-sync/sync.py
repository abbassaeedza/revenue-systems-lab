"""CRM <-> outbound-platform sync: qualification -> send -> reply/bounce -> CRM state update.

Bidirectional, idempotent. Clean-room pattern demo, mock CRM and mock outbound platform.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class LeadState(str, Enum):
    QUALIFIED = "qualified"
    SENT = "sent"
    REPLIED = "replied"
    BOUNCED = "bounced"


@dataclass
class CRMLead:
    id: str
    email: str
    state: LeadState = LeadState.QUALIFIED


class MockCRM:
    """Stand-in for HubSpot/Salesforce/etc — a dict keyed by lead id."""

    def __init__(self) -> None:
        self.leads: dict[str, CRMLead] = {}

    def upsert(self, lead: CRMLead) -> None:
        self.leads[lead.id] = lead

    def qualified_leads(self) -> list[CRMLead]:
        return [l for l in self.leads.values() if l.state == LeadState.QUALIFIED]


class MockOutboundPlatform:
    """Stand-in for Smartlead/Instantly/etc — tracks what it's already sent, to stay idempotent."""

    def __init__(self) -> None:
        self.sent_lead_ids: set[str] = set()
        self.events: list[tuple[str, str]] = []  # (lead_id, event_type)

    def send(self, lead: CRMLead) -> bool:
        """Returns False (no-op) if this lead was already sent — the idempotency guarantee."""
        if lead.id in self.sent_lead_ids:
            return False
        self.sent_lead_ids.add(lead.id)
        return True

    def poll_events(self) -> list[tuple[str, str]]:
        """A real platform would return only new events since last poll; here we drain a queue."""
        events, self.events = self.events, []
        return events


def sync_qualified_to_outbound(crm: MockCRM, outbound: MockOutboundPlatform) -> int:
    """CRM -> outbound direction: send every qualified lead, mark SENT, skip already-sent."""
    sent_count = 0
    for lead in crm.qualified_leads():
        if outbound.send(lead):
            lead.state = LeadState.SENT
            sent_count += 1
    return sent_count


def sync_outbound_events_to_crm(crm: MockCRM, outbound: MockOutboundPlatform) -> int:
    """outbound -> CRM direction: apply reply/bounce events, idempotent (event already applied = no-op)."""
    applied = 0
    for lead_id, event_type in outbound.poll_events():
        lead = crm.leads.get(lead_id)
        if lead is None:
            continue
        new_state = LeadState.REPLIED if event_type == "reply" else LeadState.BOUNCED
        if lead.state == new_state:
            continue  # already applied, idempotent no-op
        lead.state = new_state
        applied += 1
    return applied


if __name__ == "__main__":
    crm = MockCRM()
    outbound = MockOutboundPlatform()

    crm.upsert(CRMLead(id="lead-1", email="a@acme.com"))
    crm.upsert(CRMLead(id="lead-2", email="b@acme.com"))

    sent = sync_qualified_to_outbound(crm, outbound)
    assert sent == 2
    assert crm.leads["lead-1"].state == LeadState.SENT

    # re-running the CRM->outbound sync must not double-send (both leads are no longer QUALIFIED)
    sent_again = sync_qualified_to_outbound(crm, outbound)
    assert sent_again == 0, "already-sent leads must not be re-sent on a repeat sync"

    outbound.events.append(("lead-1", "reply"))
    outbound.events.append(("lead-2", "bounce"))
    applied = sync_outbound_events_to_crm(crm, outbound)
    assert applied == 2
    assert crm.leads["lead-1"].state == LeadState.REPLIED
    assert crm.leads["lead-2"].state == LeadState.BOUNCED

    # re-applying the same (already-drained) events queue is a no-op — nothing left to poll
    applied_again = sync_outbound_events_to_crm(crm, outbound)
    assert applied_again == 0, "polling an empty event queue must not touch CRM state"

    print(f"OK — sent {sent}, applied {applied} events, sync is idempotent on repeat")
