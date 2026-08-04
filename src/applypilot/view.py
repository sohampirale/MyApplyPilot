"""ApplyPilot HTML Dashboard Generator.

Generates a self-contained HTML dashboard with:
  - Summary stats (total, enriched, scored, high-fit)
  - Score distribution bar chart
  - Jobs-by-source breakdown
  - Filterable job cards grouped by score
  - Client-side search, score, and site filtering
  - Modern modal dialog for job detail viewing
"""

from __future__ import annotations

import os
import webbrowser
from html import escape
from pathlib import Path
from urllib.parse import quote as url_quote

from rich.console import Console

from applypilot.config import (
    APP_DIR, DB_PATH, PROFILE_PATH, RESUME_PATH, RESUME_PDF_PATH,
    get_active_candidate_id, list_candidates, set_active_candidate_id,
    get_candidate_profile_path, get_candidate_resume_path,
    get_candidate_resume_pdf_path, load_candidate_profile,
    migrate_legacy_profile,
)
from applypilot.database import get_connection

console = Console()


def _clean_resume_spacing(text: str) -> str:
    """Clean up spacing artifacts in resume text if present."""
    import re
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        if re.search(r'\b[A-Za-z] [A-Za-z] [A-Za-z]\b', line):
            parts = line.split('  ')
            cleaned_parts = [re.sub(r'(?<=\S) (?=\S)', '', part) for part in parts]
            cleaned.append('  '.join(cleaned_parts))
        else:
            cleaned.append(line)
    return "\n".join(cleaned)


def _build_profile_page_html(profile: dict, resume_text: str, resume_pdf_b64: str = "") -> str:
    """Build full-screen Candidate Profile Page view with embedded PDF resume viewer."""
    personal = profile.get("personal", {})
    work_auth = profile.get("work_authorization", {})
    comp = profile.get("compensation", {})
    exp = profile.get("experience", {})
    skills = profile.get("skills_boundary", {})
    eeo = profile.get("eeo_voluntary", {})
    avail = profile.get("availability", {})

    full_name = escape(personal.get("full_name") or "Candidate Profile")
    pref_name = escape(personal.get("preferred_name") or "")
    email = escape(personal.get("email") or "Not configured")
    phone = escape(personal.get("phone") or "Not configured")
    city = escape(personal.get("city") or "")
    state = escape(personal.get("province_state") or "")
    country = escape(personal.get("country") or "India")
    location = ", ".join(p for p in [city, state, country] if p) or "Not specified"
    address = escape(personal.get("address") or location)

    linkedin = escape(personal.get("linkedin_url") or "")
    github = escape(personal.get("github_url") or "")
    portfolio = escape(personal.get("portfolio_url") or "")
    password = personal.get("password") or ""

    auth_str = "Yes" if work_auth.get("legally_authorized_to_work") else "No / Pending"
    sponsorship = "Yes" if work_auth.get("require_sponsorship") else "No"
    permit = escape(str(work_auth.get("work_permit_type") or "Citizen"))
    start_date = escape(str(avail.get("earliest_start_date") or "Immediately"))

    def _format_inr(val_str: str) -> str:
        try:
            num = int(float(str(val_str).replace(",", "").replace("INR", "").strip()))
            if num >= 100000:
                lakhs = num / 100000
                return f"₹{lakhs:.1f} LPA"
            return f"₹{num:,}"
        except (ValueError, TypeError):
            return str(val_str)

    raw_exp_sal = comp.get("salary_expectation") or ""
    raw_min_sal = comp.get("salary_range_min") or ""
    raw_max_sal = comp.get("salary_range_max") or ""
    curr = escape(str(comp.get("salary_currency") or "INR"))

    exp_sal = f"{_format_inr(raw_exp_sal)} ({int(float(raw_exp_sal)):,} {curr})" if raw_exp_sal and raw_exp_sal.isdigit() else escape(str(raw_exp_sal or "N/A"))
    min_sal_fmt = _format_inr(raw_min_sal) if raw_min_sal else "N/A"
    max_sal_fmt = _format_inr(raw_max_sal) if raw_max_sal else "N/A"
    sal_range = f"{min_sal_fmt} - {max_sal_fmt} {curr}"

    yoe = escape(str(exp.get("years_of_experience_total") or "0"))
    edu = escape(str(exp.get("education_level") or "Bachelor's"))
    curr_title = escape(str(exp.get("current_title") or "Software Engineer / Fresher"))
    target_role = escape(str(exp.get("target_role") or "Software Engineer"))

    langs = skills.get("programming_languages") or skills.get("languages") or []
    frameworks = skills.get("frameworks") or []
    tools = skills.get("tools") or skills.get("databases") or []

    lang_chips = "".join(f'<span class="skill-chip">{escape(str(s))}</span>' for s in langs)
    fw_chips = "".join(f'<span class="skill-chip framework">{escape(str(s))}</span>' for s in frameworks)
    tool_chips = "".join(f'<span class="skill-chip tool">{escape(str(s))}</span>' for s in tools)

    cleaned_resume = _clean_resume_spacing(resume_text) if resume_text else "No master resume text found at ~/.applypilot/resume.txt"
    resume_display = escape(cleaned_resume)

    has_pdf = bool(resume_pdf_b64)

    pdf_viewer_markup = f"""
    <div id="pdf-resume-frame-container" style="flex:1;min-height:750px;display:flex;">
      <iframe src="data:application/pdf;base64,{resume_pdf_b64}#toolbar=1&navpanes=0&view=FitH"
              style="width:100%;height:100%;min-height:750px;border:none;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,0.5);"
              title="Master Resume PDF">
      </iframe>
    </div>
    """ if has_pdf else ""

    text_viewer_markup = f"""
    <div id="text-resume-frame-container" class="{"hidden" if has_pdf else ""}" style="flex:1;">
      <pre id="master-resume-text-el" class="resume-viewer-full">{resume_display}</pre>
    </div>
    """

    return f"""
<!-- Full-Screen Candidate Profile Page -->
<div id="profile-page-view" class="profile-page-container hidden">
  <div class="profile-page-navbar">
    <div class="profile-nav-left">
      <button class="btn-back" onclick="showDashboardView()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        Back to Dashboard
      </button>
      <div class="profile-page-title-group">
        <h1 class="profile-page-title">👤 Candidate Profile</h1>
        <span class="profile-page-subtitle">{full_name} &middot; {location}</span>
      </div>
    </div>
    <div class="profile-nav-right">
      <span class="profile-pill-badge">{target_role}</span>
    </div>
  </div>

  <div class="profile-page-content">
    <!-- Left Column: Candidate Metadata Cards -->
    <div class="profile-sidebar-col">
      
      <!-- Personal & Contact Card -->
      <div class="profile-card">
        <h3 class="profile-card-title">🧑 Personal & Contact</h3>
        <div class="profile-field"><span class="profile-field-label">Full Name:</span><span class="profile-field-value">{full_name} ({pref_name})</span></div>
        <div class="profile-field"><span class="profile-field-label">Email:</span><span class="profile-field-value">{email}</span></div>
        <div class="profile-field"><span class="profile-field-label">Phone:</span><span class="profile-field-value">{phone}</span></div>
        <div class="profile-field"><span class="profile-field-label">Location:</span><span class="profile-field-value">{location}</span></div>
        <div class="profile-field"><span class="profile-field-label">Full Address:</span><span class="profile-field-value">{address}</span></div>
        <div class="profile-field"><span class="profile-field-label">LinkedIn:</span><span class="profile-field-value">{f'<a href="{linkedin}" target="_blank">{linkedin}</a>' if linkedin else 'Not provided'}</span></div>
        <div class="profile-field"><span class="profile-field-label">GitHub:</span><span class="profile-field-value">{f'<a href="{github}" target="_blank">{github}</a>' if github else 'Not provided'}</span></div>
      </div>

      <!-- Career & Compensation Card -->
      <div class="profile-card">
        <h3 class="profile-card-title">💼 Career & Compensation</h3>
        <div class="profile-field"><span class="profile-field-label">Target Role:</span><span class="profile-field-value" style="color:#60a5fa;font-weight:600;">{target_role}</span></div>
        <div class="profile-field"><span class="profile-field-label">Experience:</span><span class="profile-field-value">{yoe} years &middot; {edu}</span></div>
        <div class="profile-field"><span class="profile-field-label">Target Salary:</span><span class="profile-field-value" style="color:#10b981;font-weight:600;">{exp_sal}</span></div>
        <div class="profile-field"><span class="profile-field-label">Acceptable Range:</span><span class="profile-field-value">{sal_range}</span></div>
        <div class="profile-field"><span class="profile-field-label">Authorized to Work:</span><span class="profile-field-value">{auth_str} ({permit})</span></div>
        <div class="profile-field"><span class="profile-field-label">Start Date:</span><span class="profile-field-value">{start_date}</span></div>
      </div>

      <!-- Skills Card -->
      <div class="profile-card">
        <h3 class="profile-card-title">🛠 Technical Skill Boundary</h3>
        <div class="profile-field-stacked">
          <span class="profile-field-label">Languages:</span>
          <div class="skill-chips">{lang_chips or 'None'}</div>
        </div>
        <div class="profile-field-stacked">
          <span class="profile-field-label">Frameworks:</span>
          <div class="skill-chips">{fw_chips or 'None'}</div>
        </div>
        <div class="profile-field-stacked">
          <span class="profile-field-label">Tools & Databases:</span>
          <div class="skill-chips">{tool_chips or 'None'}</div>
        </div>
      </div>

      <!-- Security & Credentials Card -->
      <div class="profile-card">
        <h3 class="profile-card-title">🔒 Credentials & Privacy</h3>
        <div class="profile-field">
          <span class="profile-field-label">Stored Password:</span>
          <div class="profile-field-value password-field">
            <span id="profile-password-value" data-real="{escape(password)}" data-masked="true">••••••••</span>
            <button id="profile-password-toggle" class="password-toggle" onclick="togglePasswordMask()">👁 Show</button>
          </div>
        </div>
        <div class="privacy-notice">
          <span>🔒</span>
          <div>
            <strong>Local Privacy Guarantee</strong><br>
            All candidate data is stored locally at <code>~/.applypilot/profile.json</code> and <code>resume.pdf</code>. It never leaves your device.
          </div>
        </div>
      </div>

    </div>

    <!-- Right Column: Full Master Resume PDF/Text Viewer -->
    <div class="profile-main-col">
      <div class="profile-card resume-card-container">
        <div class="resume-card-header">
          <div>
            <h3 class="profile-card-title" style="margin:0;border-bottom:none;">📄 Master Resume {"(PDF)" if has_pdf else "(Text)"}</h3>
            <span style="font-size:0.75rem;color:var(--text-muted);">Stored at ~/.applypilot/{"resume.pdf" if has_pdf else "resume.txt"}</span>
          </div>
          <div style="display:flex;gap:0.5rem;align-items:center;">
            {f'<button class="btn-secondary" onclick="toggleResumeView()">🔄 Switch View (PDF/Text)</button>' if has_pdf else ''}
            {f'<a href="data:application/pdf;base64,{resume_pdf_b64}" download="Master_Resume.pdf" class="btn-secondary" style="text-decoration:none;">📥 Download PDF</a>' if has_pdf else ''}
          </div>
        </div>

        {pdf_viewer_markup}
        {text_viewer_markup}
      </div>
    </div>
  </div>
</div>
"""



