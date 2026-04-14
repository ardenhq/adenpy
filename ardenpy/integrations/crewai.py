"""
CrewAI integration for Arden.

Wrap CrewAI tools with Arden policy enforcement using protect_tools().
The tool name sent to the Arden policy engine is ``{prefix}.{tool.name}``.

Usage::

    import ardenpy as arden
    from ardenpy.integrations.crewai import protect_tools
    from crewai import Agent, Task, Crew
    from crewai.tools import BaseTool

    arden.configure(api_key="arden_live_...")

    class RefundTool(BaseTool):
        name: str = "issue_refund"
        description: str = "Issue a refund to a customer"

        def _run(self, amount: float, customer_id: str) -> str:
            return f"Refund of ${amount} issued to {customer_id}"

    safe_tools = protect_tools([RefundTool()], tool_name_prefix="stripe")
    # Policy engine receives tool name "stripe.issue_refund"

    agent = Agent(role="Support", tools=safe_tools, ...)
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from ..guard import guard_tool
from .._autopatch import ARDEN_GUARDED

logger = logging.getLogger(__name__)


def protect_tools(
    tools: List[Any],
    approval_mode: str = "wait",
    on_approval=None,
    on_denial=None,
) -> List[Any]:
    """Wrap a list of CrewAI tools with Arden policy enforcement.

    Use this when you need per-tool approval mode overrides. For the common
    case, just call ``arden.configure()`` — Arden auto-patches CrewAI and
    every tool call is intercepted automatically without any wrapping.

    Each tool's ``_run`` method is wrapped with :func:`ardenpy.guard_tool`.
    The tool name sent to the Arden policy engine is ``tool.name`` directly.
    Create a matching policy in the dashboard for any tool you want to control.

    Args:
        tools: List of CrewAI ``BaseTool`` instances.
        approval_mode: ``"wait"`` (default), ``"async"``, or ``"webhook"``.
        on_approval: Callback for ``async``/``webhook`` modes.
        on_denial: Callback for ``async``/``webhook`` modes.

    Returns:
        The same list of tools with ``_run`` replaced by Arden-protected versions.
        Tools are modified in place and also returned for convenience.

    Example::

        # Only needed for per-tool approval mode overrides.
        # For standard use, just call arden.configure() — no wrapping required.
        safe_tools = protect_tools(
            [RefundTool()],
            approval_mode="async",
            on_approval=handle_approval,
            on_denial=handle_denial,
        )
        agent = Agent(role="Support", tools=safe_tools, ...)
    """
    for tool in tools:
        arden_tool_name = tool.name
        original_run = tool._run

        guarded_run = guard_tool(
            arden_tool_name,
            original_run,
            approval_mode=approval_mode,
            on_approval=on_approval,
            on_denial=on_denial,
        )

        # Patch the instance method
        import types
        tool._run = types.MethodType(lambda self, *a, **kw: guarded_run(*a, **kw), tool)
        # Mark so the class-level auto-patch skips this instance.
        setattr(tool, ARDEN_GUARDED, True)
        logger.debug(f"Arden protection applied to CrewAI tool '{tool.name}'")

    return tools
