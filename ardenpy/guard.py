"""Main guard functionality for wrapping and protecting tool calls."""

import functools
import hashlib
import hmac
import inspect
import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from .client import ArdenClient
from .config import get_config, is_configured
from .types import (
    PolicyDecision,
    PolicyDeniedError,
    ApprovalTimeoutError,
    PendingApproval,
    WebhookEvent,
    ArdenError,
)

F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def guard_tool(
    tool_name: str,
    func: F,
    approval_mode: str = "wait",
    on_approval: Optional[Callable] = None,
    on_denial: Optional[Callable] = None,
    webhook_url: Optional[str] = None,
) -> F:
    """Wrap a function with policy enforcement and approval workflow.
    
    Args:
        tool_name: Name identifier for the tool (used in policy evaluation)
        func: Function to wrap with policy enforcement
        approval_mode: Approval workflow mode:
            - "wait": Block until approval/denial (default)
            - "async": Non-blocking with callbacks
            - "webhook": Use webhook for notifications
        on_approval: Callback for async mode when action is approved
        on_denial: Callback for async mode when action is denied
        webhook_url: Webhook URL for webhook mode
        
    Returns:
        Wrapped function that checks policy before execution
        
    Raises:
        ConfigurationError: If Arden is not configured
        PolicyDeniedError: If policy denies the tool call
        ApprovalTimeoutError: If approval workflow times out (wait mode only)
        ArdenError: For other API communication errors
        
    Examples:
        # Wait mode (default) - blocks until approved
        def send_email(to: str, message: str):
            return f"Email sent to {to}"
        
        safe_email = guard_tool("communication.email", send_email)
        result = safe_email("user@example.com", "Hello")  # Blocks here
        
        # Async mode - non-blocking with callbacks
        def handle_approval(result):
            print(f"Email sent: {result}")
        
        def handle_denial(error):
            print(f"Email blocked: {error}")
        
        safe_email_async = guard_tool(
            "communication.email", 
            send_email,
            approval_mode="async",
            on_approval=handle_approval,
            on_denial=handle_denial
        )
        safe_email_async("user@example.com", "Hello")  # Returns immediately
        
        # Webhook mode — returns PendingApproval immediately; on_approval/on_denial
        # are called when the Arden backend POSTs to your webhook endpoint.
        # The WebhookEvent passed to on_approval contains tool_name + context
        # (all submitted args) so you can re-execute the call yourself.
        def on_approval(event: WebhookEvent):
            result = send_email(event.context["to"], event.context["message"])
            print(f"Email sent after approval: {result}")

        def on_denial(event: WebhookEvent):
            print(f"Email blocked: {event.notes}")

        safe_email_webhook = guard_tool(
            "communication.email",
            send_email,
            approval_mode="webhook",
            on_approval=on_approval,
            on_denial=on_denial,
        )
        pending = safe_email_webhook("user@example.com", "Hello")
        # pending is a PendingApproval(action_id=..., tool_name=...)
        # When the admin approves on the dashboard, your webhook endpoint
        # receives a POST and you call arden.handle_webhook(body, headers).
    """
    if not is_configured():
        raise ArdenError(
            "Arden must be configured before using guard_tool(). "
            "Call configure(api_url=...) first."
        )

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that enforces policy before calling the original function."""
        # Validate callbacks before making any network calls so the error is
        # immediate and clear (no need to wait for a requires_approval response).
        if approval_mode in ("async", "webhook") and (not on_approval or not on_denial):
            raise ArdenError(
                f"approval_mode={approval_mode!r} requires both on_approval and on_denial callbacks"
            )

        # Extract function signature so positional args like issue_refund(50.0)
        # are sent as {"amount": 50.0} and can be evaluated by policy rules.
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        context = _make_serializable(dict(bound_args.arguments))

        return _run_with_policy_check(
            tool_name=tool_name,
            context=context,
            executor=lambda: func(*args, **kwargs),
            approval_mode=approval_mode,
            on_approval=on_approval,
            on_denial=on_denial,
        )

    return cast(F, wrapper)


def _run_with_policy_check(
    tool_name: str,
    context: Dict[str, Any],
    executor: Callable,
    approval_mode: str = "wait",
    on_approval: Optional[Callable] = None,
    on_denial: Optional[Callable] = None,
) -> Any:
    """Core policy-check-and-execute logic shared by guard_tool() and auto-patch.

    Args:
        tool_name: Arden policy name for this tool.
        context: Dict of args to send to the policy engine.
        executor: Zero-argument callable that executes the original tool call.
        approval_mode: ``"wait"``, ``"async"``, or ``"webhook"``.
        on_approval: Callback for async/webhook modes.
        on_denial: Callback for async/webhook modes.
    """
    from .session import get_session
    session_id = get_session()
    metadata = {"session_id": session_id} if session_id else None

    client = ArdenClient()
    try:
        logger.debug(f"Checking policy for tool '{tool_name}'")
        response = client.check_tool_call(
            tool_name=tool_name,
            args=[],
            kwargs=context,
            metadata=metadata,
        )

        if response.decision == PolicyDecision.ALLOW:
            if response.reason == 'no_policy_configured':
                logger.debug(f"Tool '{tool_name}' allowed: no policy configured (action_id: {response.action_id})")
            else:
                logger.debug(f"Policy allows tool '{tool_name}'")
            return executor()

        elif response.decision == PolicyDecision.REQUIRE_APPROVAL:
            if not response.action_id:
                raise ArdenError("Policy requires approval but no action_id provided")

            logger.info(f"Tool '{tool_name}' requires approval, action_id: {response.action_id}")

            if approval_mode == "wait":
                status = client.wait_for_approval(response.action_id)
                if status.status.value == "approved":
                    logger.info(f"Tool '{tool_name}' approved, executing")
                    return executor()
                else:
                    raise PolicyDeniedError(
                        f"Tool call was denied: {status.message or 'No reason provided'}",
                        tool_name=tool_name,
                    )

            elif approval_mode == "async":
                if not on_approval or not on_denial:
                    raise ArdenError("Async mode requires both on_approval and on_denial callbacks")
                _start_async_approval_polling(
                    response.action_id, executor, tool_name, on_approval, on_denial
                )
                return PendingApproval(action_id=response.action_id, tool_name=tool_name)

            elif approval_mode == "webhook":
                if not on_approval or not on_denial:
                    raise ArdenError("Webhook mode requires both on_approval and on_denial callbacks")
                _register_webhook_callbacks(response.action_id, tool_name, on_approval, on_denial)
                return PendingApproval(action_id=response.action_id, tool_name=tool_name)

            else:
                raise ArdenError(f"Unknown approval_mode: {approval_mode!r}. Use 'wait', 'async', or 'webhook'")

        elif response.decision == PolicyDecision.BLOCK:
            raise PolicyDeniedError(
                response.message or f"Tool '{tool_name}' is blocked by policy",
                tool_name=tool_name,
            )

        else:
            raise ArdenError(f"Unknown policy decision: {response.decision}")

    finally:
        client.close()


def _start_async_approval_polling(
    action_id: str,
    executor: Callable,
    tool_name: str,
    on_approval: Callable[[Any], None],
    on_denial: Callable[[Exception], None],
) -> None:
    """Start background thread to poll for approval status."""

    def poll_approval():
        client = ArdenClient()
        try:
            status = client.wait_for_approval(action_id)
            if status.status.value == "approved":
                logger.info(f"Tool '{tool_name}' approved asynchronously, executing")
                try:
                    on_approval(executor())
                except Exception as e:
                    logger.error(f"Error executing approved tool '{tool_name}': {e}")
                    on_denial(e)
            else:
                on_denial(PolicyDeniedError(
                    f"Tool call was denied: {status.message or 'No reason provided'}",
                    tool_name=tool_name,
                ))
        except Exception as e:
            logger.error(f"Error in async approval polling for '{tool_name}': {e}")
            on_denial(e)
        finally:
            client.close()

    threading.Thread(target=poll_approval, daemon=True).start()


# Module-level registry mapping action_id → {on_approval, on_denial, tool_name}
# Keyed by action_id; entries are removed once the callback fires.
_webhook_callbacks: Dict[str, Dict[str, Any]] = {}


def _register_webhook_callbacks(
    action_id: str,
    tool_name: str,
    on_approval: Callable,
    on_denial: Callable,
) -> None:
    """Store callbacks to be invoked when handle_webhook() is called."""
    _webhook_callbacks[action_id] = {
        'tool_name': tool_name,
        'on_approval': on_approval,
        'on_denial': on_denial,
    }
    logger.info(f"Registered webhook callbacks for '{tool_name}', action_id: {action_id}")


def verify_webhook_signature(
    body: bytes,
    timestamp: str,
    signature: str,
    signing_key: str,
) -> bool:
    """Verify an Arden webhook signature.

    Exposed as a standalone function for users who want to integrate signature
    verification into their own middleware rather than using
    :func:`handle_webhook`.

    Arden signs each webhook as::

        HMAC-SHA256(signing_key, f"{timestamp}.{raw_body}")

    and sends the result in the ``X-Arden-Signature: sha256=<hex>`` header
    alongside ``X-Arden-Timestamp``.

    Args:
        body: Raw request body bytes (before any parsing).
        timestamp: Value of the ``X-Arden-Timestamp`` header.
        signature: Value of the ``X-Arden-Signature`` header (e.g. ``sha256=abc123``).
        signing_key: Signing key from the Arden dashboard for this agent.

    Returns:
        ``True`` if the signature is valid.  Always use this return value with
        ``if not verify_webhook_signature(...): raise ...`` rather than
        catching exceptions — the comparison is timing-safe.

    Example::

        # In your own middleware
        from ardenpy import verify_webhook_signature

        timestamp = request.headers["X-Arden-Timestamp"]
        signature = request.headers["X-Arden-Signature"]

        if not verify_webhook_signature(request.body, timestamp, signature, SIGNING_KEY):
            return HttpResponse(status=401)
    """
    sig_payload = f"{timestamp}.{body.decode('utf-8')}"
    expected = 'sha256=' + hmac.new(
        signing_key.encode('utf-8'),
        sig_payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_webhook(
    body: bytes,
    headers: Dict[str, str],
    signing_key: Optional[str] = None,
) -> None:
    """Process an incoming webhook POST from the Arden backend.

    Call this from whatever web framework you use (Flask, FastAPI, Django …)
    when Arden POSTs to your webhook URL.  It verifies the signature, parses
    the event, and dispatches to the ``on_approval`` or ``on_denial`` callback
    that was registered via ``guard_tool(..., approval_mode="webhook")``.

    Signature verification uses :func:`verify_webhook_signature` internally.
    If you need to verify the signature yourself (e.g. in middleware) before
    calling this function, pass ``signing_key=None`` and leave it unconfigured
    to skip the second verification here.

    Args:
        body: Raw request body bytes.
        headers: Request headers dict (case-insensitive lookup is handled internally).
        signing_key: HMAC-SHA256 signing key from the Arden dashboard.  If omitted
            the value from ``configure(signing_key=...)`` is used.  Pass ``None``
            *and* leave it unconfigured to skip verification entirely (only for
            local testing).

    Raises:
        ValueError: If signature headers are present but the signature does not match.
        ArdenError: If the payload cannot be parsed or the action_id is unknown.

    Example (FastAPI)::

        @app.post("/arden/webhook")
        async def arden_webhook(request: Request):
            arden.handle_webhook(
                body=await request.body(),
                headers=dict(request.headers),
            )
            return {"ok": True}
    """
    # Normalise header keys to lowercase for case-insensitive lookup
    normalised = {k.lower(): v for k, v in headers.items()}

    # --- Signature verification ---
    key = signing_key
    if key is None:
        try:
            key = get_config().signing_key
        except Exception:
            key = None

    if key:
        timestamp = normalised.get('x-arden-timestamp', '')
        signature = normalised.get('x-arden-signature', '')
        if not timestamp or not signature:
            raise ValueError("Missing X-Arden-Timestamp or X-Arden-Signature headers")

        if not verify_webhook_signature(body, timestamp, signature, key):
            raise ValueError("Webhook signature verification failed")
    else:
        logger.warning("No signing_key configured — skipping webhook signature verification")

    # --- Parse payload ---
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ArdenError(f"Invalid webhook payload: {exc}") from exc

    event_type = payload.get('event_type')   # "action_approved" or "action_denied"
    action_data = payload.get('action', {})
    approval_data = payload.get('approval', {})
    action_id = action_data.get('action_id')

    if not action_id:
        raise ArdenError("Webhook payload missing action.action_id")

    # --- Build WebhookEvent ---
    event = WebhookEvent(
        event_type=event_type or '',
        action_id=action_id,
        tool_name=action_data.get('tool_name', ''),
        context=action_data.get('context', {}),
        approved_by=approval_data.get('admin_user_id'),
        notes=approval_data.get('notes'),
        raw=payload,
    )

    # --- Dispatch ---
    entry = _webhook_callbacks.pop(action_id, None)
    if entry is None:
        # Could be a replay or a call whose guard_tool wrapper is in a different
        # process.  Log and return rather than raising so the backend gets 200.
        logger.warning(
            f"handle_webhook: no registered callback for action_id={action_id!r}. "
            "This is expected if the process restarted between the tool call and "
            "the webhook delivery."
        )
        return

    if event_type == 'action_approved':
        logger.info(f"Action {action_id} approved — calling on_approval")
        try:
            entry['on_approval'](event)
        except Exception as exc:
            logger.error(f"on_approval callback raised: {exc}")
            raise
    else:
        logger.info(f"Action {action_id} denied — calling on_denial")
        try:
            entry['on_denial'](event)
        except Exception as exc:
            logger.error(f"on_denial callback raised: {exc}")
            raise


def _make_serializable(obj: Any) -> Any:
    """Convert an object to JSON-serializable format.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable version of the object
    """
    if obj is None:
        return None
    
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    
    elif isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    
    elif isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    
    elif hasattr(obj, '__dict__'):
        # Try to serialize objects with __dict__
        try:
            return {
                '_type': type(obj).__name__,
                '_module': type(obj).__module__,
                'data': _make_serializable(obj.__dict__)
            }
        except Exception:
            pass
    
    # Fallback to string representation
    return {
        '_type': type(obj).__name__,
        '_module': type(obj).__module__,
        '_repr': str(obj)
    }


class GuardContext:
    """Context manager for managing Arden configuration and cleanup."""
    
    def __init__(self, api_url: str, **config_kwargs):
        """Initialize guard context.
        
        Args:
            api_url: API URL for Arden backend
            **config_kwargs: Additional configuration options
        """
        self.api_url = api_url
        self.config_kwargs = config_kwargs
        self._was_configured = False
    
    def __enter__(self):
        """Enter context and configure Arden."""
        global _was_configured
        self._was_configured = is_configured()
        
        if not self._was_configured:
            configure(api_url=self.api_url, **self.config_kwargs)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and cleanup if needed."""
        # Note: We don't reset configuration to avoid affecting other code
        pass


def with_guard(api_url: str, **config_kwargs):
    """Decorator to configure Arden for a function or class.
    
    Args:
        api_url: API URL for Arden backend
        **config_kwargs: Additional configuration options
        
    Example:
        @with_guard("https://myapi.com")
        def my_function():
            # Arden is configured here
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with GuardContext(api_url, **config_kwargs):
                return func(*args, **kwargs)
        return cast(F, wrapper)
    return decorator
