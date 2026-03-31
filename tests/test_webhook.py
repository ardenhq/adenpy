"""
End-to-end webhook mode tests.

Unit tests run offline and verify handle_webhook dispatch logic.
The integration test (marked with @pytest.mark.integration) hits the real
Arden backend, approves an action via direct Lambda invocation, constructs
the exact payload the backend sends, and calls handle_webhook() — proving
the full loop without needing a public HTTP server.
"""

import hashlib
import hmac
import json
import time
import pytest

import ardenpy as arden
from ardenpy.types import WebhookEvent, PendingApproval, PolicyDeniedError


LIVE_API_KEY = "arden_live_3e6159f645814adfa86b01f8c368d503"
SIGNING_KEY = "test-signing-key-for-149"  # matches what we set in DynamoDB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_webhook_payload(action_id: str, event_type: str = "action_approved",
                           tool_name: str = "stripe.issue_refund",
                           context: dict | None = None,
                           notes: str = "Looks good") -> dict:
    return {
        "event_type": event_type,
        "timestamp": "2026-03-31T00:00:00+00:00",
        "action": {
            "action_id": action_id,
            "tool_name": tool_name,
            "status": "approved" if event_type == "action_approved" else "denied",
            "agent_id": "live_agent_149ab453869b4792",
            "context": context or {"amount": 150.0, "customer_id": "cus_test123"},
        },
        "approval": {
            "action": "approve" if event_type == "action_approved" else "deny",
            "admin_user_id": "user_3A3fCRxa6G5pX29t5VHfpIsp0rh",
            "notes": notes,
        },
    }


