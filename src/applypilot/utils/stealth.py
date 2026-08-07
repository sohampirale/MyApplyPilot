"""ApplyPilot Stealth & CAPTCHA Solver Utilities.

Provides:
  - Real Chrome 122 browser headers for HTTP scrapers (JobSpy, Requests, Httpx)
  - Modular CapSolver API solver hook (activated whenever CAPSOLVER_API_KEY is present)
  - Playwright browser stealth script injector
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional

log = logging.getLogger(__name__)

# Full modern Chrome 122 browser headers
CHROME_STEALTH_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def get_capsolver_key() -> str:
    """Return CAPSOLVER_API_KEY from environment if configured."""
    return os.environ.get("CAPSOLVER_API_KEY", "").strip()


def solve_recaptcha_via_capsolver(
    website_url: str,
    website_key: str,
    version: str = "v2",
) -> Optional[str]:
    """Solve a reCAPTCHA challenge using CapSolver API if key is present in env.
    
    Returns token string if solved, or None if skipped/failed.
    """
    key = get_capsolver_key()
    if not key:
        log.debug("CapSolver key not set in env. Using Chrome Stealth Headers fallback.")
        return None

    try:
        import httpx
        task_type = "ReCaptchaV2TaskProxyLess" if version == "v2" else "ReCaptchaV3TaskProxyLess"
        payload = {
            "clientKey": key,
            "task": {
                "type": task_type,
                "websiteURL": website_url,
                "websiteKey": website_key,
            }
        }
        res = httpx.post("https://api.capsolver.com/createTask", json=payload, timeout=15)
        res_data = res.json()
        if res_data.get("errorId") != 0:
            log.warning("CapSolver error: %s", res_data.get("errorDescription"))
            return None

        task_id = res_data.get("taskId")
        log.info("CapSolver task submitted (ID: %s). Polling for token...", task_id)

        # Poll for result up to 30s
        for _ in range(15):
            time.sleep(2)
            res_result = httpx.post(
                "https://api.capsolver.com/getTaskResult",
                json={"clientKey": key, "taskId": task_id},
                timeout=10,
            ).json()
            if res_result.get("status") == "ready":
                token = res_result.get("solution", {}).get("gRecaptchaResponse")
                log.info("CapSolver solved CAPTCHA successfully!")
                return token
            elif res_result.get("status") == "failed":
                log.warning("CapSolver task failed: %s", res_result.get("errorDescription"))
                break

    except Exception as e:
        log.warning("CapSolver API request failed: %s", e)

    return None


def apply_playwright_stealth(page) -> None:
    """Inject browser stealth scripts into a Playwright page object."""
    try:
        # Patch navigator.webdriver and chrome object
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """
        page.add_init_script(stealth_js)
    except Exception as e:
        log.debug("Failed to apply Playwright stealth script: %s", e)
