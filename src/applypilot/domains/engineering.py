"""Engineering domain engine — Software, AI, Backend, DevOps."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class EngineeringEngine(BaseDomainEngine):
    """Software & AI Engineering job engine.

    Currently uses the shared base scraping pipeline. Override methods
    in this class to customize discovery, scoring, and tailoring for
    engineering roles specifically.
    """

    domain_id = 'engineering'
    display_name = 'Software & AI Engineering'
    emoji = '💻'

    default_search_terms = [
        'Software Engineer', 'Full Stack Developer', 'Backend Developer',
        'AI Engineer', 'Machine Learning Engineer', 'Data Engineer',
        'DevOps Engineer', 'Frontend Developer', 'Python Developer',
    ]

    default_locations = [
        'Bengaluru', 'Hyderabad', 'Pune', 'Gurugram', 'Noida',
        'Mumbai', 'Chennai', 'Remote',
    ]

    credential_fields = [
        {'key': 'github_url', 'label': 'GitHub Profile URL', 'required': False},
        {'key': 'portfolio_url', 'label': 'Portfolio / Blog URL', 'required': False},
        {'key': 'leetcode_handle', 'label': 'LeetCode / HackerRank Handle', 'required': False},
    ]

    scoring_prompt_addendum = ''
