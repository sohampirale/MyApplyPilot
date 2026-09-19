#!/usr/bin/env python3
"""
Maharashtra Civil & Infrastructure Jobs Discovery Runner
Discovers and stores ALL civil site, structural, quantity surveying, BIM, billing, and infrastructure
jobs across Maharashtra (Mumbai MMR, Navi Mumbai, Pune, Thane, Nagpur, Nashik, etc.)
into ApplyPilot SQLite database with domain = 'civil'.

Pure scraping only -- ZERO LLM / AI scoring is executed.
Writes live heartbeat & statistics to ~/.applypilot/logs/mh_civil_progress.json
"""

import sys
import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot import config
from applypilot.database import get_connection, init_db
from applypilot.discovery.jobspy import run_discovery
from applypilot.discovery.naukri import scrape_naukri_query

LOG_DIR = Path.home() / ".applypilot" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = LOG_DIR / "mh_civil_progress.json"
LOG_FILE = LOG_DIR / "mh_civil_scrape.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("mh_civil_scrape")


def update_progress(phase: str, status: str, extra: dict | None = None):
    try:
        conn = get_connection()
        db_total = conn.execute("SELECT COUNT(*) FROM jobs WHERE domain = 'civil'").fetchone()[0]
        by_site = [
            {"site": row[0], "count": row[1]}
            for row in conn.execute(
                "SELECT site, COUNT(*) FROM jobs WHERE domain = 'civil' GROUP BY site ORDER BY COUNT(*) DESC"
            ).fetchall()
        ]
        by_city = [
            {"city": row[0] or "Unknown", "count": row[1]}
            for row in conn.execute(
                "SELECT city, COUNT(*) FROM jobs WHERE domain = 'civil' GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10"
            ).fetchall()
        ]
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "domain": "civil",
            "phase": phase,
            "status": status,
            "db_total_civil": db_total,
            "by_site": by_site,
            "by_city": by_city,
            **(extra or {}),
        }
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log.warning("Failed to write progress JSON: %s", e)


def run_naukri_phase():
    """High-yield Naukri sweep for Maharashtra Civil & Infrastructure clusters."""
    log.info(">>> Phase 1: Naukri India Stealth Extraction (Civil & Infrastructure Epicenters)...")
    update_progress("naukri", "running")

    queries = [
        "Civil Site Engineer",
        "Graduate Engineer Trainee Civil",
        "Structural Design Engineer",
        "Quantity Surveyor",
        "Civil Billing Engineer",
        "BIM Civil Engineer",
        "Civil QC Engineer",
        "Civil Engineer Fresher",
        "Project Engineer Civil",
    ]

    locations = [
        "Mumbai",
        "Navi Mumbai",
        "Pune",
        "Thane",
        "Nagpur",
        "Nashik",
    ]

    total_new = 0
    total_dupes = 0
    total_q = len(queries) * len(locations)
    q_idx = 0

    for q in queries:
        for loc in locations:
            q_idx += 1
            log.info("[%d/%d] Naukri Sweep: '%s' in %s...", q_idx, total_q, q, loc)
            try:
                stats = scrape_naukri_query(query=q, location=loc, domain="civil", max_pages=1, delay_sec=2.5)
                total_new += stats.get("new", 0)
                total_dupes += stats.get("existing", 0)
                log.info("  -> %d new, %d dupes (total cards: %d)", stats.get("new", 0), stats.get("existing", 0), stats.get("total_cards", 0))
                update_progress("naukri", "running", {
                    "query_progress": f"{q_idx}/{total_q}",
                    "current_query": f"{q} in {loc}",
                    "naukri_new": total_new,
                    "naukri_dupes": total_dupes,
                })
            except Exception as e:
                log.warning("  -> Error: %s", e)
            time.sleep(1.5)

    update_progress("naukri", "completed", {"naukri_new": total_new, "naukri_dupes": total_dupes})
    return {"new": total_new, "existing": total_dupes}


def run_jobspy_phase():
    """JobSpy sweep across LinkedIn India & Indeed India for Civil Engineering."""
    log.info(">>> Phase 2: JobSpy Multi-Board Sweep (LinkedIn & Indeed India)...")
    update_progress("jobspy", "running")

    terms = [
        {"query": "Civil Site Engineer", "tier": 1},
        {"query": "Structural Design Engineer", "tier": 1},
        {"query": "Graduate Engineer Trainee Civil", "tier": 1},
        {"query": "Quantity Surveyor", "tier": 1},
        {"query": "BIM Modeler Civil", "tier": 2},
        {"query": "Civil Billing Engineer", "tier": 2},
        {"query": "Civil Engineer Fresher", "tier": 2},
    ]

    locations = [
        {"location": "Mumbai, Maharashtra", "remote": False},
        {"location": "Navi Mumbai, Maharashtra", "remote": False},
        {"location": "Thane, Maharashtra", "remote": False},
        {"location": "Pune, Maharashtra", "remote": False},
        {"location": "Nagpur, Maharashtra", "remote": False},
        {"location": "Nashik, Maharashtra", "remote": False},
        {"location": "Aurangabad, Maharashtra", "remote": False},
        {"location": "Maharashtra, India", "remote": False},
    ]

    accept = [
        "Mumbai", "Navi Mumbai", "Thane", "Pune", "Pimpri", "Chinchwad", "Nagpur",
        "Nashik", "Aurangabad", "Kolhapur", "Maharashtra", "MH", "India"
    ]
    reject = ["Bengaluru", "Bangalore", "Hyderabad", "Delhi", "Gurgaon", "Noida", "Chennai", "Kolkata", "US", "UK"]

    search_cfg = {
        "country": "india",
        "country_indeed": "india",
        "queries": terms,
        "locations": locations,
        "location_accept": accept,
        "location_reject_non_remote": reject,
        "hours_old": 720,
        "results_wanted": 25,
        "boards": ["linkedin", "indeed"],
    }

    try:
        js_stats = run_discovery(search_cfg, workers=3, domain="civil")
        log.info("JobSpy Civil completed: %s", js_stats)
        update_progress("jobspy", "completed", {"jobspy_stats": js_stats})
        return js_stats
    except Exception as e:
        log.error("JobSpy Civil error: %s", e)
        update_progress("jobspy", "error", {"error": str(e)})
        return {"error": str(e)}


def main():
    log.info("=" * 60)
    log.info("STARTING MAHARASHTRA CIVIL & INFRASTRUCTURE DISCOVERY SWEEP")
    log.info("=" * 60)

    conn = init_db()
    update_progress("init", "Database ready")

    # 1. Phase 1: Naukri Playwright Stealth Extraction
    naukri_stats = run_naukri_phase()

    # 2. Phase 2: JobSpy Sweep across LinkedIn India & Indeed India
    jobspy_stats = run_jobspy_phase()

    # 3. Final Summary
    total = conn.execute("SELECT COUNT(*) FROM jobs WHERE domain = 'civil'").fetchone()[0]
    log.info("=" * 60)
    log.info("CIVIL DISCOVERY FINISHED! Total Civil Jobs in DB: %d", total)
    log.info("=" * 60)
    update_progress("completed", "All phases done", {"final_total": total})


if __name__ == "__main__":
    main()