def generate_dashboard(output_path: str | None = None,
                       candidate_id: str | None = None) -> str:
    """Generate an HTML dashboard of all jobs with fit scores.

    Args:
        output_path: Where to write the HTML file. Defaults to ~/.applypilot/dashboard.html.
        candidate_id: Candidate to generate dashboard for. Uses active if None.

    Returns:
        Absolute path to the generated HTML file.
    """
    # Ensure legacy profile is migrated
    migrate_legacy_profile()

    cid = candidate_id or get_active_candidate_id()
    out = Path(output_path) if output_path else APP_DIR / "dashboard.html"

    conn = get_connection()

    # Load candidate-specific profile & resume
    import json as _json
    profile_data: dict = {}
    try:
        profile_data = load_candidate_profile(cid)
    except Exception:
        try:
            if PROFILE_PATH.exists():
                profile_data = _json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Candidate-specific resume paths
    candidate_resume_path = get_candidate_resume_path(cid)
    candidate_pdf_path = get_candidate_resume_pdf_path(cid)

    resume_raw_text = ""
    try:
        if candidate_resume_path.exists():
            resume_raw_text = candidate_resume_path.read_text(encoding="utf-8")
        elif RESUME_PATH.exists():
            resume_raw_text = RESUME_PATH.read_text(encoding="utf-8")
    except Exception:
        pass

    import base64
    resume_pdf_b64 = ""
    try:
        if candidate_pdf_path.exists():
            pdf_bytes = candidate_pdf_path.read_bytes()
            resume_pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        elif RESUME_PDF_PATH.exists():
            pdf_bytes = RESUME_PDF_PATH.read_bytes()
            resume_pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    except Exception:
        pass

    # Build candidate switcher data
    all_candidates = list_candidates()
    candidate_name = cid
    for c in all_candidates:
        if c["id"] == cid:
            candidate_name = c.get("preferred_name") or c.get("name") or cid
            break

    from applypilot.domains import get_domain_for_candidate
    domain = get_domain_for_candidate(cid)

    # Stats — candidate and domain-specific from candidate_scores & jobs pool
    total = conn.execute("SELECT COUNT(*) FROM jobs WHERE domain = ?", (domain,)).fetchone()[0]
    ready = conn.execute(
        "SELECT COUNT(*) FROM jobs "
        "WHERE full_description IS NOT NULL AND application_url IS NOT NULL AND domain = ?", (domain,)
    ).fetchone()[0]
    scored = conn.execute(
        "SELECT COUNT(*) FROM candidate_scores cs "
        "JOIN jobs j ON j.url = cs.job_url "
        "WHERE cs.candidate_id = ? AND j.domain = ?", (cid, domain)
    ).fetchone()[0]
    high_fit = conn.execute(
        "SELECT COUNT(*) FROM candidate_scores cs "
        "JOIN jobs j ON j.url = cs.job_url "
        "WHERE cs.candidate_id = ? AND cs.fit_score >= 7 AND j.domain = ?", (cid, domain)
    ).fetchone()[0]

    # Score distribution for this candidate (domain filtered)
    score_dist: dict[int, int] = {}
    if scored:
        rows = conn.execute(
            "SELECT cs.fit_score, COUNT(*) FROM candidate_scores cs "
            "JOIN jobs j ON j.url = cs.job_url "
            "WHERE cs.candidate_id = ? AND j.domain = ? "
            "GROUP BY cs.fit_score ORDER BY cs.fit_score DESC", (cid, domain)
        ).fetchall()
        for r in rows:
            score_dist[r[0]] = r[1]

    # Site stats for this candidate (domain filtered)
    site_stats = conn.execute("""
        SELECT j.site,
               COUNT(*) as total,
               SUM(CASE WHEN cs.fit_score >= 7 THEN 1 ELSE 0 END) as high_fit,
               SUM(CASE WHEN cs.fit_score BETWEEN 5 AND 6 THEN 1 ELSE 0 END) as mid_fit,
               SUM(CASE WHEN cs.fit_score < 5 THEN 1 ELSE 0 END) as low_fit,
               0 as unscored,
               ROUND(AVG(cs.fit_score), 1) as avg_score
        FROM candidate_scores cs
        JOIN jobs j ON j.url = cs.job_url
        WHERE cs.candidate_id = ? AND j.domain = ?
        GROUP BY j.site ORDER BY high_fit DESC, total DESC
    """, (cid, domain)).fetchall()

    # All scored jobs for this candidate (1+) in their domain, ordered by score desc
    jobs = conn.execute("""
        SELECT j.url, j.title, j.salary, j.description, j.location, j.site, j.strategy,
               j.full_description, j.application_url, j.detail_error,
               cs.fit_score, cs.score_reasoning, cs.tailored_resume_path
        FROM candidate_scores cs
        JOIN jobs j ON j.url = cs.job_url
        WHERE cs.candidate_id = ? AND cs.fit_score >= 1 AND j.domain = ?
        ORDER BY cs.fit_score DESC, j.site, j.title
    """, (cid, domain)).fetchall()

    # Color map per site
    colors = {
        "RemoteOK": "#10b981", "WelcomeToTheJungle": "#f59e0b",
        "Job Bank Canada": "#3b82f6", "CareerJet Canada": "#8b5cf6",
        "Hacker News Jobs": "#ff6600", "BuiltIn Remote": "#ec4899",
        "TD Bank": "#00a651", "CIBC": "#c41f3e", "RBC": "#003168",
        "indeed": "#2164f3", "linkedin": "#0a66c2",
        "Dice": "#eb1c26", "Glassdoor": "#0caa41",
    }

    # Extract unique site options for dropdown filter
    unique_sites = sorted(list({j["site"] for j in jobs if j["site"]}))

    # Site dropdown options HTML
    site_options_html = '<option value="">All Sources</option>'
    for site_item in unique_sites:
        site_options_html += f'<option value="{escape(site_item)}">{escape(site_item)}</option>'

    # Score distribution bar chart
    score_bars = ""
    max_count = max(score_dist.values()) if score_dist else 1
    for s in range(10, 0, -1):
        count = score_dist.get(s, 0)
        pct = (count / max_count * 100) if max_count else 0
        score_color = "#10b981" if s >= 7 else ("#f59e0b" if s >= 5 else "#ef4444")
        score_bars += f"""
        <div class="score-row" onclick="filterExactScore({s})" title="Click to view score {s} jobs">
          <span class="score-label">{s}</span>
          <div class="score-bar-track">
            <div class="score-bar-fill" style="width:{pct}%;background:{score_color}"></div>
          </div>
          <span class="score-count">{count}</span>
        </div>"""

    # Site stats rows
    site_rows = ""
    for s in site_stats:
        site = s["site"] or "?"
        color = colors.get(site, "#818cf8")
        avg = s["avg_score"] or 0
        site_rows += f"""
        <div class="site-row" onclick="filterBySite('{escape(site)}')" title="Click to filter by {escape(site)}">
          <div class="site-header-flex">
            <span class="site-name" style="color:{color}">{escape(site)}</span>
            <span class="site-avg-badge">avg {avg}</span>
          </div>
          <div class="site-nums">{s['total']} jobs &middot; {s['high_fit']} strong fit</div>
          <div class="bar-track">
            <div class="bar-fill" style="width:{s['high_fit']/max(s['total'],1)*100}%;background:{color}"></div>
            <div class="bar-fill" style="width:{s['mid_fit']/max(s['total'],1)*100}%;background:{color}77"></div>
          </div>
        </div>"""

    # Job cards grouped by score
    job_sections = ""
    current_score = None
    for idx, j in enumerate(jobs):
        score = j["fit_score"] or 0
        if score != current_score:
            if current_score is not None:
                job_sections += "</div>"
            score_color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")
            score_label = {
                10: "Perfect Match", 9: "Excellent Fit", 8: "Strong Fit",
                7: "Good Fit", 6: "Moderate+", 5: "Moderate",
                4: "Low-Moderate", 3: "Low Fit", 2: "Weak Match", 1: "Poor Fit",
            }.get(score, f"Score {score}")
            count_at_score = score_dist.get(score, 0)
            job_sections += f"""
            <div class="score-section-wrapper" data-score-header="{score}">
              <h2 class="score-header" style="border-color:{score_color}">
                <span class="score-badge" style="background:{score_color}">{score}</span>
                <span class="score-title-text">{score_label}</span>
                <span class="score-count-pill">{count_at_score} jobs</span>
              </h2>
            </div>
            <div class="job-grid" data-score="{score}">"""
            current_score = score

        title = escape(j["title"] or "Untitled")
        url = escape(j["url"] or "")
        salary = escape(j["salary"] or "")
        location = escape(j["location"] or "")
        site = escape(j["site"] or "")
        site_color = colors.get(j["site"] or "", "#818cf8")
        apply_url = escape(j["application_url"] or j["url"] or "")

        # Parse keywords and reasoning from score_reasoning
        reasoning_raw = j["score_reasoning"] or ""
        reasoning_lines = [line.strip() for line in reasoning_raw.split("\n") if line.strip()]
        keywords_str = reasoning_lines[0] if reasoning_lines else ""
        reasoning_str = reasoning_lines[1] if len(reasoning_lines) > 1 else ""

        # Format keyword chips
        keyword_chips_html = ""
        if keywords_str:
            kw_list = [k.strip() for k in keywords_str.split(",") if k.strip()][:5]
            for kw in kw_list:
                keyword_chips_html += f'<span class="kw-chip">{escape(kw)}</span>'

        desc_text = j["full_description"] or ""
        desc_preview = escape(desc_text[:220])
        full_desc_html = escape(desc_text).replace("\n", "<br>")

        has_resume = bool(j["tailored_resume_path"])

        meta_parts = []
        meta_parts.append(
            f'<span class="meta-tag site-tag" style="background:{site_color}18;color:{site_color};border:1px solid {site_color}44">{site}</span>'
        )
        if has_resume:
            meta_parts.append('<span class="meta-tag resume-ready">📄 Resume Ready</span>')
        else:
            meta_parts.append('<span class="meta-tag resume-auto">⚡ Auto-Tailors on Apply</span>')
        if salary:
            meta_parts.append(f'<span class="meta-tag salary">💰 {salary}</span>')
        if location:
            meta_parts.append(f'<span class="meta-tag location">📍 {location[:35]}</span>')
        meta_html = " ".join(meta_parts)

        apply_html = ""
        if apply_url:
            if has_resume:
                apply_html = f'<a href="{apply_url}" class="btn-primary apply-link" target="_blank">Apply <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></a>'
            else:
                apply_html = f'<button class="btn-primary tailor-apply-btn" onclick="tailorAndApply(this, \'{url}\', \'{apply_url}\')">⚡ Tailor & Apply</button>'

        card_id = f"job-card-{idx}"

        job_sections += f"""
        <div class="job-card" id="{card_id}" data-score="{score}" data-site="{escape(j['site'] or '')}" data-location="{location.lower()}">
          <div class="card-header">
            <span class="score-pill score-{score}">{score}</span>
            <a href="{url}" class="job-title" target="_blank" title="{title}">{title}</a>
          </div>
          <div class="meta-row">{meta_html}</div>
          {f'<div class="keywords-cloud">{keyword_chips_html}</div>' if keyword_chips_html else ''}
          {f'<div class="reasoning-box"><span class="reasoning-icon">💡</span> <span class="reasoning-text">{escape(reasoning_str)}</span></div>' if reasoning_str else ''}
          <p class="desc-preview">{desc_preview}...</p>
          
          <div class="full-desc-raw" style="display:none;">{full_desc_html}</div>
          <div class="full-title-raw" style="display:none;">{title}</div>
          <div class="apply-url-raw" style="display:none;">{apply_url}</div>
          <div class="job-url-raw" style="display:none;">{url}</div>

          <div class="card-footer">
            <div class="card-footer-left">
              <button class="btn-icon" onclick="copyLink('{apply_url}', this)" title="Copy Job Application Link">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              </button>
              {f'<a href="/job?url={url_quote(j["url"] or "", safe="")}" class="btn-secondary details-btn" style="text-decoration:none;">📄 View Details →</a>' if desc_text else ''}
            </div>
            <div class="card-footer-right">
              {apply_html}
            </div>
          </div>
        </div>"""

    if current_score is not None:
        job_sections += "</div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ApplyPilot Dashboard — AI Job Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-dark: #090d16;
    --bg-card: rgba(17, 24, 39, 0.75);
    --bg-card-hover: rgba(30, 41, 59, 0.85);
    --border-card: rgba(255, 255, 255, 0.08);
    --border-card-hover: rgba(96, 165, 250, 0.3);
    --primary: #3b82f6;
    --primary-hover: #2563eb;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #ef4444;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --text-sub: #6b7280;
    --font-heading: 'Plus Jakarta Sans', -apple-system, sans-serif;
    --font-body: 'Inter', -apple-system, sans-serif;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: var(--font-body);
    background: var(--bg-dark);
    background-image: 
      radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.12) 0px, transparent 50%),
      radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.08) 0px, transparent 50%),
      radial-gradient(at 50% 100%, rgba(139, 92, 246, 0.08) 0px, transparent 50%);
    background-attachment: fixed;
    color: var(--text-main);
    padding: 0;
    margin: 0;
    min-height: 100vh;
  }}

  /* Sticky Glass Navbar */
  .navbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(9, 13, 22, 0.82);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border-card);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
  }}

  .nav-right {{
    display: flex;
    align-items: center;
    gap: 1rem;
  }}

  .profile-nav-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1.1rem;
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.18), rgba(59, 130, 246, 0.18));
    border: 1px solid rgba(139, 92, 246, 0.4);
    color: #c4b5fd;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--font-body);
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
  }}
  .profile-nav-btn:hover {{
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.35), rgba(59, 130, 246, 0.35));
    border-color: rgba(139, 92, 246, 0.7);
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(139, 92, 246, 0.3);
  }}
  .avatar-circle {{
    font-size: 1.1rem;
  }}

  .brand {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }}
  .brand-logo {{
    width: 38px;
    height: 38px;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
  }}
  .brand-title {{
    font-family: var(--font-heading);
    font-weight: 800;
    font-size: 1.25rem;
    letter-spacing: -0.02em;
    background: linear-gradient(to right, #ffffff, #93c5fd);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  .live-badge {{
    font-size: 0.7rem;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(52, 211, 153, 0.3);
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-weight: 600;
  }}
  .live-dot {{
    width: 6px;
    height: 6px;
    background: #34d399;
    border-radius: 50%;
    box-shadow: 0 0 8px #34d399;
    animation: pulse 2s infinite;
  }}

  @keyframes pulse {{
    0% {{ transform: scale(0.95); opacity: 0.8; }}
    50% {{ transform: scale(1.15); opacity: 1; }}
    100% {{ transform: scale(0.95); opacity: 0.8; }}
  }}

  .container {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 2rem;
  }}

  /* Top Stats Cards */
  .summary-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.25rem;
    margin-bottom: 2.5rem;
  }}
  .stat-card {{
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 1.5rem;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
  }}
  .stat-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  }}
  .stat-card:hover {{
    transform: translateY(-3px);
    border-color: rgba(255,255,255,0.18);
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
  }}
  .stat-card.stat-total::before {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}
  .stat-card.stat-ready::before {{ background: linear-gradient(90deg, #10b981, #34d399); }}
  .stat-card.stat-scored::before {{ background: linear-gradient(90deg, #8b5cf6, #a78bfa); }}
  .stat-card.stat-high::before {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}

  .stat-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }}
  .stat-icon {{
    font-size: 1.25rem;
    opacity: 0.8;
  }}
  .stat-num {{
    font-family: var(--font-heading);
    font-size: 2.25rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.03em;
  }}
  .stat-card.stat-total .stat-num {{ color: #f3f4f6; }}
  .stat-card.stat-ready .stat-num {{ color: #34d399; }}
  .stat-card.stat-scored .stat-num {{ color: #a78bfa; }}
  .stat-card.stat-high .stat-num {{ color: #fbbf24; }}

  .stat-label {{
    color: var(--text-muted);
    font-size: 0.825rem;
    font-weight: 500;
  }}

  /* Filter Toolbar */
  .toolbar {{
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 2rem;
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
  }}
  .filter-group {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }}
  .filter-label {{
    color: var(--text-muted);
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-right: 0.25rem;
  }}
  .filter-btn {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--text-muted);
    padding: 0.45rem 0.9rem;
    border-radius: 10px;
    cursor: pointer;
    font-size: 0.825rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }}
  .filter-btn:hover {{
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-main);
  }}
  .filter-btn.active {{
    background: #3b82f6;
    color: #ffffff;
    border-color: #60a5fa;
    box-shadow: 0 0 16px rgba(59, 130, 246, 0.4);
    font-weight: 600;
  }}

  .site-select {{
    background: rgba(17, 24, 39, 0.9);
    border: 1px solid var(--border-card);
    color: var(--text-main);
    padding: 0.45rem 0.9rem;
    border-radius: 10px;
    font-size: 0.825rem;
    outline: none;
    cursor: pointer;
  }}

  .search-wrapper {{
    position: relative;
    display: flex;
    align-items: center;
  }}
  .search-icon {{
    position: absolute;
    left: 0.85rem;
    color: var(--text-sub);
    pointer-events: none;
  }}
  .search-input {{
    background: rgba(17, 24, 39, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: var(--text-main);
    padding: 0.5rem 1rem 0.5rem 2.4rem;
    border-radius: 10px;
    font-size: 0.85rem;
    width: 260px;
    transition: all 0.2s ease;
  }}
  .search-input:focus {{
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 16px rgba(59, 130, 246, 0.3);
    width: 300px;
  }}
  .search-input::placeholder {{ color: var(--text-sub); }}

  /* Analytics Dashboard Charts */
  .analytics-section {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 2.5rem;
  }}
  .analytics-card {{
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 1.5rem;
  }}
  .analytics-card h3 {{
    font-family: var(--font-heading);
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 1.25rem;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}

  /* Score Dist Row */
  .score-row {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
    padding: 0.25rem 0.4rem;
    border-radius: 6px;
    transition: background 0.15s;
  }}
  .score-row:hover {{
    background: rgba(255, 255, 255, 0.05);
  }}
  .score-label {{
    width: 1.5rem;
    text-align: right;
    font-size: 0.85rem;
    font-weight: 700;
  }}
  .score-bar-track {{
    flex: 1;
    height: 12px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    overflow: hidden;
  }}
  .score-bar-fill {{
    height: 100%;
    border-radius: 6px;
    transition: width 0.4s ease;
  }}
  .score-count {{
    width: 2.5rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: 600;
  }}

  /* Site Rows */
  .site-row {{
    margin-bottom: 0.85rem;
    cursor: pointer;
    padding: 0.4rem 0.5rem;
    border-radius: 8px;
    transition: background 0.15s;
  }}
  .site-row:hover {{
    background: rgba(255, 255, 255, 0.05);
  }}
  .site-header-flex {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .site-name {{
    font-weight: 700;
    font-size: 0.875rem;
  }}
  .site-avg-badge {{
    font-size: 0.725rem;
    color: var(--text-sub);
    background: rgba(255, 255, 255, 0.06);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
  }}
  .site-nums {{
    color: var(--text-muted);
    font-size: 0.75rem;
    margin: 0.2rem 0 0.4rem 0;
  }}
  .bar-track {{
    height: 6px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    display: flex;
    overflow: hidden;
  }}
  .bar-fill {{ height: 100%; transition: width 0.4s ease; }}

  /* Score Section Headers */
  .score-section-wrapper {{
    margin-top: 3rem;
    margin-bottom: 1.25rem;
  }}
  .score-header {{
    font-family: var(--font-heading);
    font-size: 1.25rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding-bottom: 0.6rem;
    border-bottom: 2px solid;
  }}
  .score-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.2rem;
    height: 2.2rem;
    border-radius: 10px;
    color: #0f172a;
    font-weight: 800;
    font-size: 1.05rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }}
  .score-title-text {{ flex: 1; color: var(--text-main); }}
  .score-count-pill {{
    font-size: 0.75rem;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.08);
    padding: 0.25rem 0.65rem;
    border-radius: 20px;
    font-weight: 600;
  }}

  /* Job Grid */
  .job-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 1.25rem;
  }}

  /* Job Cards */
  .job-card {{
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
  }}
  .job-card:hover {{
    transform: translateY(-4px);
    border-color: var(--border-card-hover);
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.45);
    background: var(--bg-card-hover);
  }}

  .card-header {{
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }}
  .score-pill {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.8rem;
    height: 1.8rem;
    border-radius: 8px;
    color: #0f172a;
    font-weight: 800;
    font-size: 0.85rem;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  }}
  .score-pill.score-10, .score-pill.score-9, .score-pill.score-8, .score-pill.score-7 {{
    background: #10b981;
  }}
  .score-pill.score-6, .score-pill.score-5 {{
    background: #f59e0b;
  }}
  .score-pill.score-4, .score-pill.score-3, .score-pill.score-2, .score-pill.score-1 {{
    background: #ef4444;
  }}

  .job-title {{
    color: var(--text-main);
    text-decoration: none;
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 1.025rem;
    line-height: 1.35;
    transition: color 0.15s;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}
  .job-title:hover {{
    color: #60a5fa;
  }}

  .meta-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.75rem;
  }}
  .meta-tag {{
    font-size: 0.725rem;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-weight: 500;
  }}
  .meta-tag.resume-ready {{ background: rgba(6, 78, 59, 0.6); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.3); }}
  .meta-tag.resume-auto {{ background: rgba(30, 58, 95, 0.6); color: #93c5fd; border: 1px solid rgba(147, 197, 253, 0.2); }}
  .meta-tag.salary {{ background: rgba(16, 185, 129, 0.1); color: #34d399; }}
  .meta-tag.location {{ background: rgba(59, 130, 246, 0.1); color: #93c5fd; }}

  /* Keyword Chips */
  .keywords-cloud {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-bottom: 0.75rem;
  }}
  .kw-chip {{
    font-size: 0.7rem;
    background: rgba(16, 185, 129, 0.12);
    color: #34d399;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    border: 1px solid rgba(52, 211, 153, 0.2);
  }}

  /* Reasoning Box */
  .reasoning-box {{
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 0.6rem 0.75rem;
    margin-bottom: 0.75rem;
    font-size: 0.775rem;
    color: var(--text-muted);
    line-height: 1.4;
    display: flex;
    gap: 0.4rem;
  }}
  .reasoning-icon {{ flex-shrink: 0; }}
  .reasoning-text {{ font-style: italic; }}

  .desc-preview {{
    font-size: 0.8rem;
    color: var(--text-sub);
    line-height: 1.5;
    margin-bottom: 1rem;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  /* Footer Actions */
  .card-footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    margin-top: auto;
  }}
  .card-footer-left {{ display: flex; gap: 0.4rem; align-items: center; }}
  .card-footer-right {{ display: flex; gap: 0.4rem; align-items: center; }}

  .btn-primary {{
    font-size: 0.8rem;
    font-weight: 600;
    color: #ffffff;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    border: 1px solid #60a5fa;
    border-radius: 8px;
    padding: 0.45rem 0.95rem;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    transition: all 0.2s ease;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
  }}
  .btn-primary:hover {{
    transform: translateY(-1px);
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5);
  }}
  .btn-primary:disabled {{
    opacity: 0.75;
    cursor: wait;
  }}

  .btn-secondary {{
    font-size: 0.775rem;
    font-weight: 500;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 0.4rem 0.75rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-secondary:hover {{
    background: rgba(255, 255, 255, 0.12);
    color: var(--text-main);
  }}

  .btn-icon {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-muted);
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-icon:hover {{
    background: rgba(255, 255, 255, 0.12);
    color: #60a5fa;
  }}

  /* Modal Dialog for Full Job Description */
  dialog#job-modal {{
    margin: auto;
    border: 1px solid var(--border-card-hover);
    border-radius: 20px;
    background: #0f172a;
    color: var(--text-main);
    padding: 2rem;
    max-width: 720px;
    width: 90vw;
    max-height: 85vh;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);

    /* Animation specs from Modern Web Guidance */
    opacity: 0;
    transform: scale(0.95);
    transition-property: opacity, transform, display, overlay;
    transition-duration: 0.25s;
    transition-timing-function: ease-out;
    transition-behavior: allow-discrete;
  }}

  dialog#job-modal[open] {{
    opacity: 1;
    transform: scale(1);

    @starting-style {{
      opacity: 0;
      transform: scale(0.95);
    }}
  }}

  dialog#job-modal::backdrop {{
    background-color: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(8px);
    transition: display 0.25s allow-discrete, overlay 0.25s allow-discrete, background-color 0.25s ease-out;
  }}

  .modal-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.25rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border-card);
  }}
  .modal-title {{
    font-family: var(--font-heading);
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.3;
  }}
  .modal-close-btn {{
    background: rgba(255, 255, 255, 0.08);
    border: none;
    color: var(--text-muted);
    width: 32px;
    height: 32px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
    flex-shrink: 0;
  }}
  .modal-close-btn:hover {{ background: rgba(255, 255, 255, 0.2); color: #fff; }}

  .modal-body {{
    font-size: 0.875rem;
    line-height: 1.65;
    color: #cbd5e1;
    max-height: 55vh;
    overflow-y: auto;
    padding-right: 0.5rem;
    white-space: pre-wrap;
    word-break: break-word;
  }}

  .modal-footer {{
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-card);
  }}

  /* Toast Notification */
  .toast-container {{
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }}
  .toast {{
    background: #1e293b;
    border: 1px solid #3b82f6;
    color: #ffffff;
    padding: 0.75rem 1.25rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 500;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    animation: toastIn 0.3s ease-out forwards;
  }}

  @keyframes toastIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  .hidden {{ display: none !important; }}
  .job-count-status {{
    color: var(--text-muted);
    font-size: 0.875rem;
    font-weight: 500;
    margin-bottom: 1.25rem;
  }}

  /* ── Full-Screen Profile Page ─────────────────────────────── */
  .profile-page-container {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 1000;
    background: var(--bg-dark);
    background-image: 
      radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.12) 0px, transparent 50%),
      radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.1) 0px, transparent 50%),
      radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
    background-attachment: fixed;
    color: var(--text-main);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }}

  .profile-page-navbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(9, 13, 22, 0.92);
    backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border-card);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }}

  .profile-nav-left {{
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }}

  .btn-back {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.55rem 1.25rem;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #60a5fa;
    border-radius: 12px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--font-body);
  }}
  .btn-back:hover {{
    background: rgba(59, 130, 246, 0.3);
    color: #ffffff;
    transform: translateX(-3px);
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
  }}

  .profile-page-title-group {{
    display: flex;
    flex-direction: column;
  }}
  .profile-page-title {{
    font-family: var(--font-heading);
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--text-main);
  }}
  .profile-page-subtitle {{
    font-size: 0.8rem;
    color: var(--text-muted);
  }}
  .profile-pill-badge {{
    padding: 0.4rem 0.9rem;
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.35);
    color: #c4b5fd;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
  }}

  .profile-page-content {{
    padding: 2rem;
    display: grid;
    grid-template-columns: 440px 1fr;
    gap: 1.5rem;
    flex: 1;
    max-width: 1600px;
    margin: 0 auto;
    width: 100%;
  }}

  .profile-card {{
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
  }}
  .profile-card-title {{
    font-family: var(--font-heading);
    font-size: 0.95rem;
    font-weight: 700;
    color: #a78bfa;
    margin-bottom: 0.85rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }}

  .profile-field {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.45rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    font-size: 0.85rem;
    line-height: 1.5;
  }}
  .profile-field:last-child {{
    border-bottom: none;
  }}
  .profile-field-label {{
    color: var(--text-muted);
    font-weight: 500;
    min-width: 130px;
    flex-shrink: 0;
  }}
  .profile-field-value {{
    color: var(--text-main);
    font-weight: 500;
    text-align: right;
    word-break: break-word;
  }}
  .profile-field-value a {{
    color: #60a5fa;
    text-decoration: none;
  }}
  .profile-field-value a:hover {{
    text-decoration: underline;
  }}

  .profile-field-stacked {{
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-bottom: 1rem;
  }}
  .profile-field-stacked:last-child {{
    margin-bottom: 0;
  }}

  .skill-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.2rem;
  }}
  .skill-chip {{
    display: inline-block;
    padding: 0.35rem 0.75rem;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.35);
    color: #93c5fd;
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.2px;
  }}
  .skill-chip.framework {{
    background: rgba(16, 185, 129, 0.15);
    border-color: rgba(16, 185, 129, 0.35);
    color: #6ee7b7;
  }}
  .skill-chip.tool {{
    background: rgba(245, 158, 11, 0.15);
    border-color: rgba(245, 158, 11, 0.35);
    color: #fcd34d;
  }}

  .password-field {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    justify-content: flex-end;
  }}
  .password-toggle {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: var(--text-muted);
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .password-toggle:hover {{ background: rgba(255, 255, 255, 0.18); color: #fff; }}

  .privacy-notice {{
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 12px;
    padding: 0.85rem 1rem;
    font-size: 0.8rem;
    color: #6ee7b7;
    margin-top: 1rem;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
    line-height: 1.5;
  }}

  .resume-card-container {{
    height: 100%;
    display: flex;
    flex-direction: column;
    margin-bottom: 0;
  }}
  .resume-card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }}

  .resume-viewer-full {{
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1.5rem;
    font-family: 'Cascadia Code', 'Fira Code', 'Courier New', monospace;
    font-size: 0.85rem;
    line-height: 1.7;
    color: #e2e8f0;
    white-space: pre-wrap;
    word-break: break-word;
    flex: 1;
    overflow-y: auto;
    max-height: calc(100vh - 220px);
  }}

  @media (max-width: 1100px) {{
    .profile-page-content {{
      grid-template-columns: 1fr;
    }}
  }}

  @media (max-width: 1024px) {{
    .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .analytics-section {{ grid-template-columns: 1fr; }}
    .job-grid {{ grid-template-columns: 1fr; }}
    .navbar {{ padding: 1rem; flex-direction: column; align-items: stretch; }}
    .nav-right {{ flex-wrap: wrap; }}
    .container {{ padding: 1rem; }}
    .profile-field {{ flex-direction: column; gap: 0.2rem; }}
    .profile-field-label {{ min-width: unset; }}
  }}
  /* ── Candidate Switcher ──────────────────────────────────── */
  .candidate-switcher-wrapper {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.25);
    border-radius: 12px;
    padding: 0.35rem 0.75rem;
  }}
  .switcher-label {{
    font-size: 0.82rem;
    font-weight: 600;
    color: #34d399;
    white-space: nowrap;
  }}
  .candidate-switcher-select {{
    background: rgba(17, 24, 39, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #f3f4f6;
    padding: 0.35rem 0.65rem;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
    outline: none;
    cursor: pointer;
    min-width: 120px;
    transition: all 0.2s;
  }}
  .candidate-switcher-select:hover {{
    border-color: rgba(16, 185, 129, 0.5);
  }}
  .candidate-switcher-select:focus {{
    border-color: #34d399;
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
  }}
  .btn-add-student {{
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.35);
    color: #34d399;
    width: 30px;
    height: 30px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
  }}
  .btn-add-student:hover {{
    background: rgba(16, 185, 129, 0.3);
    color: #fff;
    transform: scale(1.05);
  }}

