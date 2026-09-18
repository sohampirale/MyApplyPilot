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
        'Software Engineer', 'Software Developer', 'Full Stack Developer',
        'Frontend Developer', 'Backend Developer', 'Python Developer',
        'Java Developer', 'React Developer', 'Node.js Developer',
        '.NET Developer', 'C++ Developer', 'Web Developer',
        'Graduate Engineer Trainee', 'Associate Software Engineer', 'Junior Software Engineer',
        'SDE 1', 'Software Engineer Intern', 'Fresher Developer',
        'Embedded Software Engineer', 'Firmware Engineer', 'IoT Engineer',
        'Systems Engineer', 'Programmer Analyst',
        'Data Engineer', 'Data Scientist', 'Data Analyst',
        'AI Engineer', 'Machine Learning Engineer',
        'DevOps Engineer', 'Cloud Engineer', 'QA Engineer', 'SDET',
    ]

    default_locations = [
        'Pune, Maharashtra', 'Mumbai, Maharashtra', 'Navi Mumbai, Maharashtra',
        'Thane, Maharashtra', 'Nagpur, Maharashtra', 'Nashik, Maharashtra',
        'Aurangabad, Maharashtra', 'Kolhapur, Maharashtra', 'Pimpri-Chinchwad, Maharashtra',
        'Maharashtra, India', 'Remote India',
    ]

    credential_fields = [
        {'key': 'github_url', 'label': 'GitHub Profile URL', 'required': False},
        {'key': 'portfolio_url', 'label': 'Portfolio / Blog URL', 'required': False},
        {'key': 'leetcode_handle', 'label': 'LeetCode / HackerRank Handle', 'required': False},
    ]

    scoring_prompt_addendum = ''
