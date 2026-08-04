"""ApplyPilot configuration: paths, platform detection, user data."""

import json
import os
import platform
import shutil
from pathlib import Path

# User data directory — all user-specific files live here
APP_DIR = Path(os.environ.get("APPLYPILOT_DIR", Path.home() / ".applypilot"))

# Core paths
DB_PATH = APP_DIR / "applypilot.db"
PROFILE_PATH = APP_DIR / "profile.json"
RESUME_PATH = APP_DIR / "resume.txt"
RESUME_PDF_PATH = APP_DIR / "resume.pdf"
SEARCH_CONFIG_PATH = APP_DIR / "searches.yaml"
ENV_PATH = APP_DIR / ".env"

# Generated output
TAILORED_DIR = APP_DIR / "tailored_resumes"
COVER_LETTER_DIR = APP_DIR / "cover_letters"
LOG_DIR = APP_DIR / "logs"

# ---------------------------------------------------------------------------
# Multi-Student Candidate Isolation
# ---------------------------------------------------------------------------
CANDIDATES_DIR = APP_DIR / "candidates"
ACTIVE_CANDIDATE_FILE = APP_DIR / "active_candidate.txt"

# Default candidate ID used for the original single-user profile
_DEFAULT_CANDIDATE_ID = "default"


def get_active_candidate_id() -> str:
    """Get the currently active candidate ID.

    Reads from ~/.applypilot/active_candidate.txt. Falls back to 'default'.
    """
    if ACTIVE_CANDIDATE_FILE.exists():
        cid = ACTIVE_CANDIDATE_FILE.read_text(encoding="utf-8").strip()
        if cid:
            return cid
    return _DEFAULT_CANDIDATE_ID


def set_active_candidate_id(candidate_id: str) -> None:
    """Set the active candidate ID persistently."""
    ACTIVE_CANDIDATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_CANDIDATE_FILE.write_text(candidate_id.strip(), encoding="utf-8")


def get_candidate_dir(candidate_id: str | None = None) -> Path:
    """Get (and create) the directory for a candidate.

    Args:
        candidate_id: Candidate identifier. Uses active candidate if None.

    Returns:
        Path to ~/.applypilot/candidates/<candidate_id>/
    """
    cid = candidate_id or get_active_candidate_id()
    cdir = CANDIDATES_DIR / cid
    cdir.mkdir(parents=True, exist_ok=True)
    return cdir


def get_candidate_profile_path(candidate_id: str | None = None) -> Path:
    """Profile JSON path for the given (or active) candidate."""
    return get_candidate_dir(candidate_id) / "profile.json"


def get_candidate_resume_path(candidate_id: str | None = None) -> Path:
    """Plain-text resume path for the given (or active) candidate."""
    return get_candidate_dir(candidate_id) / "resume.txt"


def get_candidate_resume_pdf_path(candidate_id: str | None = None) -> Path:
    """PDF resume path for the given (or active) candidate."""
    return get_candidate_dir(candidate_id) / "resume.pdf"


def get_candidate_search_config_path(candidate_id: str | None = None) -> Path:
    """Search config path for the given (or active) candidate."""
    return get_candidate_dir(candidate_id) / "searches.yaml"


def get_candidate_tailored_dir(candidate_id: str | None = None) -> Path:
    """Tailored resumes directory for the given (or active) candidate."""
    d = get_candidate_dir(candidate_id) / "tailored_resumes"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_candidate_cover_letter_dir(candidate_id: str | None = None) -> Path:
    """Cover letters directory for the given (or active) candidate."""
    d = get_candidate_dir(candidate_id) / "cover_letters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_candidate_logs_dir(candidate_id: str | None = None) -> Path:
    """Logs directory for the given (or active) candidate."""
    d = get_candidate_dir(candidate_id) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_candidate_traces_dir(candidate_id: str | None = None) -> Path:
    """Action traces directory for the given (or active) candidate."""
    d = get_candidate_dir(candidate_id) / "traces"
    d.mkdir(parents=True, exist_ok=True)
    return d


