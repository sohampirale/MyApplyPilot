Conclusion & Operational Execution StandardsTo maintain pipeline reliability across high-frequency pharmaceutical discovery channels, deployment operations should follow established execution guidelines:Staggered Execution Schedules: Direct JSON REST queries to enterprise Workday endpoints should run on 12-hour intervals. HTML DOM scraping of niche portals should execute on 24-hour cycles to prevent IP throttling. Government notice boards and public institute PDF circulars should be queried once daily during business hours.Session Persistence and Header Diversification: Requests routed to social feeds or job aggregators must maintain dynamic user-agent rotation and persist cookies across sessions to handle anti-bot verification challenges.Database Optimization: SQLite indexing should be maintained across (domain_category, qualification_tier, location) to allow fast querying by front-end services. De-duplication using SHA-256 hashes generated from company_name + title + location ensures dataset integrity across multi-channel aggregators.

Comprehensive Architectural Blueprint for Automated Pharmaceutical Job Discovery in IndiaAutomated job discovery within the Indian pharmaceutical ecosystem presents distinct computational and data-engineering challenges. The sector is characterized by extreme fragmentation, spanning global enterprise Applicant Tracking Systems (ATS), localized retail pharmacy chains, regional plant manufacturing walk-in notices, public sector research institutes, state pharmacy councils, and niche industry job boards. Generic employment aggregators fail to capture a significant proportion of early-career opportunities due to non-standard job titles, geographic dispersion across non-metro manufacturing clusters (such as Baddi, Sikkim, Visakhapatnam, and Ankleshwar), and unconventional publishing channels like PDF recruitment circulars.This report provides an end-to-end technical blueprint for building a specialized, multi-tiered job discovery engine tailored for Indian pharmacy graduates across Diploma (D.Pharm), Bachelor (B.Pharm), and Master/Doctorate (M.Pharm/Pharm.D) academic qualifications.Current ApplyPilot Discovery Infrastructure AuditApplyPilot utilizes a modular data discovery architecture designed to orchestrate search parameter generation, dispatch concurrent network requests across targeted web scrapers, normalize unstructured DOM or API responses, and persist sanitized job records into a relational SQLite database. The engine coordinates four primary software components: jobspy.py, smartextract.py, workday.py, and pharmacy.py.Subsystem Technical Auditsrc/applypilot/discovery/jobspy.pyThis module serves as a concurrent wrapper around public job aggregator interfaces. For execution within the Indian market, parameters are explicitly configured with country_indeed='India' to force local mirror routing. The module exposes configuration parameters including target query strings, location strings, maximum posting age (hours_old=72), and batch pagination limits. It normalizes output payloads into standardized dictionaries containing title, company name, location, external application URL, posting date, and raw job text.src/applypilot/discovery/smartextract.pyThis module operates a Playwright-based headless browser pipeline engineered to handle single-page applications (SPAs) and dynamic JavaScript-rendered career portals. SmartExtract executes a dual-phase extraction strategy:JSON-LD Schema Parsing: Inspects the rendered DOM for <script type="application/ld+json"> elements, parsing schema blocks matching @type: "JobPosting". It extracts canonical attributes including title, description, hiringOrganization.name, jobLocation.address.addressLocality, datePosted, and validThrough.Fallback DOM CSS Selector Parsing: When structured JSON-LD metadata is absent, SmartExtract evaluates pre-configured CSS selector chains (e.g., h1.job-title, div.job-description, .company-name) defined in domain site profiles to reconstruct structured job models from raw HTML nodes.src/applypilot/discovery/workday.pyThis module bypasses front-end browser rendering by directly querying the underlying REST APIs of Workday Candidate Experience Systems (CXS). Enterprise pharmaceutical companies deploying Workday expose standardized endpoints operating over HTTP POST requests. The engine dispatches structured JSON payloads containing pagination limits, offset parameters, search text, and location facets, directly receiving clean JSON payloads that contain internal requisition IDs, full job descriptions, posting timestamps, and application deep-links.src/applypilot/domains/pharmacy.pyThis domain orchestrator encapsulates pharmaceutical domain knowledge. The PharmacyEngine class manages configuration attributes including default_search_terms, default_locations, and domain-specific credential_fields (such as State Pharmacy Council registration numbers). It generates parameterized query tasks that are passed down to execution scrapers.Pipeline Data Flow and Transformation SequenceThe end-to-end data flow operates through four sequential stages:Parameter Matrix Construction: PharmacyEngine evaluates the target academic tier (D.Pharm, B.Pharm, M.Pharm) and generates a query matrix by combining tier-specific keywords (e.g., "Quality Control Analyst", "Dispensing Pharmacist") with target geographic hubs (e.g., "Hyderabad", "Baddi", "Ahmedabad").Concurrent Scraper Orchestration: The task matrix is dispatched across parallel workers:Aggregator tasks route to jobspy.py.Dynamic enterprise career pages route to smartextract.py.Enterprise Workday endpoints route to workday.py.Normalization & Tagging: Ingested job payloads pass through a normalization layer. Text fields are sanitized, dates are converted to ISO 8601 timestamps, and regular expression matchers scan job descriptions for mandatory qualifications, state council registration requirements, and walk-in interview indicators.Database Persistence & Deduplication: Normalized records are persisted into the local SQLite database. Deduplication is enforced at the database level using a unique composite index built on lower(company_name), lower(title), and lower(location).Qualification-Specific Role Mapping & Regulatory ProfilingIn the Indian pharmaceutical industry, candidate qualification tiers strictly dictate career entry points, functional departments, regulatory boundaries, and compensation benchmarks. Automated scrapers must partition search space parameters according to academic tier to ensure relevant job targeting.Academic Qualification TierPrimary Job Role TitlesKey Technical & Regulatory CompetenciesTarget CTC Range (Annual INR)Optimized Search Query StringMandatory Regulatory & Licensing PrerequisitesD.Pharm (Diploma)Retail Pharmacist, Community Pharmacist, Hospital Pharmacist, Medical Store Executive, Sales & MR Trainee, Dispensing AssistantPrescription interpretation, inventory management, POS billing, cold-chain maintenance, basic pharmacology, patient counseling₹1.8 LPA – ₹3.2 LPA"Retail Pharmacist" OR "Hospital Pharmacist" OR "Dispensing Assistant" OR "Medical Store Executive" OR "MR Trainee"State Pharmacy Council Pharmacist Registration License (Form 19/20/21 legal requirement)B.Pharm (Bachelor)QA Analyst, QC Analyst, Production Chemist, Regulatory Affairs Trainee, CRA-I, Pharmacovigilance Associate, Medical Writer, Drug Safety TraineecGMP, HPLC/GC operation, QMS (TrackWise), SOP authoring, PV databases (Argus Safety), MedDRA coding, IPD/OPD protocols₹2.8 LPA – ₹5.5 LPA"QA Chemist" OR "QC Analyst" OR "Production Chemist" OR "Pharmacovigilance Associate" OR "Drug Safety Trainee" OR "Junior CRA"State Pharmacy Council Registration (mandatory for hospital/retail, preferred for QA/QC plant roles)M.Pharm / Pharm.D (Master/Doctorate)F&D Scientist, R&D Chemist, Analytical Method Development (AMD), Bio-analytical Associate, Senior Regulatory Specialist, Clinical Data ManagerFormulation optimization, dissolution profiling, LC-MS/MS, ICH guidelines, eCTD dossier preparation, USFDA/EUGMP compliance, trial statistics₹4.5 LPA – ₹9.5 LPA"Formulation Scientist" OR "R&D Chemist" OR "Method Development" OR "Regulatory Affairs Executive" OR "Clinical Data Manager"State Pharmacy Council Registration (mandatory for Pharm.D clinical hospital roles)Regulatory and Operational Tier DistinctionsD.Pharm (Diploma in Pharmacy)Prepares candidates for healthcare distribution, hospital dispensaries, and retail operations. Under the Pharmacy Act of 1948 and the Drugs and Cosmetics Act of 1940, dispensing scheduled drugs requires a valid registration certificate issued by a State Pharmacy Council. Consequently, scrapers targeting D.Pharm roles must prioritize pharmacy chain portals, hospital recruitment boards, and retail vendor channels.B.Pharm (Bachelor of Pharmacy)Serves as the baseline qualification for industrial drug manufacturing, quality assurance, quality control, regulatory affairs, and entry-level clinical research. Job listings frequently stipulate familiarity with analytical instrumentation (e.g., High-Performance Liquid Chromatography - HPLC, Gas Chromatography - GC) or global manufacturing standards (cGMP, WHO-GMP, USFDA).M.Pharm & Pharm.D (Master of Pharmacy & Doctor of Pharmacy)Targets specialized research, formulation development, advanced pharmacovigilance, and clinical trial administration. Pharm.D candidates are specialized in clinical pharmacy, ward rounds, and adverse drug reaction (ADR) monitoring. Query configurations for this tier must incorporate specialized technical terms (e.g., "Analytical Method Development", "eCTD", "Argus Safety").Traditional Channel Expansion: Aggregators, Niche Portals, and Enterprise ATS PlatformsTo maximize coverage across standard channels, ApplyPilot requires concrete configurations for general job boards, niche pharmaceutical portals, and top-tier enterprise ATS platforms.Major Indian Aggregator PlatformsNaukri.comTarget Search URL: https://www.naukri.com/{keyword}-jobs-in-{location}?experience=0Internal REST API Endpoint: https://www.naukri.com/jobapi/v3/searchRequired HTTP Headers: appid: 109, systemid: Naukri, User-Agent: Mozilla/5.0...Query Payload Parameters: noOfResults=50, keyword={keyword}, location={location}, experience=0Indeed IndiaTarget Search URL: https://in.indeed.com/jobs?q={keyword}&l={location}&fromage=3Parameters: q (Search Query), l (Location), radius=25, sort=dateScraping Strategy: Requires headless execution via SmartExtract to bypass Cloudflare protection and execute client-side rendering.Foundit India (Formerly Monster)Target Search URL: https://www.foundit.in/srp/results?query={keyword}&locations={location}Internal REST Endpoint: https://www.foundit.in/nexus/v1/searchJSON POST Payload: {"query": "{keyword}", "locations": ["{location}"], "experienceRanges": [{"min": 0, "max": 1}]}Glassdoor IndiaTarget Search URL: https://www.glassdoor.co.in/Job/india-{keyword}-jobs-SRCH_IL.0,5_IN115_KO6,{length}.htmExtraction Pattern: Extract embedded Next.js JSON state hydration objects (__NEXT_DATA__) or parse schema <script type="application/ld+json"> elements.Internshala (Freshers & Entry-Level Roles)Target Search URL: https://internshala.com/jobs/keywords-{keyword}/DOM Selectors: Container: .individual_internship, Title: .job-title, Company: .company-name, Salary: .salarySpecialized Pharmaceutical Job PortalsNiche portals provide direct exposure to plant-level walk-in drives, contract openings, and regional hiring announcements that bypass major aggregators.Portal NameTarget URL Endpoint StructureExtraction MethodTarget DOM Selectors / API SchemaPharmaTutor[cite: 1, 2, 7, 12]https://www.pharmatutor.org/pharma-jobs/vacancies/d.pharm[cite: 2]https://www.pharmatutor.org/pharma-jobs/vacancies/m.pharm[cite: 7]DOM Node Extraction (SmartExtract)Container: div.views-row, article.node-teaserTitle: h2.node-title aBody: div.field-name-bodyDate: span.date-display-single[cite: 1, 2]PharmaStatehttps://pharmastate.com/jobsHTML ParsingContainer: .job-cardTitle: .job-titleCompany: .company-nameLocation: .job-locationPharmainfo.nethttps://www.pharmainfo.net/jobsDrupal Table ParserContainer: table.views-table trTitle Link: td.views-field-title aDate: td.views-field-createdPharmaJobsIndiahttps://www.pharmajobsindia.com/latest-jobsStatic HTML ParserContainer: div.job_listingTitle: h3.job_listing-titleLocation: div.job_listing-locationEnterprise ATS Systems for Top 20 Indian Pharmaceutical ManufacturersDirectly targeting enterprise ATS endpoints provides structured job data while bypassing public front-end rendering engines.Company NamePrimary Enterprise ATS SystemCareer Portal Endpoint / Direct API Request URLExtraction Strategy / Engine ModuleSun Pharma[cite: 8, 9, 13, 14]Workdayhttps://sunpharma.wd3.myworkdayjobs.com/wday/cxs/sunpharma/SunCareers/jobs[cite: 8, 9]workday.py REST API Payload (POST)Cipla[cite: 15]SAP SuccessFactorshttps://jobs.cipla.com/search/?q=&locationsearch=India[cite: 15]smartextract.py / SuccessFactors Job List ParserDr. Reddy'sWorkdayhttps://drreddys.wd3.myworkdayjobs.com/wday/cxs/drreddys/Careers/jobsworkday.py REST API Payload (POST)LupinSAP SuccessFactorshttps://jobs.lupin.com/search/?q=&locationsearch=Indiasmartextract.py JSON-LD ParserMankind PharmaDarwinboxhttps://mankindpharma.careers.darwinbox.in/jobsDarwinbox REST API (/api/v1/jobs)Torrent PharmaCustom Enterprisehttps://www.torrentpharma.com/index.php/site/info/careersPlaywright DOM EvaluatorZydus LifesciencesCustom Enterprisehttps://zyduslife.com/careers/smartextract.py DOM EvaluatorAlkem LaboratoriesDarwinboxhttps://alkemlabs.darwinbox.in/ms/candidate/careersDarwinbox REST Payload IngestionIntas PharmaCustom Enterprisehttps://www.intaspharma.com/careers/current-openings/HTML Table ExtractionBioconWorkdayhttps://biocon.wd3.myworkdayjobs.com/wday/cxs/biocon/Biocon_Careers/jobsworkday.py REST API Payload (POST)Pfizer IndiaWorkdayhttps://pfizer.wd1.myworkdayjobs.com/wday/cxs/pfizer/PfizerCareers/jobsworkday.py REST API Payload (POST)Abbott India[cite: 9]Workdayhttps://abbott.wd5.myworkdayjobs.com/wday/cxs/abbott/abbottcareers/jobsworkday.py REST API Payload (POST)Novartis IndiaWorkdayhttps://novartis.wd3.myworkdayjobs.com/wday/cxs/novartis/Novartis_Careers/jobsworkday.py REST API Payload (POST)GlenmarkSAP SuccessFactorshttps://jobs.glenmarkpharma.com/search/?q=&locationsearch=Indiasmartextract.py SuccessFactors ParserSanofi India[cite: 2]Workdayhttps://sanofi.wd3.myworkdayjobs.com/wday/cxs/sanofi/Sanofi_Careers/jobsworkday.py REST API Payload (POST)GSK IndiaWorkdayhttps://gsk.wd3.myworkdayjobs.com/wday/cxs/gsk/GSKCareers/jobsworkday.py REST API Payload (POST)Aurobindo Pharma[cite: 12, 14]Custom Enterprisehttps://www.aurobindo.com/careers/current-openings/[cite: 12]Playwright DOM EvaluatorIPCA Laboratories[cite: 2]Custom Enterprisehttps://www.ipca.com/careers/[cite: 2]Dynamic DOM Traversal EngineMacleods Pharma[cite: 2, 5, 16]Custom / Walk-In Portalhttps://www.macleodspharma.com/careers/[cite: 2, 5]Walk-In Notice Board ParserAjanta PharmaCustom Enterprisehttps://www.ajantapharma.com/careers.aspxHTML DOM Extraction EngineNon-Traditional Discovery Mechanisms & Unconventional IngestionA significant portion of entry-level pharmacy opportunities—particularly for D.Pharm dispensing, hospital clinical pharmacy, and government research fellowships—are published outside standard ATS platforms. Capturing these positions requires specialized, non-traditional scraping strategies.Retail Pharmacy Chains and Hospital NetworksRetail chains and hospital networks represent major employers for D.Pharm and B.Pharm graduates. These organizations frequently deploy proprietary store finder backends or custom career portals rather than standard ATS platforms.Apollo PharmacyCareer Portal URL: https://careers.apollopharmacy.app/job-career[cite: 3]Internal API Target: https://careers.apollopharmacy.app/api/getJobsRequest Method: HTTP POSTPayload Structure: {"state": "All", "city": "All", "designation": "Pharmacist", "page": 1}Extraction Protocol: Dispatch direct JSON requests to the API endpoint, parsing location arrays, designation strings, minimum qualifications, and job IDs.MedPlus Health ServicesCareer Portal URL: https://www.medplusindia.com/careersExtraction Method: Render via Playwright using smartextract.py. Target job card containers (.career-card), extracting store region, designation ("Pharmacist", "Pharmacy Trainee"), and contact details.Digital Health & Pharmacy Chains (PharmEasy, Tata 1mg, Netmeds, Wellness Forever)Strategy: These organizations frequently use modern developer-friendly ATS platforms (e.g., Lever, Greenhouse, Darwinbox).Lever API Pattern Example: https://api.lever.co/v0/postings/pharmeasy?mode=jsonHealthcare Hospital Chains (Apollo Hospitals, Fortis, Max Healthcare, Manipal, Narayana Health, Aster DM)Extraction Strategy: Scrape /careers or /join-us pages. Query for clinical pharmacy terms: "Hospital Pharmacist", "Clinical Pharmacist", "In-Patient Pharmacy Executive", "IPD/OPD Dispenser".Public Sector, Regulatory Bodies, and Research InstitutesGovernment and public sector vacancies offer competitive pay scales and stable career progression. These vacancies are typically published as static HTML notices or downloadable PDF circulars on official portals.Central Drugs Standard Control Organization (CDSCO)Notice Board Endpoint: https://cdsco.gov.in/opencms/opencms/en/Notifications/Vacancy/[cite: 4]Extraction Strategy: Extract <a> tags matching hrefs ending in .pdf within table rows where the title contains terms like "Drug Inspector", "Technical Data Associate", or "Scientific Officer".Indian Pharmacopoeia Commission (IPC)Notice Board Endpoint: https://ipc.gov.in/mandate/recruitment/vacancies.htmlExtraction Protocol: Parse recruitment tables using HTML selectors. Target positions such as "Pharmacovigilance Associate" and "Junior Scientific Officer".State Pharmacy Councils (e.g., MSPC, KSPC, TNPC)Notice Board Endpoint: Regional council portals post official circulars for registered pharmacists. Scrape notification tables for contractual hospital postings.ESIC & Railway Recruitment Boards (RRB)Target Endpoints: https://www.esic.gov.in/recruitment, regional RRB web portals.Query Strategy: Match notification titles against patterns like "Pharmacist Grade-III", "Homoeopathic Pharmacist", and "Ayurvedic Pharmacist".National Research Institutes (NIPER, ICMR, CSIR-CDRI, CSIR-IICT, CSIR-NCL)Target Endpoints:CSIR-CDRI: https://www.cdri.res.in[cite: 17]CSIR-NCL: https://www.ncl-india.org/files/JoinUs/JobVacancies.aspx[cite: 11]ICMR: https://www.icmr.gov.in/careericmr.html[cite: 7]PDF Ingestion & Processing Pipeline:Retrieve notice board HTML via HTTP client.Locate anchor tags matching .pdf file extensions linked to vacancy keywords (e.g., "JRF", "Project Associate", "Research Assistant").Stream the PDF binary into pdfplumber or PyPDF2.Run regular expressions to identify target roles, stipend amounts (e.g., "Rs. 31,000 + HRA"), interview dates, and qualifications (M.Pharm / GPAT required).Walk-In Drives & Social Media Signal ExtractionManufacturing plants in industrial hubs (such as Baddi, Sikkim, Visakhapatnam, Hyderabad, and Ahmedabad) frequently host walk-in interview drives advertised via image posters or social media announcements.LinkedIn Hashtag Scraping PipelineTarget Hashtag Feeds: #PharmaWalkIn, #BPharmFreshers, #QAPharmacyJobs, #PharmaHiring, #PharmaJobsExecution Protocol: Run Playwright scripts configured with persistent session state tokens.Text Extraction Regex Patterns:Interview Date: r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2})"Venue Address: r"(?:Venue|Location|Address)\s*:\s*(.*)"HR Contact Email: r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"Contract Research Organizations (CROs)CROs hire large cohorts of B.Pharm, M.Pharm, and Pharm.D graduates for clinical trial operations, data management, and pharmacovigilance.Target CRO Platforms: IQVIA, Parexel, ICON plc, Syneos Health, Labcorp, Clinetion.IQVIA Workday Endpoint: https://iqvia.wd1.myworkdayjobs.com/wday/cxs/iqvia/IQVIA/jobsParexel Career Search Endpoint: https://jobs.parexel.com/search-jobsTarget Query Strings: "Clinical Research Associate", "CRA Trainee", "Pharmacovigilance", "Clinical Data Manager", "Safety Data Associate".Technical Implementation BlueprintThis section provides the implementation files to update ApplyPilot's domain engine, target site configurations, and scraper collection tools.Python Domain Implementation (src/applypilot/domains/pharmacy.py)Python"""
PharmacyEngine Domain Module for ApplyPilot.
Manages search terms, qualification tier routing, location contexts,
and scraping tasks for the Indian pharmaceutical job market.
"""

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class PharmacyEngine:
    """
    Domain orchestrator for pharmaceutical job discovery in India.
    Handles academic tier mappings, term expansion, council registration flags,
    and search task generation across multi-channel scrapers.
    """

    # Qualification Tier Term Mappings
    TIER_KEYWORD_MAP: Dict[str, List[str]] = {
        "D_PHARM": [
            "Retail Pharmacist",
            "Community Pharmacist",
            "Hospital Pharmacist",
            "Medical Store Executive",
            "Medical Representative Trainee",
            "Dispensing Assistant",
            "Pharmacy Assistant",
            "Chemist Store Staff"
        ],
        "B_PHARM": [
            "QA Analyst",
            "QC Chemist",
            "Production Chemist",
            "Regulatory Affairs Trainee",
            "Clinical Research Associate",
            "Pharmacovigilance Associate",
            "Medical Writer",
            "Drug Safety Trainee",
            "Quality Assurance Executive",
            "Quality Control Executive",
            "Pharma Production Officer"
        ],
        "M_PHARM_PHARMD": [
            "Formulation Development Scientist",
            "F&D Scientist",
            "R&D Chemist",
            "Analytical Method Development Chemist",
            "AMD Scientist",
            "Bioanalytical Research Associate",
            "Senior Regulatory Affairs Specialist",
            "Clinical Data Manager",
            "Medical Affairs Associate",
            "PharmD Clinical Pharmacist"
        ]
    }

    # Primary Industrial & Healthcare Hubs in India
    DEFAULT_LOCATIONS: List[str] = [
        "Hyderabad",
        "Bengaluru",
        "Ahmedabad",
        "Mumbai",
        "Pune",
        "Baddi",
        "Visakhapatnam",
        "Chennai",
        "Sikkim",
        "Indore",
        "Delhi NCR"
    ]

    # Required Credentials and Licensures
    CREDENTIAL_FIELDS: Dict[str, Any] = {
        "requires_council_registration": True,
        "council_name_field": "state_pharmacy_council_name",
        "registration_number_field": "pharmacist_registration_no",
        "degree_verification_field": "qualification_tier"
    }

    def __init__(self, target_tiers: Optional[List[str]] = None, locations: Optional[List[str]] = None):
        """
        Initialize the PharmacyEngine.

        :param target_tiers: List of tiers ('D_PHARM', 'B_PHARM', 'M_PHARM_PHARMD')
        :param locations: List of target locations in India
        """
        self.target_tiers = target_tiers or ["D_PHARM", "B_PHARM", "M_PHARM_PHARMD"]
        self.locations = locations or self.DEFAULT_LOCATIONS
        logger.info("Initialized PharmacyEngine for tiers: %s", self.target_tiers)

    def get_search_terms_for_tier(self, tier: str) -> List[str]:
        """Returns the keyword list for a specific academic tier."""
        tier_key = tier.upper()
        return self.TIER_KEYWORD_MAP.get(tier_key, [])

    def get_all_search_terms(self) -> List[str]:
        """Flattens and returns all search keywords across selected tiers."""
        terms = []
        for tier in self.target_tiers:
            terms.extend(self.get_search_terms_for_tier(tier))
        return list(set(terms))

    def generate_search_matrix(self) -> List[Dict[str, str]]:
        """
        Generates search tasks combining keywords, academic tiers,
        and geographic locations for the scraping orchestration layer.
        """
        tasks = []
        for tier in self.target_tiers:
            keywords = self.get_search_terms_for_tier(tier)
            for kw in keywords:
                for loc in self.locations:
                    tasks.append({
                        "domain": "pharmacy",
                        "qualification_tier": tier,
                        "keyword": kw,
                        "location": loc,
                        "country": "India"
                    })
        logger.info("Generated %d search tasks across %d locations.", len(tasks), len(self.locations))
        return tasks

    @staticmethod
    def enrich_job_record(raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriches a raw job record with pharmaceutical-specific flags,
        such as state pharmacy council registration requirements.
        """
        description = raw_record.get("description", "")
        title = raw_record.get("title", "")
        combined_text = f"{title} {description}"

        # Regular expression rules for council registration detection
        council_regex = re.compile(
            r"(state pharmacy council|registered pharmacist|pharmacy council registration|pci registered|registration certificate)",
            re.IGNORECASE
        )
        
        # Regular expression rules for walk-in interview detection
        walkin_regex = re.compile(
            r"(walk-in|walk in interview|interview drive|campus drive)",
            re.IGNORECASE
        )

        raw_record["requires_council_registration"] = bool(council_regex.search(combined_text))
        raw_record["is_walkin_drive"] = bool(walkin_regex.search(combined_text))
        raw_record["domain_category"] = "Pharmaceuticals"

        return raw_record
