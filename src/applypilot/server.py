"""ApplyPilot Local Dashboard & API Server.

Provides a live interactive dashboard server with on-the-fly resume tailoring
and multi-student candidate management endpoints.
"""

from __future__ import annotations

import json
import logging
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser

from applypilot.config import (
    APP_DIR, load_env, ensure_dirs,
    list_candidates, set_active_candidate_id, get_active_candidate_id,
    get_candidate_dir, get_candidate_profile_path, migrate_legacy_profile,
    CANDIDATES_DIR,
)
from applypilot.database import get_connection, init_db
from applypilot.view import generate_dashboard, generate_job_detail_page

log = logging.getLogger(__name__)


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler for dashboard static page & on-the-fly tailoring API."""

    def log_message(self, format, *args):
        """Suppress noisy default request logging."""
        log.debug(format, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/dashboard", "/dashboard.html"):
            # Pass active candidate to dashboard generation
            params = parse_qs(parsed.query)
            cid = params.get("candidate", [None])[0]
            if cid:
                set_active_candidate_id(cid)
            dash_path = generate_dashboard()
            content = Path(dash_path).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/job":
            params = parse_qs(parsed.query)
            job_url = params.get("url", [None])[0]
            if not job_url:
                self.send_error(400, "Missing 'url' query parameter")
                return
            html_content = generate_job_detail_page(job_url)
            content = html_content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/api/status":
            self._send_json({"status": "ok", "service": "ApplyPilot Dashboard Server"})
        elif parsed.path == "/api/candidates":
            candidates = list_candidates()
            self._send_json({
                "status": "ok",
                "active": get_active_candidate_id(),
                "candidates": candidates,
            })
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"

        if parsed.path == "/api/candidates/switch":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"status": "error", "error": "Invalid JSON"}, status=400)
                return
            cid = data.get("candidate_id", "").strip()
            if not cid:
                self._send_json({"status": "error", "error": "Missing candidate_id"}, status=400)
                return
            # Verify candidate exists
            cdir = CANDIDATES_DIR / cid
            if not cdir.exists() or not (cdir / "profile.json").exists():
                self._send_json({"status": "error", "error": f"Candidate '{cid}' not found"}, status=404)
                return
            set_active_candidate_id(cid)
            generate_dashboard()
            self._send_json({"status": "ok", "active_candidate": cid})

        elif parsed.path == "/api/candidates/create":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"status": "error", "error": "Invalid JSON"}, status=400)
                return
            cid = data.get("candidate_id", "").strip()
            name = data.get("name", "").strip()
            target_role = data.get("target_role", "Candidate").strip()
            domain = data.get("domain", "engineering").strip()
            if not cid:
                self._send_json({"status": "error", "error": "Missing candidate_id"}, status=400)
                return
            # Sanitize ID
            cid = cid.lower().replace(" ", "_")
            cdir = get_candidate_dir(cid)
            profile_path = cdir / "profile.json"
            if profile_path.exists():
                self._send_json({"status": "error", "error": f"Candidate '{cid}' already exists"}, status=409)
                return

            # Create profile with domain
            profile = {
                "personal": {"full_name": name or cid, "preferred_name": name or cid},
                "domain": domain,
                "experience": {"target_role": target_role, "domain": domain},
                "work_authorization": {},
                "compensation": {},
                "skills_boundary": {},
                "eeo_voluntary": {},
                "availability": {},
            }
            profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")

            # Generate domain-specific searches.yaml for candidate
            try:
                import yaml
                from applypilot.domains import get_engine
                engine = get_engine(domain)
                search_cfg = engine.get_search_config()
                (cdir / "searches.yaml").write_text(yaml.dump(search_cfg), encoding="utf-8")
            except Exception as e:
                log.warning("Could not create searches.yaml for domain '%s': %s", domain, e)

            set_active_candidate_id(cid)
            generate_dashboard()
            self._send_json({"status": "ok", "candidate_id": cid, "name": name or cid, "domain": domain})

        elif parsed.path == "/api/tailor":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_json({"status": "error", "error": "Invalid JSON"}, status=400)
                return

            job_url = data.get("url")
            if not job_url:
                self._send_json({"status": "error", "error": "Missing job url"}, status=400)
                return

            # Perform on-the-fly tailoring
            conn = get_connection()
            job = conn.execute("SELECT * FROM jobs WHERE url = ?", (job_url,)).fetchone()
            if not job:
                self._send_json({"status": "error", "error": "Job not found in database"}, status=44)
                return

            job_dict = dict(job)
            resume_path = job_dict.get("tailored_resume_path")

            if not resume_path and job_dict.get("full_description"):
                try:
                    import re
                    from applypilot.scoring.tailor import tailor_resume, load_profile, RESUME_PATH, TAILORED_DIR
                    from applypilot.scoring.pdf import convert_to_pdf
                    profile = load_profile()
                    resume_text = RESUME_PATH.read_text(encoding="utf-8")
                    TAILORED_DIR.mkdir(parents=True, exist_ok=True)
                    tailored, report = tailor_resume(resume_text, job_dict, profile)
                    status = (report.get("status") or "").lower()
                    if tailored and status in ("approved", "approved_with_judge_warning"):
                        safe_title = re.sub(r"[^\w\s-]", "", job_dict.get("title") or "job")[:50].strip().replace(" ", "_")
                        safe_site = re.sub(r"[^\w\s-]", "", job_dict.get("site") or "site")[:20].strip().replace(" ", "_")
                        prefix = f"{safe_site}_{safe_title}"
                        txt_path = TAILORED_DIR / f"{prefix}.txt"
                        txt_path.write_text(tailored, encoding="utf-8")
                        try:
                            resume_path = str(convert_to_pdf(txt_path))
                        except Exception:
                            resume_path = str(txt_path)
                        conn.execute("UPDATE jobs SET tailored_resume_path = ? WHERE url = ?", (resume_path, job_url))
                        conn.commit()
                except Exception as e:
                    log.error("On-the-fly tailoring error: %s", e)
                    self._send_json({"status": "error", "error": str(e)}, status=500)
                    return

            apply_url = job_dict.get("application_url") or job_url
            self._send_json({
                "status": "ok",
                "pdf_path": resume_path,
                "apply_url": apply_url,
                "title": job_dict.get("title")
            })
        else:
            self.send_error(404, "Not Found")

    def _send_json(self, data: dict, status: int = 200):
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def start_server(port: int = 8501, open_browser: bool = True) -> None:
    """Start local dashboard HTTP server."""
    load_env()
    ensure_dirs()
    init_db()
    migrate_legacy_profile()

    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    url = f"http://127.0.0.1:{port}"
    active = get_active_candidate_id()
    print(f"🚀 ApplyPilot Dashboard Server running at {url}")
    print(f"🎓 Active candidate: {active}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Dashboard Server...")
        httpd.server_close()

