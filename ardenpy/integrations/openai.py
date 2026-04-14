"""
OpenAI Agents SDK and raw OpenAI tool-call loop integration for Arden.

Two patterns are supported:

1. **Raw tool dispatch** (``ArdenToolExecutor``) — for the classic
   ``while response.stop_reason == "tool_use"`` loop used with the
   OpenAI Chat Completions API.

2. **OpenAI Agents SDK** (``protect_function_tools``) — for the newer
   ``openai-agents`` / ``agents`` SDK where tools are defined with
   ``@function_tool`` or as ``FunctionTool`` instances.

Usage — raw dispatch loop::

    import ardenpy as arden
    from ardenpy.integrations.openai import ArdenToolExecutor

    arden.configure(api_key="arden_live_...")

    executor = ArdenToolExecutor(tool_name_prefix="myapp")
    executor.register("issue_refund", issue_refund)
    executor.register("send_email", send_email)

    # In your tool-call dispatch loop:
    for tool_call in response.choices[0].message.tool_calls:
        result = executor.run(tool_call.function.name,
                              json.loads(tool_call.function.arguments))

Usage — OpenAI Agents SDK::

    from agents import function_tool
    from ardenpy.integrations.openai import protect_function_tools

    @function_tool
    def issue_refund(amount: float, customer_id: str) -> str:
        ...

    safe_tools = protect_function_tools([issue_refund], tool_name_prefix="stripe")
    agent = Agent(name="Support", tools=safe_tools)
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from ..guard import guard_tool
from ..types import PolicyDeniedError

logger = logging.getLogger(__name__)


class ArdenToolExecutor:
    """Dispatch table for OpenAI Chat Completions tool calls with Arden enforcement.

    Register **all** your tool functions — you don't need to decide upfront which
    ones are sensitive. Arden enforces only the tools that have policies configured
    in the dashboard; everything else is allowed and logged automatically.

    Register your tool functions once, then call ``run()`` for each tool_call
    in the model response. Arden policy is checked before the function executes.

    Example::

        executor = ArdenToolExecutor(tool_name_prefix="stripe")
        executor.register("issue_refund", issue_refund)
        executor.register("cancel_subscription", cancel_subscription)

        for tool_call in response.choices[0].message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = executor.run(name, args)
                messages.append({"role": "tool", "tool_call_id": tool_call.id,
                                  "content": str(result)})
            except PolicyDeniedError as e:
                messages.append({"role": "tool", "tool_call_id": tool_call.id,
                                  "content": f"Action blocked by policy: {e}"})
    """

    def __init__(
        self,
        approval_mode: str = "wait",
        on_approval=None,
        on_denial=None,
        tool_name_prefix: str = "openai",
    ):
        self.approval_mode = approval_mode
        self.on_approval = on_approval
        self.on_denial = on_denial
        self.tool_name_prefix = tool_name_prefix
        self._registry: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable, arden_name: Optional[str] = None) -> None:
        """Register a function as a tool with Arden protection.

        Args:
            name: The tool name as it appears in the OpenAI tool spec
                  (must match the ``name`` field in your function definition).
            func: The Python function to execute when the tool is called.
            arden_name: Override the Arden policy name. Defaults to
                        ``{prefix}.{name}``.
        """
        policy_name = arden_name or f"{self.tool_name_prefix}.{name}"
        self._registry[name] = guard_tool(
            policy_name,
            func,
            approval_mode=self.approval_mode,
            on_approval=self.on_approval,
            on_denial=self.on_denial,
        )
        logger.debug(f"Registered OpenAI tool '{name}' with Arden policy '{policy_name}'")

    def run(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name with the given arguments.

        Args:
            name: Tool name from ``tool_call.function.name``.
            arguments: Parsed arguments dict from ``tool_call.function.arguments``.

        Returns:
            The tool's return value.

        Raises:
            KeyError: If ``name`` was not registered.
            PolicyDeniedError: If Arden blocks the call.
        """
        if name not in self._registry:
            raise KeyError(f"Tool '{name}' not registered. Call executor.register() first.")
        return self._registry[name](**arguments)


def protect_function_tools(
    tools: List[Any],
    approval_mode: str = "wait",
    on_approval=None,
    on_denial=None,
    tool_name_prefix: str = "openai",
) -> List[Any]:
    """Wrap OpenAI Agents SDK ``FunctionTool`` objects with Arden policy enforcement.

    Compatible with the ``openai-agents`` package (``from agents import function_tool``).
    Each tool's underlying function is wrapped with :func:`ardenpy.guard_tool`.

    Args:
        tools: List of ``FunctionTool`` instances (created with ``@function_tool``).
        approval_mode: ``"wait"`` (default), ``"async"``, or ``"webhook"``.
        on_approval: Callback for ``async``/``webhook`` modes.
        on_denial: Callback for ``async``/``webhook`` modes.
        tool_name_prefix: Prefix for Arden policy names.

    Returns:
        The same list of tools with their functions replaced by Arden-protected versions.

    Example::

        from agents import Agent, function_tool
        from ardenpy.integrations.openai import protect_function_tools

        @function_tool
        def send_email(to: str, subject: str, body: str) -> str:
            ...

        @function_tool
        def delete_user(user_id: str) -> str:
            ...

        safe_tools = protect_function_tools([send_email, delete_user],
                                            tool_name_prefix="support")
        agent = Agent(name="SupportBot", tools=safe_tools)
    """
    for tool in tools:
        # FunctionTool stores the callable in `.fn` or `._fn` depending on SDK version
        original_fn = getattr(tool, "fn", None) or getattr(tool, "_fn", None)
        if original_fn is None:
            logger.warning(f"Could not find underlying function on tool {tool!r}, skipping")
            continue

        tool_name = getattr(tool, "name", None) or original_fn.__name__
        arden_name = f"{tool_name_prefix}.{tool_name}"

        guarded = guard_tool(
            arden_name,
            original_fn,
            approval_mode=approval_mode,
            on_approval=on_approval,
            on_denial=on_denial,
        )

        # Patch the stored function reference
        if hasattr(tool, "fn"):
            tool.fn = guarded
        elif hasattr(tool, "_fn"):
            tool._fn = guarded

        logger.debug(f"Arden protection applied to FunctionTool '{tool_name}' as '{arden_name}'")

    return tools