Site Target Configuration Additions (sites.yaml)YAMLpharmacy_targets:
  niche_portals:
    - name: "PharmaTutor"
      enabled: true
      base_url: "https://www.pharmatutor.org"
      type: "html_dom"
      endpoints:
        - path: "/pharma-jobs/vacancies"
          tier: "ALL"
        - path: "/pharma-jobs/vacancies/d.pharm"
          tier: "D_PHARM"
        - path: "/pharma-jobs/vacancies/m.pharm"
          tier: "M_PHARM_PHARMD"
      selectors:
        item_container: "div.views-row, article.node-teaser"
        title: "h2.node-title a"
        url: "h2.node-title a"
        description_snippet: "div.field-name-body"
        posted_date: "span.date-display-single"

    - name: "ApolloPharmacyCareers"
      enabled: true
      base_url: "https://careers.apollopharmacy.app"
      type: "json_api"
      api_endpoint: "https://careers.apollopharmacy.app/api/getJobs"
      method: "POST"
      payload_template:
        state: "All"
        city: "All"
        designation: "Pharmacist"
        page: 1

  corporate_workday_endpoints:
    - company: "SunPharma"
      cxs_url: "https://sunpharma.wd3.myworkdayjobs.com/wday/cxs/sunpharma/SunCareers/jobs"
      enabled: true
    - company: "DrReddys"
      cxs_url: "https://drreddys.wd3.myworkdayjobs.com/wday/cxs/drreddys/Careers/jobs"
      enabled: true
    - company: "Biocon"
      cxs_url: "https://biocon.wd3.myworkdayjobs.com/wday/cxs/biocon/Biocon_Careers/jobs"
      enabled: true
    - company: "AbbottIndia"
      cxs_url: "https://abbott.wd5.myworkdayjobs.com/wday/cxs/abbott/abbottcareers/jobs"
      enabled: true
