"""
LangChain integration for Arden.

Two ways to integrate:

1. protect_tools() — wrap a list of tools with Arden policy enforcement.
   This is the recommended approach: policies are enforced synchronously when
   the tool runs, so the agent is blocked until a human approves or denies.

2. ArdenCallbackHandler — attach to any AgentExecutor for observability.
   Records every tool call in Arden's action log without blocking execution.
   Use this if you want visibility without enforcement, or alongside protect_tools()
   to log *all* calls including ones on tools you didn't explicitly wrap.

Usage::

    import ardenpy as arden
    from ardenpy.integrations.langchain import protect_tools, ArdenCallbackHandler
    from langchain.agents import AgentExecutor

    arden.configure(api_key="arden_live_...")

    # Option 1: enforce policies
    tools = protect_tools(raw_tools, approval_mode="wait")

    # Option 2: observability only
    executor = AgentExecutor(agent=agent, tools=tools,
                             callbacks=[ArdenCallbackHandler()])

**Do not mix with guard_tool on the same tool.** If your tool function or
``_run`` method already calls ``guard_tool`` internally, do not also pass it
through ``protect_tools()`` — the policy check would run twice.

Rule of thumb:
  - Using a framework (LangChain, CrewAI, OpenAI)? Use ``protect_tools()``.
  - Custom/no-framework agent? Use ``guard_tool()`` directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from ..guard import guard_tool
from ..client import ArdenClient
from ..config import get_config

logger = logging.getLogger(__name__)


def protect_tools(
    tools: List[Any],
    approval_mode: str = "wait",
    on_approval=None,
    on_denial=None,
    tool_name_prefix: str = "langchain",
) -> List[Any]:
    """Wrap a list of LangChain tools with Arden policy enforcement.

    Each tool's ``run`` method is wrapped with :func:`ardenpy.guard_tool`.
    The tool name sent to the Arden policy engine is ``{prefix}.{tool.name}``,
    e.g. ``langchain.send_email``.

    Args:
        tools: List of LangChain ``BaseTool`` or ``Tool`` instances.
        approval_mode: ``"wait"`` (default), ``"async"``, or ``"webhook"``.
            See :func:`ardenpy.guard_tool` for details.
        on_approval: Callback for ``async``/``webhook`` modes.
        on_denial: Callback for ``async``/``webhook`` modes.
        tool_name_prefix: Prefix used when building the Arden tool name.
            Defaults to ``"langchain"``. Set to your service name for clearer
            policy rules, e.g. ``"customer_support"``.

    Returns:
        New list of tools with Arden protection applied. The original tools
        are not modified.

    Example::

        from langchain_community.tools import DuckDuckGoSearchRun
        from langchain.tools import Tool

        raw_tools = [
            DuckDuckGoSearchRun(),
            Tool(name="send_email", func=send_email, description="Send an email"),
        ]

        safe_tools = protect_tools(raw_tools, approval_mode="wait")
        # safe_tools[0] enforces policy for "langchain.duckduckgosearch"
        # safe_tools[1] enforces policy for "langchain.send_email"
    """
    try:
        from langchain.tools import Tool as LangChainTool
    except ImportError:
        raise ImportError(
            "langchain is required for this integration. "
            "Install it with: pip install langchain"
        )

    protected = []
    for tool in tools:
        arden_tool_name = f"{tool_name_prefix}.{tool.name}"

        # Wrap the synchronous run method
        guarded_run = guard_tool(
            arden_tool_name,
            tool.run,
            approval_mode=approval_mode,
            on_approval=on_approval,
            on_denial=on_denial,
        )

        # Build a new Tool that delegates to the guarded runner.
        # We preserve the original description and name so the LLM sees
        # identical tool metadata.
        protected_tool = LangChainTool(
            name=tool.name,
            func=guarded_run,
            description=tool.description,
        )
        protected.append(protected_tool)
        logger.debug(f"Arden protection applied to LangChain tool '{tool.name}' as '{arden_tool_name}'")

    return protected


class ArdenCallbackHandler:
    """LangChain callback handler that logs all tool calls to Arden.

    Attach this to an ``AgentExecutor`` for full observability: every tool
    invocation (and its output) is recorded in Arden's action log, even for
    tools that are not wrapped with :func:`protect_tools`.

    This handler does **not** enforce policies — use :func:`protect_tools` for
    that. The two can be combined: wrap high-risk tools with ``protect_tools``
    and attach ``ArdenCallbackHandler`` to capture everything else.

    Example::

        from ardenpy.integrations.langchain import ArdenCallbackHandler
        from langchain.agents import AgentExecutor

        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            callbacks=[ArdenCallbackHandler()],
        )
    """

    def __init__(self, tool_name_prefix: str = "langchain"):
        self.tool_name_prefix = tool_name_prefix
        self._pending: Dict[str, Dict[str, Any]] = {}  # run_id → metadata

    # ------------------------------------------------------------------
    # LangChain callback interface
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        arden_name = f"{self.tool_name_prefix}.{tool_name}"
        self._pending[str(run_id)] = {"tool_name": arden_name, "input": input_str}
        logger.debug(f"ArdenCallbackHandler: tool started — {arden_name}")

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        meta = self._pending.pop(str(run_id), {})
        tool_name = meta.get("tool_name", "unknown")
        logger.debug(f"ArdenCallbackHandler: tool completed — {tool_name}")

        try:
            client = ArdenClient()
            # Log via policy check in observe-only mode (no blocking).
            # The call is fire-and-forget; failures are swallowed so the
            # agent is never disrupted by Arden connectivity issues.
            client.check_tool_call(
                tool_name=tool_name,
                args=[],
                kwargs={"input": meta.get("input", ""), "output": output},
            )
            client.close()
        except Exception as exc:
            logger.warning(f"ArdenCallbackHandler: failed to log tool call: {exc}")

    def on_tool_error(
        self,
        error: Union[Exception, KeyboardInterrupt],
        *,
        run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        self._pending.pop(str(run_id), None)

    # Make this compatible with LangChain's BaseCallbackHandler interface
    # without requiring it as a hard dependency.
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    @property
    def ignore_agent(self) -> bool:
        return False

    @property
    def ignore_llm(self) -> bool:
        return True

    @property
    def ignore_chain(self) -> bool:
        return True
