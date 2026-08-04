"""Architecture & Urban Design domain engine."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class ArchitectureEngine(BaseDomainEngine):
    """Architecture & Urban Design job engine.

    Currently uses the shared base scraping pipeline. Override methods
    in this class to customize discovery, scoring, and tailoring for
    architecture roles specifically.
    """

    domain_id = 'architecture'
    display_name = 'Architecture & Urban Design'
    emoji = '🏛️'

    default_search_terms = [
        'Junior Architect', 'Architectural Designer', 'CAD Specialist',
        'BIM Modeler', 'Interior Designer', 'Urban Planner',
        'Landscape Architect', 'Revit Specialist',
    ]

    default_locations = [
        'Mumbai', 'Pune', 'Delhi NCR', 'Bengaluru',
        'Hyderabad', 'Chennai', 'Ahmedabad',
    ]

    credential_fields = [
        {'key': 'coa_license', 'label': 'Council of Architecture (COA) License Number', 'required': False},
        {'key': 'portfolio_url', 'label': 'Portfolio URL (Behance / Issuu / Personal Site)', 'required': True},
        {'key': 'cad_software', 'label': 'CAD/BIM Software (Revit, AutoCAD, Rhino, etc.)', 'required': False},
    ]

    scoring_prompt_addendum = ''
