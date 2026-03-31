"""Main guard functionality for wrapping and protecting tool calls."""

import functools
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast
import inspect

from .client import ArdenClient
from .config import get_config, is_configured
from .types import (
    PolicyDecision,
    PolicyDeniedError,
    ApprovalTimeoutError,
    ArdenError,
)

F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def guard_tool(
    tool_name: str, 
    func: F, 
    approval_mode: str = "wait",
    on_approval: Optional[Callable[[Any], None]] = None,
    on_denial: Optional[Callable[[Exception], None]] = None,
    webhook_url: Optional[str] = None
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
        
        # Webhook mode - uses webhook for notifications
        safe_email_webhook = guard_tool(
            "communication.email",
            send_email, 
            approval_mode="webhook",
            webhook_url="https://myapp.com/arden-webhook"
        )
    """
    if not is_configured():
        raise ArdenError(
            "Arden must be configured before using guard_tool(). "
            "Call configure(api_url=...) first."
        )
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Wrapper function that enforces policy before calling the original function."""
        client = ArdenClient()
        
        try:
            # Extract function signature for better argument handling
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Convert arguments to serializable format.
            # Use bound_args.arguments (all named bindings) rather than
            # bound_args.kwargs (keyword-only) so positional args like
            # issue_refund(50.0) are sent as {"amount": 50.0} and can be
            # evaluated by policy rules.
            serializable_args = _make_serializable(list(args))
            serializable_kwargs = _make_serializable(dict(bound_args.arguments))
            
            # Check policy
            logger.debug(f"Checking policy for tool '{tool_name}'")
            response = client.check_tool_call(
                tool_name=tool_name,
                args=serializable_args,
                kwargs=serializable_kwargs,
            )
            
            # Handle policy decision
            if response.decision == PolicyDecision.ALLOW:
                logger.debug(f"Policy allows tool '{tool_name}'")
                return func(*args, **kwargs)
            
            elif response.decision == PolicyDecision.REQUIRE_APPROVAL:
                if not response.action_id:
                    raise ArdenError("Policy requires approval but no action_id provided")
                
                logger.info(f"Tool '{tool_name}' requires approval, action_id: {response.action_id}")
                
                # Handle different approval modes
                if approval_mode == "wait":
                    # Wait mode: Block until approval/denial (default behavior)
                    status = client.wait_for_approval(response.action_id)
                    
                    if status.status.value == "approved":
                        logger.info(f"Tool '{tool_name}' approved, executing")
                        return func(*args, **kwargs)
                    else:
                        raise PolicyDeniedError(
                            f"Tool call was denied: {status.message or 'No reason provided'}",
                            tool_name=tool_name
                        )
                
                elif approval_mode == "async":
                    # Async mode: Start background polling and return immediately
                    if not on_approval or not on_denial:
                        raise ArdenError("Async mode requires both on_approval and on_denial callbacks")
                    
                    _start_async_approval_polling(
                        client, response.action_id, func, args, kwargs, 
                        tool_name, on_approval, on_denial
                    )
                    return None  # Return immediately, callbacks will be called later
                
                elif approval_mode == "webhook":
                    # Webhook mode: Register webhook and return immediately
                    if not webhook_url:
                        raise ArdenError("Webhook mode requires webhook_url parameter")
                    
                    _register_webhook_approval(
                        client, response.action_id, func, args, kwargs,
                        tool_name, webhook_url
                    )
                    return None  # Return immediately, webhook will handle response
                
                else:
                    raise ArdenError(f"Unknown approval_mode: {approval_mode}. Use 'wait', 'async', or 'webhook'")
            
            elif response.decision == PolicyDecision.BLOCK:
                raise PolicyDeniedError(
                    response.message or f"Tool '{tool_name}' is blocked by policy",
                    tool_name=tool_name
                )
            
            else:
                raise ArdenError(f"Unknown policy decision: {response.decision}")
        
        finally:
            client.close()
    
    return cast(F, wrapper)


def _start_async_approval_polling(
    client: ArdenClient,
    action_id: str,
    func: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    on_approval: Callable[[Any], None],
    on_denial: Callable[[Exception], None]
) -> None:
    """Start background thread to poll for approval status."""
    
    def poll_approval():
        """Background polling function."""
        try:
            # Wait for approval in background thread
            status = client.wait_for_approval(action_id)
            
            if status.status.value == "approved":
                logger.info(f"Tool '{tool_name}' approved asynchronously, executing")
                try:
                    result = func(*args, **kwargs)
                    on_approval(result)
                except Exception as e:
                    logger.error(f"Error executing approved tool '{tool_name}': {e}")
                    on_denial(e)
            else:
                error = PolicyDeniedError(
                    f"Tool call was denied: {status.message or 'No reason provided'}",
                    tool_name=tool_name
                )
                on_denial(error)
                
        except Exception as e:
            logger.error(f"Error in async approval polling for '{tool_name}': {e}")
            on_denial(e)
    
    # Start background thread
    thread = threading.Thread(target=poll_approval, daemon=True)
    thread.start()


def _register_webhook_approval(
    client: ArdenClient,
    action_id: str,
    func: Callable,
    args: tuple,
    kwargs: dict,
    tool_name: str,
    webhook_url: str
) -> None:
    """Register webhook for approval notifications."""
    
    # Store function call details for webhook handler
    # This would typically be stored in a database or cache
    # For now, we'll use a simple in-memory store
    if not hasattr(_register_webhook_approval, 'pending_calls'):
        _register_webhook_approval.pending_calls = {}
    
    _register_webhook_approval.pending_calls[action_id] = {
        'func': func,
        'args': args,
        'kwargs': kwargs,
        'tool_name': tool_name,
        'webhook_url': webhook_url
    }
    
    logger.info(f"Registered webhook for tool '{tool_name}', action_id: {action_id}")
    # Note: The actual webhook registration with the backend would happen here
    # The backend would call the webhook_url when the action is approved/denied


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
