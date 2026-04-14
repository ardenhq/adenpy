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
LangChain `AgentExecutor` with Arden protection via `protect_tools()`. One call wraps all tools — no per-class boilerplate.

```bash
pip install "ardenpy[langchain]" langchain-community langchain-openai
python langchain_integration.py
```

---

### `crewai_integration.py`
CrewAI agent using `protect_tools()` from `ardenpy.integrations.crewai`. Define plain `BaseTool` subclasses, then wrap them all at once.

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

## Key concept: guard_tool vs protect_tools

| API | When to use |
|-----|------------|
| `arden.guard_tool(name, fn)` | Custom / no-framework agents, or when you need per-tool control |
| `protect_tools(tools)` from `ardenpy.integrations.*` | LangChain or CrewAI — wraps all tools at once |
| `ArdenToolExecutor` from `ardenpy.integrations.openai` | OpenAI Chat Completions tool-call dispatch loop |

**Do not use both on the same function** — the policy check would run twice.