def _sign_payload(body: bytes, signing_key: str) -> dict:
    timestamp = str(int(time.time()))
    sig_payload = f"{timestamp}.{body.decode()}"
    signature = "sha256=" + hmac.new(
        signing_key.encode(),
        sig_payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return {"x-arden-timestamp": timestamp, "x-arden-signature": signature}


# ---------------------------------------------------------------------------
# Unit tests — no network calls
# ---------------------------------------------------------------------------

class TestHandleWebhookDispatch:

    def setup_method(self):
        arden.configure(api_key=LIVE_API_KEY, signing_key=SIGNING_KEY)
        # Clear any leftover callbacks from previous tests
        from ardenpy.guard import _webhook_callbacks
        _webhook_callbacks.clear()

    def _call_handle_webhook(self, payload: dict):
        body = json.dumps(payload, separators=(",", ":")).encode()
        headers = _sign_payload(body, SIGNING_KEY)
        arden.handle_webhook(body, headers)

    def test_on_approval_called_with_correct_event(self):
        received = {}

        def on_approval(event: WebhookEvent):
            received["event"] = event

        def on_denial(event: WebhookEvent):
            pytest.fail("on_denial should not be called")

        # Manually register callbacks (simulates guard_tool having fired)
        from ardenpy.guard import _register_webhook_callbacks
        _register_webhook_callbacks("action-001", "stripe.issue_refund", on_approval, on_denial)

        self._call_handle_webhook(_make_webhook_payload("action-001"))

        event = received["event"]
        assert event.event_type == "action_approved"
        assert event.action_id == "action-001"
        assert event.tool_name == "stripe.issue_refund"
        assert event.context["amount"] == 150.0
        assert event.context["customer_id"] == "cus_test123"
        assert event.approved_by == "user_3A3fCRxa6G5pX29t5VHfpIsp0rh"
        assert event.notes == "Looks good"

    def test_on_denial_called_for_denied_event(self):
        received = {}

        def on_approval(event):
            pytest.fail("on_approval should not be called")

        def on_denial(event: WebhookEvent):
            received["event"] = event

        from ardenpy.guard import _register_webhook_callbacks
        _register_webhook_callbacks("action-002", "stripe.issue_refund", on_approval, on_denial)

        self._call_handle_webhook(_make_webhook_payload("action-002", event_type="action_denied", notes="Too large"))

        event = received["event"]
        assert event.event_type == "action_denied"
        assert event.notes == "Too large"

    def test_callback_removed_after_dispatch(self):
        """Callbacks are consumed — a second call does not re-fire."""
        call_count = {"n": 0}

        def on_approval(event):
            call_count["n"] += 1

        from ardenpy.guard import _register_webhook_callbacks, _webhook_callbacks
        _register_webhook_callbacks("action-003", "stripe.issue_refund", on_approval, lambda e: None)

        self._call_handle_webhook(_make_webhook_payload("action-003"))
        assert call_count["n"] == 1

        # Second call — callback already removed, should silently do nothing
        self._call_handle_webhook(_make_webhook_payload("action-003"))
        assert call_count["n"] == 1

    def test_signature_verification_rejects_tampered_payload(self):
        body = b'{"event_type":"action_approved","action":{"action_id":"x"}}'
        headers = {"x-arden-timestamp": "9999999999", "x-arden-signature": "sha256=bad"}
        with pytest.raises(ValueError, match="signature verification failed"):
            arden.handle_webhook(body, headers)

    def test_missing_signature_headers_raises(self):
        body = b'{}'
        with pytest.raises(ValueError, match="Missing"):
            arden.handle_webhook(body, {})

    def test_user_can_reexecute_from_event_context(self):
        """Simulate the customer-support agent pattern: approve → re-execute."""
        refund_calls = []

        def issue_refund(amount, customer_id):
            refund_calls.append({"amount": amount, "customer_id": customer_id})
            return {"refund_id": "re_123", "amount": amount}

        def on_approval(event: WebhookEvent):
            # The user does exactly this: read args from event.context, call their function
            result = issue_refund(
                event.context["amount"],
                event.context["customer_id"],
            )
            assert result["refund_id"] == "re_123"

        from ardenpy.guard import _register_webhook_callbacks
        _register_webhook_callbacks("action-004", "stripe.issue_refund", on_approval, lambda e: None)

        self._call_handle_webhook(_make_webhook_payload(
            "action-004",
            context={"amount": 150.0, "customer_id": "cus_abc"},
        ))

        assert len(refund_calls) == 1
        assert refund_calls[0] == {"amount": 150.0, "customer_id": "cus_abc"}


class TestVerifyWebhookSignature:
    """verify_webhook_signature is a standalone helper — no configure() needed."""

    def _make_valid(self, body: bytes, key: str):
        timestamp = str(int(time.time()))
        sig_payload = f"{timestamp}.{body.decode()}"
        sig = "sha256=" + hmac.new(key.encode(), sig_payload.encode(), hashlib.sha256).hexdigest()
        return timestamp, sig

    def test_returns_true_for_valid_signature(self):
        body = b'{"event_type":"action_approved"}'
        ts, sig = self._make_valid(body, "mykey")
        assert arden.verify_webhook_signature(body, ts, sig, "mykey") is True

    def test_returns_false_for_wrong_key(self):
        body = b'{"event_type":"action_approved"}'
        ts, sig = self._make_valid(body, "rightkey")
        assert arden.verify_webhook_signature(body, ts, sig, "wrongkey") is False

    def test_returns_false_for_tampered_body(self):
        body = b'{"event_type":"action_approved"}'
        ts, sig = self._make_valid(body, "mykey")
        assert arden.verify_webhook_signature(b'{"tampered":true}', ts, sig, "mykey") is False

    def test_returns_false_for_bad_signature_format(self):
        body = b'{}'
        ts, _ = self._make_valid(body, "mykey")
        assert arden.verify_webhook_signature(body, ts, "sha256=bad", "mykey") is False

    def test_usable_without_configure(self):
        """Can be called with no global config — useful in standalone middleware."""
        body = b'{"x": 1}'
        ts, sig = self._make_valid(body, "standalone_key")
        # No arden.configure() call — should not raise
        result = arden.verify_webhook_signature(body, ts, sig, "standalone_key")
        assert result is True


class TestGuardToolWebhookMode:

    def setup_method(self):
        arden.configure(api_key=LIVE_API_KEY, signing_key=SIGNING_KEY)
        from ardenpy.guard import _webhook_callbacks
        _webhook_callbacks.clear()

    def test_requires_callbacks(self):
        def dummy(): pass
        wrapped = arden.guard_tool("stripe.issue_refund", dummy, approval_mode="webhook")
        with pytest.raises(arden.ArdenError, match="on_approval and on_denial"):
            wrapped()

    def test_webhook_url_no_longer_required(self):
        """webhook_url is now optional — callbacks are what matter."""
        def dummy(): pass
        # Should not raise just from missing webhook_url
        wrapped = arden.guard_tool(
            "stripe.issue_refund", dummy,
            approval_mode="webhook",
            on_approval=lambda e: None,
            on_denial=lambda e: None,
        )
        assert callable(wrapped)


# ---------------------------------------------------------------------------
# Integration test — hits the real Arden backend
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestWebhookEndToEnd:
    """
    Requires AWS credentials with access to arden-dev profile.
    Run with:  pytest tests/test_webhook.py -m integration -s
    """

    def setup_method(self):
        arden.configure(api_key=LIVE_API_KEY, signing_key=SIGNING_KEY)
        from ardenpy.guard import _webhook_callbacks
        _webhook_callbacks.clear()

    def test_full_loop_approve(self):
        import boto3
        import subprocess

        refund_calls = []

        def issue_refund(amount, customer_id="unknown"):
            refund_calls.append({"amount": amount, "customer_id": customer_id})
            return f"refund:{amount}"

        received_events = []

        def on_approval(event: WebhookEvent):
            received_events.append(event)
            # Re-execute using approved context — this is the intended pattern
            issue_refund(event.context["amount"], event.context.get("customer_id", "unknown"))

        def on_denial(event: WebhookEvent):
            pytest.fail(f"Unexpected denial: {event.notes}")

        safe_refund = arden.guard_tool(
            "stripe.issue_refund",
            issue_refund,
            approval_mode="webhook",
            on_approval=on_approval,
            on_denial=on_denial,
        )

        # 1. Call the guarded function — should return PendingApproval
        result = safe_refund(amount=150.0, customer_id="cus_e2e_test")
        assert isinstance(result, PendingApproval)
        assert result.tool_name == "stripe.issue_refund"
        action_id = result.action_id
        print(f"\nAction created: {action_id}")

        # 2. Approve via Lambda invoke (simulates admin clicking Approve on dashboard)
        lambda_client = boto3.client("lambda", region_name="us-east-1")
        approve_payload = {
            "pathParameters": {"action_id": action_id},
            "body": json.dumps({
                "action": "approve",
                "admin_user_id": "user_3A3fCRxa6G5pX29t5VHfpIsp0rh",
                "admin_notes": "E2E webhook test — approved",
            }),
        }
        response = lambda_client.invoke(
            FunctionName="Arden-admin-ManageAction-admin",
            Payload=json.dumps(approve_payload).encode(),
        )
        approve_result = json.loads(response["Payload"].read())
        approve_body = json.loads(approve_result["body"])
        assert approve_body["new_status"] == "approved", approve_body
        print(f"Approved via Lambda: {approve_body['new_status']}")

        # 3. Construct the exact webhook payload the backend would POST
        #    (using the updated_record from the approval response)
        updated_record = approve_body["updated_record"]
        webhook_payload = {
            "event_type": "action_approved",
            "timestamp": updated_record.get("approved_at", ""),
            "action": {
                "action_id": action_id,
                "tool_name": updated_record.get("tool_name"),
                "status": "approved",
                "agent_id": updated_record.get("agent_id"),
                "context": updated_record.get("context", {}),
            },
            "approval": {
                "action": "approve",
                "admin_user_id": updated_record.get("approved_by"),
                "notes": approve_payload["body"] and json.loads(approve_payload["body"]).get("admin_notes"),
            },
        }

        body = json.dumps(webhook_payload, separators=(",", ":")).encode()
        headers = _sign_payload(body, SIGNING_KEY)

        # 4. Handle the webhook — should call on_approval
        arden.handle_webhook(body, headers)

        # 5. Verify
        assert len(received_events) == 1
        event = received_events[0]
        assert event.action_id == action_id
        assert event.context["amount"] == 150.0
        assert event.context["customer_id"] == "cus_e2e_test"

        assert len(refund_calls) == 1  # on_approval re-executed the function
        assert refund_calls[0]["amount"] == 150.0
        print(f"on_approval fired, refund called with: {refund_calls[0]}")

    def test_full_loop_deny(self):
        import boto3

        denial_events = []

        def issue_refund(amount, customer_id="unknown"):
            pytest.fail("issue_refund should not be called after denial")

        def on_approval(event):
            pytest.fail("on_approval should not be called")

        def on_denial(event: WebhookEvent):
            denial_events.append(event)

        safe_refund = arden.guard_tool(
            "stripe.issue_refund",
            issue_refund,
            approval_mode="webhook",
            on_approval=on_approval,
            on_denial=on_denial,
        )

        result = safe_refund(amount=9999.0, customer_id="cus_denied_test")
        assert isinstance(result, PendingApproval)
        action_id = result.action_id
        print(f"\nAction created (to be denied): {action_id}")

        lambda_client = boto3.client("lambda", region_name="us-east-1")
        deny_payload = {
            "pathParameters": {"action_id": action_id},
            "body": json.dumps({
                "action": "deny",
                "admin_user_id": "user_3A3fCRxa6G5pX29t5VHfpIsp0rh",
                "admin_notes": "Amount too large",
            }),
        }
        response = lambda_client.invoke(
            FunctionName="Arden-admin-ManageAction-admin",
            Payload=json.dumps(deny_payload).encode(),
        )
        deny_result = json.loads(response["Payload"].read())
        deny_body = json.loads(deny_result["body"])
        assert deny_body["new_status"] == "denied", deny_body

        updated_record = deny_body["updated_record"]
        webhook_payload = {
            "event_type": "action_denied",
            "timestamp": updated_record.get("denied_at", ""),
            "action": {
                "action_id": action_id,
                "tool_name": updated_record.get("tool_name"),
                "status": "denied",
                "agent_id": updated_record.get("agent_id"),
                "context": updated_record.get("context", {}),
            },
            "approval": {
                "action": "deny",
                "admin_user_id": updated_record.get("denied_by"),
                "notes": "Amount too large",
            },
        }

        body = json.dumps(webhook_payload, separators=(",", ":")).encode()
        headers = _sign_payload(body, SIGNING_KEY)
        arden.handle_webhook(body, headers)

        assert len(denial_events) == 1
        assert denial_events[0].notes == "Amount too large"
        print(f"on_denial fired: {denial_events[0].notes}")
