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
    """Create a browser-use native LLM instance from ApplyPilot's env config.

    Reads LLM_URL, LLM_MODEL, LLM_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
    and returns native browser_use.llm objects (ChatDeepSeek, ChatGoogle, ChatOpenAI).
    """
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    local_url = os.environ.get("LLM_URL", "")
    model_override = os.environ.get("LLM_MODEL", "")
    api_key = os.environ.get("LLM_API_KEY", "")

    if local_url and "deepseek" in local_url.lower():
        from browser_use.llm import ChatDeepSeek
        base_url = local_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return ChatDeepSeek(
            model=model_override or "deepseek-chat",
            api_key=api_key or "not-needed",
            base_url=base_url,
            temperature=0.0,
        )

    if local_url:
        from browser_use.llm import ChatOpenAI
        base_url = local_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return ChatOpenAI(
            model=model_override or "gpt-4o-mini",
            api_key=api_key or "not-needed",
            base_url=base_url,
            temperature=0.0,
        )

    if gemini_key:
        from browser_use.llm import ChatGoogle
        return ChatGoogle(
            model=model_override or "gemini-2.0-flash",
            api_key=gemini_key,
            temperature=0.0,
        )

    if openai_key:
        from browser_use.llm import ChatOpenAI
        return ChatOpenAI(
            model=model_override or "gpt-4o-mini",
            api_key=openai_key,
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
    job_url: str | None = None,
    candidate_id: str | None = None,
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
        job_url: Target job URL for JSON trace indexing.
        candidate_id: Active candidate ID for data isolation.

    Returns:
        Tuple of (full_output_text, action_count).
    """
    from browser_use import Agent, Browser

    llm = _get_llm()

    browser = Browser(
        cdp_url=f"http://localhost:{cdp_port}",
    )

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
        enable_signal_handler=False,  # We manage signals ourselves in launcher.py
    )

    with _agent_lock:
        _active_agents[worker_id] = agent

    action_count = 0
    output_text = ""
    history = None

    try:
        history = await agent.run(max_steps=max_steps)

        output_text = history.final_result() or ""
        action_count = len(history.action_names()) if history.action_names() else 0

        extracted = history.extracted_content()
        if extracted:
            for item in extracted:
                if item and item not in output_text:
                    output_text += f"\n{item}"

        if on_action and history.action_names():
            for action_name in history.action_names():
                on_action(action_name)

        if history.has_errors():
            actual_errors = [err for err in history.errors() if err is not None]
            for err in actual_errors:
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

        # Save structured JSON action trace for candidate verification
        if job_url:
            try:
                import hashlib, json
                from datetime import datetime, timezone
                from applypilot.config import get_active_candidate_id, get_candidate_traces_dir
                cid = candidate_id or get_active_candidate_id()
                job_hash = hashlib.md5(job_url.encode()).hexdigest()[:12]
                trace_path = get_candidate_traces_dir(cid) / f"{job_hash}.json"

                trace_payload = {
                    "candidate_id": cid,
                    "job_url": job_url,
                    "worker_id": worker_id,
                    "action_count": action_count,
                    "status": "applied" if "RESULT:APPLIED" in output_text else ("failed" if "RESULT:FAILED" in output_text else "completed"),
                    "output_text": output_text[:2000],
                    "actions": history.action_names() if history and hasattr(history, "action_names") else [],
                    "extracted": history.extracted_content() if history and hasattr(history, "extracted_content") else [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                trace_path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")
                logger.info("[worker-%d] Action trace saved: %s", worker_id, trace_path.name)
            except Exception as e:
                logger.debug("[worker-%d] Could not save JSON action trace: %s", worker_id, e)

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
    job_url: str | None = None,
    candidate_id: str | None = None,
) -> tuple[str, int]:
    """Synchronous wrapper for run_browser_agent.

    Creates a new event loop for each call, safe for use in
    ThreadPoolExecutor threads.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            run_browser_agent(
                task_prompt=task_prompt,
                cdp_port=cdp_port,
                worker_id=worker_id,
                max_steps=max_steps,
                on_action=on_action,
                job_url=job_url,
                candidate_id=candidate_id,
            )
        )
    finally:
        try:
            loop.close()
        except Exception:
            pass


def cancel_agent(worker_id: int) -> None:
    """Cancel the active agent for a worker (used for Ctrl+C skip).

    Calls agent.stop() which sets an internal flag that causes the
    agent's run loop to exit gracefully at the next step boundary.
    agent.stop() is synchronous and thread-safe.
    """
    with _agent_lock:
        agent = _active_agents.get(worker_id)
        if agent is not None:
            logger.info("[worker-%d] Cancelling agent via agent.stop()", worker_id)
            try:
                agent.stop()
            except Exception as exc:
                logger.debug("[worker-%d] agent.stop() error: %s", worker_id, exc)


def cancel_all_agents() -> None:
    """Cancel all active agents (used for shutdown)."""
    with _agent_lock:
        worker_ids = list(_active_agents.keys())
    for wid in worker_ids:
        cancel_agent(wid)
