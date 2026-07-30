"""ApplyPilot Local Dashboard & API Server.

Provides a live interactive dashboard server with on-the-fly resume tailoring endpoints.
"""

from __future__ import annotations

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import webbrowser

from applypilot.config import APP_DIR, load_env, ensure_dirs
from applypilot.database import get_connection, init_db
from applypilot.view import generate_dashboard

log = logging.getLogger(__name__)


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler for dashboard static page & on-the-fly tailoring API."""

    def log_message(self, format, *args):
        """Suppress noisy default request logging."""
        log.debug(format, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/dashboard", "/dashboard.html"):
            dash_path = generate_dashboard()
            content = Path(dash_path).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        elif parsed.path == "/api/status":
            self._send_json({"status": "ok", "service": "ApplyPilot Dashboard Server"})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/tailor":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
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
                    from applypilot.scoring.tailor import tailor_resume, load_profile, RESUME_PATH, TAILORED_DIR
                    profile = load_profile()
                    resume_text = RESUME_PATH.read_text(encoding="utf-8")
                    TAILORED_DIR.mkdir(parents=True, exist_ok=True)
                    tailored, report = tailor_resume(resume_text, job_dict, profile)
                    if tailored and report.get("status") in ("APPROVED", "APPROVED_WITH_JUDGE_WARNING"):
                        clean_site = (job_dict.get("site") or "job").replace(" ", "_")
                        clean_title = (job_dict.get("title") or "role").replace(" ", "_").replace("/", "_")[:30]
                        res_file = TAILORED_DIR / f"{clean_site}_{clean_title}.pdf"
                        resume_path = res_file.as_posix()
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

    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, DashboardHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"🚀 ApplyPilot Dashboard Server running at {url}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Dashboard Server...")
        httpd.server_close()
