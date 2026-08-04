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
        elif parsed.path == "/api/job_resume":
            params = parse_qs(parsed.query)
            job_url = params.get("url", [None])[0]
            if not job_url:
                self._send_json({"status": "error", "error": "Missing 'url' parameter"}, status=400)
                return
            conn = get_connection()
            job = conn.execute("SELECT tailored_resume_path FROM jobs WHERE url = ?", (job_url,)).fetchone()
            if not job or not job["tailored_resume_path"]:
                self._send_json({"status": "ok", "has_resume": False})
                return

            rpath = Path(job["tailored_resume_path"])
            if not rpath.exists():
                self._send_json({"status": "ok", "has_resume": False, "error": "Resume file not found on disk"})
                return

            if rpath.suffix.lower() == ".pdf":
                import base64
                pdf_b64 = base64.b64encode(rpath.read_bytes()).decode("utf-8")
                self._send_json({
                    "status": "ok",
                    "has_resume": True,
                    "type": "pdf",
                    "pdf_b64": pdf_b64,
                    "path": str(rpath)
                })
            else:
                text_content = rpath.read_text(encoding="utf-8", errors="replace")
                self._send_json({
                    "status": "ok",
                    "has_resume": True,
                    "type": "txt",
                    "text": text_content,
                    "path": str(rpath)
                })
        elif parsed.path == "/api/logs":
            params = parse_qs(parsed.query)
            cid = params.get("candidate", [get_active_candidate_id()])[0]
            from applypilot.config import get_candidate_logs_dir
            log_file = get_candidate_logs_dir(cid) / "apply.log"
            if not log_file.exists():
                self._send_json({"status": "ok", "logs": []})
                return
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
            self._send_json({"status": "ok", "logs": lines})

        elif parsed.path == "/api/trace":
            params = parse_qs(parsed.query)
            cid = params.get("candidate", [get_active_candidate_id()])[0]
            job_url = params.get("url", [""])[0]
            if not job_url:
                self._send_json({"status": "error", "error": "Missing job url"}, status=400)
                return
            import hashlib
            from applypilot.config import get_candidate_traces_dir
            job_hash = hashlib.md5(job_url.encode()).hexdigest()[:12]
            trace_file = get_candidate_traces_dir(cid) / f"{job_hash}.json"
            if not trace_file.exists():
                self._send_json({"status": "ok", "has_trace": False})
                return
            try:
                data = json.loads(trace_file.read_text(encoding="utf-8"))
                self._send_json({"status": "ok", "has_trace": True, "trace": data})
            except Exception as e:
                self._send_json({"status": "error", "error": f"Error reading trace: {e}"})
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

            cid = get_active_candidate_id()
            conn = get_connection()
            job = conn.execute("SELECT * FROM jobs WHERE url = ?", (job_url,)).fetchone()
            if not job:
                self._send_json({"status": "error", "error": "Job not found in database"}, status=404)
                return

            job_dict = dict(job)
            cs_row = conn.execute(
                "SELECT tailored_resume_path FROM candidate_scores WHERE candidate_id = ? AND job_url = ?",
                (cid, job_url)
            ).fetchone()
            resume_path = cs_row["tailored_resume_path"] if cs_row and cs_row["tailored_resume_path"] else job_dict.get("tailored_resume_path")

            if not resume_path:
                desc = job_dict.get("full_description") or job_dict.get("description")
                if desc:
                    try:
                        import re
                        from datetime import datetime, timezone
                        from applypilot.scoring.tailor import tailor_resume
                        from applypilot.config import (
                            load_candidate_profile, get_candidate_resume_path,
                            get_candidate_tailored_dir, RESUME_PATH
                        )

                        profile = load_candidate_profile(cid)
                        cand_resume_p = get_candidate_resume_path(cid)
                        if cand_resume_p.exists():
                            resume_text = cand_resume_p.read_text(encoding="utf-8")
                        elif RESUME_PATH.exists():
                            resume_text = RESUME_PATH.read_text(encoding="utf-8")
                        else:
                            resume_text = f"Candidate Profile: {json.dumps(profile)}"

                        cand_tailored_dir = get_candidate_tailored_dir(cid)
                        cand_tailored_dir.mkdir(parents=True, exist_ok=True)

                        tailored, report = tailor_resume(resume_text, job_dict, profile)
                        if tailored:
                            safe_title = re.sub(r"[^\w\s-]", "", job_dict.get("title") or "job")[:50].strip().replace(" ", "_")
                            safe_site = re.sub(r"[^\w\s-]", "", job_dict.get("site") or "site")[:20].strip().replace(" ", "_")
                            prefix = f"{safe_site}_{safe_title}"
                            txt_path = cand_tailored_dir / f"{prefix}.txt"
                            txt_path.write_text(tailored, encoding="utf-8")
                            try:
                                from applypilot.scoring.pdf import convert_to_pdf
                                resume_path = str(convert_to_pdf(txt_path))
                            except Exception:
                                resume_path = str(txt_path)

                            now = datetime.now(timezone.utc).isoformat()
                            # Update candidate_scores table
                            conn.execute("""
                                INSERT INTO candidate_scores (candidate_id, job_url, fit_score, scored_at, tailored_resume_path, tailored_at)
                                VALUES (?, ?, 7, ?, ?, ?)
                                ON CONFLICT(candidate_id, job_url) DO UPDATE SET
                                    tailored_resume_path = excluded.tailored_resume_path,
                                    tailored_at = excluded.tailored_at
                            """, (cid, job_url, now, resume_path, now))
                            
                            # Update jobs table for backwards compat
                            conn.execute("UPDATE jobs SET tailored_resume_path = ? WHERE url = ?", (resume_path, job_url))
                            conn.commit()
                    except Exception as e:
                        log.error("On-the-fly tailoring error: %s", e, exc_info=True)
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

