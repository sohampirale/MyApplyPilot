"""
ApplyPilot Experience Classifier & Canonical Deduplication Engine.

Provides deterministic, zero-cost, high-reliability classification of job postings into:
  - 'fresher': 0-1 YOE, college graduates, trainees, interns, GETs.
  - 'likely_fresher': 1-2 YOE, junior developer stack.
  - 'open_entry': Standard SDE/Developer without senior qualifiers or high YOE blockers.
  - 'senior_lead': 3+ to 12+ YOE, Senior, Lead, Principal, Architect, Manager.

Features a strict "Fresher Immunity Shield" (Fresher Trumps Senior) ensuring
zero false-negative drops of genuine college graduate opportunities.
Also provides canonical clustering to collapse multi-board and repetitive listings.
"""

from datetime import datetime, timezone
import hashlib
import re
import sqlite3
from typing import TypedDict


class ClassificationResult(TypedDict):
    experience_tier: str       # 'fresher' | 'likely_fresher' | 'open_entry' | 'senior_lead'
    is_fresher_eligible: int   # 1 = Yes (Student accessible), 0 = No (Senior/Lead)
    min_experience_years: float | None
    classification_reason: str


# ---------------------------------------------------------------------------
# Regex Pattern Definitions
# ---------------------------------------------------------------------------

# Fresher Immunity Shield: If these patterns match, job is protected and CANNOT be marked senior
FRESHER_TITLE_RE = re.compile(
    r'\b(fresher|freshers|intern|internship|trainee|graduate|get|'
    r'associate\s+(?:software|developer|engineer|analyst|qa|test)|'
    r'junior|jr\.?|entry[\s-]level|apprentice)\b',
    re.IGNORECASE,
)

FRESHER_DESC_RE = re.compile(
    r'(\bfreshers?\s+(?:can\s+apply|welcome)\b|'
    r'\bno\s+prior\s+experience\b|'
    r'\bbatch\s+of\s+202[456]\b|'
    r'\b0\s*(?:-|to|\\-|–|—)\s*[12]\s*(?:years?|yrs?)\b|'
    r'\b0\s*\+?\s*(?:years?|yrs?)\b|'
    r'\bentry[\s-]level\b)',
    re.IGNORECASE,
)

# Unambiguous Senior Title Keywords (checked only when Fresher Immunity Shield is not triggered)
SENIOR_TITLE_RE = re.compile(
    r'\b(senior|sr\.?|lead|principal|architect|director|head\s+of|head|manager|'
    r'staff|expert|consultant|specialist|advisor|vp|vice\s+president|'
    r'tech\s+lead|team\s+lead|chapter\s+lead)\b',
    re.IGNORECASE,
)

# Experience extraction helpers supporting Unicode dashes and markdown escapes
_DASH = r'(?:[\-–—]|\\-|to|\bto\b)'
YOE_RANGE_RE = re.compile(rf'(\d+)\s*{_DASH}\s*(\d+)\s*(?:years?|yrs?)', re.IGNORECASE)
YOE_PLUS_RE = re.compile(
    r'(\d+)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp|relevant|industry|hands[\s\-]on)',
    re.IGNORECASE,
)
EXP_HEADER_RE = re.compile(rf'(?:experience|exp)\s*:\s*(\d+)\s*{_DASH}?\s*(\d+)?', re.IGNORECASE)

