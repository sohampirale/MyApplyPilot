"""Chemical & Process Engineering domain engine — Process Design, Plant Ops, Petrochem, Safety."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class ChemicalEngine(BaseDomainEngine):
    """Chemical & Process Engineering job engine."""

    domain_id = 'chemical'
    display_name = 'Chemical & Process Engineering'
    emoji = '🧪'

    default_search_terms = [
        # Fresher & Trainee
        'Graduate Engineer Trainee Chemical', 'GET Chemical',
        'Junior Chemical Engineer', 'Chemical Engineering Trainee',
        'Chemical Plant Trainee', 'Chemical Fresher',
        
        # Process & Design
        'Chemical Process Engineer', 'Process Design Engineer',
        'Process Safety Engineer', 'HAZOP Engineer',
        'Plant Operations Engineer', 'Piping Process Engineer',
        
        # Specialty, Materials & Water
        'Petrochemical Engineer', 'Polymer Engineer',
        'Paints & Coatings Chemist', 'Fertilizer Process Engineer',
        'Water Treatment Engineer', 'ETP Plant Engineer',
        
        # Production & Control
        'Chemical Production Engineer', 'Process Control Engineer',
        'DCS Operator Chemical', 'Chemical QC Officer',
    ]

    default_locations = [
        'Mumbai, Maharashtra', 'Navi Mumbai, Maharashtra', 'Taloja, Maharashtra',
        'Thane, Maharashtra', 'Tarapur, Maharashtra', 'Palghar, Maharashtra',
        'Roha, Maharashtra', 'Mahad, Maharashtra', 'Patalganga, Maharashtra',
        'Pune, Maharashtra', 'Nashik, Maharashtra', 'Aurangabad, Maharashtra',
        'Maharashtra, India', 'Remote India',
    ]

    credential_fields = [
        {'key': 'certifications', 'label': 'Certifications (Aspen Plus, ChemCAD, ISO 14001, HAZOP)', 'required': False},
    ]

    scoring_prompt_addendum = """
When scoring a candidate for Chemical & Process Engineering roles:
- Prioritize: Mass & energy balances, P&ID interpretation, distillation/reaction engineering, process safety (HAZOP), environmental compliance (ETP/STP), and chemical plant operations.
- Value chemical lab experience, industrial plant training, and simulation tool proficiency (Aspen Plus, ChemCAD).
- Ignore software metrics like GitHub stars, LeetCode, or web development stacks.
"""
