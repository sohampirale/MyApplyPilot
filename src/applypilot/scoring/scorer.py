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

from applypilot.config import (
    RESUME_PATH, load_profile,
    get_active_candidate_id, get_candidate_resume_path,
)
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


class QuotaExhaustedError(Exception):
    """Raised when LLM API credits or quota are exhausted."""
    pass


def is_quota_error(exc: Exception) -> bool:
    """Check if an exception indicates API quota or credit exhaustion."""
    if isinstance(exc, QuotaExhaustedError):
        return True
    msg = str(exc).lower()
    quota_indicators = (
        "quota", "insufficient_quota", "out of credits", "credit limit",
        "payment required", "billing", "exceeded your current quota",
        "resource_exhausted", "resourcehasbeenexhausted", "balance",
        "insufficient balance", "402 payment required", "rate_limit_exceeded"
    )
    if any(ind in msg for ind in quota_indicators):
        return True
    if hasattr(exc, "response") and getattr(exc.response, "status_code", None) in (402, 429):
        return True
    return False


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
        if is_quota_error(e):
            raise QuotaExhaustedError(f"LLM API quota or credits exhausted: {e}") from e
        log.error("LLM error scoring job '%s': %s", job.get("title", "?"), e)
        return {"score": 0, "keywords": "", "reasoning": f"LLM error: {e}"}


def _print_scoring_summary(conn, completed: int, errors: int, elapsed: float,
                          candidate_id: str | None = None) -> list:
    """Print score distribution summary and return distribution data."""
    cid = candidate_id or get_active_candidate_id()

    if elapsed > 0:
        log.info("Done: %d scored in %.1fs (%.1f jobs/sec)", completed, elapsed,
                 completed / elapsed)
    else:
        log.info("Done: %d scored", completed)

    # Score distribution from candidate_scores
    dist = conn.execute("""
        SELECT fit_score, COUNT(*) FROM candidate_scores
        WHERE candidate_id = ?
        GROUP BY fit_score ORDER BY fit_score DESC
    """, (cid,)).fetchall()
    distribution = [(row[0], row[1]) for row in dist]

    # Render score distribution summary table
    if distribution:
        table = Table(title=f'Fit Scoring Summary ({cid})', show_header=True, header_style='bold')
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

    # Log top rejected title patterns for this candidate
    low_score_titles = conn.execute(
        'SELECT j.title, COUNT(*) as cnt FROM candidate_scores cs '
        'JOIN jobs j ON j.url = cs.job_url '
        'WHERE cs.candidate_id = ? AND cs.fit_score <= 3 '
        'GROUP BY j.title ORDER BY cnt DESC LIMIT 5', (cid,)
    ).fetchall()
    if low_score_titles:
        log.info('Top filtered (score ≤ 3): %s',
                 ', '.join(f'{row[0][:35]} ({row[1]})' for row in low_score_titles))

    return distribution


