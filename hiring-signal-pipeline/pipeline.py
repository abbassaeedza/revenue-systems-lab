"""Hiring-signal pipeline: raw signals -> normalized -> deduped -> scored -> outbound-eligible.

Clean-room pattern demo. Synthetic data only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class RawSignal:
    source: str
    company_name: str
    domain: str
    title: str
    posted_on: date


@dataclass
class Company:
    domain: str
    name: str
    signals: list[RawSignal] = field(default_factory=list)
    score: float = 0.0
    contact_email: str | None = None


TITLE_WEIGHTS = {
    "sdr": 1.0,
    "account executive": 1.0,
    "vp sales": 1.5,
    "head of growth": 1.3,
}


def normalize_domain(raw: str) -> str:
    return raw.strip().lower().removeprefix("www.")


def ingest(signals: list[RawSignal]) -> dict[str, Company]:
    """Normalize + dedup by domain. Later signals for a known domain merge in, not overwrite."""
    companies: dict[str, Company] = {}
    for sig in signals:
        domain = normalize_domain(sig.domain)
        company = companies.setdefault(domain, Company(domain=domain, name=sig.company_name))
        company.signals.append(sig)
    return companies


def score(company: Company, today: date, freshness_window_days: int = 30) -> float:
    """Score = sum of per-signal title weight, decayed by staleness. Stale signals contribute ~0."""
    total = 0.0
    for sig in company.signals:
        weight = next((w for title, w in TITLE_WEIGHTS.items() if title in sig.title.lower()), 0.3)
        age_days = (today - sig.posted_on).days
        if age_days > freshness_window_days:
            continue
        decay = 1.0 - (age_days / freshness_window_days)
        total += weight * decay
    return round(total, 2)


def resolve_contact(company: Company) -> str | None:
    """Contact-resolution stub — a real system calls Apollo/LeadMagic/etc here.

    Only resolves companies with a scored, fresh signal; returns None otherwise (no wasted lookups).
    """
    if company.score <= 0:
        return None
    slug = company.name.lower().replace(" ", ".")
    return f"vp.sales@{company.domain}" if "vp sales" in " ".join(s.title.lower() for s in company.signals) else f"contact@{company.domain}"


def outbound_eligible(company: Company, min_score: float = 0.8) -> bool:
    return company.score >= min_score and company.contact_email is not None


def run_pipeline(signals: list[RawSignal], today: date) -> list[Company]:
    companies = ingest(signals)
    eligible = []
    for company in companies.values():
        company.score = score(company, today)
        company.contact_email = resolve_contact(company)
        if outbound_eligible(company):
            eligible.append(company)
    return sorted(eligible, key=lambda c: c.score, reverse=True)


if __name__ == "__main__":
    today = date(2026, 9, 1)
    demo_signals = [
        RawSignal("job_board_a", "Acme Robotics", "acmerobotics.io", "VP Sales", today - timedelta(days=2)),
        RawSignal("job_board_b", "Acme Robotics", "www.acmerobotics.io", "SDR", today - timedelta(days=5)),
        RawSignal("job_board_a", "Stale Corp", "stalecorp.com", "Account Executive", today - timedelta(days=60)),
        RawSignal("job_board_a", "Tiny Signal Co", "tinysignal.com", "Office Manager", today - timedelta(days=1)),
    ]

    results = run_pipeline(demo_signals, today)

    assert len(results) == 1, f"expected 1 outbound-eligible company, got {len(results)}"
    assert results[0].domain == "acmerobotics.io", "www./non-www domain variants should dedup to one company"
    assert results[0].contact_email == "vp.sales@acmerobotics.io"
    assert results[0].score > 0.8

    print(f"OK — {results[0].name} ({results[0].domain}) scored {results[0].score}, contact: {results[0].contact_email}")
