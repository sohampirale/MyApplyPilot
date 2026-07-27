# ApplyPilot: Local Setup, Logins & LLM Customization Guide

This document summarizes key research and architectural findings regarding running **ApplyPilot** locally, how login/session management works, and how to configure or swap LLM providers (including alternatives to Claude Code).

---

## 1. Local Testing & Execution Strategy

Running ApplyPilot locally on your personal machine allows you to inspect its real-time behavior, test application flows safely, and evaluate edge cases before any large-scale deployment.

### System Prerequisites
* **Python**: Python 3.11+ (Verified local version: `3.12.3`)
* **Node.js**: Node 18+ (Verified local version: `v24.17.0`) — required for `@playwright/mcp`
* **Browser**: Chrome or Chromium (Verified local version: `Chromium 150`)

### Quick Setup Steps
1. **Initialize configuration**:
   ```bash
   applypilot init
   ```
   This generates:
   * `profile.json`: Personal details, work history, compensation expectations, skills, and immutable `resume_facts`.
   * `searches.yaml`: Target job titles, locations, and search filters.
   * `.env`: API key configuration for chosen LLM models.

2. **Verify Setup**:
   ```bash
   applypilot doctor
   ```

3. **Safe Dry-Run Testing**:
   To test form navigation and auto-filling without submitting applications:
   ```bash
   applypilot apply --dry-run
   ```

---

## 2. Authentication, Logins & Session Cookies

A common question is whether you need to be manually logged into job platforms beforehand. Here is how ApplyPilot manages sessions:

1. **Chrome Profile Cloning**:
   * On first run of Stage 6 (Auto-Apply), ApplyPilot can clone essential cookies and preferences from your default Chrome profile (`setup_worker_profile()` in `src/applypilot/apply/chrome.py`).
   * Active session cookies carry over, avoiding repetitive logins on sites you already use.

2. **Automated Account Creation & Login**:
   * If no active session exists on platforms that require logins (e.g. Workday employer portals), the agent reads your credentials from `profile.json` (`email` and `password`) to log in or create a candidate account.

3. **Automated One-Time Passwords (OTP)**:
   * If an application sends a verification code via email, ApplyPilot integrates with a Gmail MCP server (`@gongrzhe/server-gmail-autoauth-mcp`) to read your inbox and enter the code into the form.

4. **Guest Applications**:
   * Standard ATS platforms (Greenhouse, Lever, SmartRecruiters, BambooHR) do not require accounts. The agent submits contact details, answers screening questions, and uploads resume/cover letter PDFs directly.

5. **SSO / OAuth Restrictions**:
   * ApplyPilot explicitly flags third-party SSO logins ("Sign in with Google/Microsoft") to avoid OAuth blocks. If SSO is strictly required, the job is flagged as `RESULT:FAILED:sso_required`. You can run with `--headless=false` to complete visual logins manually when needed.

---

## 3. LLM Architecture & Customization

The ApplyPilot pipeline is split into two distinct LLM operational zones:

```
┌─────────────────────────────────────────────────────────┐
│               APPLYPILOT LLM ARCHITECTURE              │
├───────────────────────────────────┬─────────────────────┤
│ STAGES 1-5 (Scoring, Tailoring,   │ STAGE 6             │
│ Cover Letters, Description Enrich)│ (Browser Auto-Apply)│
├───────────────────────────────────┼─────────────────────┤
│ Uses `LLMClient` (src/applypilot/ │ Spawns Claude Code  │
│ llm.py)                           │ CLI with Playwright │
│                                   │ MCP server          │
│ Supported:                        │                     │
│  - Google Gemini (Free Tier)      │ Standard:           │
│  - OpenAI (gpt-4o, gpt-4o-mini)   │  - Claude 3.5 Sonnet│
│  - Ollama / Local Models (Qwen)   │  - Claude 3 Haiku   │
│  - DeepSeek / OpenRouter          │                     │
└───────────────────────────────────┴─────────────────────┘
```

### Stages 1–5: Multi-Provider Support (`src/applypilot/llm.py`)
These stages handle job match scoring, resume tailoring, and cover letter generation. **Claude is NOT required for Stages 1–5.**

* **Google Gemini (Recommended & Free)**:
  * Set `GEMINI_API_KEY` in `.env`.
  * Uses `gemini-2.0-flash` / `gemini-2.5-flash` by default. Free tier provides 15 RPM and 1,000,000 tokens/day.
* **OpenAI**:
  * Set `OPENAI_API_KEY` in `.env`.
* **Local Models via Ollama / llama.cpp**:
  * Run 100% offline and free on your GPU/CPU.
  * Set in `.env`:
    ```env
    LLM_URL=http://localhost:11434/v1
    LLM_MODEL=qwen2.5-coder
    ```
* **Any OpenAI-Compatible Endpoint**:
  * Works with DeepSeek, Groq, OpenRouter, or Together AI by configuring `LLM_URL` and `LLM_MODEL`.

---

## 4. Using Non-Claude Models for Stage 6 (Browser Auto-Apply)

By default, Stage 6 invokes the `claude` CLI in `src/applypilot/apply/launcher.py` because Claude Code CLI natively connects to the Playwright MCP server via `--mcp-config`.

If you prefer **not to use Claude Code** for Stage 6, you have two options:

### Option A: Discovery & Tailoring Mode (`applypilot run`)
* Run Stages 1–5 using **Gemini, OpenAI, or local Ollama**.
* Generates tailored PDF resumes and cover letters for all high-fit jobs.
* Submit applications manually or semi-automatically with pre-tailored documents.

### Option B: Replace the Agent Runner in `src/applypilot/apply/launcher.py`
Because browser form automation uses standard Model Context Protocol (MCP), you can swap out the `claude` CLI invocation:
1. **Open-Source MCP Runners**: Use an alternative MCP CLI tool (e.g. `goose`, `mcp-cli`, or `langchain`) that supports Gemini, OpenAI, or local models.
2. **Custom Playwright Script**: Replace the Claude CLI subprocess with a Python Playwright loop using `LLMClient` directly (via Gemini 2.5 Pro / GPT-4o / Qwen 2.5) to inspect page DOM elements and auto-fill input fields.

---

## 5. Workflow Summary for Local Development

1. **Test Stages 1–5**:
   ```bash
   applypilot run
   ```
2. **Preview Auto-Apply (No Submission)**:
   ```bash
   applypilot apply --dry-run --headless=false
   ```
3. **Inspect Output Files**:
   * Tailored Resumes & Cover Letters: `~/.applypilot/tailored/`
   * Execution Logs: `~/.applypilot/logs/`
   * Real-time Dashboard: `applypilot dashboard`