def run_scoring(limit: int = 0, rescore: bool = False,
                candidate_id: str | None = None) -> dict:
    """Score unscored jobs for a specific candidate.

    Scores are committed to the candidate_scores table **immediately** after
    each job is scored, so progress is never lost if the process is interrupted
    (Ctrl+C, API credit exhaustion, etc.).

    Args:
        limit: Maximum number of jobs to score in this run.
        rescore: If True, re-score all jobs (not just unscored ones).
        candidate_id: Candidate to score for. Uses active candidate if None.

    Returns:
        {"scored": int, "errors": int, "elapsed": float, "distribution": list}
    """
    cid = candidate_id or get_active_candidate_id()

    # Load candidate-specific resume
    resume_path = get_candidate_resume_path(cid)
    if resume_path.exists():
        resume_text = resume_path.read_text(encoding="utf-8")
    elif RESUME_PATH.exists():
        # Fallback to legacy resume
        resume_text = RESUME_PATH.read_text(encoding="utf-8")
    else:
        log.error("No resume found for candidate '%s'", cid)
        return {"scored": 0, "errors": 0, "elapsed": 0.0, "distribution": []}

    conn = get_connection()

    if rescore:
        query = "SELECT * FROM jobs WHERE full_description IS NOT NULL"
        if limit > 0:
            query += f" LIMIT {limit}"
        jobs = conn.execute(query).fetchall()
    else:
        # Get jobs not yet scored for THIS candidate
        query = """
            SELECT j.* FROM jobs j
            WHERE j.full_description IS NOT NULL
              AND j.url NOT IN (
                  SELECT job_url FROM candidate_scores WHERE candidate_id = ?
              )
        """
        if limit > 0:
            query += f" LIMIT {limit}"
        jobs = conn.execute(query, (cid,)).fetchall()

    if not jobs:
        log.info("No unscored jobs with descriptions found for candidate '%s'.", cid)
        return {"scored": 0, "errors": 0, "elapsed": 0.0, "distribution": []}

    # Convert sqlite3.Row to dicts if needed
    if jobs and not isinstance(jobs[0], dict):
        columns = jobs[0].keys()
        jobs = [dict(zip(columns, row)) for row in jobs]

    log.info("Scoring %d jobs for candidate '%s' sequentially...", len(jobs), cid)
    t0 = time.time()
    completed = 0
    errors = 0
    consecutive_errors = 0

    # Track high-score count for progress logging
    high_scores = 0

    try:
        for job in jobs:
            try:
                result = score_job(resume_text, job)
            except QuotaExhaustedError as e:
                elapsed = time.time() - t0
                console.print(
                    f"\n[bold yellow]API Quota / Credits Exhausted:[/bold yellow] {e}\n"
                    f"[bold green]Stopping scoring stage gracefully at {completed}/{len(jobs)} jobs. "
                    f"All {completed} scored jobs are safely saved in the database.[/bold green]"
                )
                distribution = _print_scoring_summary(conn, completed, errors, elapsed, cid)
                return {
                    "status": "quota_exhausted",
                    "scored": completed,
                    "errors": errors,
                    "elapsed": elapsed,
                    "distribution": distribution,
                }

            completed += 1

            if result["score"] == 0:
                errors += 1
                consecutive_errors += 1
                if consecutive_errors >= 10:
                    elapsed = time.time() - t0
                    console.print(
                        f"\n[bold yellow]10 consecutive LLM failures encountered. Pausing scoring run.[/bold yellow]\n"
                        f"[bold green]All {completed} scored jobs are safely saved in the database.[/bold green]"
                    )
                    distribution = _print_scoring_summary(conn, completed, errors, elapsed, cid)
                    return {
                        "status": "paused_consecutive_errors",
                        "scored": completed,
                        "errors": errors,
                        "elapsed": elapsed,
                        "distribution": distribution,
                    }
            else:
                consecutive_errors = 0

            if result["score"] >= 7:
                high_scores += 1

            # ── Commit to candidate_scores table immediately ──────────
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO candidate_scores (
                    candidate_id, job_url, fit_score, score_reasoning, scored_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(candidate_id, job_url) DO UPDATE SET
                    fit_score = excluded.fit_score,
                    score_reasoning = excluded.score_reasoning,
                    scored_at = excluded.scored_at
            """, (cid, job["url"], result["score"],
                  f"{result['keywords']}\n{result['reasoning']}", now))
            conn.commit()

            # Also update legacy jobs table for backwards compat
            conn.execute(
                "UPDATE jobs SET fit_score = ?, score_reasoning = ?, scored_at = ? WHERE url = ?",
                (result["score"],
                 f"{result['keywords']}\n{result['reasoning']}",
                 now, job["url"]),
            )
            conn.commit()

            log.info(
                "[%d/%d] score=%d  %s  (candidate: %s)",
                completed, len(jobs), result["score"], job.get("title", "?")[:60], cid,
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
        distribution = _print_scoring_summary(conn, completed, errors, elapsed, cid)
        return {
            "status": "interrupted",
            "scored": completed,
            "errors": errors,
            "elapsed": elapsed,
            "distribution": distribution,
        }

    elapsed = time.time() - t0
    distribution = _print_scoring_summary(conn, completed, errors, elapsed, cid)

    return {
        "status": "ok",
        "scored": completed,
        "errors": errors,
        "elapsed": elapsed,
        "distribution": distribution,
    }


