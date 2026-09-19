"""Electrical, Electronics & Automation domain engine — Power, PLC/SCADA, Embedded Hardware, Substation."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class ElectricalEngine(BaseDomainEngine):
    """Electrical & Electronics Engineering job engine."""

    domain_id = 'electrical'
    display_name = 'Electrical & Electronics Engineering'
    emoji = '⚡'

    default_search_terms = [
        # Fresher & Trainee
        'Graduate Engineer Trainee Electrical', 'GET Electrical',
        'Junior Electrical Engineer', 'Electrical Engineering Trainee',
        'Electrical Trainee', 'Electrical Fresher',
        
        # Power, Substation & Plant
        'Electrical Design Engineer', 'Substation Engineer',
        'Switchgear Engineer', 'Power Systems Engineer',
        'High Voltage Engineer', 'Testing and Commissioning Engineer',
        'Electrical Maintenance Engineer',
        
        # Industrial Automation & Control
        'PLC Programmer', 'SCADA Engineer', 'Automation Engineer Electrical',
        'DCS Engineer', 'Instrumentation & Control Engineer',
        'Panel Design Engineer', 'AutoCAD Electrical Drafter',
        
        # Electronics & Hardware
        'Embedded Hardware Engineer', 'Hardware Design Engineer',
        'PCB Layout Engineer', 'Altium Designer',
        'Power Electronics Engineer', 'SMPS Design Engineer',
        
        # EV & Renewable
        'EV Powertrain Electrical Engineer', 'BMS Hardware Engineer',
        'Solar Electrical Engineer',
    ]

    default_locations = [
        'Pune, Maharashtra', 'Pimpri-Chinchwad, Maharashtra', 'Chakan, Maharashtra',
        'Bhosari, Maharashtra', 'Ranjangaon, Maharashtra', 'Mumbai, Maharashtra',
        'Navi Mumbai, Maharashtra', 'Thane, Maharashtra', 'Nashik, Maharashtra',
        'Aurangabad, Maharashtra', 'Kolhapur, Maharashtra', 'Nagpur, Maharashtra',
        'Maharashtra, India', 'Remote India',
    ]

    credential_fields = [
        {'key': 'portfolio_url', 'label': 'Hardware / Circuit Portfolio URL', 'required': False},
        {'key': 'certifications', 'label': 'Certifications (MATLAB, PLC/SCADA, ETAP)', 'required': False},
    ]

    scoring_prompt_addendum = """
When scoring a candidate for Electrical & Electronics Engineering roles:
- Prioritize: Power systems knowledge, single-line diagrams (SLD), voltage standards, switchgear/relay coordination, PLC/SCADA programming (Siemens, Rockwell), and PCB layout (Altium, KiCad).
- Value hands-on lab projects, testing & commissioning experience, and plant safety protocols.
- Ignore pure web development stacks (React, CSS, Node).
"""
