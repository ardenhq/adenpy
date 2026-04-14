"""
Webhook Approval Server with Arden

Shows how to use approval_mode="webhook" with guard_tool() and wire up
handle_webhook() in a Flask server. When a tool call requires approval,
Arden POSTs to your endpoint once an admin acts on the dashboard.

Use this pattern when your process can't block (long-running workers,
async services) and you want push-based delivery instead of polling.

Requirements:
    pip install ardenpy flask

Setup:
    export ARDEN_API_KEY="arden_live_..."
    export ARDEN_SIGNING_KEY="your_webhook_signing_key"   # from dashboard
    python webhook_server.py
"""

import os
from flask import Flask, request, jsonify
import ardenpy as arden

arden.configure(api_key=os.environ["ARDEN_API_KEY"])
SIGNING_KEY = os.environ.get("ARDEN_SIGNING_KEY")

app = Flask(__name__)


# ── Tool implementations ──────────────────────────────────────────────────────

def send_email(to: str, subject: str, body: str) -> str:
    print(f"  [send_email] Sending to {to}: {subject}")
    return f"Email sent to {to}"

def issue_refund(amount: float, customer_id: str) -> str:
    print(f"  [issue_refund] ${amount} → {customer_id}")
    return f"Refund of ${amount} issued"

def delete_account(user_id: str) -> str:
    print(f"  [delete_account] Deleting {user_id}")
    return f"Account {user_id} deleted"


# ── on_approval / on_denial callbacks ────────────────────────────────────────
# These are called by handle_webhook() when an admin acts on the dashboard.
# The WebhookEvent carries tool_name, context (all original args), and notes.

def on_approval(event: arden.WebhookEvent):
    print(f"Approved: {event.tool_name} by {event.approved_by}")
    # Re-execute the call using the original args from event.context
    if event.tool_name == "communication.send_email":
        send_email(**event.context)
    elif event.tool_name == "stripe.issue_refund":
        issue_refund(**event.context)
    elif event.tool_name == "admin.delete_account":
        delete_account(**event.context)

def on_denial(event: arden.WebhookEvent):
    print(f"Denied: {event.tool_name} — {event.notes}")


# ── Protect tools with webhook approval mode ──────────────────────────────────

safe_email   = arden.guard_tool("communication.send_email", send_email,
                                approval_mode="webhook",
                                on_approval=on_approval, on_denial=on_denial)

safe_refund  = arden.guard_tool("stripe.issue_refund", issue_refund,
                                approval_mode="webhook",
                                on_approval=on_approval, on_denial=on_denial)

safe_delete  = arden.guard_tool("admin.delete_account", delete_account,
                                approval_mode="webhook",
                                on_approval=on_approval, on_denial=on_denial)


# ── Webhook endpoint ──────────────────────────────────────────────────────────

@app.post("/arden/webhook")
def arden_webhook():
    """Receive approval/denial notifications from Arden."""
    try:
        arden.handle_webhook(
            body=request.get_data(),
            headers=dict(request.headers),
            signing_key=SIGNING_KEY,  # pass None to skip verification in local testing
        )
        return jsonify({"ok": True})
    except ValueError as e:
        # Signature mismatch
        return jsonify({"error": str(e)}), 401
    except arden.ArdenError as e:
        return jsonify({"error": str(e)}), 400


# ── Demo endpoint — simulates an agent triggering tool calls ──────────────────

@app.post("/demo/refund")
def demo_refund():
    """Trigger a refund — returns immediately; approval happens via webhook."""
    from flask import request as req
    data = req.get_json(force=True)
    pending = safe_refund(data["amount"], data["customer_id"])
    return jsonify({
        "status": "pending_approval",
        "action_id": pending.action_id,
    })


if __name__ == "__main__":
    print("Webhook server running on http://localhost:5000")
    print("Configure your Arden dashboard to POST approvals to:")
    print("  http://<your-host>/arden/webhook")
    print()
    print("Test with:")
    print('  curl -X POST http://localhost:5000/demo/refund \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"amount": 150, "customer_id": "cus_abc"}\'')
    app.run(port=5000, debug=True)
