"""Job fit scoring: LLM-powered evaluation of candidate-job match quality.

Scores jobs on a 1-10 scale by comparing the user's resume against each
job description. All personal data is loaded at runtime from the user's
profile and resume file.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

from applypilot.config import RESUME_PATH, load_profile
from applypilot.database import get_connection, get_jobs_by_stage
from applypilot.llm import get_client

log = logging.getLogger(__name__)
console = Console()


# ── Scoring Prompt ────────────────────────────────────────────────────────

SCORE_PROMPT = """You are a job fit evaluator. Given a candidate's resume and a job description, score how well the candidate fits the role.

SCORING CRITERIA:
- 9-10: Perfect match. Candidate has direct experience in nearly all required skills and qualifications.
- 7-8: Strong match. Candidate has most required skills, minor gaps easily bridged.
- 5-6: Moderate match. Candidate has some relevant skills but missing key requirements.
- 3-4: Weak match. Significant skill gaps, would need substantial ramp-up.
- 1-2: Poor match. Completely different field or experience level.

IMPORTANT FACTORS:
- Weight technical skills heavily (programming languages, frameworks, tools)
- Consider transferable experience (automation, scripting, API work)
- Factor in the candidate's project experience
- Be realistic about experience level vs. job requirements (years of experience, seniority)

