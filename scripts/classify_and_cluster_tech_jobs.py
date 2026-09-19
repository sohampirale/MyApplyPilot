#!/usr/bin/env python3
"""Classify experience tiers and canonically cluster existing jobs in applypilot.db.

Usage:
    ./venv/bin/python3 scripts/classify_and_cluster_tech_jobs.py
    ./venv/bin/python3 scripts/classify_and_cluster_tech_jobs.py --domain engineering
    ./venv/bin/python3 scripts/classify_and_cluster_tech_jobs.py --all-domains
    ./venv/bin/python3 scripts/classify_and_cluster_tech_jobs.py --dry-run
"""

import argparse
import logging
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from applypilot.config import DB_PATH
from applypilot.database import ensure_columns, get_connection
from applypilot.discovery.classifier import classify_job, compute_cluster_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("classify_and_cluster")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Classify experience tiers and cluster canonical duplicates."
    )
    parser.add_argument(
        "--domain",
        default="engineering",
        help="Target domain to classify and cluster (default: engineering).",
    )
    parser.add_argument(
        "--all-domains",
        action="store_true",
        help="Process jobs across all domains in the database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute classification and clustering statistics without modifying the database.",
    )
    parser.add_argument(
        "--db-path",
        default=str(DB_PATH),
        help=f"Path to SQLite database (default: {DB_PATH}).",
    )
    return parser.parse_args()


def canonical_sort_key(job: dict) -> tuple:
    """Sort key to determine which job in a cluster should be canonical.

    Highest priority:
      1. Has full_description (1 vs 0)
      2. Length of full_description / description (longer is better)
      3. Has salary (1 vs 0)
      4. Has application_url (1 vs 0)
      5. Newer date_posted / discovered_at
    """
    has_full = 1 if (job.get("full_description") and len(job["full_description"]) > 200) else 0
    desc_len = len(job.get("full_description") or job.get("description") or "")
    has_salary = 1 if job.get("salary") else 0
    has_app_url = 1 if job.get("application_url") else 0
    date_val = job.get("date_posted") or job.get("discovered_at") or ""
    return (has_full, desc_len, has_salary, has_app_url, date_val)


