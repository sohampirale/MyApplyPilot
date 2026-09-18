#!/usr/bin/env python3
"""
Maharashtra Tech Jobs Discovery Runner
Discovers and stores ALL tech, software, developer, data, AI, and engineering jobs
across Maharashtra (Pune, Mumbai, Navi Mumbai, Thane, Nagpur, Nashik, etc.)
into ApplyPilot SQLite database with domain = 'engineering'.

Pure scraping only -- NO LLM / AI scoring is executed.
Writes live heartbeat & statistics to ~/.applypilot/logs/mh_tech_progress.json
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
from applypilot.database import get_connection, init_db, get_stats
from applypilot.discovery.jobspy import run_discovery
from applypilot.discovery.workday import run_workday_discovery

LOG_DIR = Path.home() / ".applypilot" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = LOG_DIR / "mh_tech_progress.json"
LOG_FILE = LOG_DIR / "mh_tech_scrape.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("mh_tech_scrape")


def update_progress(phase: str, status: str, extra: dict | None = None):
    try:
        conn = get_connection()
        db_total = conn.execute("SELECT COUNT(*) FROM jobs WHERE domain = 'engineering'").fetchone()[0]
        by_site = [
            {"site": row[0], "count": row[1]}
            for row in conn.execute(
                "SELECT site, COUNT(*) FROM jobs WHERE domain = 'engineering' GROUP BY site ORDER BY COUNT(*) DESC"
            ).fetchall()
        ]
        by_city = [
            {"city": row[0] or "Unknown", "count": row[1]}
            for row in conn.execute(
                "SELECT city, COUNT(*) FROM jobs WHERE domain = 'engineering' GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10"
            ).fetchall()
        ]
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
            "status": status,
            "db_total_engineering": db_total,
            "by_site": by_site,
            "by_city": by_city,
            **(extra or {}),
        }
        PROGRESS_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("Failed to update progress file: %s", e)


def main():
    log.info("=" * 60)
    log.info("STARTING MAHARASHTRA ALL TECH JOBS DISCOVERY RUNNER")
    log.info("=" * 60)

    # 1. Initialize DB
    conn = init_db()
    update_progress("init", "Database ready")

    # 2. Phase 1: Workday CXS Direct API Discovery (Ultra Fast, Zero LLM)
    log.info(">>> Phase 1: Workday CXS Direct API Discovery (MNC GCCs in MH)...")
    update_progress("workday", "running")
    try:
        wd_stats = run_workday_discovery(workers=4, domain="engineering")
        log.info("Workday discovery completed: %s", wd_stats)
        update_progress("workday", "completed", {"workday_stats": wd_stats})
    except Exception as e:
        log.error("Workday discovery error: %s", e)
        update_progress("workday", "error", {"error": str(e)})

    # 3. Phase 2: JobSpy Multi-Board Sweep (LinkedIn India + Indeed India)
    log.info(">>> Phase 2: JobSpy Sweep across LinkedIn India & Indeed India...")
    update_progress("jobspy", "running")
    try:
        js_stats = run_discovery(workers=4, domain="engineering")
        log.info("JobSpy discovery completed: %s", js_stats)
        update_progress("jobspy", "completed", {"jobspy_stats": js_stats})
    except Exception as e:
        log.error("JobSpy discovery error: %s", e)
        update_progress("jobspy", "error", {"error": str(e)})

    # 4. Final DB Summary
    total = conn.execute("SELECT COUNT(*) FROM jobs WHERE domain = 'engineering'").fetchone()[0]
    log.info("=" * 60)
    log.info("DISCOVERY FINISHED! Total Engineering Jobs in DB: %d", total)
    log.info("=" * 60)
    update_progress("completed", "All phases done", {"final_total": total})


if __name__ == "__main__":
    main()
