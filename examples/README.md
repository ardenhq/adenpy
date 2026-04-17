# Arden Examples

## Which example should I use?

| Situation | Example |
|-----------|---------|
| First time using Arden | `getting_started.py` |
| Custom agent, no framework | `custom_agent.py` |
| OpenAI Chat Completions loop | `direct_openai_integration.py` |
| Autonomous / AutoGPT-style agent | `autogpt_integration.py` |
| LangChain agent | `langchain_integration.py` |
| CrewAI agent | `crewai_integration.py` |
| Webhook-based (non-blocking) approvals | `webhook_server.py` |
| Comparing all three approval modes | `approval_workflows_demo.py` |

---

## Setup

```bash
export ARDEN_API_KEY="arden_live_..."    # from app.arden.sh
export OPENAI_API_KEY="sk-..."           # for examples that use GPT
```

---

## Examples

### `getting_started.py`
The minimal Arden integration. Wraps three plain functions with `guard_tool()` and shows allow / approval / block in action. No external dependencies beyond `ardenpy`.

```bash
pip install ardenpy
python getting_started.py
```

---

### `custom_agent.py`
Custom OpenAI Chat Completions loop using `guard_tool()` directly. The right pattern when you need per-tool control over the Arden name or approval mode.

```bash
pip install ardenpy openai
python custom_agent.py
```

---

### `direct_openai_integration.py`
Same as `custom_agent.py` but uses `ArdenToolExecutor` — the recommended helper for Chat Completions dispatch loops. Register tools once, call `executor.run(name, args)` in the loop.

```bash
pip install ardenpy openai
python direct_openai_integration.py
```

---

### `autogpt_integration.py`
Autonomous agent that loops until its goal is complete, using `ArdenToolExecutor`. Demonstrates how Arden policies gate each tool call even when the agent is running unsupervised.

```bash
pip install ardenpy openai
python autogpt_integration.py
```

---

### `langchain_integration.py`
LangChain `AgentExecutor` with Arden auto-patching. Call `configure()` once and every tool in the process is intercepted — no `protect_tools()` required. All tool calls are logged.

```bash
pip install "ardenpy[langchain]" langchain-community langchain-openai
python langchain_integration.py
```

---

### `langchain_protect_tools.py`
Same agent but using explicit `protect_tools()` to set a different approval mode (`webhook`) on a specific tool. All other tools are still auto-patched and logged. Use this only when you need per-tool approval mode overrides — `langchain_integration.py` covers the common case.

```bash
pip install "ardenpy[langchain]" langchain-community langchain-openai
python langchain_protect_tools.py
```

---

### `crewai_integration.py`
CrewAI agent with Arden auto-patching. Call `configure()` once and every `BaseTool._run()` call in the process is intercepted — define plain subclasses as usual. All tool calls are logged.

```bash
pip install "ardenpy[crewai]" crewai
python crewai_integration.py
```

---

### `crewai_protect_tools.py`
Same agent but using explicit `protect_tools()` to set a different approval mode (`webhook`) on a specific tool. All other tools are still auto-patched and logged. Use this only when you need per-tool approval mode overrides — `crewai_integration.py` covers the common case.

```bash
pip install "ardenpy[crewai]" crewai
python crewai_protect_tools.py
```

---

### `webhook_server.py`
Flask server that receives Arden approval/denial webhooks. Use this when your process can't block — tool calls return a `PendingApproval` immediately, and the server re-executes the function once an admin approves on the dashboard.

```bash
pip install ardenpy flask
export ARDEN_SIGNING_KEY="..."   # from dashboard webhook settings
python webhook_server.py
```

---

### `approval_workflows_demo.py`
Side-by-side comparison of all three approval modes (`wait`, `async`, `webhook`) using the same tool functions. Good reference for choosing the right mode.

```bash
pip install ardenpy
python approval_workflows_demo.py
```

---

## Key concept: which API to use

| Situation | API |
|-----------|-----|
| LangChain or CrewAI (standard) | `arden.configure(api_key="...")` — auto-patched, all tools logged |
| LangChain or CrewAI with per-tool approval modes | `protect_tools()` from `ardenpy.integrations.*` for those tools; the rest are still auto-patched |
| OpenAI Agents SDK | `protect_function_tools()` from `ardenpy.integrations.openai` |
| OpenAI Chat Completions loop | `ArdenToolExecutor` from `ardenpy.integrations.openai` |
| Custom agent, no framework | `arden.guard_tool(name, fn)` per tool |

## Does protect_tools() affect logging?

No. `configure()` must be called before `protect_tools()` (required to initialise the SDK), and that call auto-patches the framework's base class. This means:

- Tools **in** `protect_tools()` → handled by `guard_tool()` → logged via policy check ✅
- Tools **not in** `protect_tools()` → caught by the auto-patcher → also logged ✅

Every tool call appears in the action log regardless of which tools you explicitly wrap.

**Do not mix auto-patching with `protect_tools()` on the same tool** — the policy check would run twice. Tools wrapped explicitly are automatically skipped by the auto-patcher via the `_arden_guarded` sentinel.

## Session tracking

Attach a session ID to group all tool calls from a single conversation or run in the action log:

```python
import ardenpy as arden
import uuid

arden.configure(api_key="arden_live_...")

# Set once per request / conversation — picked up by all guard_tool and
# auto-patched tool calls in the current async task or thread.
arden.set_session(str(uuid.uuid4()))

# Clear when done (optional — collected automatically at task end)
arden.clear_session()
```

`set_session()` uses `contextvars.ContextVar`, so concurrent async requests
never share a session ID. Omitting it entirely has no effect — fully optional.
