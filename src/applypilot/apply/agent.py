"""Google Antigravity SDK agent runner for ApplyPilot Stage 6 (Auto-Apply).

Drives browser automation using the Google Antigravity (AGY) SDK and Playwright MCP.
Connects to an existing Chrome instance via CDP (Chrome DevTools Protocol)
and executes job application form-filling tasks autonomously.
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


def _get_model_name() -> str:
    """Determine the model name for Google Antigravity SDK.

    Reads AGY_MODEL or LLM_MODEL from environment, defaulting to 'gemini-2.5-pro'.
    """
    return (
        os.environ.get("AGY_MODEL")
        or os.environ.get("LLM_MODEL")
        or "gemini-2.5-pro"
    )


async def run_antigravity_agent(
    task_prompt: str,
    cdp_port: int,
    worker_id: int = 0,
    max_steps: int = 100,
    on_action: Callable[[str], None] | None = None,
) -> tuple[str, int]:
    """Run a Google Antigravity agent to complete a job application.

    Connects to an existing Chrome instance via Playwright MCP (over CDP)
    and drives it using Google Antigravity SDK.

    Args:
        task_prompt: The full instruction prompt (from prompt.py).
        cdp_port: CDP port of the Chrome instance to connect to.
        worker_id: Numeric worker identifier (for logging/tracking).
        max_steps: Maximum agent turns before timeout.
        on_action: Optional callback invoked with action description strings
                   as the agent takes actions (for dashboard updates).

    Returns:
        Tuple of (full_output_text, action_count).
    """
    from google.antigravity import Agent, LocalAgentConfig, types, policy

    model_name = _get_model_name()

    # Configure Playwright MCP server pointing to worker's Chrome CDP port
    viewport_size = config.DEFAULTS.get("viewport", "1280x900")
    mcp_servers = [
        types.McpStdioServer(
            command="npx",
            args=[
                "-y",
                "@playwright/mcp@latest",
                f"--cdp-endpoint=http://localhost:{cdp_port}",
                f"--viewport-size={viewport_size}",
            ],
        ),
        types.McpStdioServer(
            command="npx",
            args=["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
        ),
    ]

    agent_config = LocalAgentConfig(
        model=model_name,
        mcp_servers=mcp_servers,
        safety_policy=[
            policy.allow_all(),
        ],
    )

    action_count = 0
    output_text = ""

    try:
        async with Agent(agent_config) as agent:
            # Track for cancellation support
            with _agent_lock:
                _active_agents[worker_id] = agent

            # Instruct agent to perform task
            response = await agent.chat(task_prompt)
            output_text = await response.text()

            # Increment action count and invoke callback if available
            action_count = max(1, len(output_text.splitlines()) // 10)
            if on_action:
                on_action("Antigravity task completed")

    except asyncio.CancelledError:
        logger.info("[worker-%d] Antigravity Agent cancelled (skip requested)", worker_id)
        output_text = "RESULT:FAILED:cancelled"
    except Exception as exc:
        logger.exception("[worker-%d] Antigravity Agent crashed: %s", worker_id, exc)
        output_text = f"RESULT:FAILED:agent_crash:{str(exc)[:100]}"
    finally:
        with _agent_lock:
            _active_agents.pop(worker_id, None)

    return output_text, action_count


# Backwards compatibility alias for launcher / CLI references
run_browser_agent = run_antigravity_agent


def run_agent_sync(
    task_prompt: str,
    cdp_port: int,
    worker_id: int = 0,
    max_steps: int = 100,
    on_action: Callable[[str], None] | None = None,
) -> tuple[str, int]:
    """Synchronous wrapper for run_antigravity_agent.

    Creates a new event loop for each call, safe for use in ThreadPoolExecutor threads.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            run_antigravity_agent(
                task_prompt=task_prompt,
                cdp_port=cdp_port,
                worker_id=worker_id,
                max_steps=max_steps,
                on_action=on_action,
            )
        )
    finally:
        try:
            loop.close()
        except Exception:
            pass


def cancel_agent(worker_id: int) -> None:
    """Cancel the active Antigravity agent for a worker (used for Ctrl+C skip)."""
    with _agent_lock:
        agent = _active_agents.get(worker_id)
        if agent is not None:
            logger.info("[worker-%d] Cancelling Antigravity agent", worker_id)
            try:
                if hasattr(agent, "stop"):
                    agent.stop()
            except Exception as exc:
                logger.debug("[worker-%d] cancel_agent error: %s", worker_id, exc)


def cancel_all_agents() -> None:
    """Cancel all active Antigravity agents (used for shutdown)."""
    with _agent_lock:
        worker_ids = list(_active_agents.keys())
    for wid in worker_ids:
        cancel_agent(wid)
