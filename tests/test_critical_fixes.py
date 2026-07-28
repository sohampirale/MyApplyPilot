"""Unit tests verifying the 6 critical bug fixes in ApplyPilot."""

import pytest
import os


def test_c1_browser_use_imports():
    """C1: Verify browser_use import and Browser cdp_url init in agent.py."""
    from applypilot.apply.agent import run_browser_agent
    from browser_use import Agent, Browser
    # Verify Browser accepts cdp_url without error
    b = Browser(cdp_url="http://localhost:9222")
    assert b is not None


def test_c2_location_filter_empty_whitelist():
    """C2: Verify _location_ok accepts non-remote jobs when accept whitelist is empty."""
    from applypilot.discovery.workday import _location_ok as workday_loc_ok
    from applypilot.discovery.jobspy import _location_ok as jobspy_loc_ok
    from applypilot.discovery.smartextract import _location_ok as smart_loc_ok

    accept = []
    reject = ["new york"]

    # Pune is non-remote, not in reject, accept is empty -> Should be True
    assert workday_loc_ok("Pune, MH, India", accept, reject) is True
    assert jobspy_loc_ok("Pune, MH, India", accept, reject) is True
    assert smart_loc_ok("Pune, MH, India", accept, reject) is True

    # New York is in reject -> Should be False
    assert workday_loc_ok("New York, NY", accept, reject) is False
    assert jobspy_loc_ok("New York, NY", accept, reject) is False
    assert smart_loc_ok("New York, NY", accept, reject) is False


def test_c5_prompt_captcha_js_braces():
    """C5: Verify CAPTCHA instructions in prompt.py produce single literal JS braces { }."""
    from applypilot.apply.prompt import _build_captcha_section

    section = _build_captcha_section()
    # Should contain single braces for JS objects, e.g., "const r = {};"
    assert "const r = {};" in section
    # Should NOT contain double braces "{{}}"
    assert "{{}}" not in section
    assert "{{{" not in section


def test_c6_smartextract_root_array():
    """C6: Verify resolve_json_path_raw handles root array when path is empty/null."""
    from applypilot.discovery.smartextract import resolve_json_path_raw

    root_array = [{"title": "Dev 1"}, {"title": "Dev 2"}]

    assert resolve_json_path_raw(root_array, "") == root_array
    assert resolve_json_path_raw(root_array, None) == root_array
    assert resolve_json_path_raw(root_array, "null") == root_array
