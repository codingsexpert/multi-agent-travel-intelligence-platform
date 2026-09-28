"""Structured Research models, source trust classification, and conflicting claim schemas."""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field, ConfigDict


class SourceTrustCategory(str, Enum):
    """Categorical source classification according to authority and curation."""

    OFFICIAL = "OFFICIAL"      # Government, embassy, official tourism board, airport authority
    NEWS = "NEWS"              # Established news agency, accredited journalism
    REFERENCE = "REFERENCE"    # Encyclopedias, verified geography portals (Wikipedia, Wikivoyage)
    COMMUNITY = "COMMUNITY"    # Forums, travel blogs, community discussion (Reddit, TripAdvisor forums)
    UNKNOWN = "UNKNOWN"        # Unclassified or unverified external sources


# Curated domain maps for deterministic classification
_OFFICIAL_DOMAINS = {
    "travel.state.gov",
    "state.gov",
    "gov.uk",
    "visitbritain.com",
    "visitlondon.com",
    "japan.travel",
    "jnto.go.jp",
    "metro.tokyo.jp",
    "parisjetaime.com",
    "diplomatie.gouv.fr",
    "nycgo.com",
    "ny.gov",
    "incredibleindia.org",
    "italia.it",
    "comune.roma.it",
    "who.int",
    "un.org",
    "schengenvisainfo.com",
}

_NEWS_DOMAINS = {
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "apnews.com",
    "cnn.com",
    "nytimes.com",
    "theguardian.com",
    "japantimes.co.jp",
    "lemonde.fr",
    "timesofindia.indiatimes.com",
    "bloomberg.com",
    "wsj.com",
    "aljazeera.com",
    "france24.com",
    "independent.co.uk",
    "standard.co.uk",
}

_REFERENCE_DOMAINS = {
    "wikipedia.org",
    "en.wikipedia.org",
    "wikivoyage.org",
    "en.wikivoyage.org",
    "lonelyplanet.com",
    "roughguides.com",
    "fodors.com",
    "frommers.com",
    "cntraveler.com",
}

_COMMUNITY_DOMAINS = {
    "reddit.com",
    "tripadvisor.com",
    "quora.com",
    "flyertalk.com",
    "nomadicmatt.com",
    "thepointsguy.com",
    "yelp.com",
}


def classify_domain_trust(url_or_domain: str) -> SourceTrustCategory:
    """Classify the trust tier of an external source URL or domain name."""
    if not url_or_domain:
        return SourceTrustCategory.UNKNOWN

    raw = url_or_domain.strip().lower()
    if "://" in raw:
        try:
            parsed = urlparse(raw)
            domain = parsed.hostname or raw
        except Exception:
            domain = raw
    else:
        domain = raw.split("/")[0]

    domain = domain.lower().strip()

    # 1. Government and official TLDs
    if (
        domain.endswith(".gov")
        or ".gov." in domain
        or domain.endswith(".mil")
        or ".gouv." in domain
        or domain.endswith(".gc.ca")
    ):
        return SourceTrustCategory.OFFICIAL

    # 2. Known official tourism / authority portals
    if any(domain == d or domain.endswith(f".{d}") for d in _OFFICIAL_DOMAINS):
        return SourceTrustCategory.OFFICIAL

    # 3. Known news media
    if any(domain == d or domain.endswith(f".{d}") for d in _NEWS_DOMAINS):
        return SourceTrustCategory.NEWS

    # 4. Known reference portals
    if any(domain == d or domain.endswith(f".{d}") for d in _REFERENCE_DOMAINS):
        return SourceTrustCategory.REFERENCE

    # 5. Community and user forums
    if any(domain == d or domain.endswith(f".{d}") for d in _COMMUNITY_DOMAINS):
        return SourceTrustCategory.COMMUNITY

    return SourceTrustCategory.UNKNOWN


class ResearchFinding(BaseModel):
    """Specific synthesized travel intelligence finding backed by sources."""

    model_config = ConfigDict(extra="ignore")

    claim: str = Field(description="Factual claim or observation")
    category: str = Field(
        default="general",
        description="Category: event, festival, disruption, closure, advisory, entry_requirement",
    )
    sources: List[str] = Field(default_factory=list, description="Preserved citation URLs or source labels")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    is_verified: bool = Field(default=True)
    is_authoritative: bool = Field(default=False, description="True if backed by an OFFICIAL source")
    published_at: Optional[str] = Field(default=None, description="Original publication timestamp if available")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConflictingClaim(BaseModel):
    """Explicitly flagged divergence or contradiction between research sources."""

    model_config = ConfigDict(extra="ignore")

    topic: str = Field(description="Subject of disagreement (e.g. holiday hours, entry fee)")
    claim_a: str = Field(description="Statement from first source")
    source_a: str = Field(description="Source identifier for claim A")
    date_a: Optional[str] = None
    claim_b: str = Field(description="Contradicting statement from second source")
    source_b: str = Field(description="Source identifier for claim B")
    date_b: Optional[str] = None
    uncertainty_note: str = Field(description="Guidance on resolving conflict or verification gap")


class FreshWebResearchResult(BaseModel):
    """Structured research deliverable generated from fresh web and news queries."""

    model_config = ConfigDict(extra="ignore")

    query: str
    destination: str
    findings: List[ResearchFinding] = Field(default_factory=list)
    conflicts: List[ConflictingClaim] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    freshness: str = Field(default="recent", description="today, 24h, 7d, 30d, recent")
    official_verified: bool = Field(default=False, description="Whether core travel requirements were verified via OFFICIAL sources")
    warnings: List[str] = Field(default_factory=list)
    data_mode: str = Field(default="DEMO")
    provider: str = Field(default="Search MCP")