def migrate_legacy_profile() -> str | None:
    """Migrate single-user legacy profile into candidates/default/ directory.

    If ~/.applypilot/profile.json exists but candidates/default/ doesn't,
    copies profile.json, resume.txt, resume.pdf, and searches.yaml into the
    default candidate directory. Sets active candidate to 'default'.

    Returns:
        The candidate_id that was migrated, or None if no migration was needed.
    """
    default_dir = CANDIDATES_DIR / _DEFAULT_CANDIDATE_ID
    default_profile = default_dir / "profile.json"

    # Already migrated or no legacy profile
    if default_profile.exists() or not PROFILE_PATH.exists():
        return None

    default_dir.mkdir(parents=True, exist_ok=True)

    # Copy files (don't move — preserve backwards compat)
    for src, dst_name in [
        (PROFILE_PATH, "profile.json"),
        (RESUME_PATH, "resume.txt"),
        (RESUME_PDF_PATH, "resume.pdf"),
        (SEARCH_CONFIG_PATH, "searches.yaml"),
    ]:
        if src.exists():
            shutil.copy2(str(src), str(default_dir / dst_name))

    # Set as active
    set_active_candidate_id(_DEFAULT_CANDIDATE_ID)
    return _DEFAULT_CANDIDATE_ID


def list_candidates() -> list[dict]:
    """List all registered candidate profiles.

    Returns:
        List of dicts with keys: id, name, preferred_name, target_role, active.
    """
    # Ensure migration has run
    migrate_legacy_profile()

    if not CANDIDATES_DIR.exists():
        return []

    candidates = []
    active_id = get_active_candidate_id()

    for cdir in sorted(CANDIDATES_DIR.iterdir()):
        if not cdir.is_dir():
            continue
        pfile = cdir / "profile.json"
        if pfile.exists():
            try:
                pdata = json.loads(pfile.read_text(encoding="utf-8"))
                personal = pdata.get("personal", {})
                exp = pdata.get("experience", {})
                candidates.append({
                    "id": cdir.name,
                    "name": personal.get("full_name") or cdir.name,
                    "preferred_name": personal.get("preferred_name") or "",
                    "target_role": exp.get("target_role") or "Candidate",
                    "active": cdir.name == active_id,
                })
            except Exception:
                candidates.append({
                    "id": cdir.name,
                    "name": cdir.name,
                    "preferred_name": "",
                    "target_role": "Candidate",
                    "active": cdir.name == active_id,
                })
    return candidates


def load_candidate_profile(candidate_id: str | None = None) -> dict:
    """Load a candidate's profile.json.

    Falls back to legacy PROFILE_PATH if candidate profile doesn't exist.
    """
    cid = candidate_id or get_active_candidate_id()
    path = get_candidate_profile_path(cid)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    # Fallback to legacy path
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    raise FileNotFoundError(
        f"Profile not found for candidate '{cid}'. Run `applypilot init` first."
    )


# Chrome worker isolation (use snap/chromium/common on Linux if snap chromium is present to prevent AppArmor crashes)
_snap_dir = Path.home() / "snap" / "chromium" / "common" / "applypilot"
if _snap_dir.parent.exists():
    CHROME_WORKER_DIR = _snap_dir / "chrome-workers"
else:
    CHROME_WORKER_DIR = APP_DIR / "chrome-workers"

APPLY_WORKER_DIR = APP_DIR / "apply-workers"

# Package-shipped config (YAML registries)
PACKAGE_DIR = Path(__file__).parent
CONFIG_DIR = PACKAGE_DIR / "config"