</style>
</head>
<body>

<!-- Glass Navbar -->
<div class="navbar">
  <div class="brand">
    <div class="brand-logo">⚡</div>
    <div>
      <div class="brand-title">ApplyPilot</div>
      <div class="live-badge"><span class="live-dot"></span> Dashboard Active</div>
    </div>
  </div>

  <div class="nav-right">
    <div class="candidate-switcher-wrapper">
      <span class="switcher-label">🎓 Student:</span>
      <select id="candidate-switcher" class="candidate-switcher-select" onchange="switchCandidate(this.value)">
        {''.join(f'<option value="{escape(c["id"])}" {"selected" if c["id"] == cid else ""}>{escape(c.get("preferred_name") or c.get("name", c["id"]))} ({escape(c.get("target_role", ""))})</option>' for c in all_candidates)}
      </select>
      <button class="btn-add-student" onclick="openAddStudentModal()" title="Add a new student profile">➕</button>
    </div>
    <button class="profile-nav-btn" onclick="showProfileView()" title="View Candidate Profile & Master Resume">
      <span class="avatar-circle">👤</span> Candidate Profile
    </button>
    <div class="search-wrapper">
      <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="main-search" class="search-input" placeholder="Search titles, skills, locations... (/)" oninput="filterText(this.value)">
    </div>
  </div>
