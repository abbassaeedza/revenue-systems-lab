"""Enrichment waterfall: ordered provider chain, non-destructive writes, rate-limit fallthrough.

Clean-room pattern demo. Providers here are fake/synthetic stand-ins for real enrichment APIs.
"""
from __future__ import annotations

from dataclasses import dataclass, fields


class RateLimited(Exception):
    """Raised by a provider stub to simulate a 429/quota-exhausted response."""


@dataclass
class Lead:
    domain: str
    owner_name: str | None = None
    email: str | None = None
    company_size: int | None = None


# --- provider stubs, ordered cheapest/most-reliable first -----------------------------------

UNKNOWN_TO_PROVIDER_A = {"unknown-corp.com", "rate-limited-corp.com"}


def provider_a_firmographics(lead: Lead) -> dict:
    """Simulates a firmographics+owner provider. Reliable, but doesn't know everyone."""
    if lead.domain in UNKNOWN_TO_PROVIDER_A:
        return {}
    return {"owner_name": "Jordan Rivera", "company_size": 42}


def provider_b_email_finder(lead: Lead) -> dict:
    """Simulates an email-finder keyed on a known owner name."""
    if not lead.owner_name:
        return {}
    return {"email": f"{lead.owner_name.split()[0].lower()}@{lead.domain}"}


def provider_c_flaky_backup(lead: Lead) -> dict:
    """Simulates a provider that's rate-limited on this particular domain."""
    if lead.domain == "rate-limited-corp.com":
        raise RateLimited(f"provider_c quota exhausted for {lead.domain}")
    return {"owner_name": "Fallback Owner"}


WATERFALL = [provider_a_firmographics, provider_b_email_finder, provider_c_flaky_backup]


def enrich(lead: Lead, providers: list = WATERFALL) -> Lead:
    """Run each provider in order. Never overwrite an already-populated field.

    A provider raising RateLimited is skipped, not fatal — the waterfall keeps going.
    """
    lead_fields = {f.name for f in fields(Lead)} - {"domain"}
    for provider in providers:
        if all(getattr(lead, f) is not None for f in lead_fields):
            break  # fully enriched, no need to call remaining (cheaper) providers
        try:
            result = provider(lead)
        except RateLimited:
            continue
        for key, value in result.items():
            if getattr(lead, key) is None:
                setattr(lead, key, value)
    return lead


if __name__ == "__main__":
    # normal case: provider_a fills owner+size, provider_b fills email from owner
    lead = enrich(Lead(domain="acme.com"))
    assert lead.owner_name == "Jordan Rivera"
    assert lead.email == "jordan@acme.com"
    assert lead.company_size == 42

    # non-destructive write: a pre-populated field must survive the whole chain untouched
    lead2 = enrich(Lead(domain="acme.com", owner_name="Pre-Existing Name"))
    assert lead2.owner_name == "Pre-Existing Name", "enrichment must never overwrite a populated field"
    assert lead2.email == "pre-existing@acme.com"  # derived from the pre-existing name, not provider_a's

    # provider_a has nothing, provider_c is rate-limited on this exact domain -> owner_name stays None
    lead3 = enrich(Lead(domain="rate-limited-corp.com"))
    assert lead3.owner_name is None, "rate-limited provider must be skipped, not raise out of the waterfall"

    # provider_a has nothing but provider_c is NOT rate-limited on this domain -> falls through to it
    lead4 = enrich(Lead(domain="unknown-corp.com"))
    assert lead4.owner_name == "Fallback Owner", "a rate limit on a different domain must not block this one"

    print(f"OK — {lead.domain}: {lead.owner_name} / {lead.email} / size={lead.company_size}")
    print(f"OK — non-destructive: {lead2.owner_name} preserved through the chain")
