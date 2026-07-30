#!/usr/bin/env python3
"""Utility script to pop (delete) top pending jobs from ApplyPilot database.

Usage:
    python pop_job.py          # Pop (delete) top 1 job
    python pop_job.py --count 5 # Pop top 5 jobs
    python pop_job.py --peek    # View top job without deleting
"""

import sys
import argparse
from applypilot.database import get_connection

def pop_jobs(count: int = 1, peek: bool = False, min_score: int = 7) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, title, site, location, fit_score 
            FROM jobs 
            WHERE (apply_status IS NULL OR apply_status = 'failed')
              AND fit_score >= ?
            ORDER BY fit_score DESC, url
            LIMIT ?
        """, (min_score, count))
        
        rows = cursor.fetchall()
        if not rows:
            print(f"No pending jobs found with fit_score >= {min_score}.")
            return

        action = "Peeking" if peek else "Popping"
        print(f"\n{action} top {len(rows)} job(s) from queue:\n")
        
        for i, row in enumerate(rows, 1):
            fit = row["fit_score"]
            title = row["title"]
            site = row["site"]
            loc = row["location"] or "Unknown"
            url = row["url"]
            print(f"  {i}. [{fit}/10] {title} @ {site} (Loc: {loc})")
            print(f"     URL: {url}")

            if not peek:
                cursor.execute("DELETE FROM jobs WHERE url = ?", (url,))

        if not peek:
            conn.commit()
            print(f"\n✅ Successfully deleted {len(rows)} job(s) from database.")

def main():
    parser = argparse.ArgumentParser(description="Pop top job(s) from ApplyPilot queue.")
    parser.add_argument("-n", "--count", type=int, default=1, help="Number of jobs to pop (default: 1)")
    parser.add_argument("--peek", action="store_true", help="Inspect top job without deleting")
    parser.add_argument("--min-score", type=int, default=7, help="Minimum fit score threshold (default: 7)")
    args = parser.parse_args()

    pop_jobs(count=args.count, peek=args.peek, min_score=args.min_score)

if __name__ == "__main__":
    main()
