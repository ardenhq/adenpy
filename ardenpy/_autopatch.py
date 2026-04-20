"""Auto-patch installed AI agent frameworks to intercept all tool calls.

Called automatically by configure(). Patches the base-class invocation method
of each detected framework so that every tool call goes through Arden's policy
engine without any explicit wrapping by the user.

Frameworks patched:
- LangChain:         BaseTool.run          (class-level)
- CrewAI:            BaseTool.run          (class-level)
- OpenAI Agents SDK: FunctionTool.__init__ (wraps on_invoke_tool per instance)

Tools that were explicitly wrapped with protect_tools() carry an
``_arden_guarded`` sentinel attribute; the auto-patch skips those to avoid
double policy checks.
"""

from __future__ import annotations

import functools
import logging

logger = logging.getLogger(__name__)

# Sentinel attribute set on explicitly-wrapped tool instances.
# The auto-patch respects this to avoid checking the same call twice.
ARDEN_GUARDED = "_arden_guarded"

# Class-level sentinel to avoid patching the same base class twice.
_CLASS_PATCHED = "_arden_class_patched"

# Frameworks successfully patched in this process.
_patched: set[str] = set()


def patch_all() -> list[str]:
    """Detect installed frameworks and patch their tool base classes.

    Returns the list of framework names that were newly patched this call.
    Safe to call multiple times — already-patched classes are left alone.
    """
    newly_patched = []
    if _try_patch_langchain():
        newly_patched.append("langchain")
    if _try_patch_crewai():
        newly_patched.append("crewai")
    if _try_patch_openai_agents():
        newly_patched.append("openai-agents")
    return newly_patched


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_context(tool_input) -> dict:
    """Convert a framework tool input (str or dict) into a policy-engine context."""
    if isinstance(tool_input, dict):
        return dict(tool_input)
    return {"input": str(tool_input)}


# ── LangChain ─────────────────────────────────────────────────────────────────

def _try_patch_langchain() -> bool:
    if "langchain" in _patched:
        return False

    try:
        from langchain_core.tools.base import BaseTool  # langchain >= 0.1
    except ImportError:
        try:
            from langchain.tools import BaseTool  # type: ignore[no-redef]
        except ImportError:
            return False

    if getattr(BaseTool, _CLASS_PATCHED, False):
        _patched.add("langchain")
        return False

    _orig_run = BaseTool.run

    @functools.wraps(_orig_run)
    def _patched_run(self, tool_input, *args, **kwargs):
        # Skip if this instance was explicitly wrapped with protect_tools()
        if getattr(self, ARDEN_GUARDED, False):
            return _orig_run(self, tool_input, *args, **kwargs)

        from .guard import _run_with_policy_check, _make_serializable
        return _run_with_policy_check(
            tool_name=self.name,
            context=_make_serializable(_make_context(tool_input)),
            executor=lambda: _orig_run(self, tool_input, *args, **kwargs),
        )

    BaseTool.run = _patched_run
    setattr(BaseTool, _CLASS_PATCHED, True)
    _patched.add("langchain")
    logger.debug("Arden: auto-patched LangChain BaseTool.run")
    return True


# ── CrewAI ────────────────────────────────────────────────────────────────────

def _try_patch_crewai() -> bool:
    if "crewai" in _patched:
        return False

    try:
        from crewai.tools.base_tool import BaseTool  # crewai >= 0.28
    except ImportError:
        try:
            from crewai.tools import BaseTool  # type: ignore[no-redef]
        except ImportError:
            return False

    if getattr(BaseTool, _CLASS_PATCHED, False):
        _patched.add("crewai")
        return False

    _orig_run = BaseTool.run

    @functools.wraps(_orig_run)
    def _patched_run(self, tool_input=None, **kwargs):
        # Skip if this instance was explicitly wrapped with protect_tools()
        if getattr(self, ARDEN_GUARDED, False):
            return _orig_run(self, tool_input, **kwargs) if tool_input is not None else _orig_run(self, **kwargs)

        from .guard import _run_with_policy_check, _make_serializable

        if tool_input is not None:
            context = _make_serializable(_make_context(tool_input))
            executor = lambda: _orig_run(self, tool_input, **kwargs)
        else:
            context = _make_serializable(kwargs)
            executor = lambda: _orig_run(self, **kwargs)

        return _run_with_policy_check(
            tool_name=self.name,
            context=context,
            executor=executor,
        )

    BaseTool.run = _patched_run
    setattr(BaseTool, _CLASS_PATCHED, True)
    _patched.add("crewai")
    logger.debug("Arden: auto-patched CrewAI BaseTool.run")
    return True


# ── OpenAI Agents SDK ─────────────────────────────────────────────────────────

def _try_patch_openai_agents() -> bool:
    if "openai-agents" in _patched:
        return False

    try:
        from agents.tool import FunctionTool
    except ImportError:
        try:
            from agents import FunctionTool  # type: ignore[no-redef]
        except ImportError:
            return False

    if getattr(FunctionTool, _CLASS_PATCHED, False):
        _patched.add("openai-agents")
        return False

    _orig_init = FunctionTool.__init__

    @functools.wraps(_orig_init)
    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)

        # Skip instances explicitly wrapped with protect_function_tools()
        if getattr(self, ARDEN_GUARDED, False):
            return

        _orig_on_invoke = self.on_invoke_tool
        tool_name = self.name

        async def _guarded_on_invoke(ctx, input_str):
            import json as _json
            try:
                tool_args = _json.loads(input_str) if input_str else {}
            except Exception:
                tool_args = {"input": str(input_str)}

            from .guard import _make_serializable
            from .session import get_session
            from .client import ArdenClient
            from .types import PolicyDecision, PolicyDeniedError, ArdenError

            session_id = get_session()
            metadata = {"session_id": session_id} if session_id else None
            context = _make_serializable(tool_args)

            client = ArdenClient()
            try:
                response = client.check_tool_call(
                    tool_name=tool_name,
                    args=[],
                    kwargs=context,
                    metadata=metadata,
                )

                if response.decision == PolicyDecision.ALLOW:
                    return await _orig_on_invoke(ctx, input_str)

                elif response.decision == PolicyDecision.BLOCK:
                    raise PolicyDeniedError(
                        response.message or f"Tool '{tool_name}' is blocked by policy",
                        tool_name=tool_name,
                    )

                elif response.decision == PolicyDecision.REQUIRE_APPROVAL:
                    if not response.action_id:
                        raise ArdenError("Policy requires approval but no action_id provided")
                    status = client.wait_for_approval(response.action_id)
                    if status.status.value == "approved":
                        return await _orig_on_invoke(ctx, input_str)
                    else:
                        raise PolicyDeniedError(
                            f"Tool call was denied: {status.message or 'No reason provided'}",
                            tool_name=tool_name,
                        )

                else:
                    raise ArdenError(f"Unknown policy decision: {response.decision}")

            finally:
                client.close()

        self.on_invoke_tool = _guarded_on_invoke

    FunctionTool.__init__ = _patched_init
    setattr(FunctionTool, _CLASS_PATCHED, True)
    _patched.add("openai-agents")
    logger.debug("Arden: auto-patched OpenAI Agents SDK FunctionTool.__init__")
    return True
