# 🏢 Pharmacy Employers & Scrape Targets (`docs/pharmacy/EMPLOYERS_AND_TARGETS.md`)

ApplyPilot monitors 13 global pharmaceutical corporate career portals via direct Workday APIs, plus dedicated Indian pharmaceutical job portals via Playwright SmartExtract.

---

## 🏛️ 1. Workday Corporate Pharma Tenants (`config/employers.yaml`)

The following Workday corporate tenants are registered under `domain: "pharmacy"`:

| Employer Key | Company Name | Workday Tenant URL | Specialization |
| :--- | :--- | :--- | :--- |
| `iqvia` | IQVIA | `https://iqvia.wd1.myworkdayjobs.com/IQVIA` | Clinical Data, CRO, MSL, CRA |
| `lonza` | Lonza | `https://lonza.wd3.myworkdayjobs.com/Lonza_Careers` | Biopharma Manufacturing, QC, QA |
| `medtronic` | Medtronic | `https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers` | Medical Devices, Regulatory |
| `novartis` | Novartis India | `https://novartis.wd3.myworkdayjobs.com/Novartis` | Formulations, R&D, Clinical |
| `pfizer` | Pfizer India | `https://pfizer.wd1.myworkdayjobs.com/PfizerCareers` | Quality Assurance, Sterile Injections |
| `abbott` | Abbott India | `https://abbott.wd5.myworkdayjobs.com/abbottcareers` | Diagnostic, Nutrition, Pharma |
| `astrazeneca` | AstraZeneca India | `https://astrazeneca.wd3.myworkdayjobs.com/Careers` | Oncology, Cardiovascular, PV |
| `roche` | Roche | `https://roche.wd3.myworkdayjobs.com/roche_careers` | Diagnostics, Biotech, R&D |
| `sanofi` | Sanofi | `https://sanofi.wd3.myworkdayjobs.com/sanofi` | Vaccines, Diabetes, Regulatory |
| `gsk` | GSK (GlaxoSmithKline) | `https://gsk.wd5.myworkdayjobs.com/GSK` | Vaccines, Consumer Healthcare |
| `merck` | Merck Group | `https://merck.wd3.myworkdayjobs.com/Merck_Careers` | Lifesciences, Performance Materials |
| `lilly` | Eli Lilly | `https://lilly.wd5.myworkdayjobs.com/Lilly_Careers` | Diabetes, Bio-Medicines |
| `bayer` | Bayer | `https://bayer.wd3.myworkdayjobs.com/Bayer_Careers` | Crop Science, Pharmaceuticals |

---

## 🌐 2. Dedicated Indian Pharmacy Portals (`config/sites.yaml`)

Specialized Indian pharmacy target portals scraped via Playwright SmartExtract (`src/applypilot/discovery/smartextract.py`):

1. **Pharmatutor Jobs** (`https://www.pharmatutor.org/pharma-jobs`):
   - Dedicated Indian pharmaceutical job portal for B.Pharm, M.Pharm, and D.Pharm freshers & experienced candidates.
2. **Naukri Pharmacy** (`https://www.naukri.com/pharma-jobs`):
   - Naukri's specialized pharmaceutical manufacturing and dispensing vertical.
3. **Unstop Pharmacy** (`https://unstop.com/jobs?domain=pharmacy`):
   - Off-campus hiring, pharma student hackathons, and trainee roles.

---

## 🛠️ 3. URL Construction Rules & Workday Fix

- **Workday URL Standard**: `https://[tenant].wd[N].myworkdayjobs.com/[SiteID]/job/[Location]/[Title]_[ReqID]`
- **Avoid `/en-US/` Prefix Insertion**: Workday servers return a 404 error if `/en-US/` is forcibly inserted before the tenant site ID. URLs are built using exact API `externalPath` or `externalUrl` properties without path mutation.