</div>

<!-- Add Student Modal -->
<dialog id="add-student-modal" style="margin:auto;border:1px solid rgba(96,165,250,0.3);border-radius:20px;background:#0f172a;color:#f3f4f6;padding:2rem;max-width:480px;width:90vw;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid rgba(255,255,255,0.08);">
    <h3 style="font-family:var(--font-heading);font-size:1.2rem;font-weight:700;">➕ Add New Student</h3>
    <button onclick="document.getElementById('add-student-modal').close()" style="background:rgba(255,255,255,0.08);border:none;color:#9ca3af;width:32px;height:32px;border-radius:50%;cursor:pointer;font-size:1.1rem;">×</button>
  </div>
  <div style="display:flex;flex-direction:column;gap:1rem;">
    <div>
      <label style="font-size:0.8rem;color:#9ca3af;display:block;margin-bottom:0.4rem;">Student ID (lowercase, no spaces)</label>
      <input id="new-student-id" type="text" placeholder="e.g. priya_pharmacy" style="width:100%;background:rgba(17,24,39,0.9);border:1px solid rgba(255,255,255,0.12);color:#f3f4f6;padding:0.6rem 0.9rem;border-radius:10px;font-size:0.9rem;outline:none;">
    </div>
    <div>
      <label style="font-size:0.8rem;color:#9ca3af;display:block;margin-bottom:0.4rem;">Full Name</label>
      <input id="new-student-name" type="text" placeholder="e.g. Priya Sharma" style="width:100%;background:rgba(17,24,39,0.9);border:1px solid rgba(255,255,255,0.12);color:#f3f4f6;padding:0.6rem 0.9rem;border-radius:10px;font-size:0.9rem;outline:none;">
    </div>
    <div>
      <label style="font-size:0.8rem;color:#9ca3af;display:block;margin-bottom:0.4rem;">Academic Discipline / Domain Engine</label>
      <select id="new-student-domain" style="width:100%;background:rgba(17,24,39,0.9);border:1px solid rgba(255,255,255,0.12);color:#f3f4f6;padding:0.6rem 0.9rem;border-radius:10px;font-size:0.9rem;outline:none;cursor:pointer;">
        <option value="engineering">💻 Software &amp; AI Engineering Engine</option>
        <option value="pharmacy">💊 Pharmacy &amp; Lifesciences Engine</option>
        <option value="architecture">🏛️ Architecture &amp; Urban Design Engine</option>
        <option value="mba">📊 MBA &amp; Business Management Engine</option>
      </select>
    </div>
    <div>
      <label style="font-size:0.8rem;color:#9ca3af;display:block;margin-bottom:0.4rem;">Target Role Title</label>
      <input id="new-student-role" type="text" placeholder="e.g. Pharmacist, Architect, Software Engineer" style="width:100%;background:rgba(17,24,39,0.9);border:1px solid rgba(255,255,255,0.12);color:#f3f4f6;padding:0.6rem 0.9rem;border-radius:10px;font-size:0.9rem;outline:none;">
    </div>
    <button onclick="createStudent()" style="margin-top:0.5rem;width:100%;padding:0.7rem;background:linear-gradient(135deg,#3b82f6,#2563eb);border:1px solid #60a5fa;color:#fff;border-radius:10px;font-size:0.95rem;font-weight:600;cursor:pointer;transition:all 0.2s;">Create Student Profile</button>
  </div>
