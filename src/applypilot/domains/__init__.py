"""Domain-specific job discovery & evaluation engines."""

from applypilot.domains.registry import (
    get_engine,
    list_domains,
    get_domain_for_candidate,
    DOMAIN_REGISTRY,
)