def main():
    args = parse_args()
    db_path = Path(args.db_path)

    if not db_path.exists():
        log.error("Database not found at %s", db_path)
        sys.exit(1)

    log.info("Connecting to database: %s", db_path)
    conn = get_connection(db_path)

    # 1. Ensure columns exist
    ensure_columns(conn)

    # 2. Query target jobs
    if args.all_domains:
        log.info("Selecting all jobs across ALL domains...")
        cursor = conn.execute(
            """SELECT url, title, company, description, full_description, salary,
                      application_url, discovered_at, date_posted, domain
               FROM jobs"""
        )
    else:
        log.info("Selecting jobs for domain: '%s'...", args.domain)
        cursor = conn.execute(
            """SELECT url, title, company, description, full_description, salary,
                      application_url, discovered_at, date_posted, domain
               FROM jobs WHERE domain = ?""",
            (args.domain,),
        )

    cols = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    total_jobs = len(rows)
    log.info("Found %d jobs to process.", total_jobs)

    if total_jobs == 0:
        log.info("No jobs found matching criteria. Exiting.")
        return

    start_time = time.perf_counter()

    # 3. Classify and group into clusters by (domain, cluster_id)
    clusters: dict[tuple[str, str], list[dict]] = defaultdict(list)
    tier_counts = defaultdict(int)
    fresher_eligible_count = 0

    log.info("Classifying jobs and generating cluster keys...")
    for row in rows:
        job = dict(zip(cols, row))
        title = job.get("title")
        company = job.get("company")
        desc = job.get("full_description") or job.get("description") or ""

        # Classify
        c_res = classify_job(title, desc, company)
        job["_experience_tier"] = c_res["experience_tier"]
        job["_is_fresher_eligible"] = c_res["is_fresher_eligible"]
        job["_min_experience_years"] = c_res["min_experience_years"]
        job["_classification_reason"] = c_res["classification_reason"]

        tier_counts[c_res["experience_tier"]] += 1
        if c_res["is_fresher_eligible"] == 1:
            fresher_eligible_count += 1

        # Cluster
        cluster_id = compute_cluster_key(company, title)
        job["_cluster_id"] = cluster_id

        domain_key = (job.get("domain") or "engineering", cluster_id)
        clusters[domain_key].append(job)

    num_clusters = len(clusters)
    num_duplicates = total_jobs - num_clusters
    log.info(
        "Classification completed: %d total jobs -> %d unique clusters (%d duplicate listings to collapse).",
        total_jobs,
        num_clusters,
        num_duplicates,
    )

    # 4. Determine canonical representative for each cluster
    update_records = []
    canonical_fresher_count = 0
    top_duplicate_clusters = []

    for (dom, c_id), job_list in clusters.items():
        # Sort cluster members: best/richest job first
        sorted_jobs = sorted(job_list, key=canonical_sort_key, reverse=True)
        canonical_job = sorted_jobs[0]
        dup_count = len(sorted_jobs)

        if dup_count > 1:
            top_duplicate_clusters.append((
                canonical_job.get("company") or "Unknown",
                canonical_job.get("title") or "Unknown",
                dup_count,
            ))

        # Canonical parent record
        update_records.append((
            canonical_job["_experience_tier"],
            canonical_job["_is_fresher_eligible"],
            canonical_job["_min_experience_years"],
            canonical_job["_classification_reason"],
            c_id,
            1,  # is_canonical
            dup_count,  # duplicate_count
            None,  # canonical_job_url
            canonical_job["url"],
        ))

        if canonical_job["_is_fresher_eligible"] == 1:
            canonical_fresher_count += 1

        # Sibling duplicate records
        for sibling in sorted_jobs[1:]:
            update_records.append((
                sibling["_experience_tier"],
                sibling["_is_fresher_eligible"],
                sibling["_min_experience_years"],
                sibling["_classification_reason"],
                c_id,
                0,  # is_canonical
                1,  # duplicate_count
                canonical_job["url"],  # canonical_job_url
                sibling["url"],
            ))

    # 5. Apply updates to database
    if args.dry_run:
        log.info("[DRY RUN] Would update %d rows in SQLite. Skipping DB commit.", len(update_records))
    else:
        log.info("Updating %d rows in SQLite...", len(update_records))
        update_sql = """
            UPDATE jobs SET
                experience_tier = ?,
                is_fresher_eligible = ?,
                min_experience_years = ?,
                classification_reason = ?,
                cluster_id = ?,
                is_canonical = ?,
                duplicate_count = ?,
                canonical_job_url = ?
            WHERE url = ?
        """
        # Execute in chunks of 1,000 for smooth transaction handling
        chunk_size = 1000
        for i in range(0, len(update_records), chunk_size):
            chunk = update_records[i : i + chunk_size]
            conn.executemany(update_sql, chunk)
            conn.commit()
        log.info("Database updates successfully committed.")

    elapsed = time.perf_counter() - start_time

    # 6. Pretty print summary table
    print("\n" + "=" * 70)
    print(" 🚀 CLASSIFICATION & CANONICAL DEDUPLICATION REPORT")
    print("=" * 70)
    print(f" Target Domain(s)            : {'ALL' if args.all_domains else args.domain}")
    print(f" Total Jobs Evaluated        : {total_jobs:,}")
    print(f" Unique Canonical Clusters   : {num_clusters:,} ({(num_clusters/total_jobs*100):.1f}%)")
    print(f" Sibling Duplicates Collapsed: {num_duplicates:,} ({(num_duplicates/total_jobs*100):.1f}%)")
    print(f" Processing Time             : {elapsed:.2f} seconds ({total_jobs/max(elapsed, 0.001):.0f} jobs/sec)")
    print("-" * 70)
    print(" 📊 EXPERIENCE TIER BREAKDOWN (ALL LISTINGS):")
    for tier in ["fresher", "likely_fresher", "open_entry", "senior_lead"]:
        cnt = tier_counts.get(tier, 0)
        pct = (cnt / total_jobs * 100) if total_jobs else 0
        tag = "🟢 KEPT (Fresher)" if tier in ("fresher", "likely_fresher") else ("🔵 KEPT (Open Entry)" if tier == "open_entry" else "🔴 SENIOR (Filtered)")
        print(f"   • {tier:<16}: {cnt:>5,} ({pct:>5.1f}%)  [{tag}]")
    print("-" * 70)
    print(f" 🎓 STUDENT-ELIGIBLE JOBS (is_fresher_eligible = 1):")
    print(f"   • Total Accessible Listings : {fresher_eligible_count:,} / {total_jobs:,} ({(fresher_eligible_count/total_jobs*100):.1f}%)")
    print(f"   • Clean Canonical Cards     : {canonical_fresher_count:,} unique cards")
    print("-" * 70)
    print(" 🏆 TOP DUPLICATE CLUSTERS COLLAPSED:")
    top_duplicate_clusters.sort(key=lambda x: x[2], reverse=True)
    for comp, tit, cnt in top_duplicate_clusters[:10]:
        print(f"   • {comp[:28]:<28} | {tit[:30]:<30} | {cnt} listings -> 1 card")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