</dialog>

<div class="container">

  <!-- Summary Stats -->
  <div class="summary-grid">
    <div class="stat-card stat-total">
      <div class="stat-top"><span class="stat-label">Total Jobs Discovered</span><span class="stat-icon">📊</span></div>
      <div class="stat-num">{total}</div>
    </div>
    <div class="stat-card stat-ready">
      <div class="stat-top"><span class="stat-label">Ready (Desc + URL)</span><span class="stat-icon">⚡</span></div>
      <div class="stat-num">{ready}</div>
    </div>
    <div class="stat-card stat-scored">
      <div class="stat-top"><span class="stat-label">Scored by AI</span><span class="stat-icon">🎯</span></div>
      <div class="stat-num">{scored}</div>
    </div>
    <div class="stat-card stat-high">
      <div class="stat-top"><span class="stat-label">Strong Matches (7+)</span><span class="stat-icon">🌟</span></div>
      <div class="stat-num">{high_fit}</div>
    </div>
  </div>

  <!-- Filter Toolbar -->
  <div class="toolbar">
    <div class="filter-group">
      <span class="filter-label">Fit Score:</span>
      <button class="filter-btn active" onclick="filterScore(0)">All Scored</button>
      <button class="filter-btn" onclick="filterScore(5)">5+ Moderate</button>
      <button class="filter-btn" onclick="filterScore(7)">7+ Strong</button>
      <button class="filter-btn" onclick="filterScore(8)">8+ Excellent</button>
      <button class="filter-btn" onclick="filterScore(9)">9+ Perfect</button>
    </div>

    <div class="filter-group">
      <span class="filter-label">Source:</span>
      <select id="site-filter" class="site-select" onchange="filterSite(this.value)">
        {site_options_html}
      </select>
    </div>
  </div>

  <div id="job-count" class="job-count-status"></div>

  {job_sections}

  <!-- Analytics Section (Score Distribution & Source Distribution) placed below job list -->
  <div class="analytics-section" style="margin-top: 3rem;">
    <div class="analytics-card">
      <h3><span>📊</span> Score Distribution</h3>
      {score_bars}
    </div>
    <div class="analytics-card">
      <h3><span>🌐</span> Source Distribution</h3>
      {site_rows}
    </div>
  </div>

</div>

