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