def get_chrome_path() -> str:
    """Auto-detect Chrome/Chromium executable path, cross-platform.

    Override with CHROME_PATH environment variable.
    """
    env_path = os.environ.get("CHROME_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    system = platform.system()

    if system == "Windows":
        candidates = [
            Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
    elif system == "Darwin":
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    else:  # Linux
        candidates = []
        for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
            found = shutil.which(name)
            if found:
                candidates.append(Path(found))

    for c in candidates:
        if c and c.exists():
            return str(c)

    # Fall back to PATH search
    for name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return found

    raise FileNotFoundError(
        "Chrome/Chromium not found. Install Chrome or set CHROME_PATH environment variable."
    )


def get_chrome_user_data() -> Path:
    """Default Chrome user data directory, cross-platform."""
    system = platform.system()
    if system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
    elif system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    else:
        return Path.home() / ".config" / "google-chrome"


def ensure_dirs():
    """Create all required directories."""
    for d in [APP_DIR, TAILORED_DIR, COVER_LETTER_DIR, LOG_DIR, CHROME_WORKER_DIR, APPLY_WORKER_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_profile() -> dict:
    """Load user profile from ~/.applypilot/profile.json."""
    import json
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Profile not found at {PROFILE_PATH}. Run `applypilot init` first."
        )
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def load_search_config() -> dict:
    """Load search configuration from ~/.applypilot/searches.yaml."""
    import yaml
    if not SEARCH_CONFIG_PATH.exists():
        # Fall back to package-shipped example
        example = CONFIG_DIR / "searches.example.yaml"
        if example.exists():
            return yaml.safe_load(example.read_text(encoding="utf-8"))
        return {}
    return yaml.safe_load(SEARCH_CONFIG_PATH.read_text(encoding="utf-8"))


def load_sites_config() -> dict:
    """Load sites.yaml configuration (sites list, manual_ats, blocked, etc.)."""
    import yaml
    path = CONFIG_DIR / "sites.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def is_manual_ats(url: str | None) -> bool:
    """Check if a URL routes through an ATS that requires manual application."""
    if not url:
        return False
    sites_cfg = load_sites_config()
    domains = sites_cfg.get("manual_ats", [])
    url_lower = url.lower()
    return any(domain in url_lower for domain in domains)


def load_blocked_sites() -> tuple[set[str], list[str]]:
    """Load blocked sites and URL patterns from sites.yaml.

    Returns:
        (blocked_site_names, blocked_url_patterns)
    """
    cfg = load_sites_config()
    blocked = cfg.get("blocked", {})
    sites = set(blocked.get("sites", []))
    patterns = blocked.get("url_patterns", [])
    return sites, patterns


def load_blocked_sso() -> list[str]:
    """Load blocked SSO domains from sites.yaml."""
    cfg = load_sites_config()
    return cfg.get("blocked_sso", [])


def load_base_urls() -> dict[str, str | None]:
    """Load site base URLs for URL resolution from sites.yaml."""
    cfg = load_sites_config()
    return cfg.get("base_urls", {})


# ---------------------------------------------------------------------------
# Default values — referenced across modules instead of magic numbers
# ---------------------------------------------------------------------------

DEFAULTS = {
    "min_score": 7,
    "max_apply_attempts": 3,
    "max_tailor_attempts": 5,
    "poll_interval": 60,
    "apply_timeout": 300,
    "viewport": "1280x900",
}


def load_env():
    """Load environment variables from ~/.applypilot/.env if it exists."""
    from dotenv import load_dotenv
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    # Also try CWD .env as fallback
    load_dotenv()


# ---------------------------------------------------------------------------
# Tier system — feature gating by installed dependencies
# ---------------------------------------------------------------------------

TIER_LABELS = {
    1: "Discovery",
    2: "AI Scoring & Tailoring",
    3: "Full Auto-Apply",
}

TIER_COMMANDS: dict[int, list[str]] = {
    1: ["init", "run discover", "run enrich", "status", "dashboard"],
    2: ["run score", "run tailor", "run cover", "run pdf", "run"],
    3: ["apply"],
}


def get_tier() -> int:
    """Detect the current tier based on available dependencies.

    Tier 1 (Discovery):            Python + pip
    Tier 2 (AI Scoring & Tailoring): + LLM API key
    Tier 3 (Full Auto-Apply):       + Claude Code CLI + Chrome
    """
    load_env()

    has_llm = any(os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_URL"))
    if not has_llm:
        return 1

    has_browser_use = False
    try:
        import browser_use  # noqa: F401
        has_browser_use = True
    except ImportError:
        pass
    try:
        get_chrome_path()
        has_chrome = True
    except FileNotFoundError:
        has_chrome = False

    if has_browser_use and has_chrome:
        return 3

    return 2


def check_tier(required: int, feature: str) -> None:
    """Raise SystemExit with a clear message if the current tier is too low.

    Args:
        required: Minimum tier needed (1, 2, or 3).
        feature: Human-readable description of the feature being gated.
    """
    current = get_tier()
    if current >= required:
        return

    from rich.console import Console
    _console = Console(stderr=True)

    missing: list[str] = []
    if required >= 2 and not any(os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "LLM_URL")):
        missing.append("LLM API key — run [bold]applypilot init[/bold] or set GEMINI_API_KEY")
    if required >= 3:
        try:
            import browser_use  # noqa: F401
        except ImportError:
            missing.append("browser-use — run [bold]pip install browser-use langchain-openai[/bold]")
        try:
            get_chrome_path()
        except FileNotFoundError:
            missing.append("Chrome/Chromium — install or set CHROME_PATH")

    _console.print(
        f"\n[red]'{feature}' requires {TIER_LABELS.get(required, f'Tier {required}')} (Tier {required}).[/red]\n"
        f"Current tier: {TIER_LABELS.get(current, f'Tier {current}')} (Tier {current})."
    )
    if missing:
        _console.print("\n[yellow]Missing:[/yellow]")
        for m in missing:
            _console.print(f"  - {m}")
    _console.print()
    raise SystemExit(1)