<!-- Modal Dialog for Full Job Details -->
<dialog id="job-modal">
  <div class="modal-header">
    <div class="modal-title" id="modal-job-title">Job Details</div>
    <button class="modal-close-btn" onclick="closeJobModal()">&times;</button>
  </div>
  <div class="modal-body" id="modal-job-body">
    Loading full job description...
  </div>
  <div class="modal-footer" id="modal-job-footer">
    <button class="btn-secondary" onclick="closeJobModal()">Close</button>
  </div>
</dialog>

<!-- Toast Container -->
<div id="toast-container" class="toast-container"></div>

<style>
  .show-more-wrapper {{ grid-column: 1 / -1; display: flex; justify-content: center; margin-top: 1.5rem; }}
  .show-more-btn {{
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.4);
    color: #60a5fa;
    padding: 0.65rem 1.75rem;
    border-radius: 10px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }}
  .show-more-btn:hover {{
    background: rgba(59, 130, 246, 0.25);
    color: #ffffff;
    transform: translateY(-2px);
  }}
</style>

<script>
let minScore = 0;
let selectedSite = '';
let searchText = '';
const expandedGrids = new Set();

// Keyboard shortcut '/' to focus search
document.addEventListener('keydown', (e) => {{
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {{
    e.preventDefault();
    document.getElementById('main-search').focus();
  }}
}});

