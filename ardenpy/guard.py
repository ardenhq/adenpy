"""Main guard functionality for wrapping and protecting tool calls."""

import functools
import logging
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


def guard_tool(tool_name: str, func: F) -> F:
    """Wrap a function with policy enforcement and approval workflow.
    
    Args:
        tool_name: Name identifier for the tool (used in policy evaluation)
        func: Function to wrap with policy enforcement
        
    Returns:
        Wrapped function that checks policy before execution
        
    Raises:
        ConfigurationError: If Arden is not configured
        PolicyDeniedError: If policy denies the tool call
        ApprovalTimeoutError: If approval workflow times out
        ArdenError: For other API communication errors
        
    Example:
        def my_tool(x: int, y: int) -> int:
            return x + y
            
        protected_tool = guard_tool("my_tool", my_tool)
        result = protected_tool(5, 7)  # Policy check happens here
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
            
            # Convert arguments to serializable format
            serializable_args = _make_serializable(list(args))
            serializable_kwargs = _make_serializable(dict(bound_args.kwargs))
            
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
                
                # Wait for approval
                status = client.wait_for_approval(response.action_id)
                
                if status.status.value == "approved":
                    logger.info(f"Tool '{tool_name}' approved, executing")
                    return func(*args, **kwargs)
                else:
                    raise PolicyDeniedError(
                        f"Tool call was denied: {status.message or 'No reason provided'}",
                        tool_name=tool_name
                    )
            
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