Specialized Scraper Module (src/applypilot/discovery/pharmatutor_scraper.py)Python"""
Playwright Scraper for PharmaTutor Job Vacancies & Walk-In Drives.
"""

import asyncio
import logging
from typing import Dict, List, Any
from playwright.async_api import async_playwright, Browser, Page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pharmatutor_scraper")

PHARMATUTOR_URL = "https://www.pharmatutor.org/pharma-jobs/vacancies"

async def extract_pharmatutor_vacancies(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Scrapes job postings and walk-in notices from PharmaTutor using Playwright.
    """
    scraped_jobs: List[Dict[str, Any]] = []

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page: Page = await context.new_page()

        logger.info("Navigating to %s", PHARMATUTOR_URL)
        try:
            await page.goto(PHARMATUTOR_URL, wait_until="domcontentloaded", timeout=30000)
            
            # Locate all vacancy nodes
            job_nodes = await page.query_selector_all("div.views-row, article.node-teaser")
            logger.info("Found %d job nodes on page.", len(job_nodes))

            for node in job_nodes[:limit]:
                # Extract title and link
                title_elem = await node.query_selector("h2.node-title a, h2 a")
                if not title_elem:
                    continue

                title_text = (await title_elem.inner_text()).strip()
                href = await title_elem.get_attribute("href")
                full_url = f"https://www.pharmatutor.org{href}" if href and href.startswith("/") else href

                # Extract snippet text
                body_elem = await node.query_selector("div.field-name-body, div.content")
                body_text = (await body_elem.inner_text()).strip() if body_elem else ""

                # Extract posted date
                date_elem = await node.query_selector("span.date-display-single, time")
                date_text = (await date_elem.inner_text()).strip() if date_elem else "N/A"

                # Infer qualification tiers from title and body text
                combined = f"{title_text} {body_text}".upper()
                tiers = []
                if "D.PHARM" in combined or "D.PHARMA" in combined or "DIP.PHARM" in combined:
                    tiers.append("D_PHARM")
                if "B.PHARM" in combined or "B.PHARMA" in combined or "BACHELOR OF PHARMACY" in combined:
                    tiers.append("B_PHARM")
                if "M.PHARM" in combined or "M.PHARMA" in combined or "PHARM.D" in combined:
                    tiers.append("M_PHARM_PHARMD")
                if not tiers:
                    tiers.append("GENERAL_PHARMA")

                record = {
                    "title": title_text,
                    "url": full_url,
                    "company_name": "PharmaTutor Sourced",
                    "snippet": body_text[:300],
                    "posted_date": date_text,
                    "detected_tiers": tiers,
                    "source": "PharmaTutor"
                }
                scraped_jobs.append(record)

        except Exception as e:
            logger.error("Error occurred while scraping PharmaTutor: %s", str(e))
        finally:
            await browser.close()

    return scraped_jobs

if __name__ == "__main__":
    results = asyncio.run(extract_pharmatutor_vacancies(limit=10))
    print(f"Successfully scraped {len(results)} jobs.")
    for idx, job in enumerate(results, 1):
        print(f"\n[{idx}] {job['title']}")
        print(f"    URL: {job['url']}")
        print(f"    Tiers: {job['detected_tiers']}")
        print(f"    Date: {job['posted_date']}")
Conclusion & Operational Execution StandardsTo maintain pipeline reliability across high-frequency pharmaceutical discovery channels, deployment operations should follow established execution guidelines:Staggered Execution Schedules: Direct JSON REST queries to enterprise Workday endpoints should run on 12-hour intervals. HTML DOM scraping of niche portals should execute on 24-hour cycles to prevent IP throttling. Government notice boards and public institute PDF circulars should be queried once daily during business hours.Session Persistence and Header Diversification: Requests routed to social feeds or job aggregators must maintain dynamic user-agent rotation and persist cookies across sessions to handle anti-bot verification challenges.Database Optimization: SQLite indexing should be maintained across (domain_category, qualification_tier, location) to allow fast querying by front-end services. De-duplication using SHA-256 hashes generated from company_name + title + location ensures dataset integrity across multi-channel aggregators.
