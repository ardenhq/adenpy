"""
Arden - AI Agent Tool Call Gate

A Python SDK for protecting AI agent tool calls with policy enforcement
and human approval workflows.
"""

from .guard import guard_tool, with_guard, GuardContext
from .config import configure, get_config, is_configured, configure_test, configure_live, ArdenConfig
from .client import ArdenClient
from .types import (
    ActionStatus,
    PolicyDecision,
    ArdenError,
    PolicyDeniedError,
    ApprovalTimeoutError,
    ConfigurationError,
)

__version__ = "0.1.0"
__author__ = "Arden Team"
__email__ = "team@arden.dev"

__all__ = [
    # Main API
    "guard_tool",
    "configure",
    "configure_test",
    "configure_live", 
    "get_config",
    "is_configured",
    
    # Context management
    "with_guard",
    "GuardContext",
    
    # Client
    "ArdenClient",
    
    # Configuration
    "ArdenConfig",
    
    # Types and enums
    "ActionStatus",
    "PolicyDecision",
    
    # Exceptions
    "ArdenError",
    "PolicyDeniedError",
    "ApprovalTimeoutError",
    "ConfigurationError",
]
