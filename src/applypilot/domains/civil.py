"""Civil & Infrastructure Engineering domain engine — Structural, Site, BIM, Quantity Surveying."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class CivilEngine(BaseDomainEngine):
    """Civil & Infrastructure Engineering job engine."""

    domain_id = 'civil'
    display_name = 'Civil & Infrastructure Engineering'
    emoji = '🏗️'

    default_search_terms = [
        # Fresher & Trainee
        'Graduate Engineer Trainee Civil', 'GET Civil',
        'Junior Civil Engineer', 'Civil Site Engineer Fresher',
        'Civil Engineering Trainee', 'Civil Trainee',
        
        # Site & Execution
        'Civil Site Engineer', 'Construction Site Engineer',
        'Project Engineer Civil', 'Site Execution Engineer',
        'Finishing Engineer', 'Civil QC Engineer',
        
        # Structural & Design
        'Structural Design Engineer', 'Structural Engineer',
        'STAAD.Pro Engineer', 'ETABS Designer',
        'Steel Structure Engineer', 'RCC Design Engineer', 'Bridge Engineer',
        
        # Surveying, Billing & Estimation
        'Quantity Surveyor', 'Civil Billing Engineer',
        'Estimation & Costing Engineer', 'Land Surveyor',
        
        # BIM & CAD
        'BIM Modeler Civil', 'BIM Civil Engineer',
        'Revit Civil Designer', 'Civil CAD Drafter',
        
        # Infra & Geotech
        'Highway Engineer', 'Geotechnical Engineer',
        'Water Supply Engineer', 'Environmental Civil Engineer',
    ]

    default_locations = [
        'Mumbai, Maharashtra', 'Navi Mumbai, Maharashtra', 'Thane, Maharashtra',
        'Pune, Maharashtra', 'Pimpri-Chinchwad, Maharashtra', 'Nashik, Maharashtra',
        'Nagpur, Maharashtra', 'Aurangabad, Maharashtra', 'Kolhapur, Maharashtra',
        'Maharashtra, India', 'Remote India',
    ]

    credential_fields = [
        {'key': 'portfolio_url', 'label': 'Project / Drawing Portfolio URL', 'required': False},
        {'key': 'certifications', 'label': 'Certifications (STAAD.Pro, Revit, Primavera P6)', 'required': False},
    ]

    scoring_prompt_addendum = """
When scoring a candidate for Civil & Infrastructure Engineering roles:
- Prioritize: Site execution, structural analysis (STAAD.Pro, ETABS), quantity surveying, billing & BBS (Bar Bending Schedule), IS Codes (IS 456, IS 800, IS 1893), and BIM (Revit).
- Value on-site internships, site survey proficiency (Total Station), and contractor coordination.
- Ignore software development metrics like GitHub stars, LeetCode, or web development stacks.
"""
