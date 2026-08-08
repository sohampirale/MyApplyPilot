# 🏛️ Multi-Tenant Candidate Architecture (`docs/architecture/MULTI_TENANT_DOMAINS.md`)

ApplyPilot supports multi-tenant candidate data isolation across colleges, majors, and disciplines while sharing a common, high-efficiency discovery engine.

---

## 🔒 1. Per-Candidate Directory Isolation

Each candidate profile resides in an isolated candidate folder:
```text
~/.applypilot/candidates/<candidate_id>/
├── profile.json            # Target roles, locations, credentials, education
├── resume.txt              # Candidate baseline text resume
├── resume.pdf              # Generated PDF resume
├── searches.yaml           # Search terms and locations
├── tailored_resumes/       # Tailored resumes for scored jobs
└── cover_letters/          # Generated cover letters
```

Active candidate ID is stored in `~/.applypilot/active_candidate.txt`.

---

## 🗄️ 2. Candidate Scores Table (`candidate_scores`)

Candidate evaluation metrics are isolated in SQL table `candidate_scores`:
```sql
CREATE TABLE candidate_scores (
    candidate_id           TEXT,
    job_url                TEXT,
    fit_score              INTEGER,
    score_reasoning        TEXT,
    tailored_resume_path   TEXT,
    tailored_at            TEXT,
    scored_at              TEXT,
    PRIMARY KEY (candidate_id, job_url),
    FOREIGN KEY (job_url) REFERENCES jobs(url) ON DELETE CASCADE
);
```

---

## 🏷️ 3. Domain Job Pool Isolation (`domain` Column in `jobs` Table)

Discovered jobs are tagged with a `domain` column in SQLite:
- `pharmacy` — Pure Pharmacy & Lifesciences Jobs (validated by `is_pharmacy_title`)
- `engineering` — Software, DevOps, Data Science, and Tech Jobs
- `mba` — Business Analyst, Management Trainee, Product Manager
- `architecture` — BIM Modeler, CAD Specialist, Urban Planner

Pharmacy students do not see software engineering jobs in their raw pool, scored lists, or dashboard summary statistics.

---

## 💻 4. CLI Execution Commands

- List candidate profiles: `applypilot candidates`
- Switch active candidate: `applypilot switch <candidate_id>`
- Domain-specific discovery: `applypilot run discover pharmacy -w 5`
- Full pipeline run: `applypilot run -w 5`
- Launch dashboard server: `applypilot serve`
