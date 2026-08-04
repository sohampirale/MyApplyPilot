"""Pharmacy & Lifesciences domain engine."""

from applypilot.domains.base import BaseDomainEngine
from applypilot.domains.registry import register_domain


@register_domain
class PharmacyEngine(BaseDomainEngine):
    """Pharmacy & Lifesciences job engine.

    Currently uses the shared base scraping pipeline. Override methods
    in this class to customize discovery, scoring, and tailoring for
    pharmacy and lifesciences roles specifically.
    """

    domain_id = 'pharmacy'
    display_name = 'Pharmacy & Lifesciences'
    emoji = '💊'

    default_search_terms = [
        'Pharmacist', 'Quality Assurance Executive', 'QC Analyst',
        'Regulatory Affairs', 'Clinical Research Associate',
        'Formulation Scientist', 'Drug Safety Associate', 'Medical Representative',
    ]

    default_locations = [
        'Mumbai', 'Hyderabad', 'Pune', 'Bengaluru',
        'Ahmedabad', 'Chennai', 'Vadodara',
    ]

    credential_fields = [
        {'key': 'pci_registration', 'label': 'PCI (Pharmacy Council) Registration Number', 'required': False},
        {'key': 'researchgate_url', 'label': 'ResearchGate / Google Scholar URL', 'required': False},
        {'key': 'lab_equipment', 'label': 'Lab Equipment Proficiency (HPLC, GC, etc.)', 'required': False},
    ]

    scoring_prompt_addendum = ''
