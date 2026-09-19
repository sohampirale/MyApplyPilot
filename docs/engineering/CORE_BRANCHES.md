# ⚙️ Core Engineering Engines & Industrial Architecture (`docs/engineering/CORE_BRANCHES.md`)

Maharashtra is India's preeminent manufacturing, automotive, and infrastructure hub. ApplyPilot provides dedicated, isolated domain engines for all major non-software engineering disciplines.

---

## 🏛️ 1. Core Engineering Domain Taxonomy

### ⚙️ Mechanical & Automobile Engineering (`MechanicalEngine` — `domain = 'mechanical'`)
- **Module**: [`src/applypilot/domains/mechanical.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/domains/mechanical.py)
- **Role Categories**:
  - *Fresher & Entry*: `Graduate Engineer Trainee Mechanical`, `GET Mechanical`, `Trainee Mechanical Engineer`, `Junior Mechanical Engineer`, `Mechanical Engineer Fresher`
  - *Design & Simulation*: `Mechanical Design Engineer`, `CAD Engineer`, `SolidWorks Engineer`, `CATIA Designer`, `Creo Engineer`, `FEA Analyst`, `CFD Engineer`, `Ansys Engineer`, `Product Design Engineer`, `Tool Design Engineer`
  - *Manufacturing & Production*: `Production Engineer`, `Manufacturing Engineer`, `Process Engineer Mechanical`, `CNC Programmer`, `CAM Engineer`, `Piping Design Engineer`
  - *Quality & Maintenance*: `Mechanical QC Engineer`, `Quality Assurance Mechanical`, `Plant Maintenance Engineer`, `Preventive Maintenance Engineer`, `HVAC Engineer`, `Thermal Engineer`
  - *Automotive & EV*: `Automotive Engineer`, `Chassis Design Engineer`, `Powertrain Engineer`, `EV Mechanical Engineer`, `Battery Pack Design Engineer`
- **Key Clusters**: Pune (Chakan, Bhosari, Talegaon, Pimpri-Chinchwad), Aurangabad (Waluj), Nashik (Ambad), Kolhapur (Gokul Shirgaon).

### 🏗️ Civil & Infrastructure Engineering (`CivilEngine` — `domain = 'civil'`)
- **Module**: [`src/applypilot/domains/civil.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/domains/civil.py)
- **Role Categories**:
  - *Fresher & Entry*: `Graduate Engineer Trainee Civil`, `GET Civil`, `Junior Civil Engineer`, `Civil Site Engineer Fresher`, `Civil Engineering Trainee`
  - *Site & Execution*: `Civil Site Engineer`, `Construction Site Engineer`, `Project Engineer Civil`, `Site Execution Engineer`, `Finishing Engineer`, `Civil QC Engineer`
  - *Structural & Design*: `Structural Design Engineer`, `Structural Engineer`, `STAAD.Pro Engineer`, `ETABS Designer`, `Steel Structure Engineer`, `RCC Design Engineer`, `Bridge Engineer`
  - *Surveying & Estimation*: `Quantity Surveyor (QS)`, `Civil Billing Engineer`, `Estimation & Costing Engineer`, `Land Surveyor`
  - *BIM & Digital Twin*: `BIM Modeler Civil`, `BIM Civil Engineer`, `Revit Civil Designer`, `Civil CAD Drafter`
  - *Infra*: `Highway Engineer`, `Geotechnical Engineer`, `Water Supply Engineer`
- **Key Clusters**: Mumbai Metropolitan Region (Coastal Road, Metro lines), Navi Mumbai (Airport, CIDCO), Pune (PMRDA/PMC), Thane.

### ⚡ Electrical & Electronics Engineering (`ElectricalEngine` — `domain = 'electrical'`)
- **Module**: [`src/applypilot/domains/electrical.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/domains/electrical.py)
- **Role Categories**:
  - *Fresher & Entry*: `Graduate Engineer Trainee Electrical`, `GET Electrical`, `Junior Electrical Engineer`, `Electrical Engineering Trainee`
  - *Power & High Voltage*: `Electrical Design Engineer`, `Substation Engineer`, `Switchgear Engineer`, `Power Systems Engineer`, `High Voltage Engineer`, `Testing and Commissioning Engineer`, `Electrical Maintenance Engineer`
  - *Industrial Automation*: `PLC Programmer`, `SCADA Engineer`, `Automation Engineer Electrical`, `DCS Engineer`, `Instrumentation & Control Engineer`, `Panel Design Engineer`
  - *Hardware & Electronics*: `Embedded Hardware Engineer`, `Hardware Design Engineer`, `PCB Layout Engineer`, `Altium Designer`, `Power Electronics Engineer`
- **Key Clusters**: Pune (Ranjangaon Electronics SEZ, Chakan), Navi Mumbai (Rabale, Mahape), Nashik.

### 🧪 Chemical & Process Engineering (`ChemicalEngine` — `domain = 'chemical'`)
- **Module**: [`src/applypilot/domains/chemical.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/domains/chemical.py)
- **Role Categories**:
  - *Fresher & Entry*: `Graduate Engineer Trainee Chemical`, `GET Chemical`, `Junior Chemical Engineer`, `Chemical Engineering Trainee`
  - *Process & Design*: `Chemical Process Engineer`, `Process Design Engineer`, `Process Safety Engineer`, `HAZOP Engineer`, `Plant Operations Engineer`
  - *Specialty & Treatment*: `Petrochemical Engineer`, `Polymer Engineer`, `Paints & Coatings Chemist`, `Water Treatment Engineer`, `ETP Plant Engineer`
  - *Production & Control*: `Chemical Production Engineer`, `Process Control Engineer`, `DCS Operator Chemical`
