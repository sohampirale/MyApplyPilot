"""Domain engine registry and auto-discovery."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from applypilot.domains.base import BaseDomainEngine

# Registry mapping domain_id -> engine class
DOMAIN_REGISTRY: dict[str, type[BaseDomainEngine]] = {}


def register_domain(cls: type[BaseDomainEngine]) -> type[BaseDomainEngine]:
    """Class decorator to register a domain engine."""
    DOMAIN_REGISTRY[cls.domain_id] = cls
    return cls


def get_engine(domain_id: str) -> BaseDomainEngine:
    """Get an engine instance by domain ID. Falls back to engineering."""
    # Lazy import to avoid circular imports
    _ensure_loaded()
    cls = DOMAIN_REGISTRY.get(domain_id)
    if cls is None:
        cls = DOMAIN_REGISTRY.get('engineering')
    if cls is None:
        raise ValueError(f"Domain '{domain_id}' not found and no fallback available")
    return cls()


def list_domains() -> list[dict]:
    """List all registered domains with metadata."""
    _ensure_loaded()
    result = []
    for did, cls in sorted(DOMAIN_REGISTRY.items()):
        result.append({
            'id': cls.domain_id,
            'name': cls.display_name,
            'emoji': cls.emoji,
            'search_terms': cls.default_search_terms,
        })
    return result


def get_domain_for_candidate(candidate_id: str | None = None) -> str:
    """Get the domain_id for a candidate from their profile.
    Falls back to 'engineering' if not specified.
    """
    from applypilot.config import load_candidate_profile, get_active_candidate_id
    cid = candidate_id or get_active_candidate_id()
    try:
        profile = load_candidate_profile(cid)
        # Check multiple possible locations for domain
        domain = (
            profile.get('domain')
            or profile.get('experience', {}).get('domain')
            or 'engineering'
        )
        return domain
    except Exception:
        return 'engineering'


_loaded = False


def _ensure_loaded():
    """Import all engine modules to trigger registration."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    import applypilot.domains.engineering  # noqa: F401
    import applypilot.domains.pharmacy    # noqa: F401
    import applypilot.domains.architecture  # noqa: F401
    import applypilot.domains.mba         # noqa: F401
