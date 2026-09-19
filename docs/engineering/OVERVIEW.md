# 💻 Engineering & Tech Engine Architecture (`docs/engineering/OVERVIEW.md`)

The `EngineeringEngine` (`src/applypilot/domains/engineering.py`) manages job discovery, fit evaluation, resume tailoring, and auto-applications for Software Engineering, Data Science, DevOps, AI/ML, and Technical roles.

---

## 🎯 1. Engineering Role Taxonomy

- **Entry-Level & Fresher**: `Software Engineer Intern`, `Graduate Engineer Trainee (GET)`, `Associate Software Engineer`, `Junior Software Engineer`, `SDE 1`, `Trainee Software Engineer`, `Fresher Developer`, `Off Campus Fresher`
- **Backend & Core**: `Software Engineer`, `Software Developer`, `Python Developer`, `Java Developer`, `Go Developer`, `Node.js Developer`, `.NET Developer`, `C++ Developer`
- **Frontend & Full Stack**: `Frontend Developer`, `React Developer`, `Full Stack Developer`, `Web Developer`
- **Automotive & Embedded (Pune/MH Specialty)**: `Embedded Software Engineer`, `Firmware Engineer`, `IoT Engineer`, `Systems Engineer`, `Programmer Analyst`
- **Infrastructure & Cloud**: `DevOps Engineer`, `Site Reliability Engineer (SRE)`, `Cloud Engineer (AWS/GCP/Azure)`
- **Data & AI**: `Data Engineer`, `Data Scientist`, `Data Analyst`, `Machine Learning Engineer`, `AI Engineer`
- **Quality & Testing**: `Software QA Engineer`, `Automation QA Engineer`, `SDET`

---

## 📍 2. Maharashtra Tech Hubs & IT Clusters

- **Pune** (Maharashtra) — Hinjawadi Phase 1-3, EON Kharadi, Magarpatta Cybercity, Baner, Viman Nagar
- **Mumbai** — Bandra-Kurla Complex (BKC), Andheri, Powai Tech Corridor, Goregaon
- **Navi Mumbai** — Mahape Millennium Business Park, Airoli Mindspace, Vashi
- **Thane** — Wagle Estate IT Park, Ghodbunder Road
- **Nagpur** — MIHAN SEZ Tech Hub (Infosys, TCS, HCLTech)
- **Nashik** — Ambad MIDC & IT Parks
- **Aurangabad (Chhatrapati Sambhajinagar)** — Shendra MIDC IT Zone
- **Kolhapur** — IT Park & Regional Tech Units
- **Pimpri-Chinchwad** — Bhosari & Nigdi Automotive Software Hubs
- **Remote India / Maharashtra** — Distributed Remote Engineering Teams

---

## 🏢 3. Workday GCC Tech Employers

17 Corporate Workday career endpoints tagged for direct CXS JSON scraping:
- Mastercard, NVIDIA, Barclays, ServiceNow, Salesforce, PayPal, Cisco, Intel, Adobe, Motorola Solutions, Thomson Reuters, DocuSign, Uber, PwC, BDO, TELUS International.

---

## 📊 4. Baseline Tech Job Pool (Maharashtra Discovery Sweep)

- **Total Verified Tech Jobs**: **8,484** (Pure scraping, zero AI scoring run).
- **Deduplicated Cross-Postings**: **26,267 duplicate postings** unified across platforms.
- **Sources / Platforms**:
  - **LinkedIn India**: 5,518 jobs (65.0%)
  - **Indeed India**: 2,720 jobs (32.1%)
  - **Workday Direct Corporate GCCs**: 246 jobs (Mastercard: 139, PwC: 66, NVIDIA: 28, Adobe: 6, Cisco: 5, Salesforce: 2)
- **Top Hiring Employers**:
  - Accenture in India (1,268+ jobs), Mastercard (232), Citi (201), Persistent Systems (176), Wipro (134), Sourceo (116), Siemens (81), EY (76), PwC (70), NVIDIA (66), Deloitte (64), Birlasoft (61), Vertiv (58), Barclays (56), TCS (52), BNY (50), JPMorganChase (49), UST (49).
- **Geographic Distribution**:
  - **Pune Region (Hinjawadi, Kharadi, Magarpatta, Baner)**: ~3,000+ jobs
  - **Mumbai Metropolitan Region (BKC, Andheri, Powai, Navi Mumbai, Thane)**: ~1,500+ jobs
  - **Nagpur (MIHAN SEZ)**: 111 jobs
  - **Nashik (Ambad MIDC)**: 45 jobs
  - **Aurangabad / Kolhapur**: Emerging regional hubs
  - **Remote MH / India**: ~400+ distributed roles
- **Location Hygiene**: 100% verified Maharashtra / India tech roles with 0 foreign leakage.

---

## 🛡️ 5. Experience Classification & Canonical Deduplication System

The tech engine includes an ultra-fast, deterministic rule-based engine in [`src/applypilot/discovery/classifier.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/discovery/classifier.py):

### 5.1 Experience Tiers & Zero Data Loss
Jobs are tagged at ingestion without deleting any senior postings from SQLite:
- `fresher` (🟢 0-1 YOE, Intern, Trainee, GET, College Graduate): `is_fresher_eligible = 1`
- `likely_fresher` (🟢 1-2 YOE, Junior Developer): `is_fresher_eligible = 1`
- `open_entry` (🔵 Standard SDE without senior blockers or high YOE requirements): `is_fresher_eligible = 1` (Benefit of the doubt)
- `senior_lead` (🔴 3+ to 12+ YOE, Senior, Lead, Principal, Architect, Manager): `is_fresher_eligible = 0`

### 5.2 The "Fresher Immunity Shield" (Fresher Trumps Senior)
Fresher and trainee indicators (`intern`, `trainee`, `graduate`, `get`, `0-1 yrs exp`, `freshers can apply`) strictly override senior keywords, guaranteeing **0.0% False Negatives** on student opportunities even if senior roles/teams are mentioned in the description.

### 5.3 Canonical Deduplication
Collapses cross-platform and repetitive listings into single representative parent cards:
- Cluster key: `sha256(normalize_company + "___" + normalize_title)[:16]`
- Sibling listings link to `canonical_job_url` with `is_canonical = 0`.
- Canonical parent maintains `duplicate_count` (e.g. 569 Accenture "Custom Software Engineer" postings collapse into 1 card with `duplicate_count = 569`).

### 5.4 Migration & Real-Time Hooks
- **Backfill Script**: [`scripts/classify_and_cluster_tech_jobs.py`](file:///home/soham/coding/proj/MyApplyPilot/scripts/classify_and_cluster_tech_jobs.py) backfills existing jobs in SQLite in under 5 seconds.
- **Ingestion Hooks**: Scrapers (`JobSpy`, `Naukri`, `Workday`, `SmartExtract`) automatically classify and canonically cluster incoming jobs on the fly via `classify_and_insert_job()`.
