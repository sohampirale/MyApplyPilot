"""MBA & Business Management domain engine."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class MBAEngine(BaseDomainEngine):
    """MBA & Business Management job engine.

    Currently uses the shared base scraping pipeline. Override methods
    in this class to customize discovery, scoring, and tailoring for
    business management roles specifically.
    """

    domain_id = 'mba'
    display_name = 'MBA & Business Management'
    emoji = '📊'

    default_search_terms = [
        'Business Analyst', 'Management Trainee', 'Product Manager',
        'Consultant', 'Operations Manager', 'Strategy Analyst',
        'Marketing Manager', 'HR Manager',
    ]

    default_locations = [
        'Mumbai', 'Delhi NCR', 'Bengaluru', 'Pune',
        'Hyderabad', 'Chennai', 'Kolkata',
    ]

    credential_fields = [
        {'key': 'linkedin_url', 'label': 'LinkedIn Profile URL', 'required': True},
        {'key': 'mba_specialization', 'label': 'MBA Specialization (Finance, Marketing, HR, Operations)', 'required': False},
        {'key': 'certifications', 'label': 'Certifications (CFA, Six Sigma, PMP, etc.)', 'required': False},
    ]

    scoring_prompt_addendum = ''
