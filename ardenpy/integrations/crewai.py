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

logger = logging.getLogger(__name__)


def protect_tools(
    tools: List[Any],
    approval_mode: str = "wait",
    on_approval=None,
    on_denial=None,
    tool_name_prefix: str = "crewai",
) -> List[Any]:
    """Wrap a list of CrewAI tools with Arden policy enforcement.

    Each tool's ``_run`` method is wrapped with :func:`ardenpy.guard_tool`.
    The Arden tool name is ``{prefix}.{tool.name}``.

    Args:
        tools: List of CrewAI ``BaseTool`` instances.
        approval_mode: ``"wait"`` (default), ``"async"``, or ``"webhook"``.
        on_approval: Callback for ``async``/``webhook`` modes.
        on_denial: Callback for ``async``/``webhook`` modes.
        tool_name_prefix: Prefix for the Arden tool name. Set this to your
            service name for clearer policies, e.g. ``"stripe"`` or ``"finance"``.

    Returns:
        The same list of tools with ``_run`` replaced by Arden-protected versions.
        Tools are modified in place and also returned for convenience.

    Example::

        from crewai.tools import BaseTool
        from ardenpy.integrations.crewai import protect_tools

        class DeleteRecordTool(BaseTool):
            name: str = "delete_record"
            description: str = "Permanently delete a database record"

            def _run(self, record_id: str) -> str:
                ...

        safe_tools = protect_tools([DeleteRecordTool()], tool_name_prefix="database")

        agent = Agent(role="DBA", tools=safe_tools, ...)
    """
    for tool in tools:
        arden_tool_name = f"{tool_name_prefix}.{tool.name}"
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
        logger.debug(f"Arden protection applied to CrewAI tool '{tool.name}' as '{arden_tool_name}'")

    return tools
