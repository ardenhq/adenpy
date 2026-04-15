"""Type definitions for Arden SDK."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ActionStatus(str, Enum):
    """Status of an action in the approval workflow."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class PolicyDecision(str, Enum):
    """Policy decision for a tool call."""
    ALLOW = "allow"
    REQUIRE_APPROVAL = "requires_approval"
    BLOCK = "block"


class ToolCallRequest(BaseModel):
    """Request model for tool call policy check."""
    tool_name: str = Field(..., description="Name of the tool being called")
    args: List[Any] = Field(default_factory=list, description="Positional arguments")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class ToolCallResponse(BaseModel):
    """Response model for tool call policy check."""
    decision: PolicyDecision = Field(..., description="Policy decision")
    action_id: Optional[str] = Field(default=None, description="Action ID for approval workflow")
    message: Optional[str] = Field(default=None, description="Optional message")
    reason: Optional[str] = Field(default=None, description="Reason for decision (e.g. 'no_policy_configured')")
    status: Optional[str] = Field(default=None, description="Request status")
    environment: Optional[str] = Field(default=None, description="Environment (test/live)")
    user_id: Optional[str] = Field(default=None, description="User identifier")


class ActionStatusResponse(BaseModel):
    """Response model for action status check."""
    action_id: str = Field(..., description="Action identifier")
    status: ActionStatus = Field(..., description="Current status")
    message: Optional[str] = Field(default=None, description="Status message")
    created_at: str = Field(..., description="Creation timestamp")


class ApprovalRequest(BaseModel):
    """Request model for approval/denial actions."""
    message: Optional[str] = Field(default=None, description="Optional approval message")


class ArdenError(Exception):
    """Base exception for Arden SDK."""
    pass


class PolicyDeniedError(ArdenError):
    """Raised when a policy decision denies a tool call."""
    def __init__(self, message: str, tool_name: str):
        self.tool_name = tool_name
        super().__init__(message)


class ApprovalTimeoutError(ArdenError):
    """Raised when waiting for approval times out."""
    def __init__(self, action_id: str, timeout: float):
        self.action_id = action_id
        self.timeout = timeout
        super().__init__(f"Approval timeout for action {action_id} after {timeout}s")


class ConfigurationError(ArdenError):
    """Raised when SDK is not properly configured."""
    pass


@dataclass
class WebhookEvent:
    """Parsed payload delivered to on_approval / on_denial callbacks.

    All the information needed to re-execute the original tool call is here.
    The user's callback receives this object and decides what to do with it.

    Example::

        def on_approval(event: WebhookEvent):
            result = issue_refund(
                event.context["amount"],
                event.context["customer_id"],
            )
            print(f"Refund issued: {result}")
    """

    event_type: str          # "action_approved" or "action_denied"
    action_id: str
    tool_name: str           # e.g. "stripe.issue_refund"
    context: Dict[str, Any]  # all kwargs/context that were originally submitted
    approved_by: Optional[str] = None
    notes: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)  # full original payload


@dataclass
class PendingApproval:
    """Returned by guard_tool when a call is queued for human approval.

    In webhook and async modes the original call returns immediately with
    this object instead of the function's real return value.  Use the
    ``action_id`` for logging or correlation.
    """

    action_id: str
    tool_name: str

    def __str__(self) -> str:
        return (
            f"This action requires human approval before it can execute. "
            f"A request has been sent to your administrator. "
            f"The action will complete once approved. (action_id: {self.action_id})"
        )

    def __repr__(self) -> str:
        return f"PendingApproval(action_id={self.action_id!r}, tool_name={self.tool_name!r})"
