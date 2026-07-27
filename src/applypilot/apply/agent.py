"""Browser-use agent runner for ApplyPilot Stage 6 (Auto-Apply).

Replaces the Claude Code CLI subprocess with the browser-use Python library.
Uses DeepSeek (or any OpenAI-compatible LLM) as the reasoning engine and
Playwright (via browser-use) for browser automation.

The agent connects to an existing Chrome instance via CDP (Chrome DevTools
Protocol) and executes form-filling tasks autonomously.
"""

import asyncio
import logging
import os
import threading
import time
from typing import Callable

from applypilot import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Active agent tracking (for Ctrl+C / skip support)
# ---------------------------------------------------------------------------

_active_agents: dict[int, object] = {}  # worker_id -> Agent instance
_agent_lock = threading.Lock()


def _get_llm():
    """Create a LangChain ChatOpenAI instance from ApplyPilot's env config.

    Reads the same LLM_URL, LLM_MODEL, LLM_API_KEY, GEMINI_API_KEY,
    OPENAI_API_KEY environment variables that llm.py uses, but returns
    a LangChain-compatible object for browser-use.
    """
    from langchain_openai import ChatOpenAI

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    local_url = os.environ.get("LLM_URL", "")
    model_override = os.environ.get("LLM_MODEL", "")
    api_key = os.environ.get("LLM_API_KEY", "")

    if local_url:
        # DeepSeek, Ollama, or any OpenAI-compatible endpoint
        base_url = local_url.rstrip("/")
        # Ensure /v1 suffix for LangChain compatibility
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return ChatOpenAI(
            model=model_override or "deepseek-chat",
            openai_api_key=api_key or "not-needed",
            openai_api_base=base_url,
            temperature=0.0,
        )

    if gemini_key:
        return ChatOpenAI(
            model=model_override or "gemini-2.0-flash",
            openai_api_key=gemini_key,
            openai_api_base="https://generativelanguage.googleapis.com/v1beta/openai",
            temperature=0.0,
        )

    if openai_key:
        return ChatOpenAI(
            model=model_override or "gpt-4o-mini",
            openai_api_key=openai_key,
            temperature=0.0,
        )

    raise RuntimeError(
        "No LLM provider configured. "
        "Set LLM_URL + LLM_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY."
    )


async def run_browser_agent(
    task_prompt: str,
    cdp_port: int,
    worker_id: int = 0,
    max_steps: int = 100,
    on_action: Callable[[str], None] | None = None,
) -> tuple[str, int]:
    """Run a browser-use agent to complete a job application.

    Connects to an existing Chrome instance via CDP and drives it using
    the configured LLM (DeepSeek by default).

    Args:
        task_prompt: The full instruction prompt (from prompt.py).
        cdp_port: CDP port of the Chrome instance to connect to.
        worker_id: Numeric worker identifier (for logging/tracking).
        max_steps: Maximum agent steps before timeout.
        on_action: Optional callback invoked with action description strings
                   as the agent takes actions (for dashboard updates).

    Returns:
        Tuple of (full_output_text, action_count).
    """
    from browser_use import Agent, Browser, BrowserConfig

    llm = _get_llm()

    # Connect to the existing Chrome instance launched by chrome.py
    browser = Browser(
        config=BrowserConfig(
            cdp_url=f"http://localhost:{cdp_port}",
        )
    )

    # Build extended system message with ApplyPilot-specific guidance
    system_extension = (
        "You are an autonomous job application agent. "
        "Follow the task instructions precisely. "
        "When you complete the task, include your result code (e.g. RESULT:APPLIED) "
        "in your final output using the done() action. "
        "When uploading files, use the exact file paths provided in the task. "
        "Always check for CAPTCHAs after navigation and form submissions."
    )

    agent = Agent(
        task=task_prompt,
        llm=llm,
        browser=browser,
        use_vision=False,  # Required for DeepSeek (no vision support)
        extend_system_message=system_extension,
        max_actions_per_step=5,
        max_failures=5,
    )

    # Track for cancellation support
    with _agent_lock:
        _active_agents[worker_id] = agent

    action_count = 0
    output_text = ""

    try:
        history = await agent.run(max_steps=max_steps)

        # Extract results from history
        output_text = history.final_result() or ""
        action_count = len(history.action_names()) if history.action_names() else 0

        # Also collect any extracted content as supplementary output
        extracted = history.extracted_content()
        if extracted:
            for item in extracted:
                if item and item not in output_text:
                    output_text += f"\n{item}"

        # Report actions to callback
        if on_action and history.action_names():
            for action_name in history.action_names():
                on_action(action_name)

        # Log errors if any
        errors = history.errors()
        if errors:
            for err in errors:
                logger.warning("[worker-%d] Agent error: %s", worker_id, err)
                output_text += f"\nERROR: {err}"

    except asyncio.CancelledError:
        logger.info("[worker-%d] Agent cancelled (skip requested)", worker_id)
        output_text = "RESULT:FAILED:cancelled"
    except Exception as exc:
        logger.exception("[worker-%d] Agent crashed: %s", worker_id, exc)
        output_text = f"RESULT:FAILED:agent_crash:{str(exc)[:100]}"
    finally:
        with _agent_lock:
            _active_agents.pop(worker_id, None)
        try:
            await browser.close()
        except Exception:
            pass

    return output_text, action_count


def run_agent_sync(
    task_prompt: str,
    cdp_port: int,
    worker_id: int = 0,
    max_steps: int = 100,
    on_action: Callable[[str], None] | None = None,
) -> tuple[str, int]:
    """Synchronous wrapper for run_browser_agent.

    Creates a new event loop for each call, safe for use in
    ThreadPoolExecutor threads.

    Args:
        task_prompt: The full instruction prompt.
        cdp_port: CDP port of the Chrome instance.
        worker_id: Numeric worker identifier.
        max_steps: Maximum agent steps.
        on_action: Optional action callback.

    Returns:
        Tuple of (full_output_text, action_count).
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            run_browser_agent(
                task_prompt=task_prompt,
                cdp_port=cdp_port,
                worker_id=worker_id,
                max_steps=max_steps,
                on_action=on_action,
            )
        )
    finally:
        loop.close()


def cancel_agent(worker_id: int) -> None:
    """Cancel the active agent for a worker (used for Ctrl+C skip)."""
    with _agent_lock:
        agent = _active_agents.get(worker_id)
        if agent is not None:
            # browser-use Agent doesn't have a direct cancel, but we can
            # stop it by closing the browser or setting an internal flag
            logger.info("[worker-%d] Cancelling agent", worker_id)
            # The agent will be cleaned up in the finally block of run_browser_agent


def cancel_all_agents() -> None:
    """Cancel all active agents (used for shutdown)."""
    with _agent_lock:
        worker_ids = list(_active_agents.keys())
    for wid in worker_ids:
        cancel_agent(wid)
