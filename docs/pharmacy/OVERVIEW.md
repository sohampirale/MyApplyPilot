# 💊 Pharmacy & Lifesciences Engine Architecture (`docs/pharmacy/OVERVIEW.md`)

ApplyPilot provides 100% isolated job discovery, AI fit scoring, resume tailoring, and auto-application submission for Pharmacy, Lifesciences, and Pharmaceutical Sciences candidates (B.Pharm, M.Pharm, Pharm.D, Ph.D, D.Pharm).

---

## 🎯 1. Pharmacy Role Taxonomy (51 Search Categories)

The `PharmacyEngine` (`src/applypilot/domains/pharmacy.py`) defines 51 specialized search terms across 3 main tiers:

### Tier 1: Core Quality, Production & Dispensing (High Volume)
- **Dispensing & Clinical**: `Pharmacist`, `Junior Pharmacist`, `Hospital Pharmacist`, `Clinical Pharmacist`, `Retail Pharmacist`
- **Quality Control (QC)**: `Quality Control Officer`, `QC Analyst`, `QC Executive`, `QC Chemist`
- **Quality Assurance (QA)**: `Quality Assurance Officer`, `QA Executive`, `QA Chemist`, `IPQA Officer`
- **Production & Manufacturing**: `Production Executive`, `Production Officer`, `Manufacturing Officer`
- **Regulatory Affairs (RA)**: `Regulatory Affairs Executive`, `Regulatory Affairs Officer`, `RA Officer`
- **Clinical Research**: `Clinical Research Associate`, `CRA`, `Clinical Trial Assistant`

### Tier 2: R&D, Clinical & Scientific Roles (M.Pharm / Pharm.D / Ph.D)
- **Formulation**: `Formulation Development Scientist`, `F&D Executive`, `F&D Scientist`
- **Analytical Method**: `Analytical Method Development`, `ADL Scientist`, `ADL Executive`
- **Pharmacovigilance**: `Pharmacovigilance Associate`, `PV Officer`, `Drug Safety Associate`, `Drug Safety Physician`
- **Clinical Data**: `Clinical Data Manager`, `CDM Associate`
- **Scientific Writing**: `Medical Writer`, `Scientific Writer`, `Medical Information Specialist`
- **Regulatory Submissions**: `Regulatory Documentation Specialist`, `eCTD Specialist`, `DMF Writer`

### Tier 3: Sales, Marketing, Trainee & Allied Roles (D.Pharm / B.Pharm / Fresher)
- **Medical Sales**: `Medical Representative`, `MR`, `Pharma Sales Executive`, `Territory Manager Pharma`
- **Product Management**: `Product Executive`, `Product Manager Pharma`
- **Trainees**: `Pharma Trainee`, `Pharmacy Apprentice`, `Graduate Trainee Pharma`
- **Allied**: `Medical Coder`, `Pharma Data Analyst`, `Biostatistician`, `Medical Science Liaison (MSL)`

---

## 📍 2. Pan-India Pharma Clusters (16 Target Regions)

1. **Hyderabad / Genome Valley** (Telangana) — Bulk drugs, CROs, Formulations
2. **Bengaluru** (Karnataka) — Biopharma, Clinical Data, Medical Coding
3. **Mumbai / Thane / Navi Mumbai** (Maharashtra) — HQ Corporate, Global Regulatory
4. **Pune / Kurkumbh / Pimpri** (Maharashtra) — Vaccines, Biotech, Manufacturing
5. **Ahmedabad / Changodar / Sanand** (Gujarat) — Formulations, QC Labs
6. **Vadodara / Ankleshwar / Vapi** (Gujarat) — Active Pharmaceutical Ingredients (APIs)
7. **Baddi / Solan / Paonta Sahib** (Himachal Pradesh) — Formulation Manufacturing Hub
8. **Visakhapatnam / Jawaharlal Nehru Pharma City** (Andhra Pradesh) — APIs & Bulk Pharma
9. **Chennai** (Tamil Nadu) — Healthcare, Clinical Operations
10. **Goa** (Verna Industrial Estate) — Export Manufacturing Facilities
11. **Indore / Pithampur** (Madhya Pradesh) — SEZ Manufacturing
12. **Jaipur** (Rajasthan) — Academic & Retail Pharmacy
13. **Delhi / NCR (Gurugram / Noida)** — Regulatory Affairs & Medical Affairs HQ
14. **Kolkata** (West Bengal) — Regional Distribution & Clinical Trials
15. **Chandigarh / Mohali** — Biopharma & R&D
16. **Remote India** — Medical Writing, Clinical Data Management, Regulatory Publishing

---

## 🛡️ 3. Strict Domain Auto-Sanitization (`is_pharmacy_title`)

To prevent non-pharma corporate postings (e.g. `.Net Software Architect`, `DevOps Engineer`, `Bankkaufmann`, `HR Business Partner`) from polluting the Pharmacy job pool when scraping corporate MNC portals (IQVIA, Lonza, Medtronic):

- **Validator Implementation**: `is_pharmacy_title(title: str)` in [`src/applypilot/domains/pharmacy.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/domains/pharmacy.py).
- **Database Guard**: `store_jobs()` in [`src/applypilot/database.py`](file:///home/soham/coding/proj/MyApplyPilot/src/applypilot/database.py) validates every incoming title.
- **Rule**: If a scraped job title contains non-pharma tech/corporate keywords, it is automatically re-classified to the `engineering` pool behind the scenes!

---

## 📜 4. Pharmacy Candidate Profile Credentials

Pharmacy profiles contain specialized credential fields in `profile.json`:
- `pci_registration`: Pharmacy Council of India (PCI) State Registration Number
- `lab_equipment`: Lab equipment proficiency (`HPLC`, `GC`, `LC-MS`, `UV-Vis`, `Dissolution Tester`)
- `gmp_knowledge`: Good Manufacturing Practice (cGMP), WHO-GMP, US-FDA regulatory compliance
- `researchgate_url`: Academic research profile / Google Scholar URL
