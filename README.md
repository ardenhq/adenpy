# Arden Python SDK

**Policy enforcement and human approval workflows for AI agent tool calls.**

Arden sits between your AI agent and its tools. Every call is checked against your policies — automatically allowed, blocked, or held for a human to approve before execution continues.

## Installation

```bash
pip install ardenpy
```

## Quick Start

### 1. Get your API key

Visit [https://arden.sh](https://arden.sh) and create an agent. You'll get two keys:
- `arden_test_...` — for development, hits `https://api-test.arden.sh`
- `arden_live_...` — for production, hits `https://api.arden.sh`

### 2. Configure once

```python
import ardenpy as arden

arden.configure(api_key="arden_live_your_key_here")
```

### 3. Wrap your tools

```python
def issue_refund(amount: float, customer_id: str) -> dict:
    # your real implementation
    return {"refund_id": "re_123", "amount": amount}

safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

# Now call it normally — Arden enforces your policy
result = safe_refund(150.0, customer_id="cus_abc")
```

Depending on the policy you set for `stripe.issue_refund` in the dashboard, Arden will:
- **Allow** — execute immediately and return the result
- **Require approval** — pause until a human approves or denies it on the dashboard
- **Block** — raise `PolicyDeniedError` immediately

---

## Approval Modes

When a tool call requires human approval, you choose how your code handles the wait.

### Mode 1: `wait` (default)

Blocks the current thread until a human acts on the dashboard. The function either returns its result or raises `PolicyDeniedError`.

```python
safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

try:
    result = safe_refund(150.0, customer_id="cus_abc")
    # execution resumes here only after a human approves
    print(f"Refund issued: {result}")
except arden.PolicyDeniedError as e:
    print(f"Refund denied: {e}")
except arden.ApprovalTimeoutError as e:
    print(f"No response within timeout: {e}")
```

**When to use:** Simple scripts, CLI tools, synchronous request handlers where blocking is acceptable.

---

### Mode 2: `async`

Returns a `PendingApproval` object immediately. A background thread polls for the decision and calls your callback when it arrives.

```python
def on_approval(event: arden.WebhookEvent):
    # called from background thread when admin approves
    result = issue_refund(event.context["amount"], event.context["customer_id"])
    print(f"Refund issued: {result}")

def on_denial(event: arden.WebhookEvent):
    print(f"Refund denied: {event.notes}")

safe_refund = arden.guard_tool(
    "stripe.issue_refund",
    issue_refund,
    approval_mode="async",
    on_approval=on_approval,
    on_denial=on_denial,
)

pending = safe_refund(150.0, customer_id="cus_abc")
# returns PendingApproval(action_id="...", tool_name="stripe.issue_refund")
# your program continues; callbacks fire when the admin decides
print(f"Waiting for approval: {pending.action_id}")
```

**When to use:** Long-running processes (agents, workers) where you can't block the main loop.

> **Note:** `on_approval` and `on_denial` both receive a `WebhookEvent` (see [WebhookEvent reference](#webhookevent-reference)). The function is not re-executed automatically — you call it yourself inside the callback using `event.context`.

---

### Mode 3: `webhook`

Returns a `PendingApproval` object immediately. When the admin acts on the dashboard, Arden POSTs to your webhook endpoint. You call `arden.handle_webhook()` from your web server to dispatch to your callbacks.

This mode has **no background polling** — your server receives a push notification instead.

#### Step 1 — Configure your webhook in the Arden dashboard

Go to your agent's settings → Webhooks → add your endpoint URL (e.g. `https://yourapp.com/arden/webhook`) and note the **signing key**.

#### Step 2 — Wrap your tool

```python
def on_approval(event: arden.WebhookEvent):
    # The dashboard approved this call — re-execute with the approved args
    result = issue_refund(
        event.context["amount"],
        event.context["customer_id"],
    )
    # do whatever comes next: update DB, notify user, etc.
    print(f"Refund issued after approval: {result}")

def on_denial(event: arden.WebhookEvent):
    print(f"Refund denied by {event.approved_by}: {event.notes}")

safe_refund = arden.guard_tool(
    "stripe.issue_refund",
    issue_refund,
    approval_mode="webhook",
    on_approval=on_approval,
    on_denial=on_denial,
)

pending = safe_refund(150.0, customer_id="cus_abc")
# returns PendingApproval immediately — no blocking, no polling
```

#### Step 4 — Handle incoming webhooks in your web framework

Pass the signing key (shown in the Arden dashboard when you create the webhook) directly to `handle_webhook`. Keep it in an environment variable — don't hardcode it.

**FastAPI:**
```python
import os
from fastapi import Request
import ardenpy as arden

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

@app.post("/arden/webhook")
async def arden_webhook(request: Request):
    arden.handle_webhook(
        body=await request.body(),
        headers=dict(request.headers),
        signing_key=SIGNING_KEY,
    )
    return {"ok": True}
```

**Flask:**
```python
import os
from flask import request
import ardenpy as arden

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

@app.post("/arden/webhook")
def arden_webhook():
    arden.handle_webhook(
        body=request.get_data(),
        headers=dict(request.headers),
        signing_key=SIGNING_KEY,
    )
    return {"ok": True}
```

**Django:**
```python
import os
from django.views import View
from django.http import JsonResponse
import ardenpy as arden

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

class ArdenWebhookView(View):
    def post(self, request):
        arden.handle_webhook(
            body=request.body,
            headers=dict(request.headers),
            signing_key=SIGNING_KEY,
        )
        return JsonResponse({"ok": True})
```

`handle_webhook` verifies the `X-Arden-Signature` header, looks up the registered callbacks for the `action_id` in the payload, and calls `on_approval` or `on_denial`. It raises `ValueError` if the signature doesn't match.

#### Signature verification in your own middleware

If your framework already has webhook verification middleware, or you want to verify before doing anything else, use `verify_webhook_signature` directly instead of relying on `handle_webhook` to do it:

```python
import os
from ardenpy import verify_webhook_signature

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

# e.g. in a FastAPI dependency or Django middleware
timestamp = request.headers.get("X-Arden-Timestamp", "")
signature = request.headers.get("X-Arden-Signature", "")

if not verify_webhook_signature(request.body, timestamp, signature, SIGNING_KEY):
    raise HTTPException(status_code=401, detail="Invalid webhook signature")

# verified — now dispatch (pass signing_key=None to skip the second check)
arden.handle_webhook(body=request.body, headers={}, signing_key=None)
```

`verify_webhook_signature` returns `True`/`False` and takes the key directly — no `configure()` call needed.

**When to use:** Production services where you want push-based delivery instead of polling, or when your process may restart between the tool call and the approval.

---

## `WebhookEvent` Reference

Both `on_approval` and `on_denial` receive a `WebhookEvent` with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `str` | `"action_approved"` or `"action_denied"` |
| `action_id` | `str` | Unique ID for this approval request |
| `tool_name` | `str` | Tool name as passed to `guard_tool`, e.g. `"stripe.issue_refund"` |
| `context` | `dict` | All args submitted with the original call, keyed by parameter name |
| `approved_by` | `str \| None` | Admin user ID who acted on the dashboard |
| `notes` | `str \| None` | Admin notes from the dashboard |
| `raw` | `dict` | Full webhook payload for anything not covered above |

```python
def on_approval(event: arden.WebhookEvent):
    print(event.tool_name)          # "stripe.issue_refund"
    print(event.context["amount"])  # 150.0
    print(event.context["customer_id"])  # "cus_abc"
    print(event.approved_by)        # "user_admin123"
    print(event.notes)              # "Verified with customer"
```

---

## Policy Decision Reference

| Decision | What happens |
|----------|-------------|
| `allow` | Function executes immediately, returns its result |
| `requires_approval` | Depends on `approval_mode` — see above |
| `block` | `PolicyDeniedError` raised immediately, function never executes |

---

## Exceptions

```python
from ardenpy import PolicyDeniedError, ApprovalTimeoutError, ArdenError

try:
    result = safe_refund(150.0, customer_id="cus_abc")
except PolicyDeniedError as e:
    # Policy blocked this call, or a human denied it (wait mode)
    print(f"Blocked: {e}")
except ApprovalTimeoutError as e:
    # Nobody approved within max_poll_time (wait mode only)
    print(f"Timed out after {e.timeout}s, action_id={e.action_id}")
except ArdenError as e:
    # API communication error, misconfiguration, etc.
    print(f"Arden error: {e}")
```

---

## Configuration Reference

```python
arden.configure(
    api_key="arden_live_...",       # required
    environment="live",             # "live" or "test" (auto-detected from api_key prefix)
    api_url="https://api.arden.sh", # override API base URL
    timeout=30.0,                   # HTTP request timeout in seconds
    poll_interval=2.0,              # seconds between status polls (wait/async modes)
    max_poll_time=300.0,            # max seconds to wait before ApprovalTimeoutError
    retry_attempts=3,               # retries on transient API errors
)
```

The webhook signing key is **not** part of `configure()`. Pass it directly to `handle_webhook(signing_key=...)` or `verify_webhook_signature(...)` — it's a per-endpoint secret, not global SDK configuration.

Environment-specific helpers:
```python
arden.configure_test(api_key="arden_test_...")   # sets environment="test" automatically
arden.configure_live(api_key="arden_live_...")   # sets environment="live" automatically
```

---

## Framework Integration

`guard_tool` wraps a plain Python function, so it works with any agent framework.

### LangChain

```python
from langchain.tools import Tool
import ardenpy as arden

arden.configure(api_key="arden_live_...")

def send_email(to: str, subject: str, body: str) -> str:
    # real implementation
    return f"Email sent to {to}"

safe_email = arden.guard_tool("communication.email", send_email)

tools = [
    Tool(name="send_email", func=safe_email, description="Send an email"),
]
```

### CrewAI

```python
from crewai import tool
import ardenpy as arden

arden.configure(api_key="arden_live_...")

def process_refund(amount: float, customer_id: str) -> str:
    return f"Refund of ${amount} issued to {customer_id}"

safe_refund = arden.guard_tool("stripe.issue_refund", process_refund)

@tool("process_refund")
def refund_tool(amount: float, customer_id: str) -> str:
    """Issue a refund to a customer."""
    return safe_refund(amount, customer_id=customer_id)
```

### Direct OpenAI tool calls

```python
from openai import OpenAI
import ardenpy as arden
import json

arden.configure(api_key="arden_live_...")

def issue_refund(amount: float, customer_id: str) -> dict:
    return {"refund_id": "re_123", "amount": amount}

safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

# In your tool dispatch loop:
def handle_tool_call(name: str, arguments: dict):
    if name == "issue_refund":
        return safe_refund(**arguments)
```

---

## Links

- **Dashboard**: [https://app.arden.sh](https://app.arden.sh)
- **Documentation**: [https://arden.sh/docs](https://arden.sh/docs)
- **Website**: [https://arden.sh](https://arden.sh)
- **PyPI**: [https://pypi.org/project/ardenpy/](https://pypi.org/project/ardenpy/)
- **Support**: [team@arden.sh](mailto:team@arden.sh)

## License

MIT License — see LICENSE file for details.