# Disambiguation filters for non-experience numbers
DEGREE_TRAP_RE = re.compile(r'\b[34]\s*[-–—]?\s*years?\s*(?:degree|diploma|bachelor|program|course)\b', re.IGNORECASE)
COMPANY_AGE_RE = re.compile(r'\b(?:over|for|past|celebrating)\s+\d+\s*\+?\s*years?\b', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Normalization & Canonical Clustering
# ---------------------------------------------------------------------------

def normalize_company(company: str | None) -> str:
    """Normalize company name to remove legal, geographic, and corporate fluff."""
    if not company:
        return "unknown"
    co = company.lower().strip()
    # Strip common corporate, legal, preposition, and regional words
    co = re.sub(r'\b(in\s+india|india|pvt|ltd|limited|private|inc|llc|corp|corporation|technologies|technology|tech|solutions|services|group|systems|software|global|international|bpm|bpo|consulting|consultancy)\b', '', co)
    co = re.sub(r'[^a-z0-9]', '', co)
    return co.strip() or "unknown"



def normalize_title(title: str | None) -> str:
    """Normalize job title by removing hiring fluff, brackets, locations, and punctuation."""
    if not title:
        return "unknown"
    t = title.lower().strip()
    # Remove parentheticals like (Hybrid), (Pune), (Urgent Hiring)
    t = re.sub(r'\(.*?\)', '', t)
    t = re.sub(r'\[.*?\]', '', t)
    # Remove common Indian recruiting fluff
    t = re.sub(r'\b(urgent|immediate|joiner|joiners|hiring|openings?|multiple|hybrid|remote|pune|mumbai|bangalore|india)\b', '', t)
    # Standardize common acronyms
    t = re.sub(r'\bsr\.?\b', 'senior', t)
    t = re.sub(r'\bjr\.?\b', 'junior', t)
    t = re.sub(r'\bdev\b', 'developer', t)
    # Keep only alphanumeric and collapse spaces
    t = re.sub(r'[^a-z0-9]', ' ', t)
    t = ' '.join(t.split())
    return t or "unknown"


def compute_cluster_key(company: str | None, title: str | None) -> str:
    """Generate a deterministic 16-character SHA-256 cluster key for deduplication."""
    norm_co = normalize_company(company)
    norm_t = normalize_title(title)
    raw = f"{norm_co}___{norm_t}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Classification Core
# ---------------------------------------------------------------------------

def classify_job(
    title: str | None,
    description: str | None,
    company: str | None = "",
) -> ClassificationResult:
    """Classify job into experience tiers with strict Fresher Immunity Shield.

    Guarantees:
      - 0% False Negatives on freshers (interns/trainees are never marked senior).
      - Hard Senior roles are flagged as is_fresher_eligible = 0.
      - Open-entry SDE roles receive benefit-of-the-doubt as is_fresher_eligible = 1.
    """
    t = title or ""
    d = description or ""
    full_text = f"{t}\n{d}"

    # -----------------------------------------------------------------------
    # Step 1: Fresher Immunity Shield
    # -----------------------------------------------------------------------
    m_ft = FRESHER_TITLE_RE.search(t)
    if m_ft:
        return {
            "experience_tier": "fresher",
            "is_fresher_eligible": 1,
            "min_experience_years": 0.0,
            "classification_reason": f'Protected Fresher title: "{m_ft.group(0)}"',
        }

    m_fd = FRESHER_DESC_RE.search(d[:3500])
    if m_fd:
        return {
            "experience_tier": "fresher",
            "is_fresher_eligible": 1,
            "min_experience_years": 0.0,
            "classification_reason": f'Protected Fresher description: "{m_fd.group(0)}"',
        }

    # -----------------------------------------------------------------------
    # Step 2: Unambiguous Senior Title
    # -----------------------------------------------------------------------
    m_st = SENIOR_TITLE_RE.search(t)
    if m_st:
        return {
            "experience_tier": "senior_lead",
            "is_fresher_eligible": 0,
            "min_experience_years": 5.0,
            "classification_reason": f'Senior Title: "{m_st.group(0)}"',
        }

    # -----------------------------------------------------------------------
    # Step 3: Experience Extraction from Description (Cleaned of Traps)
    # -----------------------------------------------------------------------
    cleaned_d = DEGREE_TRAP_RE.sub('', d)
    cleaned_d = COMPANY_AGE_RE.sub('', cleaned_d)
    cleaned_text = f"{t}\n{cleaned_d}"

    ranges = YOE_RANGE_RE.findall(cleaned_text)
    plus = YOE_PLUS_RE.findall(cleaned_text)
    exp_h = EXP_HEADER_RE.findall(cleaned_text)

    yoe_list: list[tuple[int, int]] = []
    for low, high in ranges:
        try:
            yoe_list.append((int(low), int(high)))
        except (ValueError, TypeError):
            pass
    for val in plus:
        try:
            yoe_list.append((int(val), int(val)))
        except (ValueError, TypeError):
            pass
    for low, high in exp_h:
        try:
            l = int(low)
            h = int(high) if high else l
            yoe_list.append((l, h))
        except (ValueError, TypeError):
            pass

    if yoe_list:
        min_y = min(y[0] for y in yoe_list)
        max_y = max(y[1] for y in yoe_list)

        if min_y >= 3:
            return {
                "experience_tier": "senior_lead",
                "is_fresher_eligible": 0,
                "min_experience_years": float(min_y),
                "classification_reason": f"Demands {min_y}+ YOE: {yoe_list[:2]}",
            }
        elif min_y == 0:
            return {
                "experience_tier": "fresher",
                "is_fresher_eligible": 1,
                "min_experience_years": 0.0,
                "classification_reason": f"Explicit 0-{max_y} YOE requirement",
            }
        elif min_y <= 2:
            return {
                "experience_tier": "likely_fresher",
                "is_fresher_eligible": 1,
                "min_experience_years": float(min_y),
                "classification_reason": f"Low YOE bracket ({min_y}-{max_y} yrs)",
            }

    # -----------------------------------------------------------------------
    # Step 4: Default Open Entry (Benefit of the Doubt)
    # -----------------------------------------------------------------------
    return {
        "experience_tier": "open_entry",
        "is_fresher_eligible": 1,
        "min_experience_years": None,
        "classification_reason": "Standard SDE/Developer, 0 senior blockers",
    }


# ---------------------------------------------------------------------------
# Real-Time Ingestion & Canonical Clustering Hook
# ---------------------------------------------------------------------------

def classify_and_insert_job(
    conn: sqlite3.Connection,
    *,
    url: str,
    title: str | None,
    company: str | None,
    description: str | None = None,
    salary: str | None = None,
    location: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    site: str = "unknown",
    strategy: str = "unknown",
    now: str | None = None,
    date_posted: str | None = None,
    full_description: str | None = None,
    application_url: str | None = None,
    detail_scraped_at: str | None = None,
    detail_error: str | None = None,
    domain: str = "engineering",
) -> bool:
    """Classify experience tier, canonically cluster, and insert a job into SQLite.

    Guarantees:
      - Experience classification is evaluated at ingestion time.
      - Canonical representative card (is_canonical = 1) is chosen for each cluster.
      - Duplicate sibling listings (is_canonical = 0) point to the canonical parent URL.
      - Canonical parent duplicate_count is incremented for every sibling.
      - Returns True if newly inserted, False on URL primary key collision.
    """
    if not url:
        return False

    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    desc_to_eval = full_description or description or ""

    # 1. Experience tier classification
    c_res = classify_job(title, desc_to_eval, company)
    exp_tier = c_res["experience_tier"]
    is_fresher = c_res["is_fresher_eligible"]
    min_exp = c_res["min_experience_years"]
    reason = c_res["classification_reason"]

    # 2. Canonical Cluster Key
    cluster_id = compute_cluster_key(company, title)

    # Check if a canonical job already exists in this cluster for this domain
    row = conn.execute(
        "SELECT url, duplicate_count FROM jobs WHERE cluster_id = ? AND domain = ? AND is_canonical = 1 LIMIT 1",
        (cluster_id, domain),
    ).fetchone()

    if row:
        canonical_parent_url = row[0]
        is_canonical = 0
        canonical_job_url = canonical_parent_url
        duplicate_count = 1
    else:
        canonical_parent_url = None
        is_canonical = 1
        canonical_job_url = None
        duplicate_count = 1

    try:
        conn.execute(
            """INSERT INTO jobs (
                url, title, salary, description, location, site, strategy,
                discovered_at, date_posted, full_description, application_url,
                detail_scraped_at, detail_error, domain, company, city, state, country,
                experience_tier, is_fresher_eligible, min_experience_years, classification_reason,
                cluster_id, is_canonical, duplicate_count, canonical_job_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                url, title, salary, description, location, site, strategy,
                now, date_posted, full_description, application_url,
                detail_scraped_at, detail_error, domain, company, city, state, country,
                exp_tier, is_fresher, min_exp, reason,
                cluster_id, is_canonical, duplicate_count, canonical_job_url,
            ),
        )

        # Increment canonical parent duplicate count & opportunistically enrich parent
        if is_canonical == 0 and canonical_parent_url:
            conn.execute(
                "UPDATE jobs SET duplicate_count = duplicate_count + 1 WHERE url = ?",
                (canonical_parent_url,),
            )
            if full_description:
                conn.execute(
                    "UPDATE jobs SET full_description = COALESCE(full_description, ?), "
                    "detail_scraped_at = COALESCE(detail_scraped_at, ?) WHERE url = ?",
                    (full_description, detail_scraped_at or now, canonical_parent_url),
                )
            if salary:
                conn.execute(
                    "UPDATE jobs SET salary = COALESCE(salary, ?) WHERE url = ?",
                    (salary, canonical_parent_url),
                )
        return True
    except sqlite3.IntegrityError:
        return False
