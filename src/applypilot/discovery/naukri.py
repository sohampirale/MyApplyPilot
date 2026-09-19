"""Naukri India Playwright Stealth Scraper.

Extracts job postings from Naukri India using Playwright Chromium with Chrome 122 stealth
headers, extracting job title, company, location, experience range, salary, and description tags.
Directly ingests discovered jobs into SQLite database.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from applypilot.database import get_connection, store_jobs
from applypilot.utils.stealth import CHROME_STEALTH_HEADERS, apply_playwright_stealth

log = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Convert search term to Naukri URL slug (lowercase, hyphenated)."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    return re.sub(r"[-\s]+", "-", clean)


def build_naukri_url(query: str, location: str, page_num: int = 1, experience: int | None = None) -> str:
    """Construct standard Naukri India search URL."""
    q_slug = _slugify(query)
    
    # Clean location slug (e.g. "Pune, Maharashtra" -> "pune")
    loc_clean = location.split(",")[0].strip()
    l_slug = _slugify(loc_clean)
    
    if page_num > 1:
        base = f"https://www.naukri.com/{q_slug}-jobs-in-{l_slug}-{page_num}"
    else:
        base = f"https://www.naukri.com/{q_slug}-jobs-in-{l_slug}"
        
    if experience is not None:
        base = f"{base}?experience={experience}"
        
    return base


def scrape_naukri_query(
    query: str,
    location: str,
    domain: str = "engineering",
    max_pages: int = 1,
    experience: int | None = None,
    delay_sec: float = 3.0,
) -> dict:
    """Scrape Naukri India for a given query and location across pages.
    
    Returns:
        dict with keys: 'new', 'existing', 'total_cards', 'errors'
    """
    stats = {"new": 0, "existing": 0, "total_cards": 0, "errors": 0}
    conn = get_connection()
    now_iso = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=CHROME_STEALTH_HEADERS["User-Agent"],
            extra_http_headers={
                "Accept-Language": CHROME_STEALTH_HEADERS["Accept-Language"],
                "Sec-Ch-Ua": CHROME_STEALTH_HEADERS["Sec-Ch-Ua"],
                "Sec-Ch-Ua-Platform": CHROME_STEALTH_HEADERS["Sec-Ch-Ua-Platform"],
            },
        )
        page = context.new_page()
        apply_playwright_stealth(page)

        for p_idx in range(1, max_pages + 1):
            url = build_naukri_url(query, location, page_num=p_idx, experience=experience)
            log.info("[Naukri] Fetching %s (page %d)...", url, p_idx)

            try:
                page.goto(url, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(3500)
                
                # Check for bot block
                page_title = page.title()
                if "Access Denied" in page_title or "Security Check" in page_title:
                    log.warning("[Naukri] Bot detection triggered on page %d: %s", p_idx, page_title)
                    stats["errors"] += 1
                    break

                cards = page.query_selector_all(".srp-jobtuple-wrapper, .cust-job-tuple, article.jobTuple")
                if not cards:
                    log.info("[Naukri] No job cards found on page %d. Stopping pagination.", p_idx)
                    break

                stats["total_cards"] += len(cards)
                page_jobs: list[dict] = []

                for c in cards:
                    title_el = c.query_selector("a.title")
                    comp_el = c.query_selector("a.comp-name, .companyInfo a")
                    loc_el = c.query_selector(".loc-wrap, span.locWdth, .location")
                    exp_el = c.query_selector(".exp-wrap, .experience")
                    sal_el = c.query_selector(".sal-wrap, .salary")
                    desc_el = c.query_selector(".job-desc, .job-description, .row6")
                    tags_els = c.query_selector_all(".tags-gt li, .dot-gt li")

                    job_title = title_el.inner_text().strip() if title_el else ""
                    job_url = title_el.get_attribute("href") if title_el else ""
                    if not job_url or not job_title:
                        continue

                    # Clean tracking params from URL
                    job_url = job_url.split("?")[0]
                    company = comp_el.inner_text().strip() if comp_el else "Unknown"
                    job_loc = loc_el.inner_text().strip() if loc_el else location
                    exp_text = exp_el.inner_text().strip() if exp_el else ""
                    sal_text = sal_el.inner_text().strip() if sal_el else ""
                    desc_snippet = desc_el.inner_text().strip() if desc_el else ""
                    skills = [t.inner_text().strip() for t in tags_els if t.inner_text().strip()]

                    full_desc = f"{desc_snippet}\n\nExperience: {exp_text}\nSkills: {', '.join(skills)}"

                    page_jobs.append({
                        "url": job_url,
                        "title": job_title,
                        "company": company,
                        "location": job_loc,
                        "salary": sal_text,
                        "description": full_desc,
                        "site": "naukri",
                        "strategy": "naukri_playwright",
                        "domain": domain,
                        "discovered_at": now_iso,
                    })

                # Ingest into SQLite
                if page_jobs:
                    # Filter existing to calculate new vs existing
                    urls = [j["url"] for j in page_jobs]
                    placeholders = ",".join("?" * len(urls))
                    existing_urls = set(
                        r[0] for r in conn.execute(
                            f"SELECT url FROM jobs WHERE url IN ({placeholders})", urls
                        ).fetchall()
                    )

                    new_jobs = [j for j in page_jobs if j["url"] not in existing_urls]
                    dupes_count = len(page_jobs) - len(new_jobs)

                    store_jobs(conn, page_jobs, site="naukri", strategy="naukri_playwright", domain=domain)
                    stats["new"] += len(new_jobs)
                    stats["existing"] += dupes_count
                    log.info("[Naukri] Page %d: %d results -> %d new, %d dupes", p_idx, len(page_jobs), len(new_jobs), dupes_count)

                time.sleep(delay_sec)

            except Exception as e:
                log.warning("[Naukri] Error fetching page %d: %s", p_idx, e)
                stats["errors"] += 1
                break

        browser.close()

    return stats
