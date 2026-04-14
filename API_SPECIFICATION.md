# Arden API Reference

This document describes the REST API calls the ardenpy SDK makes to the Arden backend.
You only need this if you're building a custom backend or debugging SDK behaviour.
For normal SDK usage, see the [README](README.md).

---

## Authentication

Every request includes the API key in the `X-API-Key` header:

```
X-API-Key: arden_live_...
Content-Type: application/json
```

API key formats:
- Live keys: `arden_live_<32 hex chars>` — hits `https://api.arden.sh`
- Test keys: `arden_test_<32 hex chars>` — hits `https://api-test.arden.sh`

The SDK detects the environment from the key prefix and sets the base URL automatically.

---

## Endpoints

### POST /policy/check

Check whether a tool call is allowed. Called by `guard_tool()` before executing the wrapped function.

**Request**

```json
{
  "tool_name": "stripe.issue_refund",
  "args": [],
  "kwargs": { "amount": 150.0, "customer_id": "cus_abc" }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Required. The name passed to `guard_tool()`. |
| `args` | array | Positional arguments (usually empty — all args are bound by name). |
| `kwargs` | object | Named arguments from the function call. |

**Response**

```json
{
  "decision": "allow",
  "action_id": "a1b2c3d4-...",
  "reason": "no_policy_configured",
  "status": "completed",
  "environment": "live",
  "user_id": "user_abc"
}
```

| Field | Description |
|-------|-------------|
| `decision` | `"allow"`, `"block"`, or `"requires_approval"` |
| `action_id` | UUID of the logged action record (present for all decisions) |
| `reason` | `"no_policy_configured"` when the tool passed through because no matching policy exists |
| `status` | `"completed"` or `"pending"` (pending only when `requires_approval`) |
| `environment` | `"live"` or `"test"` |

**SDK behaviour by decision:**

| Decision | What the SDK does |
|----------|------------------|
| `allow` | Executes the original function and returns its result |
| `block` | Raises `PolicyDeniedError` immediately |
| `requires_approval` | Polls `GET /status/{action_id}` (wait/async modes) or registers webhook callbacks (webhook mode) |

---

### GET /status/{action_id}

Poll for approval status. Called by the SDK in `wait` and `async` modes.

**Response**

```json
{
  "action_id": "a1b2c3d4-...",
  "status": "pending",
  "message": null,
  "created_at": "2026-04-14T12:00:00+00:00"
}
```

| `status` value | Meaning |
|----------------|---------|
| `pending` | Waiting for a human to act on the dashboard |
| `approved` | Human approved — SDK executes the function |
| `denied` | Human denied — SDK raises `PolicyDeniedError` |

The SDK polls this endpoint every `poll_interval` seconds (default 2s) up to `max_poll_time` seconds (default 300s), then raises `ApprovalTimeoutError`.

---

## Webhook flow (approval_mode="webhook")

When `approval_mode="webhook"`, the SDK does **not** poll. Instead:

1. SDK calls `POST /policy/check` → receives `requires_approval` + `action_id`
2. SDK returns a `PendingApproval` object to the caller immediately
3. When an admin approves or denies on the dashboard, the Arden backend POSTs to your webhook endpoint
4. Your server calls `arden.handle_webhook(body, headers, signing_key=...)` which dispatches to your `on_approval` or `on_denial` callback

**Webhook POST payload (sent by Arden to your endpoint)**

```json
{
  "event_type": "action_approved",
  "action": {
    "action_id": "a1b2c3d4-...",
    "tool_name": "stripe.issue_refund",
    "agent_id": "agent_xyz",
    "context": { "amount": 150.0, "customer_id": "cus_abc" },
    "created_at": "2026-04-14T12:00:00+00:00",
    "environment": "live"
  },
  "approval": {
    "admin_user_id": "user_admin",
    "notes": "Verified with customer"
  }
}
```

**Webhook headers**

```
X-Arden-Timestamp: 1713096000
X-Arden-Signature: sha256=<hmac_hex>
```

The signature is `HMAC-SHA256(signing_key, "{timestamp}.{raw_body}")`. Verify it with `arden.verify_webhook_signature()` or pass `signing_key` to `arden.handle_webhook()`.

`event_type` is `"action_approved"` or `"action_denied"`.

---

## Error responses

```json
{ "error": "Tool call requires agent-specific API key" }
```

| Status code | Meaning |
|-------------|---------|
| 400 | Malformed request (missing `tool_name`, invalid JSON) |
| 403 | API key valid but missing agent association |
| 500 | Internal server error |

The SDK raises `ArdenError` for 4xx/5xx responses after `retry_attempts` retries (default 3).
