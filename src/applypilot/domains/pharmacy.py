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


PHARMA_KEYWORDS = [
    'pharmacist', 'pharmacy', 'pharma', 'quality control', 'qc ', 'qc analyst', 'qc officer', 'qc executive', 'qc chemist',
    'quality assurance', 'qa ', 'qa officer', 'qa executive', 'qa chemist', 'ipqa', 'gmp',
    'production officer', 'production executive', 'manufacturing officer', 'formulation', 'f&d', 'adl', 'analytical method',
    'regulatory affairs', 'ra officer', 'ra executive', 'ectd', 'dmf',
    'clinical research', 'cra', 'clinical trial', 'clinical data', 'cdm',
    'pharmacovigilance', 'pv officer', 'pv associate', 'drug safety',
    'medical writer', 'scientific writer', 'medical representative', 'mr', 'pharma sales', 'medical science liaison', 'msl',
    'nurse', 'nurse advisor', 'phlebotomy', 'haematology', 'oncology', 'chemist', 'microbiologist', 'toxicologist', 'biostatistician',
    'medical coder', 'lab coordinator', 'laboratory', 'biomedical', 'pharmaberater', 'biochemist'
]

NON_PHARMA_KEYWORDS = [
    'software', 'devops', 'developer', 'architect', 'full stack', 'frontend', 'backend', '.net', 'c#', 'java', 'python',
    'firmware', 'controls engineer', 'automation engineer', 'data engineer', 'it technologist', 'it commercial', 'it head',
    'hr ', 'human resources', 'accounts payable', 'auditor', 'audit manager', 'bankkaufmann', 'tender analyst',
    'scheduler', 'business partner', 'consulting', 'financial', 'finance', 'strategist', 'delegate coordinator', 'intern analyst',
    'intercompany', 'electrician'
]


def is_pharmacy_title(title: str) -> bool:
    """Validate if a job title strictly belongs to Pharmacy & Lifesciences domain."""
    t = (title or '').lower()
    if any(b in t for b in NON_PHARMA_KEYWORDS):
        return False
    return any(w in t for w in PHARMA_KEYWORDS)
