# Arden Python SDK — Library Reference

This document is the complete reference for the `ardenpy` SDK. It covers every public function, class, parameter, return value, exception, and behavioral detail.

---

## Table of Contents

1. [Installation](#installation)
2. [How It Works](#how-it-works)
3. [Configuration](#configuration)
   - [configure()](#configure)
   - [configure_test()](#configure_test)
   - [configure_live()](#configure_live)
   - [get_config()](#get_config)
   - [is_configured()](#is_configured)
   - [ArdenConfig](#ardenconfig)
4. [Protecting Tool Calls](#protecting-tool-calls)
   - [guard_tool()](#guard_tool)
   - [Tool Naming](#tool-naming)
   - [How Arguments Are Sent](#how-arguments-are-sent)
5. [Approval Modes](#approval-modes)
   - [wait (default)](#wait-mode)
   - [async](#async-mode)
   - [webhook](#webhook-mode)
6. [Webhook Integration](#webhook-integration)
   - [handle_webhook()](#handle_webhook)
   - [verify_webhook_signature()](#verify_webhook_signature)
   - [Webhook Payload Reference](#webhook-payload-reference)
   - [Framework Examples](#framework-examples)
7. [Framework Integrations](#framework-integrations)
   - [LangChain](#langchain-integration)
   - [CrewAI](#crewai-integration)
   - [OpenAI](#openai-integration)
8. [Types and Data Classes](#types-and-data-classes)
   - [WebhookEvent](#webhookevent)
   - [PendingApproval](#pendingapproval)
   - [PolicyDecision](#policydecision)
   - [ActionStatus](#actionstatus)
9. [Exceptions](#exceptions)
   - [ArdenError](#ardenerror)
   - [PolicyDeniedError](#policydeniderror)
   - [ApprovalTimeoutError](#approvaltimeouterror)
   - [ConfigurationError](#configurationerror)
10. [Error Handling Patterns](#error-handling-patterns)
11. [Policy Configuration](#policy-configuration)
12. [Environments](#environments)
13. [Logging](#logging)

---

## Installation

```bash
pip install ardenpy
```

Requires Python 3.8 or later.

---

## How It Works

Every tool call protected by Arden follows this sequence:

1. Your code calls the wrapped function (e.g. `safe_refund(150.0, customer_id="cus_abc")`).
2. The SDK sends the tool name and all arguments to the Arden policy engine.
3. The policy engine evaluates the call against the rules you configured in the dashboard for this agent.
4. One of three decisions is returned:
   - **allow** — the SDK immediately executes the original function and returns its result.
   - **block** — the SDK raises `PolicyDeniedError` without executing the function.
   - **requires_approval** — a human must approve or deny the call on the Arden dashboard before anything executes. How your code waits for that decision depends on the [approval mode](#approval-modes) you chose.

The original function is **never executed** unless the policy explicitly allows it or a human approves it.

---

## Configuration

Configure the SDK once at application startup, before any calls to `guard_tool()`.

---

### `configure()`

```python
ardenpy.configure(
    api_key: str | None = None,
    api_url: str | None = None,
    environment: str | None = None,
    timeout: float | None = None,
    poll_interval: float | None = None,
    max_poll_time: float | None = None,
    retry_attempts: int | None = None,
    signing_key: str | None = None,
) -> ArdenConfig
```

Sets the global SDK configuration. Returns the resulting `ArdenConfig` instance.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | `ARDEN_API_KEY` env var | Your agent's API key. Keys beginning with `arden_test_` automatically set `environment="test"`. Keys beginning with `arden_live_` set `environment="live"`. |
| `api_url` | `str` | Auto-set from environment | Base URL for the Arden API. Defaults to `https://api-test.arden.sh` in test mode and `https://api.arden.sh` in live mode. Override only if self-hosting. |
| `environment` | `str` | `"live"` | Either `"test"` or `"live"`. Auto-detected from the API key prefix when possible. |
| `timeout` | `float` | `30.0` | Seconds before an individual HTTP request to the Arden API times out. |
| `poll_interval` | `float` | `2.0` | Seconds between status checks when polling for approval in `wait` or `async` modes. |
| `max_poll_time` | `float` | `300.0` | Maximum total seconds to wait for a human decision before raising `ApprovalTimeoutError`. Applies to `wait` and `async` modes. |
| `retry_attempts` | `int` | `3` | Number of times to retry a failed HTTP request before raising `ArdenError`. |
| `signing_key` | `str` | `None` | HMAC-SHA256 signing key for verifying incoming webhook payloads. |

**Returns** — `ArdenConfig`

**Raises**
- `ValueError` — if `api_key` is not provided and `ARDEN_API_KEY` is not set, or if any parameter value is invalid.

**Notes**

- `configure()` must be called before any `guard_tool()` call.
- `configure()` automatically detects and patches installed AI frameworks (LangChain, CrewAI, OpenAI Agents SDK). After it returns, all tool calls from those frameworks are intercepted, enforced, and logged — no explicit wrapping is needed. See [Framework Integrations](#framework-integrations).
- Calling `configure()` a second time overwrites the previous configuration globally.
- The `api_key` can also be set via the `ARDEN_API_KEY` environment variable. If both are provided, the explicit parameter takes precedence.

**Example**

```python
import ardenpy as arden

arden.configure(
    api_key="arden_live_3e6159f645814adfa86b01f8c368d503",
    timeout=60.0,
    max_poll_time=600.0,
)
```

Reading from environment:

```python
import os
import ardenpy as arden

# ARDEN_API_KEY is set in the environment
arden.configure()
```

---

### `configure_test()`

```python
ardenpy.configure_test(api_key: str, **kwargs) -> ArdenConfig
```

Convenience wrapper for `configure()` that sets `environment="test"` and points the API URL to `https://api-test.arden.sh`. Accepts all the same keyword arguments as `configure()`.

**Example**

```python
arden.configure_test(api_key="arden_test_79ca7d77540646be88ce65f276adc32d")
```

---

### `configure_live()`

```python
ardenpy.configure_live(api_key: str, **kwargs) -> ArdenConfig
```

Convenience wrapper for `configure()` that sets `environment="live"` and points the API URL to `https://api.arden.sh`. Accepts all the same keyword arguments as `configure()`.

**Example**

```python
arden.configure_live(api_key="arden_live_3e6159f645814adfa86b01f8c368d503")
```

---

### `get_config()`

```python
ardenpy.get_config() -> ArdenConfig
```

Returns the current global `ArdenConfig` instance.

**Raises**
- `ConfigurationError` — if `configure()` has not been called.

---

### `is_configured()`

```python
ardenpy.is_configured() -> bool
```

Returns `True` if `configure()` has been called and a global configuration exists, `False` otherwise. Does not raise.

**Example**

```python
if not arden.is_configured():
    arden.configure(api_key=os.environ["ARDEN_API_KEY"])
```

---

### `ArdenConfig`

The configuration object returned by `configure()`. All fields are read-only after construction.

```python
class ArdenConfig:
    api_key: str
    api_url: str
    environment: str           # "test" or "live"
    timeout: float             # default 30.0
    poll_interval: float       # default 2.0
    max_poll_time: float       # default 300.0
    retry_attempts: int        # default 3
```

---

## Protecting Tool Calls

---

### `guard_tool()`

```python
ardenpy.guard_tool(
    tool_name: str,
    func: Callable,
    approval_mode: str = "wait",
    on_approval: Callable[[WebhookEvent], None] | None = None,
    on_denial: Callable[[WebhookEvent], None] | None = None,
) -> Callable
```

Wraps `func` with Arden policy enforcement. Returns a new callable with the same signature as `func`. The original function is not modified.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tool_name` | `str` | required | The name used to look up this tool's policy in the dashboard. See [Tool Naming](#tool-naming). |
| `func` | `Callable` | required | The function to protect. Must be a plain Python callable. Works with instance methods, static methods, lambdas, and functions with any signature. |
| `approval_mode` | `str` | `"wait"` | How the SDK behaves when a policy decision of `requires_approval` is returned. One of `"wait"`, `"async"`, or `"webhook"`. See [Approval Modes](#approval-modes). |
| `on_approval` | `Callable` | `None` | Required when `approval_mode` is `"async"` or `"webhook"`. Called when a human approves the action. Receives a `WebhookEvent`. |
| `on_denial` | `Callable` | `None` | Required when `approval_mode` is `"async"` or `"webhook"`. Called when a human denies the action. Receives a `WebhookEvent`. |

**Returns**

A callable with the same signature as `func`. When the policy decision is:
- `allow` — returns whatever `func` returns.
- `block` — raises `PolicyDeniedError`.
- `requires_approval` — depends on `approval_mode` (see below).

**Raises** (at call time, not at wrap time)

| Exception | When |
|-----------|------|
| `ArdenError` | SDK is not configured, or API communication failed. |
| `PolicyDeniedError` | Policy decision is `block`, or a human denied the action (`wait` mode only). |
| `ApprovalTimeoutError` | No human decision within `max_poll_time` (`wait` mode only). |

**Raises** (at wrap time)

| Exception | When |
|-----------|------|
| `ArdenError` | `configure()` has not been called before `guard_tool()` is invoked. |

**Example — basic usage**

```python
import ardenpy as arden

arden.configure(api_key="arden_live_...")

def issue_refund(amount: float, customer_id: str) -> dict:
    # real implementation
    return {"refund_id": "re_123", "amount": amount}

safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

# Later, in your agent or request handler:
result = safe_refund(150.0, customer_id="cus_abc")
```

**Notes**

- `guard_tool()` can be called at module level (before any requests are processed). The policy check happens at call time, not at wrap time.
- The wrapped function preserves the original function's `__name__`, `__doc__`, and `__module__` via `functools.wraps`.
- Multiple calls to `guard_tool()` with the same `tool_name` are independent — each creates a separate wrapped function.

---

### Tool Naming

The `tool_name` string is the key that links a function call to a policy rule in the dashboard. It has no technical constraints, but the recommended format is `namespace.action` or `namespace.resource.action`.

**Convention**

```
<service_or_domain>.<action>
```

Examples:

| Tool name | What it represents |
|-----------|-------------------|
| `stripe.issue_refund` | Issue a refund via Stripe |
| `stripe.create_charge` | Create a charge via Stripe |
| `communication.email` | Send an email |
| `communication.sms` | Send an SMS |
| `database.delete` | Delete a database record |
| `database.read` | Read from a database |
| `file.write` | Write a file |
| `deployment.production` | Deploy to production |

**Wildcard matching in policies**

In the dashboard, policies support wildcards on the resource segment. A policy for `communication.*` matches `communication.email`, `communication.sms`, and any other tool starting with `communication.`.

A single `*` policy matches all tools — useful as a default deny rule.

---

### How Arguments Are Sent

When the wrapped function is called, the SDK captures all arguments by name using Python's `inspect.signature` and sends them to the policy engine as a `kwargs` dictionary, regardless of whether they were passed positionally or by keyword.

```python
def issue_refund(amount: float, customer_id: str) -> dict:
    ...

safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

# Both of these send {"amount": 150.0, "customer_id": "cus_abc"} to the policy engine:
safe_refund(150.0, "cus_abc")
safe_refund(amount=150.0, customer_id="cus_abc")
```

This matters because policy rules use argument values to make decisions — for example, a rule like `amount > 100` requires the policy engine to see `amount` as a named key.

Default parameter values are included. If `customer_id` defaults to `"unknown"` and you don't pass it, `{"amount": 150.0, "customer_id": "unknown"}` is sent.

---

## Approval Modes

When a policy decision of `requires_approval` is returned, the SDK's behavior depends on the `approval_mode` you set on `guard_tool()`.

---

### Wait Mode

```python
approval_mode="wait"   # default
```

**Behavior:** Blocks the calling thread. Polls the Arden API every `poll_interval` seconds until a human approves or denies the action on the dashboard, or until `max_poll_time` seconds have passed.

- If approved: executes `func` and returns its result.
- If denied: raises `PolicyDeniedError`.
- If `max_poll_time` is exceeded: raises `ApprovalTimeoutError`.

**Return value:** The return value of `func` (same as if there were no policy check).

**Example**

```python
safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)

try:
    result = safe_refund(150.0, customer_id="cus_abc")
    # Execution only reaches here after a human approves on the dashboard.
    print(f"Refund issued: {result}")

except arden.PolicyDeniedError as e:
    # Human clicked "Deny" on the dashboard, or policy blocked it outright.
    print(f"Refund blocked: {e}")
    print(f"Tool name: {e.tool_name}")

except arden.ApprovalTimeoutError as e:
    # Nobody responded within max_poll_time seconds.
    print(f"Timed out after {e.timeout}s (action_id={e.action_id})")
```

**When to use:** Scripts, CLI tools, synchronous web request handlers, or any context where blocking the current thread is acceptable and the caller expects a direct result.

**Resource usage note:** In wait mode, the thread is held open for up to `max_poll_time` seconds polling at `poll_interval` intervals. For workloads with many concurrent pending approvals or long approval windows, prefer `async` or `webhook` mode.

---

### Async Mode

```python
approval_mode="async",
on_approval=...,
on_denial=...,
```

**Behavior:** Returns a `PendingApproval` object immediately. A daemon background thread begins polling for the approval decision. When a human acts on the dashboard, the thread calls either `on_approval` or `on_denial`.

- `on_approval` receives a `WebhookEvent`. It is called **after** the SDK has already executed `func` with the original arguments — the result of `func` is passed to `on_approval` as its argument. **Note: in async mode, `on_approval` receives the function's return value directly, not a `WebhookEvent`.**
- `on_denial` receives a `PolicyDeniedError` exception object.

**Return value:** `PendingApproval(action_id=..., tool_name=...)`

**Parameters**

Both `on_approval` and `on_denial` are required. Omitting either raises `ArdenError` at call time.

| Callback | Receives | Called when |
|----------|----------|-------------|
| `on_approval` | The return value of `func` | Human approves; `func` was executed successfully |
| `on_denial` | `PolicyDeniedError` or other `Exception` | Human denies, or `func` raises after approval |

**Example**

```python
results_log = []

def on_approval(result):
    # result is the return value of issue_refund(...)
    results_log.append(result)
    notify_customer(result["refund_id"])

def on_denial(error):
    # error is a PolicyDeniedError
    log_denied_refund(str(error))

safe_refund = arden.guard_tool(
    "stripe.issue_refund",
    issue_refund,
    approval_mode="async",
    on_approval=on_approval,
    on_denial=on_denial,
)

pending = safe_refund(150.0, customer_id="cus_abc")
print(f"Queued for approval: {pending.action_id}")
# Code here runs immediately without waiting for the decision.
```

**Thread safety:** `on_approval` and `on_denial` are called from a daemon background thread, not the thread that called the wrapped function. Ensure any shared state accessed inside these callbacks is thread-safe.

**Process lifetime:** The background thread is a daemon thread. If the process exits before a decision is reached, the thread is silently killed. For long approval windows in short-lived processes, use `webhook` mode instead.

**When to use:** Long-running services (agents, workers) where you cannot block the main thread but also don't have an HTTP server to receive webhooks.

---

### Webhook Mode

```python
approval_mode="webhook",
on_approval=...,
on_denial=...,
```

**Behavior:** Returns a `PendingApproval` object immediately. No background thread is started. Instead, when a human acts on the Arden dashboard, the Arden backend makes an HTTP POST to the webhook URL you configured for this agent in the dashboard. Your web server receives the POST and calls `arden.handle_webhook()`, which dispatches to the registered `on_approval` or `on_denial` callback.

**Return value:** `PendingApproval(action_id=..., tool_name=...)`

**Parameters**

Both `on_approval` and `on_denial` are required. Omitting either raises `ArdenError` at call time.

| Callback | Receives | Called when |
|----------|----------|-------------|
| `on_approval` | `WebhookEvent` | Human approves on the dashboard |
| `on_denial` | `WebhookEvent` | Human denies on the dashboard |

Unlike async mode, **the SDK does not re-execute `func` automatically.** Your `on_approval` callback receives the full context of the original call (via `WebhookEvent.context`) and is responsible for re-executing the function if needed.

**Example**

```python
def on_approval(event: arden.WebhookEvent):
    # event.context contains all the arguments from the original call
    result = issue_refund(
        event.context["amount"],
        event.context["customer_id"],
    )
    notify_customer(result["refund_id"])

def on_denial(event: arden.WebhookEvent):
    notify_customer_of_denial(event.notes)

safe_refund = arden.guard_tool(
    "stripe.issue_refund",
    issue_refund,
    approval_mode="webhook",
    on_approval=on_approval,
    on_denial=on_denial,
)

pending = safe_refund(150.0, customer_id="cus_abc")
# Returns immediately. on_approval fires when the dashboard POST arrives.
print(f"Pending: {pending.action_id}")
```

**Callback storage:** Callbacks are stored in a module-level in-memory dictionary keyed by `action_id`. If the process restarts between the original call and the webhook delivery, the callbacks will not be found and `handle_webhook()` will log a warning and return without calling anything. For processes that may restart, consider saving the `action_id` to a database and re-registering the callback after restart, or use `async` mode.

**When to use:** Production services with a publicly reachable HTTP endpoint, or any scenario where you want push-based delivery without long-lived polling threads.

---

## Webhook Integration

---

### `handle_webhook()`

```python
ardenpy.handle_webhook(
    body: bytes,
    headers: dict[str, str],
    signing_key: str | None = None,
) -> None
```

Processes an incoming webhook POST from the Arden backend. Call this from your web framework's route handler when Arden POSTs to your configured webhook URL.

**What it does, in order:**

1. Normalises header keys to lowercase for case-insensitive lookup.
2. Reads the signing key from the `signing_key` parameter (or falls back to `configure(signing_key=...)` if set).
3. If a signing key is available, verifies the `X-Arden-Signature` header using `verify_webhook_signature()`. Raises `ValueError` if the signature does not match.
4. Parses the JSON body. Raises `ArdenError` if parsing fails.
5. Looks up the registered callbacks for the `action_id` in the payload.
6. Calls `on_approval(event)` or `on_denial(event)` with a `WebhookEvent`.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `body` | `bytes` | required | The raw, unparsed request body. Must be bytes, not a decoded string. |
| `headers` | `dict` | required | The request headers as a dictionary. Keys are matched case-insensitively. |
| `signing_key` | `str \| None` | `None` | The webhook signing key from the Arden dashboard. Pass it directly here rather than in `configure()`. If `None` and no key is configured globally, signature verification is skipped with a warning. |

**Returns** — `None`

**Raises**

| Exception | When |
|-----------|------|
| `ValueError` | Signature headers are present but `X-Arden-Timestamp` or `X-Arden-Signature` are missing, or the signature does not match. |
| `ArdenError` | The request body is not valid JSON, or the payload is missing `action.action_id`. |

**Notes**

- If `handle_webhook()` finds no registered callback for the `action_id`, it logs a warning at `WARNING` level and returns without raising. This handles replayed webhooks, duplicate deliveries, and process-restart scenarios gracefully — your server will still return a 200 to Arden.
- Always return HTTP 200 from your webhook endpoint regardless of internal errors, unless signature verification fails (in which case return 401). Returning 4xx or 5xx causes Arden to retry the delivery.
- Exceptions raised by your `on_approval` or `on_denial` callbacks propagate out of `handle_webhook()`. Wrap them in a `try/except` at the route level if you do not want callback errors to affect the HTTP response.

**Framework examples** — see [Framework Examples](#framework-examples).

---

### `verify_webhook_signature()`

```python
ardenpy.verify_webhook_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_key: str,
) -> bool
```

Verifies an Arden webhook signature. Exposed as a standalone function for integration into custom middleware or existing webhook verification pipelines, without using `handle_webhook()`.

**Signing scheme**

Arden computes the signature as:

```
HMAC-SHA256(signing_key, "{timestamp}.{raw_body_as_string}")
```

and sends it as:

```
X-Arden-Signature: sha256=<lowercase_hex_digest>
X-Arden-Timestamp: <unix_timestamp_seconds>
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `body` | `bytes` | The raw request body bytes, before any JSON parsing. |
| `timestamp` | `str` | The value of the `X-Arden-Timestamp` request header. |
| `signature` | `str` | The value of the `X-Arden-Signature` request header, including the `sha256=` prefix. |
| `signing_key` | `str` | The signing key from the Arden dashboard for this agent's webhook. |

**Returns** — `bool`. `True` if the signature is valid, `False` otherwise.

**Security note:** The comparison is performed using `hmac.compare_digest()`, which runs in constant time to prevent timing attacks. Always use the return value with a conditional check rather than catching exceptions.

**Notes**

- This function requires no call to `configure()` — it is fully self-contained.
- It does not validate that the timestamp is recent. If you want to reject replayed webhooks, check that `abs(time.time() - int(timestamp)) < 300` before or after calling this function.

**Example — standalone middleware**

```python
import os
import time
from ardenpy import verify_webhook_signature

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]
MAX_TIMESTAMP_AGE_SECONDS = 300

def verify_arden_request(body: bytes, headers: dict) -> bool:
    timestamp = headers.get("X-Arden-Timestamp", "")
    signature = headers.get("X-Arden-Signature", "")

    # Reject stale timestamps to prevent replay attacks
    try:
        if abs(time.time() - int(timestamp)) > MAX_TIMESTAMP_AGE_SECONDS:
            return False
    except (ValueError, TypeError):
        return False

    return verify_webhook_signature(body, timestamp, signature, SIGNING_KEY)
```

---

### Webhook Payload Reference

When Arden POSTs to your webhook URL, the request body is a JSON object with the following structure:

```json
{
  "event_type": "action_approved",
  "timestamp": "2026-03-31T23:17:22+00:00",
  "action": {
    "action_id": "83acb7a0-1225-4c74-b303-78252d94c6b2",
    "tool_name": "stripe.issue_refund",
    "status": "approved",
    "agent_id": "live_agent_149ab453869b4792",
    "context": {
      "amount": 150.0,
      "customer_id": "cus_abc123"
    }
  },
  "approval": {
    "action": "approve",
    "admin_user_id": "user_admin123",
    "notes": "Verified with customer, amount is correct"
  }
}
```

**Top-level fields**

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `event_type` | `string` | `"action_approved"`, `"action_denied"` | The outcome of the human review. |
| `timestamp` | `string` | ISO 8601 | When the approval decision was made. |
| `action` | `object` | — | Details about the original tool call. |
| `approval` | `object` | — | Details about the human decision. |

**`action` object**

| Field | Type | Description |
|-------|------|-------------|
| `action_id` | `string` | UUID identifying this approval request. Matches `PendingApproval.action_id`. |
| `tool_name` | `string` | The `tool_name` passed to `guard_tool()`. |
| `status` | `string` | `"approved"` or `"denied"`. |
| `agent_id` | `string` | The Arden agent ID associated with the API key. |
| `context` | `object` | All arguments from the original function call, keyed by parameter name. This is what you use to re-execute the function in `on_approval`. |

**`approval` object**

| Field | Type | Description |
|-------|------|-------------|
| `action` | `string` | `"approve"` or `"deny"`. |
| `admin_user_id` | `string` | ID of the admin who acted on the dashboard. |
| `notes` | `string` | Optional notes the admin entered when approving or denying. |

**Request headers**

| Header | Description |
|--------|-------------|
| `Content-Type` | `application/json` |
| `X-Arden-Timestamp` | Unix timestamp (seconds) when the request was signed. |
| `X-Arden-Signature` | `sha256=<hex>` — HMAC-SHA256 signature of `{timestamp}.{body}`. |

---

### Framework Examples

#### FastAPI

```python
import os
from fastapi import FastAPI, Request, HTTPException
import ardenpy as arden

app = FastAPI()
SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

@app.post("/arden/webhook")
async def arden_webhook(request: Request):
    body = await request.body()
    try:
        arden.handle_webhook(
            body=body,
            headers=dict(request.headers),
            signing_key=SIGNING_KEY,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    return {"ok": True}
```

#### Flask

```python
import os
from flask import Flask, request, abort
import ardenpy as arden

app = Flask(__name__)
SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

@app.post("/arden/webhook")
def arden_webhook():
    try:
        arden.handle_webhook(
            body=request.get_data(),
            headers=dict(request.headers),
            signing_key=SIGNING_KEY,
        )
    except ValueError:
        abort(401)
    return {"ok": True}
```

#### Django

```python
import os
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import ardenpy as arden

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

@method_decorator(csrf_exempt, name="dispatch")
class ArdenWebhookView(View):
    def post(self, request):
        try:
            arden.handle_webhook(
                body=request.body,
                headers=dict(request.headers),
                signing_key=SIGNING_KEY,
            )
        except ValueError:
            return HttpResponse(status=401)
        return JsonResponse({"ok": True})
```

#### Starlette / raw ASGI

```python
import os
from starlette.requests import Request
from starlette.responses import JSONResponse
import ardenpy as arden

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

async def arden_webhook(request: Request):
    body = await request.body()
    try:
        arden.handle_webhook(
            body=body,
            headers=dict(request.headers),
            signing_key=SIGNING_KEY,
        )
    except ValueError:
        return JSONResponse({"error": "Invalid signature"}, status_code=401)
    return JSONResponse({"ok": True})
```

#### Using `verify_webhook_signature` in your own middleware

If you have a framework-level authentication layer that runs before your route handlers:

```python
import os
import time
from ardenpy import verify_webhook_signature

SIGNING_KEY = os.environ["ARDEN_SIGNING_KEY"]

def arden_auth_middleware(body: bytes, headers: dict) -> bool:
    timestamp = headers.get("x-arden-timestamp", "")
    signature = headers.get("x-arden-signature", "")

    # Optional: reject timestamps older than 5 minutes
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except (ValueError, TypeError):
        return False

    return verify_webhook_signature(body, timestamp, signature, SIGNING_KEY)

# In your route handler, after middleware has verified:
# arden.handle_webhook(body=body, headers={}, signing_key=None)
# (pass signing_key=None to skip the second verification)
```

---

## Types and Data Classes

---

### `WebhookEvent`

```python
@dataclass
class WebhookEvent:
    event_type: str
    action_id:  str
    tool_name:  str
    context:    dict[str, Any]
    approved_by: str | None = None
    notes:       str | None = None
    raw:         dict[str, Any] = field(default_factory=dict)
```

Delivered to both `on_approval` and `on_denial` callbacks in `webhook` mode. Contains everything needed to identify the action and re-execute the original function call.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `str` | `"action_approved"` or `"action_denied"`. |
| `action_id` | `str` | UUID identifying this approval request. Matches `PendingApproval.action_id`. |
| `tool_name` | `str` | The `tool_name` string passed to `guard_tool()`. |
| `context` | `dict` | All arguments from the original function call, keyed by parameter name. Use these to re-execute the function. |
| `approved_by` | `str \| None` | The admin user ID who acted on the dashboard. May be `None` if not available. |
| `notes` | `str \| None` | Admin notes entered on the dashboard when approving or denying. May be `None`. |
| `raw` | `dict` | The full, unparsed webhook payload. Use this to access any fields not surfaced above. |

**Example**

```python
def on_approval(event: arden.WebhookEvent):
    print(event.event_type)          # "action_approved"
    print(event.action_id)           # "83acb7a0-1225-4c74-b303-78252d94c6b2"
    print(event.tool_name)           # "stripe.issue_refund"
    print(event.context["amount"])   # 150.0
    print(event.context["customer_id"])  # "cus_abc123"
    print(event.approved_by)         # "user_admin123"
    print(event.notes)               # "Verified with customer"

    # Re-execute the original call using the approved context
    result = issue_refund(
        event.context["amount"],
        event.context["customer_id"],
    )
```

---

### `PendingApproval`

```python
@dataclass
class PendingApproval:
    action_id: str
    tool_name: str
```

Returned by the wrapped function when `approval_mode` is `"async"` or `"webhook"` and the policy decision is `requires_approval`. Signals that the call has been queued for human review.

**Fields**

| Field | Type | Description |
|-------|------|-------------|
| `action_id` | `str` | UUID for this approval request. Use this to correlate log entries, database records, or support tickets with the pending action. |
| `tool_name` | `str` | The tool name passed to `guard_tool()`. |

**Example**

```python
pending = safe_refund(150.0, customer_id="cus_abc")

if isinstance(pending, arden.PendingApproval):
    db.save_pending_action(
        action_id=pending.action_id,
        tool=pending.tool_name,
        user_id=current_user.id,
    )
    return {"status": "pending_approval", "action_id": pending.action_id}
```

---

### `PolicyDecision`

```python
class PolicyDecision(str, Enum):
    ALLOW            = "allow"
    REQUIRE_APPROVAL = "requires_approval"
    BLOCK            = "block"
```

Enum representing the three possible outcomes of a policy evaluation. You do not need to import or use this directly — it is used internally by `guard_tool()`. It is exported for use in type annotations or advanced `ArdenClient` usage.

---

### `ActionStatus`

```python
class ActionStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    DENIED   = "denied"
```

Enum representing the lifecycle state of an approval action. Used in `ActionStatusResponse` returned by `ArdenClient.get_action_status()`. Exported for advanced usage.

---

## Exceptions

All exceptions inherit from `ArdenError`, which itself inherits from `Exception`.

---

### `ArdenError`

```python
class ArdenError(Exception):
    ...
```

Base class for all Arden SDK exceptions. Catch this to handle any Arden-related error in one place.

**Raised when:**
- `configure()` has not been called before `guard_tool()`.
- The Arden API returned an unexpected response.
- The webhook payload could not be parsed.
- An unknown `approval_mode` was passed.
- Required callback parameters were omitted.

---

### `PolicyDeniedError`

```python
class PolicyDeniedError(ArdenError):
    tool_name: str
```

Raised when a tool call is blocked, either automatically by policy (`block` decision) or because a human denied it on the dashboard (`wait` mode).

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `tool_name` | `str` | The `tool_name` that was blocked. |

**When raised:**
- Policy decision is `block` (any mode).
- Human clicked Deny on the dashboard and `approval_mode="wait"`.

**Not raised** in `async` or `webhook` modes on denial — instead, the `on_denial` callback is called.

**Example**

```python
try:
    result = safe_refund(150.0, customer_id="cus_abc")
except arden.PolicyDeniedError as e:
    print(f"Blocked: {e}")
    print(f"Tool: {e.tool_name}")   # "stripe.issue_refund"
```

---

### `ApprovalTimeoutError`

```python
class ApprovalTimeoutError(ArdenError):
    action_id: str
    timeout: float
```

Raised in `wait` mode when no human decision is received within `max_poll_time` seconds.

**Attributes**

| Attribute | Type | Description |
|-----------|------|-------------|
| `action_id` | `str` | The ID of the approval request that timed out. Save this to correlate with dashboard activity. |
| `timeout` | `float` | The `max_poll_time` value that was exceeded, in seconds. |

**Example**

```python
try:
    result = safe_refund(150.0, customer_id="cus_abc")
except arden.ApprovalTimeoutError as e:
    print(f"No decision after {e.timeout}s")
    print(f"Action ID: {e.action_id}")
    # Optionally notify the team that an approval is still pending
    alert_team(f"Approval {e.action_id} has not been reviewed")
```

---

### `ConfigurationError`

```python
class ConfigurationError(ArdenError):
    ...
```

Raised when `get_config()` is called before `configure()`, or when the SDK is used in a context where configuration is required but absent.

---

## Error Handling Patterns

**Pattern 1: Handle all decisions at the call site (wait mode)**

```python
def process_customer_request(amount: float, customer_id: str):
    try:
        result = safe_refund(amount, customer_id=customer_id)
        return {"ok": True, "refund": result}

    except arden.PolicyDeniedError:
        return {"ok": False, "reason": "refund_not_allowed"}

    except arden.ApprovalTimeoutError as e:
        return {"ok": False, "reason": "approval_timeout", "action_id": e.action_id}

    except arden.ArdenError as e:
        logger.error(f"Arden API error: {e}")
        return {"ok": False, "reason": "policy_check_failed"}
```

**Pattern 2: Deferred handling (async/webhook mode)**

```python
# Tool is wrapped once at startup
safe_refund = arden.guard_tool(
    "stripe.issue_refund",
    issue_refund,
    approval_mode="webhook",
    on_approval=handle_refund_approved,
    on_denial=handle_refund_denied,
)

# At call time, only check for immediate blocks
def process_customer_request(amount: float, customer_id: str):
    try:
        result = safe_refund(amount, customer_id=customer_id)
    except arden.PolicyDeniedError:
        # Immediate block (policy said "block", no human involved)
        return {"ok": False, "reason": "refund_not_allowed"}
    except arden.ArdenError as e:
        logger.error(f"Arden API error: {e}")
        return {"ok": False, "reason": "policy_check_failed"}

    if isinstance(result, arden.PendingApproval):
        return {"ok": True, "status": "pending", "action_id": result.action_id}

    return {"ok": True, "refund": result}

# Approval/denial handled separately when webhook arrives
def handle_refund_approved(event: arden.WebhookEvent):
    result = issue_refund(event.context["amount"], event.context["customer_id"])
    db.update_refund_status(event.action_id, "completed", result)

def handle_refund_denied(event: arden.WebhookEvent):
    db.update_refund_status(event.action_id, "denied", {"notes": event.notes})
```

**Pattern 3: Fail open vs. fail closed**

By default, if the Arden API is unreachable, `ArdenError` is raised and the function does not execute. This is **fail closed** — the safest default for sensitive operations.

If you need fail-open behavior (execute the function even if the policy check fails), wrap explicitly:

```python
def safe_refund_fail_open(amount, customer_id):
    try:
        return safe_refund(amount, customer_id=customer_id)
    except arden.ArdenError:
        logger.warning("Arden unreachable — executing without policy check")
        return issue_refund(amount, customer_id)
```

Only do this for non-sensitive operations where availability matters more than enforcement.

---

## Policy Configuration

Policies are configured in the [Arden dashboard](https://app.arden.sh) per agent. Each policy targets a specific `tool_name` (or a wildcard pattern) and defines one of three effects:

| Effect | SDK behavior |
|--------|-------------|
| `allow` | Function executes immediately |
| `block` | `PolicyDeniedError` is raised, function never executes |
| `requires_approval` | Handled per `approval_mode` |

**Hybrid policies** combine rule-based conditions with a fallback effect. Rules are evaluated in order; the first matching rule's effect applies. If no rule matches, the policy's default effect applies.

Example rule in the dashboard:

```
Tool: stripe.issue_refund
If: amount <= 50   → allow
If: amount > 50    → requires_approval
Default:             block
```

With this policy:
- `safe_refund(25.0, ...)` → executes immediately
- `safe_refund(150.0, ...)` → goes to approval queue
- Any call without an `amount` argument → blocked

Rules can reference any named argument from the function call by the parameter name used in the function signature.

---

## Environments

Arden has two isolated environments. Each has its own API endpoint, API keys, agents, policies, and actions.

| Environment | API URL | Key prefix |
|-------------|---------|------------|
| Test | `https://api-test.arden.sh` | `arden_test_` |
| Live | `https://api.arden.sh` | `arden_live_` |

The environment is auto-detected from the API key prefix. Test keys never affect live data and vice versa.

**Recommended setup**

```python
import os
import ardenpy as arden

# Use test environment in development, live in production.
# The key prefix determines the environment automatically.
arden.configure(api_key=os.environ["ARDEN_API_KEY"])
```

Set `ARDEN_API_KEY=arden_test_...` in development and `ARDEN_API_KEY=arden_live_...` in production. No code changes needed.

---

## Logging

The SDK uses Python's standard `logging` module under the `ardenpy` logger namespace.

| Logger name | What it logs |
|-------------|-------------|
| `ardenpy` | Root logger — all SDK messages |
| `ardenpy.guard` | Policy decisions, approval status, webhook dispatch |
| `ardenpy.client` | HTTP requests and retries |

**Enable debug logging**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or configure just the Arden logger:

```python
import logging
logging.getLogger("ardenpy").setLevel(logging.DEBUG)
```

**Log levels used**

| Level | Examples |
|-------|---------|
| `DEBUG` | Policy check started, decision received |
| `INFO` | Tool approved and executing, webhook callback dispatched |
| `WARNING` | Signature verification skipped, unknown action_id in handle_webhook |
| `ERROR` | Callback raised an exception, polling error in async mode |

---

## Framework Integrations

### How it works

Pass all your tools through Arden — you don't need to decide upfront which ones are sensitive. Tools with a policy configured in the dashboard are enforced (allow / block / require approval). Tools with no policy pass through automatically and are logged with `reason: no_policy_configured`, giving you full visibility from day one.

### What to use

| Situation | How |
|-----------|-----|
| LangChain agent | Just `configure()` — auto-patched at startup |
| CrewAI agent | Just `configure()` — auto-patched at startup |
| OpenAI Chat Completions loop | `ArdenToolExecutor` |
| OpenAI Agents SDK | `protect_function_tools()` |
| Custom / no framework | `guard_tool()` |

Install optional framework dependencies as needed:

```bash
pip install "ardenpy[langchain]"      # LangChain
pip install "ardenpy[crewai]"         # CrewAI
pip install "ardenpy[openai-agents]"  # OpenAI Agents SDK
pip install "ardenpy[all]"            # everything
```

---

### LangChain and CrewAI — auto-patched

`configure()` patches `BaseTool.run` on LangChain and CrewAI's base class at startup. Every tool instance in the process — including ones created after `configure()` returns — has its calls intercepted automatically. No explicit wrapping is needed.

```python
import ardenpy as arden

arden.configure(api_key="arden_live_...")
# All LangChain / CrewAI tool calls are now intercepted.

# LangChain — use normally
agent = create_react_agent(llm, tools, prompt)

# CrewAI — use normally
agent = Agent(role="Support Agent", tools=[RefundTool(), EmailTool()], ...)
```

Tool names in the dashboard match each tool's `.name` attribute directly (e.g. `"issue_refund"`). The API key already identifies which agent is making the call, so no prefix is needed.

---

### `protect_tools()` — explicit override (optional)

For cases where you need a specific `approval_mode`, per-call `on_approval`/`on_denial` callbacks, or a different prefix for a subset of tools, use `protect_tools()` explicitly. Tools wrapped with `protect_tools()` are marked internally so the auto-patch skips them — no double-checking.

**LangChain**

```python
from ardenpy.integrations.langchain import protect_tools

safe_tools = protect_tools(
    raw_tools,
    approval_mode="webhook",
    on_approval=my_approval_handler,
    on_denial=my_denial_handler,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tools` | `list` | required | LangChain tool instances |
| `approval_mode` | `str` | `"wait"` | `"wait"`, `"async"`, or `"webhook"` |
| `on_approval` | callable | `None` | Required for `async`/`webhook` modes |
| `on_denial` | callable | `None` | Required for `async`/`webhook` modes |

**CrewAI**

```python
from ardenpy.integrations.crewai import protect_tools

safe_tools = protect_tools(
    [RefundTool(), EmailTool()],
    approval_mode="async",
    on_approval=handle_approval,
    on_denial=handle_denial,
)
```

Same parameter signature as LangChain.

---

### `ArdenCallbackHandler` (LangChain observability)

Logs every tool call to Arden without blocking execution. Attach to `AgentExecutor` for full visibility without enforcement — useful alongside auto-patching when you want to capture non-tool events too.

```python
from ardenpy.integrations.langchain import ArdenCallbackHandler
from langchain.agents import AgentExecutor

executor = AgentExecutor(agent=agent, tools=tools, callbacks=[ArdenCallbackHandler()])
```

---

### OpenAI Chat Completions — `ArdenToolExecutor`

**`ArdenToolExecutor(approval_mode="wait", on_approval=None, on_denial=None)`**

Dispatch table for the OpenAI Chat Completions tool-call loop. Register all functions once; Arden checks policy on each `run()` call.

```python
from ardenpy.integrations.openai import ArdenToolExecutor

executor = ArdenToolExecutor()
executor.register("issue_refund", issue_refund)
executor.register("send_email",   send_email)

# In your tool-call dispatch loop:
result = executor.run(tc.function.name, json.loads(tc.function.arguments))
```

**`executor.register(name, func, arden_name=None)`** — Register a function. `arden_name` overrides the tool name used for policy lookup if you need a custom name.

**`executor.run(name, arguments)`** — Execute a registered tool. Raises `PolicyDeniedError` if blocked. Raises `KeyError` if `name` was not registered.

---

### OpenAI Agents SDK — `protect_function_tools()`

**`protect_function_tools(tools, approval_mode="wait", on_approval=None, on_denial=None)`**

Wraps the underlying callable on `FunctionTool` objects (created with `@function_tool`). Returns the same list.

```python
from agents import function_tool
from ardenpy.integrations.openai import protect_function_tools

@function_tool
def delete_user(user_id: str) -> str: ...

safe_tools = protect_function_tools([delete_user])
agent = Agent(name="AdminBot", tools=safe_tools)
```

---

## Session Tracking

Attach a session ID to group all tool calls from a single conversation in the action log. Useful for debugging, auditing, and session replay on the dashboard.

```python
import ardenpy as arden
import uuid

arden.configure(api_key="arden_live_...")

# Set once per request / conversation turn
arden.set_session(str(uuid.uuid4()))

# Every guard_tool and auto-patched call in this context now carries the session ID.
# Call clear_session() when done (optional — cleaned up automatically at task end).
arden.clear_session()
```

Implemented with `contextvars.ContextVar` — safe for concurrent async requests with no locking needed. Session tracking is completely optional; existing code is unaffected when `set_session()` is never called.

| Function | Description |
|----------|-------------|
| `arden.set_session(session_id: str)` | Attach a session ID to the current async task or thread |
| `arden.get_session() -> str \| None` | Read the current session ID |
| `arden.clear_session()` | Remove the session ID from the current context |

---

*For the dashboard, API key management, and policy configuration, see [app.arden.sh](https://app.arden.sh). For support, contact [team@arden.sh](mailto:team@arden.sh).*