RESPOND IN EXACTLY THIS FORMAT (no other text):
SCORE: [1-10]
KEYWORDS: [comma-separated ATS keywords from the job description that match or could match the candidate]
REASONING: [2-3 sentences explaining the score]"""


def _parse_score_response(response: str) -> dict:
    """Parse the LLM's score response into structured data.

    Args:
        response: Raw LLM response text.

    Returns:
        {"score": int, "keywords": str, "reasoning": str}
    """
    score = 0
    keywords = ""
    reasoning = response

    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("SCORE:"):
            try:
                score = int(re.search(r"\d+", line).group())
                score = max(1, min(10, score))
            except (AttributeError, ValueError):
                score = 0
        elif line.startswith("KEYWORDS:"):
            keywords = line.replace("KEYWORDS:", "").strip()
        elif line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()

    return {"score": score, "keywords": keywords, "reasoning": reasoning}


def score_job(resume_text: str, job: dict) -> dict:
    """Score a single job against the resume.

    Args:
        resume_text: The candidate's full resume text.
        job: Job dict with keys: title, site, location, full_description.

    Returns:
        {"score": int, "keywords": str, "reasoning": str}
    """
    job_text = (
        f"TITLE: {job['title']}\n"
        f"COMPANY: {job['site']}\n"
        f"LOCATION: {job.get('location', 'N/A')}\n\n"
        f"DESCRIPTION:\n{(job.get('full_description') or '')[:6000]}"
    )

    messages = [
        {"role": "system", "content": SCORE_PROMPT},
        {"role": "user", "content": f"RESUME:\n{resume_text}\n\n---\n\nJOB POSTING:\n{job_text}"},
    ]

    try:
        client = get_client()
        response = client.chat(messages, max_tokens=512, temperature=0.2)
        return _parse_score_response(response)
    except Exception as e:
        log.error("LLM error scoring job '%s': %s", job.get("title", "?"), e)
        return {"score": 0, "keywords": "", "reasoning": f"LLM error: {e}"}


def _print_scoring_summary(conn, completed: int, errors: int, elapsed: float) -> list:
    """Print score distribution summary and return distribution data."""
    if elapsed > 0:
        log.info("Done: %d scored in %.1fs (%.1f jobs/sec)", completed, elapsed,
                 completed / elapsed)
    else:
        log.info("Done: %d scored", completed)

    # Score distribution
    dist = conn.execute("""
        SELECT fit_score, COUNT(*) FROM jobs
        WHERE fit_score IS NOT NULL
        GROUP BY fit_score ORDER BY fit_score DESC
    """).fetchall()
    distribution = [(row[0], row[1]) for row in dist]

    # Render score distribution summary table
    if distribution:
        table = Table(title='Fit Scoring Summary', show_header=True, header_style='bold')
        table.add_column('Score Tier', style='bold')
        table.add_column('Count', justify='right')
        table.add_column('Action', style='dim')

        # Group scores into tiers
        perfect = sum(c for s, c in distribution if s >= 9)
        strong = sum(c for s, c in distribution if 7 <= s <= 8)
        moderate = sum(c for s, c in distribution if 5 <= s <= 6)
        weak = sum(c for s, c in distribution if s <= 4)

        if perfect:
            table.add_row('[green]9-10 (Perfect)[/green]', str(perfect), 'Resume tailoring')
        if strong:
            table.add_row('[green]7-8 (Strong)[/green]', str(strong), 'Resume tailoring')
        if moderate:
            table.add_row('[yellow]5-6 (Moderate)[/yellow]', str(moderate), 'Saved (skipped tailoring)')
        if weak:
            table.add_row('[red]1-4 (Weak/Poor)[/red]', str(weak), 'Filtered out')

        table.add_row('', '', '')
        table.add_row('[bold]Total scored[/bold]', f'[bold]{sum(c for _, c in distribution)}[/bold]', '')

        console.print(table)

    # Log top rejected title patterns
    low_score_titles = conn.execute(
        'SELECT title, COUNT(*) as cnt FROM jobs '
        'WHERE fit_score IS NOT NULL AND fit_score <= 3 '
        'GROUP BY title ORDER BY cnt DESC LIMIT 5'
    ).fetchall()
    if low_score_titles:
        log.info('Top filtered (score ≤ 3): %s',
                 ', '.join(f'{row[0][:35]} ({row[1]})' for row in low_score_titles))

    return distribution


def run_scoring(limit: int = 0, rescore: bool = False) -> dict:
    """Score unscored jobs that have full descriptions.

    Scores are committed to the database **immediately** after each job is
    scored, so progress is never lost if the process is interrupted (Ctrl+C,
    API credit exhaustion, etc.).

    Args:
        limit: Maximum number of jobs to score in this run.
        rescore: If True, re-score all jobs (not just unscored ones).

    Returns:
        {"scored": int, "errors": int, "elapsed": float, "distribution": list}
    """
    resume_text = RESUME_PATH.read_text(encoding="utf-8")
    conn = get_connection()

    if rescore:
        query = "SELECT * FROM jobs WHERE full_description IS NOT NULL"
        if limit > 0:
            query += f" LIMIT {limit}"
        jobs = conn.execute(query).fetchall()
    else:
        jobs = get_jobs_by_stage(conn=conn, stage="pending_score", limit=limit)

    if not jobs:
        log.info("No unscored jobs with descriptions found.")
        return {"scored": 0, "errors": 0, "elapsed": 0.0, "distribution": []}

    # Convert sqlite3.Row to dicts if needed
    if jobs and not isinstance(jobs[0], dict):
        columns = jobs[0].keys()
        jobs = [dict(zip(columns, row)) for row in jobs]

    log.info("Scoring %d jobs sequentially...", len(jobs))
    t0 = time.time()
    completed = 0
    errors = 0

    # Track high-score count for progress logging
    high_scores = 0

    try:
        for job in jobs:
            result = score_job(resume_text, job)
            completed += 1

            if result["score"] == 0:
                errors += 1
            if result["score"] >= 7:
                high_scores += 1

            # ── Commit this score to DB immediately ──────────────────
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE jobs SET fit_score = ?, score_reasoning = ?, scored_at = ? WHERE url = ?",
                (result["score"],
                 f"{result['keywords']}\n{result['reasoning']}",
                 now, job["url"]),
            )
            conn.commit()

            log.info(
                "[%d/%d] score=%d  %s",
                completed, len(jobs), result["score"], job.get("title", "?")[:60],
            )

            # Every 100 jobs, log a progress summary
            if completed % 100 == 0:
                elapsed_so_far = time.time() - t0
                rate = completed / elapsed_so_far if elapsed_so_far > 0 else 0
                remaining = len(jobs) - completed
                eta_min = (remaining / rate / 60) if rate > 0 else 0
                log.info(
                    'Progress: %d/%d (%.0f%%) | %.1f jobs/sec | ETA: %.0f min | Score>=7: %d',
                    completed, len(jobs), completed / len(jobs) * 100,
                    rate, eta_min, high_scores,
                )

    except KeyboardInterrupt:
        elapsed = time.time() - t0
        console.print(
            f"\n[yellow]Interrupted after scoring {completed}/{len(jobs)} jobs. "
            f"All {completed} scores are safely saved in the database.[/yellow]"
        )
        distribution = _print_scoring_summary(conn, completed, errors, elapsed)
        return {
            "scored": completed,
            "errors": errors,
            "elapsed": elapsed,
            "distribution": distribution,
        }

    elapsed = time.time() - t0
    distribution = _print_scoring_summary(conn, completed, errors, elapsed)

    return {
        "scored": completed,
        "errors": errors,
        "elapsed": elapsed,
        "distribution": distribution,
    }
