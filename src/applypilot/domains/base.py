"""Base domain engine class."""


class BaseDomainEngine:
    """Base domain engine for job discovery & evaluation."""

    domain_id: str = 'base'
    display_name: str = 'Base Domain'
    emoji: str = '🌐'
    default_search_terms: list[str] = []
    default_locations: list[str] = []
    credential_fields: list[dict] = []
    scoring_prompt_addendum: str = ''

    def get_search_config(self) -> dict:
        """Return search terms, locations, and domain ID for scrapers."""
        return {
            'search_terms': self.default_search_terms,
            'queries': [{'query': term, 'tier': 1} for term in self.default_search_terms],
            'locations': [{'location': loc, 'remote': ('remote' in loc.lower())} for loc in self.default_locations],
            'domain': self.domain_id,
        }

    def get_scoring_context(self) -> str:
        """Return extra context appended to the LLM scoring prompt."""
        return self.scoring_prompt_addendum

    def get_credential_fields(self) -> list[dict]:
        """Return credential field specifications for candidate profiles."""
        return self.credential_fields