- **Key Clusters**: Tarapur MIDC (Palghar), Taloja MIDC, Roha & Mahad MIDC, Patalganga, Rasayani, Dombivli.

---

## 🌐 2. Dedicated Naukri India Playwright Stealth Scraper

While tech startups hire on LinkedIn, **core engineering in India has 70%+ volume on Naukri India**. ApplyPilot features a dedicated Playwright scraper:
- **Module**: [`src/applypilot/discovery/naukri.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/discovery/naukri.py)
- **Stealth Architecture**: Chrome 122 user-agent and client hints, headless browser detection neutralization via `apply_playwright_stealth`.
- **Field Extraction**: Extracts job title, company, location, experience range (e.g. `0 Yrs` for freshers), salary in LPA (e.g. `4.5 - 6.5 Lacs PA`), skills tags, and direct job URLs.

---

## 📊 3. Baseline Discovery Results: Mechanical & Automobile Engineering

The first automated sweep across Maharashtra industrial hubs completed with **0 errors**:
- **Total Verified Mechanical Jobs**: **972** (stored under `domain = 'mechanical'`, 0 AI scoring run).
- **Source Breakdown**:
  - **LinkedIn India**: 506 jobs (52.1%)
  - **Naukri India Stealth**: 466 jobs (47.9%)
- **Top Hiring Companies**:
  - WSP in India (18), Vertiv (17), Eaton (15), Reliance Industries (14), Honeywell (12), Burns & McDonnell (11), Jacobs (10), Emerson (10), Capgemini Engineering (10), Valeo (9), Siemens (9).
- **Top Job Roles**:
  - Production Engineer (34), Mechanical Engineer (21), Mechanical Design Engineer (18), Design Engineer (17), CAD Engineer (9), Plant Maintenance Engineer (8), QC / Quality Inspector (16).
- **Geographic Clusters**:
  - Pune & Pimpri-Chinchwad (including Chakan, Bhosari, Talegaon): ~450+ jobs
  - Mumbai MMR & Navi Mumbai: ~200+ jobs
  - Nashik (Ambad/Satpur MIDC): 86 jobs
  - Aurangabad (Waluj MIDC): Regional auto suppliers
  - Kolhapur (Gokul Shirgaon): Foundries & fabrication units

---

## 📊 4. Baseline Discovery Results: Civil & Infrastructure Engineering

The second automated sweep across Maharashtra infrastructure corridors completed with **0 errors**:
- **Total Verified Civil Jobs**: **754** (stored under `domain = 'civil'`, 0 AI scoring run).
- **Source Breakdown**:
  - **Naukri India Stealth**: 467 jobs (61.9%)
  - **LinkedIn India**: 287 jobs (38.1%)
- **Top Hiring Companies**:
  - WSP in India (27), Larsen & Toubro (15), Worley (9), Jacobs (9), AtkinsRéalis (9), Veradigm (7), Techture (7), SSOE Group (7), Vertiv (6).
- **Top Job Roles**:
  - Civil Engineer (60), Structural Design Engineer (23), Quantity Surveyor (19), Civil Site Engineer (16), Project Manager/Engineer (19), Site Supervisor/Engineer (18), Civil Billing Engineer (7), BIM Civil Engineer.
- **Geographic Clusters**:
  - Mumbai MMR (Mumbai, Navi Mumbai, Thane): ~350+ jobs (Coastal Road, Metro, redevelopment)
  - Pune & PMRDA: ~200+ jobs
  - Nashik: 47 jobs
  - Nagpur (Metro & Samruddhi): 43 jobs

---

## 📊 5. Baseline Discovery Results: Electrical, Electronics & Automation Engineering

The third automated sweep across Maharashtra electrical, power, and automation hubs completed with **0 errors**:
- **Total Verified Electrical Jobs**: **605** (stored under `domain = 'electrical'`, 0 AI scoring run).
- **Source Breakdown**:
  - **Naukri India Stealth**: 476 jobs (78.7%)
  - **LinkedIn India**: 129 jobs (21.3%)
- **Top Hiring Companies**:
  - Jacobs (12), Vertiv Energy (10), Honeywell Technologies (10), Black & Veatch (7), Tata AutoComp (6), Schneider Electric (6), Hitachi Energy (6), Siemens (5), ABB (5), NXP Semiconductors (5), Neilsoft (4), Rhythmsoft Robotics Automation (4).
- **Top Job Roles**:
  - Electrical Engineer (82), Electrical Design Engineer (38), PLC Programmer (28), Substation Engineer (22), Switchgear Engineer (16), SCADA Engineer (15), Embedded Hardware Engineer (12), Graduate Engineer Trainee Electrical (18).
- **Geographic Clusters**:
  - Pune (Pune District, Ranjangaon Electronics Zone, Chakan, Hinjawadi): 140+ jobs
  - Mumbai MMR (Mumbai, Navi Mumbai, Thane): 150+ jobs
  - Nashik (Ambad MIDC electrical OEMs): 54 jobs
  - Aurangabad (Chhatrapati Sambhajinagar): 12+ jobs