function showToast(msg) {{
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>✨</span> <span>${{msg}}</span>`;
  container.appendChild(toast);
  setTimeout(() => {{
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }}, 2500);
}}

function copyLink(url, btn) {{
  navigator.clipboard.writeText(url).then(() => {{
    showToast('Job application link copied to clipboard!');
  }}).catch(() => {{
    showToast('Failed to copy link');
  }});
}}

function openJobModal(cardId) {{
  const card = document.getElementById(cardId);
  if (!card) return;
  const title = card.querySelector('.full-title-raw')?.textContent || 'Job Details';
  const desc = card.querySelector('.full-desc-raw')?.innerHTML || 'No description available.';
  const applyUrl = card.querySelector('.apply-url-raw')?.textContent || '';
  const jobUrl = card.querySelector('.job-url-raw')?.textContent || '';

  document.getElementById('modal-job-title').textContent = title;
  document.getElementById('modal-job-body').innerHTML = desc;

  const footer = document.getElementById('modal-job-footer');
  footer.innerHTML = `
    <button class="btn-secondary" onclick="closeJobModal()">Close</button>
    <button class="btn-secondary" onclick="copyLink('${{applyUrl}}', this)">📋 Copy Link</button>
    <a href="${{applyUrl}}" target="_blank" class="btn-primary">Apply Now ↗</a>
  `;

  const modal = document.getElementById('job-modal');
  modal.showModal();
}}

function closeJobModal() {{
  const modal = document.getElementById('job-modal');
  modal.close();
}}

// Close modal on backdrop click
document.getElementById('job-modal').addEventListener('click', (e) => {{
  const dialogBounds = e.target.getBoundingClientRect();
  if (
    e.clientX < dialogBounds.left ||
    e.clientX > dialogBounds.right ||
    e.clientY < dialogBounds.top ||
    e.clientY > dialogBounds.bottom
  ) {{
    closeJobModal();
  }}
}});

async function tailorAndApply(btn, jobUrl, applyUrl) {{
  btn.disabled = true;
  btn.textContent = '⏳ Tailoring Resume...';

  const newTab = window.open('about:blank', '_blank');
  if (newTab) {{
    newTab.document.write('<div style="font-family:Inter,sans-serif;background:#090d16;color:#f3f4f6;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1rem;"><h2>⚡ ApplyPilot is tailoring your resume...</h2><p style="color:#9ca3af;">Redirecting to application page shortly!</p></div>');
  }}

  try {{
    const res = await fetch('/api/tailor', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ url: jobUrl }})
    }});
    const data = await res.json();
    const targetUrl = (data.status === 'ok' && data.apply_url) ? data.apply_url : applyUrl;

    if (newTab && !newTab.closed) {{
      newTab.location.href = targetUrl;
    }} else {{
      window.location.href = targetUrl;
    }}

    const card = btn.closest('.job-card');
    const badge = card ? card.querySelector('.resume-auto') : null;
    if (badge) {{
      badge.textContent = '📄 Resume Ready';
      badge.className = 'meta-tag resume-ready';
    }}

    btn.textContent = 'Apply ↗';
    btn.className = 'btn-primary apply-link';
    btn.disabled = false;
    btn.onclick = () => window.open(targetUrl, '_blank');
    showToast('Resume tailored successfully!');
  }} catch (e) {{
    if (newTab && !newTab.closed) newTab.location.href = applyUrl;
    else window.location.href = applyUrl;
  }}
}}

function filterScore(min) {{
  minScore = min;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  applyFilters();
}}

function filterExactScore(score) {{
  minScore = score;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  applyFilters();
}}

function filterSite(site) {{
  selectedSite = site;
  applyFilters();
}}

function filterBySite(site) {{
  selectedSite = site;
  const select = document.getElementById('site-filter');
  if (select) select.value = site;
  applyFilters();
}}

function filterText(text) {{
  searchText = text.toLowerCase();
  applyFilters();
}}

function toggleGridExpand(score) {{
  if (expandedGrids.has(score)) {{
    expandedGrids.delete(score);
  }} else {{
    expandedGrids.add(score);
  }}
  applyFilters();
}}

function applyFilters() {{
  let shown = 0;
  let total = 0;
  
  document.querySelectorAll('.job-grid').forEach(grid => {{
    const score = parseInt(grid.dataset.score) || 0;
    const cards = Array.from(grid.querySelectorAll('.job-card'));
    let gridMatching = 0;

    cards.forEach(card => {{
      total++;
      const cardScore = parseInt(card.dataset.score) || 0;
      const cardSite = card.dataset.site || '';
      const text = card.textContent.toLowerCase();

      const scoreMatch = minScore === 0 ? true : (minScore >= 5 ? cardScore >= minScore : cardScore === minScore);
      const siteMatch = !selectedSite || cardSite === selectedSite;
      const textMatch = !searchText || text.includes(searchText);

      if (scoreMatch && siteMatch && textMatch) {{
        gridMatching++;
        const isExpanded = expandedGrids.has(score) || Boolean(searchText) || Boolean(selectedSite);
        if (isExpanded || gridMatching <= 6) {{
          card.classList.remove('hidden');
          shown++;
        }} else {{
          card.classList.add('hidden');
        }}
      }} else {{
        card.classList.add('hidden');
      }}
    }});

    let btnWrapper = grid.nextElementSibling;
    if (!btnWrapper || !btnWrapper.classList.contains('show-more-wrapper')) {{
      btnWrapper = document.createElement('div');
      btnWrapper.className = 'show-more-wrapper';
      grid.after(btnWrapper);
    }}

    const isExpanded = expandedGrids.has(score) || Boolean(searchText) || Boolean(selectedSite);
    const hiddenInGrid = gridMatching - 6;

    if (gridMatching > 6 && !searchText && !selectedSite) {{
      btnWrapper.style.display = 'flex';
      btnWrapper.innerHTML = `<button class="show-more-btn" onclick="toggleGridExpand(${{score}})">${{isExpanded ? 'Collapse' : 'Show More (+' + hiddenInGrid + ' jobs)'}}</button>`;
    }} else {{
      btnWrapper.style.display = 'none';
    }}

    const headerWrapper = grid.previousElementSibling;
    if (headerWrapper && headerWrapper.classList.contains('score-section-wrapper')) {{
      headerWrapper.style.display = gridMatching > 0 ? '' : 'none';
      grid.style.display = gridMatching > 0 ? '' : 'none';
    }}
  }});

  document.getElementById('job-count').textContent = `Showing ${{shown}} of ${{total}} scored jobs`;
}}

applyFilters();

// ── Candidate Switcher & Add Student Handlers ─────────────────
function switchCandidate(candidateId) {{
  // Reload page with new candidate via server
  window.location.href = '/?candidate=' + encodeURIComponent(candidateId);
}}

function openAddStudentModal() {{
  document.getElementById('add-student-modal')?.showModal();
}}

async function createStudent() {{
  const idEl = document.getElementById('new-student-id');
  const nameEl = document.getElementById('new-student-name');
  const roleEl = document.getElementById('new-student-role');
  const domainEl = document.getElementById('new-student-domain');
  const sid = (idEl?.value || '').trim().toLowerCase().replace(/\\s+/g, '_');
  const sname = (nameEl?.value || '').trim();
  const srole = (roleEl?.value || '').trim() || 'Candidate';
  const sdomain = (domainEl?.value || 'engineering').trim();

  if (!sid) {{
    showToast('Please enter a Student ID');
    return;
  }}

  try {{
    const res = await fetch('/api/candidates/create', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ candidate_id: sid, name: sname, target_role: srole, domain: sdomain }})
    }});
    const data = await res.json();
    if (data.status === 'ok') {{
      showToast(`Student "${{sname || sid}}" created successfully!`);
      document.getElementById('add-student-modal')?.close();
      // Reload to show the new candidate's dashboard
      setTimeout(() => window.location.href = '/?candidate=' + encodeURIComponent(sid), 500);
    }} else {{
      showToast('Error: ' + (data.error || 'Failed to create student'));
    }}
  }} catch (e) {{
    showToast('Network error creating student');
  }}
}}
// ── Full-Screen Profile View Handlers ───────────────────────
function showProfileView() {{
  document.getElementById('profile-page-view')?.classList.remove('hidden');
  window.location.hash = 'profile';
}}

function showDashboardView() {{
  document.getElementById('profile-page-view')?.classList.add('hidden');
  if (window.location.hash === '#profile') {{
    history.pushState("", document.title, window.location.pathname + window.location.search);
  }}
}}

function copyResumeText() {{
  const text = document.getElementById('master-resume-text-el')?.textContent || '';
  navigator.clipboard.writeText(text).then(() => {{
    showToast('Master resume copied to clipboard!');
  }}).catch(() => {{
    showToast('Failed to copy text');
  }});
}}

function togglePasswordMask() {{
  const el = document.getElementById('profile-password-value');
  const btn = document.getElementById('profile-password-toggle');
  if (!el || !btn) return;
  if (el.dataset.masked === 'true') {{
    el.textContent = el.dataset.real;
    el.dataset.masked = 'false';
    btn.textContent = '🙈 Hide';
  }} else {{
    el.textContent = '••••••••';
    el.dataset.masked = 'true';
    btn.textContent = '👁 Show';
  }}
}}

// Handle Hash Routing & Keybindings
window.addEventListener('hashchange', () => {{
  if (window.location.hash === '#profile') {{
    document.getElementById('profile-page-view')?.classList.remove('hidden');
  }} else {{
    document.getElementById('profile-page-view')?.classList.add('hidden');
  }}
}});

if (window.location.hash === '#profile') {{
  document.getElementById('profile-page-view')?.classList.remove('hidden');
}}

document.addEventListener('keydown', (e) => {{
  if (e.key === 'Escape') {{
    const profileView = document.getElementById('profile-page-view');
    if (profileView && !profileView.classList.contains('hidden')) {{
      showDashboardView();
    }}
  }}
}});
function toggleResumeView() {{
  const pdfBox = document.getElementById('pdf-resume-frame-container');
  const txtBox = document.getElementById('text-resume-frame-container');
  if (pdfBox && txtBox) {{
    pdfBox.classList.toggle('hidden');
    txtBox.classList.toggle('hidden');
  }}
}}
</script>

{_build_profile_page_html(profile_data, resume_raw_text, resume_pdf_b64)}

</body>
</html>"""

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    abs_path = str(out.resolve())
    console.print(f"[green]Dashboard written to {abs_path}[/green]")
    return abs_path

def generate_job_detail_page(job_url: str) -> str:
    """Generate a standalone HTML detail page for a single job.

    Args:
        job_url: The URL primary key of the job in the database.

    Returns:
        HTML string of the complete page, or a simple error HTML if job not found.
    """
    conn = get_connection()
    
    cols = """url, title, salary, description, location, site, strategy,
              full_description, application_url, detail_error,
              fit_score, score_reasoning, tailored_resume_path,
              discovered_at, detail_scraped_at, scored_at, tailored_at, 
              cover_letter_path, applied_at, apply_status, apply_error, apply_attempts"""
              
    jobs = conn.execute(f"""
        SELECT {cols}
        FROM jobs
        WHERE fit_score >= 1
        ORDER BY fit_score DESC, site, title
    """).fetchall()
    
    job_idx = -1
    for i, j in enumerate(jobs):
        if j["url"] == job_url:
            job_idx = i
            break
            
    if job_idx == -1:
        current_job = conn.execute(f"SELECT {cols} FROM jobs WHERE url = ?", (job_url,)).fetchone()
        if not current_job:
            return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Job Not Found - ApplyPilot</title>
    <style>body { background: #090d16; color: white; font-family: sans-serif; text-align: center; padding: 50px; }</style>
</head>
<body><h1>Job Not Found</h1><p>The requested job could not be found in the database.</p><a href="/" style="color:#3b82f6;">Return to Dashboard</a></body>
</html>"""
        prev_url = ""
        next_url = ""
        pos_text = "Unscored Job"
    else:
        current_job = jobs[job_idx]
        prev_url = jobs[job_idx - 1]["url"] if job_idx > 0 else ""
        next_url = jobs[job_idx + 1]["url"] if job_idx < len(jobs) - 1 else ""
        pos_text = f"Job {job_idx + 1} of {len(jobs)}"
        
    j = current_job
    
    title = escape(j["title"] or "Untitled")
    url = escape(j["url"] or "")
    salary = escape(j["salary"] or "")
    location = escape(j["location"] or "")
    site = escape(j["site"] or "")
    strategy = escape(j["strategy"] or "Unknown")
    apply_url = escape(j["application_url"] or j["url"] or "")
    
    score = j["fit_score"] or 0
    score_color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")
    score_label = {
        10: "Perfect Match", 9: "Excellent Fit", 8: "Strong Fit",
        7: "Good Fit", 6: "Moderate+", 5: "Moderate",
        4: "Low-Moderate", 3: "Low Fit", 2: "Weak Match", 1: "Poor Fit",
    }.get(score, f"Score {score}") if score else "Not Scored"
    
    colors = {
        "RemoteOK": "#10b981", "WelcomeToTheJungle": "#f59e0b",
        "Job Bank Canada": "#3b82f6", "CareerJet Canada": "#8b5cf6",
        "Hacker News Jobs": "#ff6600", "BuiltIn Remote": "#ec4899",
        "TD Bank": "#00a651", "CIBC": "#c41f3e", "RBC": "#003168",
        "indeed": "#2164f3", "linkedin": "#0a66c2",
        "Dice": "#eb1c26", "Glassdoor": "#0caa41",
    }
    site_color = colors.get(j["site"] or "", "#818cf8")
    
    # Reasoning parsing
    reasoning_raw = j["score_reasoning"] or ""
    reasoning_lines = [line.strip() for line in reasoning_raw.split("\n") if line.strip()]
    keywords_str = reasoning_lines[0] if reasoning_lines else ""
    reasoning_str = reasoning_lines[1] if len(reasoning_lines) > 1 else "No reasoning available."
    
    keyword_chips_html = ""
    if keywords_str:
        kw_list = [k.strip() for k in keywords_str.split(",") if k.strip()]
        for kw in kw_list:
            keyword_chips_html += f'<span class="kw-chip">{escape(kw)}</span>'
            
    desc_text = j["full_description"] or j["description"] or "No description available."
    full_desc_html = escape(desc_text).replace("\n", "<br>")
    
    has_resume = bool(j["tailored_resume_path"])
    resume_status = escape(j["tailored_resume_path"]) if has_resume else "Not yet tailored"
    cover_status = escape(j["cover_letter_path"]) if j["cover_letter_path"] else "Not generated"
    
    applied_at = escape(j["applied_at"]) if j["applied_at"] else "Not applied"
    apply_status = escape(j["apply_status"]) if j["apply_status"] else "-"
    
    # Meta pills
    meta_pills = ""
    if salary:
        meta_pills += f'<span class="meta-tag salary">💰 {salary}</span> '
    if location:
        meta_pills += f'<span class="meta-tag location">📍 {location}</span> '
    if has_resume:
        meta_pills += '<span class="meta-tag resume-ready">📄 Resume Ready</span>'
    else:
        meta_pills += '<span class="meta-tag resume-auto">⚡ Auto-Tailors on Apply</span>'

    # Nav buttons
    prev_html = f'<a href="/job?url={url_quote(prev_url, safe="")}" class="nav-btn">‹ Prev</a>' if prev_url else '<span class="nav-btn disabled">‹ Prev</span>'
    next_html = f'<a href="/job?url={url_quote(next_url, safe="")}" class="nav-btn">Next ›</a>' if next_url else '<span class="nav-btn disabled">Next ›</span>'

    # Action buttons
    action_html = ""
    if has_resume:
        action_html = f'<a href="{apply_url}" target="_blank" class="btn-primary">Apply Now ↗</a>'
    else:
        action_html = f'<button class="btn-primary tailor-apply-btn" onclick="tailorAndApply(this, \'{url}\', \'{apply_url}\')">⚡ Tailor &amp; Apply</button>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - ApplyPilot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg-dark: #090d16;
    --bg-card: rgba(17, 24, 39, 0.75);
    --bg-card-hover: rgba(30, 41, 59, 0.85);
    --border-card: rgba(255, 255, 255, 0.08);
    --border-card-hover: rgba(96, 165, 250, 0.3);
    --primary: #3b82f6;
    --primary-hover: #2563eb;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-rose: #ef4444;
    --text-main: #f3f4f6;
    --text-muted: #9ca3af;
    --text-sub: #6b7280;
    --font-heading: 'Plus Jakarta Sans', -apple-system, sans-serif;
    --font-body: 'Inter', -apple-system, sans-serif;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: var(--font-body);
    background: var(--bg-dark);
    background-image: 
      radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.12) 0px, transparent 50%),
      radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.08) 0px, transparent 50%),
      radial-gradient(at 50% 100%, rgba(139, 92, 246, 0.08) 0px, transparent 50%);
    background-attachment: fixed;
    color: var(--text-main);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }}
  .navbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: rgba(9, 13, 22, 0.82);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border-card);
    padding: 1rem 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .nav-left, .nav-right, .nav-center {{ display: flex; align-items: center; gap: 1rem; }}
  .nav-center {{ color: var(--text-muted); font-size: 0.9rem; font-weight: 500; }}
  .nav-link {{
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.9rem;
    font-weight: 500;
    transition: color 0.2s;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .nav-link:hover {{ color: var(--text-main); }}
  .nav-btn {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: var(--text-main);
    padding: 0.4rem 0.85rem;
    border-radius: 8px;
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s;
  }}
  .nav-btn:hover:not(.disabled) {{ background: rgba(255, 255, 255, 0.15); color: #fff; }}
  .nav-btn.disabled {{ opacity: 0.4; cursor: not-allowed; pointer-events: none; }}
  
  .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; flex: 1; width: 100%; }}
  
  .hero-section {{
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 20px;
    padding: 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
    animation: fadeIn 0.5s ease-out;
  }}
  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  
  .hero-top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 2rem; }}
  .hero-main {{ flex: 1; }}
  .job-title {{ font-family: var(--font-heading); font-size: 2.5rem; font-weight: 800; line-height: 1.2; margin-bottom: 1rem; color: #fff; }}
  .site-badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 1rem;
  }}
  .meta-row {{ display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 2rem; }}
  .meta-tag {{ font-size: 0.85rem; padding: 0.35rem 0.75rem; border-radius: 8px; font-weight: 500; display: inline-flex; align-items: center; gap: 0.4rem; }}
  .meta-tag.salary {{ background: rgba(16, 185, 129, 0.1); color: #34d399; }}
  .meta-tag.location {{ background: rgba(59, 130, 246, 0.1); color: #93c5fd; }}
  .meta-tag.resume-ready {{ background: rgba(6, 78, 59, 0.6); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.3); }}
  .meta-tag.resume-auto {{ background: rgba(30, 58, 95, 0.6); color: #93c5fd; border: 1px solid rgba(147, 197, 253, 0.2); }}

  .hero-score-box {{
    display: flex;
    flex-direction: column;
    align-items: center;
    background: rgba(0, 0, 0, 0.2);
    padding: 1.5rem;
    border-radius: 16px;
    border: 1px solid var(--border-card);
    min-width: 140px;
  }}
  .score-circle {{
    width: 80px; height: 80px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 2.5rem; font-weight: 800; font-family: var(--font-heading);
    margin-bottom: 0.5rem; color: #0f172a;
    box-shadow: 0 0 30px {score_color}40;
  }}
  .score-label {{ font-size: 0.9rem; font-weight: 600; color: var(--text-main); text-align: center; }}
  
  .action-bar {{
    display: flex; gap: 1rem; margin-top: 1rem;
    padding-top: 1.5rem; border-top: 1px solid var(--border-card);
  }}
  
  .btn-primary {{
    font-size: 0.95rem; font-weight: 600; color: #ffffff;
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    border: 1px solid #60a5fa; border-radius: 10px;
    padding: 0.75rem 1.5rem; cursor: pointer; text-decoration: none;
    display: inline-flex; align-items: center; gap: 0.5rem;
    transition: all 0.2s ease; box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
  }}
  .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5); background: linear-gradient(135deg, #2563eb, #1d4ed8); }}
  .btn-primary:disabled {{ opacity: 0.7; cursor: wait; }}
  
  .btn-secondary {{
    font-size: 0.95rem; font-weight: 500; color: var(--text-main);
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px; padding: 0.75rem 1.25rem; cursor: pointer; text-decoration: none;
    display: inline-flex; align-items: center; gap: 0.5rem; transition: all 0.2s;
  }}
  .btn-secondary:hover {{ background: rgba(255, 255, 255, 0.15); color: #fff; }}
  
  .two-col {{ display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; }}
  @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} .hero-top {{ flex-direction: column; }} }}
  
  .card {{
    background: var(--bg-card); backdrop-filter: blur(16px);
    border: 1px solid var(--border-card); border-radius: 16px;
    padding: 1.5rem; margin-bottom: 2rem;
    transition: all 0.3s;
  }}
  .card:hover {{ border-color: rgba(255, 255, 255, 0.15); }}
  .card h3 {{ font-family: var(--font-heading); font-size: 1.2rem; margin-bottom: 1.25rem; color: #fff; display: flex; align-items: center; gap: 0.5rem; border-bottom: 1px solid var(--border-card); padding-bottom: 0.75rem; }}
  
  .kw-chip {{
    font-size: 0.8rem; background: rgba(16, 185, 129, 0.12); color: #34d399;
    padding: 0.25rem 0.6rem; border-radius: 6px; border: 1px solid rgba(52, 211, 153, 0.2);
    display: inline-block; margin: 0 0.4rem 0.4rem 0;
  }}
  .reasoning-text {{ font-size: 0.95rem; line-height: 1.6; color: var(--text-muted); margin-top: 1rem; font-style: italic; background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 8px; border-left: 3px solid {score_color}; }}
  
  .job-desc {{ font-size: 0.95rem; line-height: 1.7; color: #cbd5e1; white-space: pre-wrap; word-break: break-word; }}
  
  .meta-list {{ list-style: none; }}
  .meta-list li {{ margin-bottom: 1.25rem; font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.35rem; }}
  .meta-list .lbl {{ color: var(--text-sub); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
  .meta-list .val {{ color: var(--text-main); word-break: break-all; font-weight: 500; }}
  .meta-list .val a {{ color: #60a5fa; text-decoration: none; }}
  .meta-list .val a:hover {{ text-decoration: underline; }}
  
  .footer {{ text-align: center; padding: 2rem; color: var(--text-sub); font-size: 0.85rem; border-top: 1px solid var(--border-card); margin-top: auto; }}
  
  .toast-container {{ position: fixed; bottom: 2rem; right: 2rem; z-index: 1000; display: flex; flex-direction: column; gap: 0.5rem; }}
  .toast {{ background: #1e293b; border: 1px solid #3b82f6; color: #ffffff; padding: 0.75rem 1.25rem; border-radius: 12px; font-size: 0.85rem; font-weight: 500; box-shadow: 0 10px 25px rgba(0,0,0,0.5); display: flex; align-items: center; gap: 0.5rem; animation: toastIn 0.3s ease-out forwards; }}
  @keyframes toastIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
</head>
<body>

<div class="navbar">
  <div class="nav-left">
    <a href="/" class="nav-link">← Back to Dashboard</a>
  </div>
  <div class="nav-center">
    {prev_html}
    <span>{pos_text}</span>
    {next_html}
  </div>
  <div class="nav-right">
    <a href="{url}" target="_blank" class="nav-btn">🌐 View Original Posting</a>
  </div>
</div>

<div class="container">
  <div class="hero-section">
    <div class="hero-top">
      <div class="hero-main">
        <div class="site-badge" style="background:{site_color}20; color:{site_color}; border: 1px solid {site_color}40;">
          {site}
        </div>
        <h1 class="job-title">{title}</h1>
        <div class="meta-row">{meta_pills}</div>
      </div>
      <div class="hero-score-box">
        <div class="score-circle" style="background:{score_color}">{score}</div>
        <div class="score-label">{score_label}</div>
      </div>
    </div>
    <div class="action-bar">
      {action_html}
      <button class="btn-secondary" onclick="copyLink('{apply_url}')">📋 Copy Application Link</button>
    </div>
  </div>

  <div class="two-col">
    <div class="left-col">
      <div class="card">
        <h3>🎯 AI Fit Analysis</h3>
        <div>{keyword_chips_html}</div>
        <div class="reasoning-text">"{escape(reasoning_str)}"</div>
      </div>
      
      <div class="card">
        <h3>📝 Full Job Description</h3>
        <div class="job-desc">{full_desc_html}</div>
      </div>
    </div>
    
    <div class="right-col">
      <div class="card">
        <h3>🗂️ Job Metadata</h3>
        <ul class="meta-list">
          <li><span class="lbl">Source</span><span class="val">{site}</span></li>
          <li><span class="lbl">Discovery Strategy</span><span class="val">{strategy}</span></li>
          <li><span class="lbl">Job URL</span><span class="val"><a href="{url}" target="_blank">{(url[:40] + '...') if len(url) > 40 else url}</a></span></li>
          <li><span class="lbl">Application URL</span><span class="val"><a href="{apply_url}" target="_blank">{(apply_url[:40] + '...') if len(apply_url) > 40 else apply_url}</a></span></li>
          <li><span class="lbl">Discovered</span><span class="val">{escape(str(j["discovered_at"]) if j["discovered_at"] else "-")}</span></li>
          <li><span class="lbl">Enriched</span><span class="val">{escape(str(j["detail_scraped_at"]) if j["detail_scraped_at"] else "-")}</span></li>
          <li><span class="lbl">Scored</span><span class="val">{escape(str(j["scored_at"]) if j["scored_at"] else "-")}</span></li>
        </ul>
      </div>
      
      <div class="card">
        <h3>🚀 Pipeline Status</h3>
        <ul class="meta-list">
          <li><span class="lbl">Resume</span><span class="val">{resume_status}</span></li>
          <li><span class="lbl">Cover Letter</span><span class="val">{cover_status}</span></li>
          <li><span class="lbl">Application</span><span class="val">{applied_at} / {apply_status} / {escape(j["apply_error"] or "No errors")}</span></li>
          <li><span class="lbl">Apply Attempts</span><span class="val">{j["apply_attempts"] or 0}</span></li>
        </ul>
      </div>
    </div>
  </div>
</div>

<div class="footer">Generated by ApplyPilot · AI Job Agent</div>
<div id="toast-container" class="toast-container"></div>

<script>
function showToast(msg) {{
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `<span>✨</span> <span>${{msg}}</span>`;
  container.appendChild(toast);
  setTimeout(() => {{
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }}, 2500);
}}

function copyLink(url) {{
  navigator.clipboard.writeText(url).then(() => {{
    showToast('Job application link copied to clipboard!');
  }}).catch(() => {{
    showToast('Failed to copy link');
  }});
}}

async function tailorAndApply(btn, jobUrl, applyUrl) {{
  btn.disabled = true;
  btn.textContent = '⏳ Tailoring...';
  
  const newTab = window.open('about:blank', '_blank');
  if (newTab) {{
    newTab.document.write('<div style="font-family:Inter,sans-serif;background:#090d16;color:#f3f4f6;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1rem;"><h2>⚡ ApplyPilot is tailoring your resume...</h2><p style="color:#9ca3af;">Redirecting to application page shortly!</p></div>');
  }}
  
  try {{
    const res = await fetch('/api/tailor', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ url: jobUrl }})
    }});
    const data = await res.json();
    const targetUrl = (data.status === 'ok' && data.apply_url) ? data.apply_url : applyUrl;
    
    if (newTab && !newTab.closed) {{
      newTab.location.href = targetUrl;
    }} else {{
      window.location.href = targetUrl;
    }}
    
    btn.textContent = 'Apply ↗';
    btn.className = 'btn-primary apply-link';
    btn.disabled = false;
    btn.onclick = () => window.open(targetUrl, '_blank');
    showToast('Resume tailored successfully!');
  }} catch (e) {{
    if (newTab && !newTab.closed) newTab.location.href = applyUrl;
    else window.location.href = applyUrl;
  }}
}}
</script>
</body>
</html>"""

    return html


def open_dashboard(output_path: str | None = None) -> None:
    """Generate the dashboard and open it in the default browser.

    Args:
        output_path: Where to write the HTML file. Defaults to ~/.applypilot/dashboard.html.
    """
    path = generate_dashboard(output_path)
    console.print("[dim]Opening in browser...[/dim]")
    webbrowser.open(f"file:///{path}")
