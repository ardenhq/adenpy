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
LangChain `AgentExecutor` with Arden auto-patching. Call `configure()` once and every tool in the process is intercepted — no `protect_tools()` required.

```bash
pip install "ardenpy[langchain]" langchain-community langchain-openai
python langchain_integration.py
```

---

### `crewai_integration.py`
CrewAI agent with Arden auto-patching. Call `configure()` once and every `BaseTool._run()` call in the process is intercepted — define plain subclasses as usual.

```bash
pip install "ardenpy[crewai]" crewai
python crewai_integration.py
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
| LangChain or CrewAI | Just `arden.configure(api_key="...", tool_name_prefix="...")` — auto-patched |
| OpenAI Agents SDK | `protect_function_tools()` from `ardenpy.integrations.openai` |
| OpenAI Chat Completions loop | `ArdenToolExecutor` from `ardenpy.integrations.openai` |
| Custom agent, no framework | `arden.guard_tool(name, fn)` for per-tool control |
| LangChain/CrewAI with per-tool overrides | `protect_tools()` from `ardenpy.integrations.*` |

**Do not mix auto-patching with `protect_tools()` on the same tool** — the policy check would run twice. Tools wrapped explicitly with `protect_tools()` or `guard_tool()` are automatically skipped by the auto-patcher.
