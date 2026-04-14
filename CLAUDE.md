# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Ardenpy is a Python SDK that sits between AI agents and their tools, enforcing policies (allow/block/require-human-approval) on tool calls. It communicates with the hosted Arden backend at `https://api.arden.sh` (live) or `https://api-test.arden.sh` (test).

## Commands

### Install dependencies
```bash
pip install -e ".[dev]"
# or
pip install httpx pydantic typing-extensions
```

### Run all tests
```bash
pytest tests/
```

### Run a single test file
```bash
pytest tests/test_basic.py
pytest tests/test_webhook.py
```

### Run a single test
```bash
pytest tests/test_webhook.py::TestHandleWebhookDispatch::test_on_approval_called_with_correct_event
```

### Skip integration tests (default — no AWS credentials required)
```bash
pytest tests/ -m "not integration"
```

### Run integration tests (requires AWS credentials with `arden-dev` profile)
```bash
pytest tests/test_webhook.py -m integration -s
```

### Build package for PyPI
```bash
python -m build
twine check dist/*
```

### Local development without pip install
```bash
# Start mock backend (requires fastapi + uvicorn)
python mock_backend.py

# Then point the SDK at localhost
arden.configure(api_key="test_local_key", api_url="http://localhost:8000")
```

## Architecture

### Core flow

`guard_tool(tool_name, func)` returns a wrapper. When the wrapper is called:
1. `ArdenClient.check_tool_call()` POSTs to `/policy/check` — gets back `allow`, `block`, or `requires_approval`
2. **allow** → call the real function, return its result
3. **block** → raise `PolicyDeniedError` immediately
4. **requires_approval** → three approval modes (see below)

### Approval modes

| Mode | Behavior |
|------|----------|
| `wait` (default) | Blocks the calling thread, polls `/status/{action_id}` until approved/denied/timeout |
| `async` | Spawns a daemon thread to poll; calls `on_approval(result)` or `on_denial(error)` when done |
| `webhook` | Returns `PendingApproval` immediately; registers callbacks in `_webhook_callbacks` dict; `handle_webhook()` dispatches when the backend POSTs |

### Module layout

- **`ardenpy/config.py`** — `ArdenConfig` (pydantic model), global `_config`, `configure()`, `configure_test()`, `configure_live()`. API key is read from `ARDEN_API_KEY` env var if not passed directly. Key prefix (`arden_test_` / `arden_live_`) auto-selects the environment.
- **`ardenpy/client.py`** — `ArdenClient` wraps `httpx.Client`. Endpoints: `POST /policy/check`, `GET /status/{id}`. Retries on transient HTTP errors.
- **`ardenpy/guard.py`** — `guard_tool()`, `handle_webhook()`, `verify_webhook_signature()`, `_webhook_callbacks` registry, `GuardContext`/`with_guard` context manager/decorator.
- **`ardenpy/types.py`** — Pydantic models (`ToolCallRequest`, `ToolCallResponse`, `ActionStatusResponse`, `WebhookEvent`, `PendingApproval`) and exceptions (`ArdenError`, `PolicyDeniedError`, `ApprovalTimeoutError`, `ConfigurationError`).

### Webhook signature

`HMAC-SHA256(signing_key, f"{timestamp}.{raw_body}")` sent as `X-Arden-Signature: sha256=<hex>` + `X-Arden-Timestamp`. The signing key is per-webhook, not part of `configure()` — pass it directly to `handle_webhook(signing_key=...)` or `verify_webhook_signature(...)`.

### Key design decisions

- `_webhook_callbacks` is a module-level dict keyed by `action_id`. Entries are popped on first dispatch (one-shot). A missing key logs a warning and returns rather than raising, so a server restart between tool call and webhook delivery doesn't cause a 500.
- In `async` mode, `on_approval` receives the **function's return value**, not a `WebhookEvent`. In `webhook` mode, both callbacks receive a `WebhookEvent` with `event.context` containing all original args — the user must re-execute the function themselves.
- `_make_serializable` in `guard.py` uses `bound_args.arguments` (not just kwargs) so positional args are sent by parameter name for policy evaluation.

## Testing Notes

`tests/test_basic.py` uses `unittest` and resets `ardenpy.config._config = None` in `setUp`/`tearDown`. `tests/test_webhook.py` uses `pytest`. Integration tests in `TestWebhookEndToEnd` invoke a real AWS Lambda (`Arden-admin-ManageAction-admin`) and require `boto3` + AWS credentials.
