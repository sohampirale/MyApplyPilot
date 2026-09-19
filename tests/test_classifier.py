"""Unit tests for Experience Classifier & Canonical Deduplication Engine."""

import sqlite3
import pytest

from applypilot.database import init_db
from applypilot.discovery.classifier import (
    classify_job,
    compute_cluster_key,
    normalize_company,
    normalize_title,
    classify_and_insert_job,
)


def test_fresher_immunity_shield_titles():
    """Verify genuine fresher, trainee, intern and junior titles are protected."""
    fresher_titles = [
        "Software Engineer Intern",
        "Graduate Engineer Trainee (GET)",
        "Junior Python Developer",
        "Associate Software Engineer",
        "Java Developer - Fresher 2025",
        "Entry-Level Web Developer",
        "Apprentice QA Tester",
        "Associate Developer",
    ]
    for title in fresher_titles:
        res = classify_job(title=title, description="We build software.")
        assert res["is_fresher_eligible"] == 1, f"Failed for {title}: {res}"
        assert res["experience_tier"] in ("fresher", "likely_fresher"), f"Failed tier for {title}: {res}"


def test_fresher_immunity_shield_descriptions():
    """Verify fresher immunity triggers from description even if title is generic."""
    desc_cases = [
        "Software Engineer. Freshers can apply for this opening.",
        "Backend Developer. No prior experience required. Training will be provided.",
        "Full Stack Developer. Candidate should have 0 - 1 years of experience.",
        "Web Developer. Freshers welcome to apply.",
    ]
    for desc in desc_cases:
        res = classify_job(title="Software Engineer", description=desc)
        assert res["is_fresher_eligible"] == 1
        assert res["experience_tier"] == "fresher"


def test_fresher_trumps_senior():
    """Verify Fresher Immunity Shield trumps senior keywords (e.g. Intern in Senior Team)."""
    # E.g. "Software Intern - Senior Engineering Team"
    res = classify_job(
        title="Software Intern",
        description="You will work directly with our Senior Engineering Director and Principal Architects with 10+ years experience.",
    )
    assert res["is_fresher_eligible"] == 1
    assert res["experience_tier"] == "fresher"


def test_senior_exclusion():
    """Verify high YOE and senior titles are flagged without deleting them."""
    senior_titles = [
        "Senior Software Engineer",
        "Sr. Full Stack Developer",
        "Tech Lead - Backend",
        "Principal System Architect",
        "Engineering Manager",
        "Staff Software Engineer",
        "Director of Engineering",
    ]
    for title in senior_titles:
        res = classify_job(title=title, description="Lead our engineering team.")
        assert res["is_fresher_eligible"] == 0, f"Failed for {title}: {res}"
        assert res["experience_tier"] == "senior_lead", f"Failed tier for {title}: {res}"


def test_yoe_extraction_and_bracket_classification():
    """Verify explicit YOE ranges are classified into proper tiers."""
    # 5+ YOE -> Senior
    res_sr = classify_job(
        title="Python Developer",
        description="Requirements: Minimum 5+ years of experience in Django and PostgreSQL.",
    )
    assert res_sr["is_fresher_eligible"] == 0
    assert res_sr["experience_tier"] == "senior_lead"
    assert res_sr["min_experience_years"] == 5.0

    # 1-2 YOE -> Likely Fresher
    res_jr = classify_job(
        title="Python Developer",
        description="Requirements: 1 - 2 years of experience in Python.",
    )
    assert res_jr["is_fresher_eligible"] == 1
    assert res_jr["experience_tier"] == "likely_fresher"
    assert res_jr["min_experience_years"] == 1.0


def test_trap_disambiguation():
    """Verify degree requirements and company age are not mistaken for candidate YOE."""
    # 4-year degree should NOT trigger senior classification
    res_degree = classify_job(
        title="Software Engineer",
        description="Requires a 4-year degree in Computer Science. Standard developer tasks.",
    )
    assert res_degree["is_fresher_eligible"] == 1
    assert res_degree["experience_tier"] == "open_entry"

    # Company age (over 20 years in business) should NOT trigger senior classification
    res_comp_age = classify_job(
        title="Frontend Developer",
        description="Celebrating over 25 years of excellence in tech consulting. We build modern React apps.",
    )
    assert res_comp_age["is_fresher_eligible"] == 1
    assert res_comp_age["experience_tier"] == "open_entry"


def test_canonical_normalization_and_clustering():
    """Verify company & title normalization collapse corporate fluff and noise."""
    # Companies
    c1 = normalize_company("Accenture in India")
    c2 = normalize_company("Accenture Solutions Pvt Ltd")
    c3 = normalize_company("Accenture Technology Services")
    assert c1 == c2 == c3 == "accenture"

    # Titles
    t1 = normalize_title("Custom Software Engineer")
    t2 = normalize_title("Custom Software Engineer - Immediate Joiner (Pune)")
    t3 = normalize_title("[Urgent Hiring] Custom Software Engineer (Hybrid)")
    assert t1 == t2 == t3 == "custom software engineer"

    # Cluster key
    k1 = compute_cluster_key("Accenture in India", "Custom Software Engineer")
    k2 = compute_cluster_key("Accenture Solutions Pvt Ltd", "Custom Software Engineer (Pune)")
    assert k1 == k2


def test_realtime_ingestion_and_clustering():
    """Verify classify_and_insert_job correctly maintains canonical cards and counts."""
    conn = init_db(":memory:")

    # Insert 1st job
    ok1 = classify_and_insert_job(
        conn,
        url="https://company.com/job/1",
        title="Frontend Developer",
        company="Infosys Limited",
        description="Freshers welcome 0-1 yrs exp",
        domain="engineering",
    )
    assert ok1 is True

    # Insert 2nd job in same cluster
    ok2 = classify_and_insert_job(
        conn,
        url="https://naukri.com/job/infosys-2",
        title="Frontend Developer (Pune)",
        company="Infosys BPM India Pvt Ltd",
        description="React developer role",
        domain="engineering",
    )
    assert ok2 is True

    # Re-inserting exact URL should be safely ignored
    ok_dup = classify_and_insert_job(
        conn,
        url="https://company.com/job/1",
        title="Frontend Developer",
        company="Infosys",
        domain="engineering",
    )
    assert ok_dup is False

    rows = conn.execute(
        """SELECT url, is_canonical, duplicate_count, canonical_job_url, experience_tier, is_fresher_eligible
           FROM jobs ORDER BY is_canonical DESC"""
    ).fetchall()

    assert len(rows) == 2
    canonical = rows[0]
    sibling = rows[1]

    assert canonical[0] == "https://company.com/job/1"
    assert canonical[1] == 1  # is_canonical
    assert canonical[2] == 2  # duplicate_count updated to 2
    assert canonical[3] is None  # canonical_job_url
    assert canonical[4] == "fresher"
    assert canonical[5] == 1  # is_fresher_eligible

    assert sibling[0] == "https://naukri.com/job/infosys-2"
    assert sibling[1] == 0  # sibling
    assert sibling[2] == 1  # duplicate_count
    assert sibling[3] == "https://company.com/job/1"  # points to canonical
