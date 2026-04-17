"""
Arden - AI Agent Tool Call Gate

A Python SDK for protecting AI agent tool calls with policy enforcement
and human approval workflows.
"""

from .guard import guard_tool, handle_webhook, verify_webhook_signature, with_guard, GuardContext
from .config import configure, get_config, is_configured, configure_test, configure_live, ArdenConfig
from .session import set_session, get_session, clear_session
from .client import ArdenClient
from .types import (
    ActionStatus,
    PolicyDecision,
    WebhookEvent,
    PendingApproval,
    ArdenError,
    PolicyDeniedError,
    ApprovalTimeoutError,
    ConfigurationError,
)
from . import integrations

__version__ = "0.4.0"
__author__ = "Arden Team"
__email__ = "team@arden.dev"

__all__ = [
    # Main API
    "guard_tool",
    "handle_webhook",
    "verify_webhook_signature",
    "configure",
    # Session tracking (optional)
    "set_session",
    "get_session",
    "clear_session",
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

    # Framework integrations (import from ardenpy.integrations.*)
    "integrations",

    # Types and enums
    "ActionStatus",
    "PolicyDecision",
    "WebhookEvent",
    "PendingApproval",

    # Exceptions
    "ArdenError",
    "PolicyDeniedError",
    "ApprovalTimeoutError",
    "ConfigurationError",
]
