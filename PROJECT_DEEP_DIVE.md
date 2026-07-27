# ApplyPilot: In-Depth Architecture & Enterprise Integration Guide

> **Document Purpose**: This comprehensive guide serves as the single source of truth for understanding the internal architecture of **ApplyPilot**, how its 6-stage pipeline operates, how data flows through the system, and how to adapt/self-host it as an API backend for a multi-tenant enterprise or college career platform.

---

## Table of Contents
1. [Overview & Core Architecture](#1-overview--core-architecture)
2. [Codebase Map & Module Breakdown](#2-codebase-map--module-breakdown)
3. [The 6-Stage Job Application Pipeline](#3-the-6-stage-job-application-pipeline)
4. [Data Schema & State Management](#4-data-schema--state-management)
5. [LLM & AI Engine Integration](#5-llm--ai-engine-integration)
6. [Auto-Apply Mechanism (Stage 6)](#6-auto-apply-mechanism-stage-6)
7. [Enterprise & College Platform Integration Blueprint](#7-enterprise--college-platform-integration-blueprint)
8. [Licensing & AGPL-3.0 Compliance](#8-licensing--agpl-30-compliance)

---

## 1. Overview & Core Architecture

**ApplyPilot** is an open-source, autonomous job application agent designed to automate the job search and application lifecycle. 

### Key Capabilities
- **Multi-Source Job Discovery**: Simultaneously queries job aggregators (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google Jobs), 48+ Workday employer portals, and 30+ direct career sites.
- **AI-Powered Match Scoring**: Evaluates candidate profiles against job descriptions, rating fit on a 1–10 scale.
- **Anti-Hallucination Resume Tailoring**: Rewrites markdown resumes for targeted job descriptions without fabricating facts or metrics.
- **Cover Letter Generation**: Produces targeted cover letters referencing job-specific requirements.
- **Autonomous Browser Submission**: Drives a headless or headed Chrome browser via Claude Code and Playwright MCP to fill ATS forms, upload documents, answer screening questions, and submit applications.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              APPLYPILOT PIPELINE                                │
├─────────────┬─────────────┬───────────┬─────────────┬──────────────┬────────────┤
│ 1. DISCOVER │  2. ENRICH  │ 3. SCORE  │  4. TAILOR  │ 5. COVER LTR │ 6. APPLY   │
│             │             │           │             │              │            │
│ Scrape 5+   │ Fetch full  │ Rate fit  │ Per-job     │ Per-job AI   │ Playwright │
│ boards &    │ description │ 1-10 via  │ AI resume   │ cover letter │ form auto- │
│ Workday     │ via JSON-LD │ LLM       │ rewrite     │ generation   │ submission │
└──────┬──────┴──────┬──────┴─────┬─────┴──────┬──────┴──────┬──────┴─────┬──────┘
       │             │            │            │             │            │
       └─────────────┴────────────┼────────────┴─────────────┴────────────┘
                                  ▼
                     SQLite Cache & State Database (`applypilot.db`)
```

---

## 2. Codebase Map & Module Breakdown

The project is structured under `src/applypilot/`:

```
src/applypilot/
├── __init__.py          # Package initialization & versioning
├── __main__.py          # Main entry point for python -m applypilot
├── cli.py               # Typer/Click CLI command interface
├── config.py            # Global paths, environment variables, settings loader
├── database.py          # SQLite schema, WAL connection helpers, state queries
├── llm.py               # Multi-provider LLM abstraction (Gemini, Claude, OpenAI, Ollama)
├── pipeline.py          # Multithreaded pipeline stage orchestrator
├── view.py              # Rich terminal formatting & console output helpers
├── apply/               # Stage 6: Autonomous submission engine
│   ├── chrome.py        # Chrome browser process manager & remote debugging setup
│   ├── dashboard.py     # Real-time web dashboard for active apply workers
│   ├── launcher.py      # Claude Code CLI runner & Playwright MCP orchestrator
│   └── prompt.py        # Dynamic prompt builder for form navigation & question answering
├── config/              # Static YAML configuration registries
│   ├── employers.yaml   # Preconfigured Workday portal endpoints (48+ companies)
│   ├── searches.example.yaml # Query & preference template
│   └── sites.yaml       # Direct career site URL patterns & extraction rules
├── discovery/           # Stage 1: Job search scrapers
│   ├── jobspy.py        # Wrapper around python-jobspy for major boards
│   ├── smartextract.py  # Direct career site crawler & HTML parser
│   └── workday.py       # Dedicated API scraper for Workday tenant career sites
├── enrichment/          # Stage 2: Description extraction
│   └── detail.py        # 3-tier cascade: JSON-LD -> CSS Selectors -> AI Extraction
├── scoring/             # Stages 3, 4, 5: AI Evaluation & Document Generation
│   ├── scorer.py        # Stage 3: Job fit evaluator (returns score 1-10 + reasoning)
│   ├── tailor.py        # Stage 4: Resume rewriter (preserves resume_facts)
│   ├── cover_letter.py  # Stage 5: Targeted cover letter generator
│   ├── pdf.py           # Markdown to PDF/HTML compiler for resumes
│   └── validator.py     # Quality & hallucination validator (strict vs. lenient)
└── wizard/              # Interactive CLI setup wizard (applypilot init)
```

---

## 3. The 6-Stage Job Application Pipeline

Each stage operates independently and writes state back to the database.

### Stage 1: Discover (`discovery/`)
- Queries **Indeed, LinkedIn, Glassdoor, ZipRecruiter, and Google Jobs** via `python-jobspy`.
- Hits **Workday Employer Portals** directly using JSON endpoints (`workday.py`).
- Crawls **Direct Sites** using regex & pattern matching (`smartextract.py`).
- **Deduplication**: Job URLs are normalized and deduplicated against existing database entries.

### Stage 2: Enrich (`enrichment/detail.py`)
- Fetches full job descriptions for newly discovered URLs.
- **3-Tier Cascade Extraction**:
  1. Parses embedded `JSON-LD` (`JobPosting` schema).
  2. Fallback to CSS selectors for known ATS platforms (Greenhouse, Lever, SmartRecruiters, Workday).
  3. Fallback to LLM-based extraction for unknown/unstructured HTML pages.

### Stage 3: Score (`scoring/scorer.py`)
- Compares student `profile.json` (skills, preferences, experience) with enriched job descriptions.
- The LLM outputs:
  - **Score**: Integer from 1 to 10 (9–10: Strong match, 7–8: Good match, 1–4: Skip).
  - **Reasoning**: Summary of matching & missing qualifications.
- Jobs below the `--min-score` threshold (default: 7) are filtered out from subsequent stages.

### Stage 4: Tailor (`scoring/tailor.py`)
- Takes candidate’s master resume and job description.
- LLM reorganizes sections, emphasizes relevant skills, and integrates job keywords.
- **Strict Anti-Hallucination Constraint**: `resume_facts` (companies worked at, titles, dates, education, metrics) defined in `profile.json` are passed into the prompt as immutable constraints. Any altered facts fail `validator.py` check and trigger a retry.

### Stage 5: Cover Letter (`scoring/cover_letter.py`)
- Generates a tailored 3-paragraph cover letter referencing specific company details and matching candidate experiences.

### Stage 6: Auto-Apply (`apply/`)
- Launches parallel Chrome browser instances.
- Configures Playwright MCP server dynamically.
- Invokes **Claude Code CLI** with custom system prompts ([`apply/prompt.py`](file:///home/soham/coding/proj/ApplyPilot/src/applypilot/apply/prompt.py)).
- Claude navigates application forms, inputs contact data, answers EEO/screening questions based on `profile.json`, uploads tailored resumes, and submits.

---

## 4. Data Schema & State Management

ApplyPilot uses a single SQLite database (`applypilot.db`) with Write-Ahead Logging (WAL) enabled for safe concurrent multi-threading ([`database.py`](file:///home/soham/coding/proj/ApplyPilot/src/applypilot/database.py)).

### Primary Table: `jobs`

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Auto-incrementing identifier |
| `url` | TEXT UNIQUE | Canonical job posting URL |
| `title` | TEXT | Job title |
| `company` | TEXT | Employer name |
| `location` | TEXT | City/State/Remote |
| `source` | TEXT | Source board (e.g. `linkedin`, `workday`) |
| `description` | TEXT | Enriched job description text |
| `score` | INTEGER | AI fit score (1–10) |
| `score_reason` | TEXT | AI match reasoning |
| `tailored_resume` | TEXT | Path to generated markdown/PDF resume |
| `cover_letter` | TEXT | Path to generated cover letter |
| `status` | TEXT | Stage flag (`discovered`, `enriched`, `scored`, `tailored`, `applied`, `failed`) |
| `applied_at` | TIMESTAMP | Submission timestamp |
| `error_message` | TEXT | Exception traceback if apply fails |

---

## 5. LLM & AI Engine Integration

Managed by [`src/applypilot/llm.py`](file:///home/soham/coding/proj/ApplyPilot/src/applypilot/llm.py).

### Supported Providers:
1. **Google Gemini** (Default: `gemini-2.5-flash` or `gemini-1.5-flash`) - *Recommended for high rate limits & free tier.*
2. **Anthropic Claude** (`claude-3-5-sonnet`, `claude-3-haiku`)
3. **OpenAI** (`gpt-4o`, `gpt-4o-mini`)
4. **Ollama / Local LLMs** (e.g., Llama 3, Mistral)

---

## 6. Auto-Apply Mechanism (Stage 6)

Stage 6 automates browser form interactions using an AI-agent loop:

```
[Launcher] ──► Spawns Debug Chrome ──► Starts Playwright MCP Server ──► Launches Claude Code CLI
                                                                                │
[Form Submission Completed] ◄── [Performs Form Actions] ◄── [Reads Page DOM] ◄──┘
```

### Form Handling Capabilities:
- **Standard Fields**: Name, Email, Phone, Address, LinkedIn URL, Portfolio.
- **Work Experience / Education**: Dynamically adds rows on Workday/Greenhouse.
- **File Uploads**: Attaches tailored PDF resume and cover letter.
- **Screening Questions**: LLM evaluates questions (e.g. "Do you have 3+ years experience with Python?") using candidate profile context.
- **EEO Compliance**: Fills Gender, Race, Veteran, and Disability status using defaults from `profile.json`.
- **CAPTCHA Support**: Integrates optional CapSolver API key to bypass hCaptcha, reCAPTCHA, and Turnstile.

---

## 7. Enterprise & College Platform Integration Blueprint

To adapt ApplyPilot as a backend service for a **College Student Career Platform**:

### Recommended Architecture (Hybrid Model)

```
┌────────────────────────────────────────────────────────────────────────┐
│                   COLLEGE BACKEND INFRASTRUCTURE                       │
│                                                                        │
│  [PostgreSQL DB] ──► [FastAPI / Django Web Service]                    │
│                            │                                           │
│                            ├─► Job Scraper (ApplyPilot Stage 1)       │
│                            ├─► Description Enricher (Stage 2)          │
│                            ├─► AI Job Matcher (Stage 3)               │
│                            ├─► Resume Tailoring Engine (Stage 4)       │
│                            └─► Cover Letter Generator (Stage 5)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     STUDENT FRONTEND & CLIENT                          │
│                                                                        │
│  [Student Web Portal]  ──────►  [Chrome Extension / Client Agent]       │
│  - Selects matched jobs         - Downloads server-tailored materials  │
│  - Reviews generated resumes    - Executes Stage 6 form auto-fill on   │
│                                   student's laptop using residential IP│
└────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Implementation Strategy:

1. **Replace Local Files with Relational Database**:
   - Migrate SQLite to **PostgreSQL**.
   - Create tables: `users` (students), `student_profiles`, `resume_facts`, `job_searches`, `job_matches`, `applications`.

2. **Wrap ApplyPilot Core into REST API Endpoints**:
   - Expose Python modules via FastAPI:
     - `POST /api/v1/jobs/discover`
     - `POST /api/v1/jobs/score`
     - `POST /api/v1/resumes/tailor`
     - `POST /api/v1/cover-letters/generate`

3. **Execution Layer for Stage 6 (Auto-Apply)**:
   - **Hybrid Extension Model (Best Practice)**: Run Stages 1–5 on the cloud server. Provide students with a 1-click Chrome Extension that calls the server API for tailored data and performs DOM form filling directly in the student's browser. This avoids datacenter IP bans and credential management issues.

---

## 8. Licensing & AGPL-3.0 Compliance

ApplyPilot is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### Key Implications:
- **Internal / Personal Use**: Free to use without restriction.
- **SaaS / Web Service Deployment**: If you modify ApplyPilot and run it as a network service for college students, AGPL-3.0 requires you to release the source code of your modified network service under the AGPL-3.0 license.
- **Modular Architecture**: Keeping your web frontend and proprietary database separate from the core open-source ApplyPilot library wrapper helps maintain clean license boundaries.

---

*Document updated for ApplyPilot v1.0+ core codebase.*
