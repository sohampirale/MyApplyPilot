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
        # Tier 1: Core Quality, Production & Dispensing (High Volume)
        'Pharmacist', 'Junior Pharmacist', 'Hospital Pharmacist', 'Clinical Pharmacist', 'Retail Pharmacist',
        'Quality Control Officer', 'QC Analyst', 'QC Executive', 'QC Chemist',
        'Quality Assurance Officer', 'QA Executive', 'QA Chemist', 'IPQA Officer',
        'Production Executive', 'Production Officer', 'Manufacturing Officer',
        'Regulatory Affairs Executive', 'Regulatory Affairs Officer', 'RA Officer',
        'Clinical Research Associate', 'CRA', 'Clinical Trial Assistant',
        # Tier 2: R&D, Clinical & Scientific Roles (M.Pharm / Pharm.D / Ph.D)
        'Formulation Development Scientist', 'F&D Executive', 'F&D Scientist',
        'Analytical Method Development', 'ADL Scientist', 'ADL Executive',
        'Pharmacovigilance Associate', 'PV Officer', 'Drug Safety Associate', 'Drug Safety Physician',
        'Clinical Data Manager', 'CDM Associate',
        'Medical Writer', 'Scientific Writer', 'Medical Information Specialist',
        'Regulatory Documentation Specialist', 'eCTD Specialist', 'DMF Writer',
        # Tier 3: Sales, Marketing, Trainee & Allied Roles (D.Pharm / B.Pharm / Fresher)
        'Medical Representative', 'MR', 'Pharma Sales Executive', 'Territory Manager Pharma',
        'Product Executive', 'Product Manager Pharma',
        'Pharma Trainee', 'Pharmacy Apprentice', 'Graduate Trainee Pharma',
        'Medical Coder', 'Pharma Data Analyst',
    ]

    default_locations = [
        'India', 'Remote India',
        'Mumbai', 'Hyderabad', 'Pune', 'Bengaluru',
        'Ahmedabad', 'Vadodara', 'Ankleshwar', 'Vapi',
        'Baddi', 'Solan', 'Visakhapatnam', 'Chennai', 'Goa', 'Indore',
    ]

    credential_fields = [
        {'key': 'pci_registration', 'label': 'PCI (Pharmacy Council) Registration Number', 'required': False},
        {'key': 'researchgate_url', 'label': 'ResearchGate / Google Scholar URL', 'required': False},
        {'key': 'lab_equipment', 'label': 'Lab Equipment Proficiency (HPLC, GC, etc.)', 'required': False},
    ]

    scoring_prompt_addendum = ''
