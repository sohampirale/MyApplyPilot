"""Mechanical & Automobile Engineering domain engine — CAD, Production, Auto, HVAC."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class MechanicalEngine(BaseDomainEngine):
    """Mechanical, Automobile, and Manufacturing Engineering job engine."""

    domain_id = 'mechanical'
    display_name = 'Mechanical & Automobile Engineering'
    emoji = '⚙️'

    default_search_terms = [
        # Fresher & Trainee
        'Graduate Engineer Trainee Mechanical', 'GET Mechanical',
        'Trainee Mechanical Engineer', 'Junior Mechanical Engineer',
        'Mechanical Engineer Fresher', 'Mechanical Trainee',
        
        # Design & CAD/CAM/CAE
        'Mechanical Design Engineer', 'CAD Engineer', 'SolidWorks Engineer',
        'CATIA Designer', 'Creo Engineer', 'FEA Analyst', 'CFD Engineer',
        'Ansys Engineer', 'Product Design Engineer', 'Tool Design Engineer',
        
        # Manufacturing & Production
        'Production Engineer', 'Manufacturing Engineer', 'Process Engineer Mechanical',
        'CNC Programmer', 'CAM Engineer', 'Piping Design Engineer',
        
        # Quality, Testing & Maintenance
        'Mechanical QC Engineer', 'Quality Assurance Mechanical',
        'Plant Maintenance Engineer', 'Preventive Maintenance Engineer',
        'HVAC Engineer', 'Thermal Engineer',
        
        # Automotive & EV
        'Automotive Engineer', 'Chassis Design Engineer', 'Powertrain Engineer',
        'EV Mechanical Engineer', 'Battery Pack Design Engineer',
    ]

    default_locations = [
        'Pune, Maharashtra', 'Pimpri-Chinchwad, Maharashtra', 'Chakan, Maharashtra',
        'Bhosari, Maharashtra', 'Talegaon, Maharashtra', 'Mumbai, Maharashtra',
        'Navi Mumbai, Maharashtra', 'Thane, Maharashtra', 'Nashik, Maharashtra',
        'Aurangabad, Maharashtra', 'Kolhapur, Maharashtra', 'Nagpur, Maharashtra',
        'Maharashtra, India', 'Remote India',
    ]

    credential_fields = [
        {'key': 'cad_portfolio_url', 'label': 'CAD Portfolio / Drive URL', 'required': False},
        {'key': 'certifications', 'label': 'Certifications (SolidWorks, Ansys, Six Sigma)', 'required': False},
    ]

    scoring_prompt_addendum = """
When scoring a candidate for Mechanical & Automobile Engineering roles:
- Prioritize: 3D CAD modeling (SolidWorks, CATIA, Creo, AutoCAD), FEA/CFD simulation (Ansys, HyperMesh), GD&T, manufacturing process knowledge, production/assembly experience, and site safety.
- For GET / Fresher roles: Prioritize collegiate design competitions (Formula Student, BAJA SAE, SUPRA), CAD modeling portfolios, and academic capstone projects.
- Ignore software development metrics like GitHub stars, LeetCode, or web development stacks.
"""
