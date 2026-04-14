# ardenpy

**Policy enforcement and human approval for AI agent tool calls.**

Arden sits between your agent and its tools. Every call is checked against policies you configure in the dashboard — automatically allowed, blocked, or held for a human to approve.

## Install

```bash
pip install ardenpy
```

For framework integrations:

```bash
pip install "ardenpy[langchain]"     # LangChain
pip install "ardenpy[crewai]"        # CrewAI
pip install "ardenpy[openai-agents]" # OpenAI Agents SDK
pip install "ardenpy[all]"           # everything
```

## Quick start

**1. Get your API key** from [app.arden.sh](https://app.arden.sh). You'll get two keys:
- `arden_test_...` — development, hits `api-test.arden.sh`
- `arden_live_...` — production, hits `api.arden.sh`

**2. Configure once**

```python
import ardenpy as arden
arden.configure(api_key="arden_live_...")
```

**3. Wrap your tools and call them normally**

```python
def issue_refund(amount: float, customer_id: str) -> dict:
    return {"refund_id": "re_123", "amount": amount}

safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

result = safe_refund(150.0, customer_id="cus_abc")
# Arden checks policy first — allow, block, or wait for human approval
```

---

## How it works

Every tool call goes through a policy check before executing:

| Policy decision | What happens |
|----------------|-------------|
| `allow` | Function executes immediately |
| `block` | `PolicyDeniedError` raised, function never runs |
| `requires_approval` | Pauses until a human approves or denies on the dashboard |

**No policy configured?** The call is allowed automatically and logged — you get a full audit trail from day one and can add policies incrementally.

---

## Approval modes

When a tool requires approval, you choose how your code waits:

**`wait` (default)** — blocks until a human acts, then executes or raises `PolicyDeniedError`.
Good for scripts and synchronous code.

**`async`** — returns a `PendingApproval` immediately, background thread polls and calls your callback.
Good for long-running agents that can't block.

**`webhook`** — returns `PendingApproval` immediately, no polling. Arden POSTs to your endpoint when an admin decides. Good for production services.

```python
# wait (default)
safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

# async
safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund,
    approval_mode="async", on_approval=handle_approval, on_denial=handle_denial)

# webhook
safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund,
    approval_mode="webhook", on_approval=on_approval, on_denial=on_denial)
```

For webhook setup (FastAPI, Flask, Django examples) see the [Library Reference](LIBRARY_REFERENCE.md#webhook-integration).

---

## Framework integrations

**Wrap all your tools — Arden enforces only the ones you configure policies for.**
No need to cherry-pick which tools are risky. Tools with no policy pass through automatically, logged for visibility.

### LangChain

```python
from ardenpy.integrations.langchain import protect_tools

safe_tools = protect_tools(all_my_tools, tool_name_prefix="support")
# Arden name: "support.{tool.name}" — create policies in dashboard for any you want to control
```

### CrewAI

```python
from ardenpy.integrations.crewai import protect_tools

safe_tools = protect_tools([RefundTool(), SearchTool()], tool_name_prefix="support")
agent = Agent(role="Support", tools=safe_tools, ...)
```

### OpenAI Chat Completions

```python
from ardenpy.integrations.openai import ArdenToolExecutor

executor = ArdenToolExecutor(tool_name_prefix="support")
executor.register("issue_refund", issue_refund_fn)
executor.register("send_email",   send_email_fn)

# In your loop:
result = executor.run(tc.function.name, json.loads(tc.function.arguments))
```

### OpenAI Agents SDK

```python
from ardenpy.integrations.openai import protect_function_tools

safe_tools = protect_function_tools([issue_refund, search], tool_name_prefix="support")
agent = Agent(name="SupportBot", tools=safe_tools)
```

See [examples/](examples/README.md) for runnable code for every integration.

---

## Error handling

```python
try:
    result = safe_refund(150.0, customer_id="cus_abc")
except arden.PolicyDeniedError:
    # blocked by policy, or denied by a human
except arden.ApprovalTimeoutError:
    # nobody approved within max_poll_time (wait mode)
except arden.ArdenError:
    # API/configuration error
```

---

## Links

- [Library Reference](LIBRARY_REFERENCE.md) — full API docs
- [Examples](examples/README.md) — runnable code
- [Dashboard](https://app.arden.sh)
- [PyPI](https://pypi.org/project/ardenpy/)
- [Support](mailto:team@arden.sh)
