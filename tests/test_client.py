"""Tests for ArdenClient HTTP methods (mocked httpx)."""

import pytest
from unittest.mock import MagicMock, patch, call
import httpx

import ardenpy.config as _cfg


@pytest.fixture(autouse=True)
def configure_arden():
    _cfg._config = None
    import ardenpy
    ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")
    yield
    _cfg._config = None


def _mock_response(json_data: dict, status_code: int = 200):
    """Return a mock httpx.Response that returns json_data and doesn't raise."""
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    resp.status_code = status_code
    return resp


def _http_status_error(message: str = "400 Bad Request"):
    request = MagicMock(spec=httpx.Request)
    response = MagicMock(spec=httpx.Response)
    return httpx.HTTPStatusError(message, request=request, response=response)


# ---------------------------------------------------------------------------
# _make_request
# ---------------------------------------------------------------------------

class TestMakeRequest:

    def test_success_returns_json(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        with patch.object(client._client, "request", return_value=_mock_response({"ok": True})):
            result = client._make_request("GET", "/test")
        assert result == {"ok": True}

    def test_passes_correct_url_and_headers(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        mock_req = MagicMock(return_value=_mock_response({}))
        with patch.object(client._client, "request", mock_req):
            client._make_request("POST", "/policy/check", data={"x": 1})
        _, kwargs = mock_req.call_args
        assert "https://api-test.arden.sh/policy/check" in mock_req.call_args[1].values() or \
               "https://api-test.arden.sh/policy/check" in mock_req.call_args[0]
        headers = mock_req.call_args[1]["headers"]
        assert headers["X-API-Key"] == "arden_test_key"
        assert headers["Content-Type"] == "application/json"

    def test_http_error_retries_and_raises_arden_error(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        resp = MagicMock(spec=httpx.Response)
        resp.raise_for_status.side_effect = _http_status_error()
        with patch.object(client._client, "request", return_value=resp):
            with patch("time.sleep"):  # don't actually sleep
                with pytest.raises(ArdenError, match="API request failed"):
                    client._make_request("GET", "/test")

    def test_request_error_retries_and_raises_arden_error(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        with patch.object(
            client._client, "request",
            side_effect=httpx.RequestError("connection refused")
        ):
            with patch("time.sleep"):
                with pytest.raises(ArdenError, match="API request failed"):
                    client._make_request("GET", "/test")

    def test_retry_succeeds_on_second_attempt(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        resp_fail = MagicMock(spec=httpx.Response)
        resp_fail.raise_for_status.side_effect = _http_status_error()
        resp_ok = _mock_response({"result": "ok"})
        with patch.object(client._client, "request", side_effect=[resp_fail, resp_ok]):
            with patch("time.sleep"):
                result = client._make_request("GET", "/test")
        assert result == {"result": "ok"}

    def test_params_passed_to_request(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        mock_req = MagicMock(return_value=_mock_response({}))
        with patch.object(client._client, "request", mock_req):
            client._make_request("GET", "/status/abc", params={"foo": "bar"})
        assert mock_req.call_args[1]["params"] == {"foo": "bar"}


# ---------------------------------------------------------------------------
# check_tool_call
# ---------------------------------------------------------------------------

class TestCheckToolCall:

    def test_returns_tool_call_response_on_success(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import PolicyDecision
        client = ArdenClient()
        json_data = {"decision": "allow", "action_id": "act_123", "message": None, "reason": None}
        with patch.object(client, "_make_request", return_value=json_data):
            resp = client.check_tool_call("stripe.refund", [], {"amount": 50})
        assert resp.decision == PolicyDecision.ALLOW
        assert resp.action_id == "act_123"

    def test_raises_arden_error_when_request_fails(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        with patch.object(client, "_make_request", side_effect=ArdenError("timeout")):
            with pytest.raises(ArdenError, match="Policy check failed"):
                client.check_tool_call("stripe.refund", [], {})

    def test_sends_tool_name_in_payload(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        json_data = {"decision": "allow", "action_id": None, "message": None, "reason": None}
        mock_req = MagicMock(return_value=json_data)
        with patch.object(client, "_make_request", mock_req):
            client.check_tool_call("my.tool", [1], {"key": "val"}, metadata={"session_id": "s1"})
        _, kwargs = mock_req.call_args
        payload = kwargs["data"]
        assert payload["tool_name"] == "my.tool"
        assert payload["kwargs"] == {"key": "val"}


# ---------------------------------------------------------------------------
# get_action_status
# ---------------------------------------------------------------------------

class TestGetActionStatus:

    def test_returns_action_status_response(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus
        client = ArdenClient()
        json_data = {"action_id": "act_1", "status": "pending", "message": None, "created_at": "2026-01-01T00:00:00Z"}
        with patch.object(client, "_make_request", return_value=json_data):
            resp = client.get_action_status("act_1")
        assert resp.action_id == "act_1"
        assert resp.status == ActionStatus.PENDING

    def test_raises_arden_error_on_failure(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        with patch.object(client, "_make_request", side_effect=ArdenError("not found")):
            with pytest.raises(ArdenError, match="Status check failed"):
                client.get_action_status("act_missing")

    def test_calls_correct_endpoint(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        json_data = {"action_id": "act_2", "status": "approved", "message": None, "created_at": "2026-01-01T00:00:00Z"}
        mock_req = MagicMock(return_value=json_data)
        with patch.object(client, "_make_request", mock_req):
            client.get_action_status("act_2")
        assert mock_req.call_args[1]["endpoint"] == "/status/act_2"


# ---------------------------------------------------------------------------
# wait_for_approval
# ---------------------------------------------------------------------------

class TestWaitForApproval:

    def test_returns_immediately_when_approved(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus
        client = ArdenClient()
        approved = MagicMock()
        approved.status = ActionStatus.APPROVED
        with patch.object(client, "get_action_status", return_value=approved):
            result = client.wait_for_approval("act_1", timeout=10)
        assert result.status == ActionStatus.APPROVED

    def test_returns_when_denied(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus
        client = ArdenClient()
        denied = MagicMock()
        denied.status = ActionStatus.DENIED
        with patch.object(client, "get_action_status", return_value=denied):
            result = client.wait_for_approval("act_2", timeout=10)
        assert result.status == ActionStatus.DENIED

    def test_polls_until_approved(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus
        client = ArdenClient()
        pending = MagicMock(); pending.status = ActionStatus.PENDING
        approved = MagicMock(); approved.status = ActionStatus.APPROVED
        with patch.object(client, "get_action_status", side_effect=[pending, pending, approved]):
            with patch("time.sleep"):
                result = client.wait_for_approval("act_3", timeout=30)
        assert result.status == ActionStatus.APPROVED

    def test_raises_timeout_error_when_exceeded(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus, ApprovalTimeoutError
        client = ArdenClient()
        pending = MagicMock(); pending.status = ActionStatus.PENDING
        # timeout=0 means the while condition is False immediately, so we reach raise
        with patch.object(client, "get_action_status", return_value=pending):
            with patch("time.sleep"):
                with pytest.raises(ApprovalTimeoutError):
                    client.wait_for_approval("act_4", timeout=0)

    def test_uses_config_timeout_when_none_given(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus
        client = ArdenClient()
        approved = MagicMock(); approved.status = ActionStatus.APPROVED
        # Just verify it doesn't explode when timeout=None
        with patch.object(client, "get_action_status", return_value=approved):
            result = client.wait_for_approval("act_5")
        assert result.status == ActionStatus.APPROVED

    def test_continues_after_status_check_error(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ActionStatus, ArdenError
        client = ArdenClient()
        approved = MagicMock(); approved.status = ActionStatus.APPROVED
        with patch.object(
            client, "get_action_status",
            side_effect=[ArdenError("transient"), approved]
        ):
            with patch("time.sleep"):
                result = client.wait_for_approval("act_6", timeout=30)
        assert result.status == ActionStatus.APPROVED


# ---------------------------------------------------------------------------
# approve_action / deny_action
# ---------------------------------------------------------------------------

class TestApproveAndDenyAction:

    def test_approve_returns_true(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        with patch.object(client, "_make_request", return_value={"ok": True}):
            assert client.approve_action("act_1") is True

    def test_approve_raises_arden_error_on_failure(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        with patch.object(client, "_make_request", side_effect=Exception("boom")):
            with pytest.raises(ArdenError, match="Approval failed"):
                client.approve_action("act_1")

    def test_deny_returns_true(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        with patch.object(client, "_make_request", return_value={"ok": True}):
            assert client.deny_action("act_2") is True

    def test_deny_raises_arden_error_on_failure(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        with patch.object(client, "_make_request", side_effect=Exception("boom")):
            with pytest.raises(ArdenError, match="Denial failed"):
                client.deny_action("act_2")

    def test_approve_with_message(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        mock_req = MagicMock(return_value={})
        with patch.object(client, "_make_request", mock_req):
            client.approve_action("act_3", message="Looks good")
        assert mock_req.call_args[1]["endpoint"] == "/approve/act_3"

    def test_deny_with_message(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        mock_req = MagicMock(return_value={})
        with patch.object(client, "_make_request", mock_req):
            client.deny_action("act_4", message="Too risky")
        assert mock_req.call_args[1]["endpoint"] == "/deny/act_4"


# ---------------------------------------------------------------------------
# log_token_usage
# ---------------------------------------------------------------------------

class TestLogTokenUsage:

    def test_sends_model_and_token_counts(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        expected = {"usage_id": "u_1", "total_tokens": 150, "total_cost_usd": 0.002}
        mock_req = MagicMock(return_value=expected)
        with patch.object(client, "_make_request", mock_req):
            result = client.log_token_usage("gpt-4o", 100, 50)
        assert result == expected
        payload = mock_req.call_args[1]["data"]
        assert payload["model"] == "gpt-4o"
        assert payload["prompt_tokens"] == 100
        assert payload["completion_tokens"] == 50
        assert "session_id" not in payload

    def test_includes_session_id_when_provided(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        mock_req = MagicMock(return_value={})
        with patch.object(client, "_make_request", mock_req):
            client.log_token_usage("gpt-4o", 10, 5, session_id="sess_abc")
        assert mock_req.call_args[1]["data"]["session_id"] == "sess_abc"

    def test_returns_empty_dict_on_failure(self):
        from ardenpy.client import ArdenClient
        from ardenpy.types import ArdenError
        client = ArdenClient()
        with patch.object(client, "_make_request", side_effect=ArdenError("server error")):
            result = client.log_token_usage("gpt-4o", 10, 5)
        assert result == {}

    def test_posts_to_token_usage_endpoint(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        mock_req = MagicMock(return_value={})
        with patch.object(client, "_make_request", mock_req):
            client.log_token_usage("claude-sonnet-4-6", 200, 100)
        assert mock_req.call_args[1]["endpoint"] == "/token-usage"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestClientContextManager:

    def test_context_manager_calls_close(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        close_called = []
        original_close = client.close
        client.close = lambda: close_called.append(True)
        with client:
            pass
        assert close_called == [True]

    def test_context_manager_returns_client(self):
        from ardenpy.client import ArdenClient
        client = ArdenClient()
        with client as c:
            assert c is client
