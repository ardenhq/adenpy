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
    # Token usage capture — fire-and-forget, separate from tool enforcement
    _try_patch_langchain_llm()
    _try_patch_openai_agents_runner()
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


# ── Token usage: LangChain / CrewAI ──────────────────────────────────────────

def _try_patch_langchain_llm() -> bool:
    """Patch BaseChatModel.invoke to capture token usage after each LLM call."""
    if "langchain-llm" in _patched:
        return False

    try:
        from langchain_core.language_models.chat_models import BaseChatModel
    except ImportError:
        try:
            from langchain.chat_models.base import BaseChatModel  # type: ignore
        except ImportError:
            return False

    if getattr(BaseChatModel, "_arden_llm_patched", False):
        _patched.add("langchain-llm")
        return False

    def _extract_and_log(self, result):
        """Extract token usage from an AIMessage and fire log_token_usage."""
        try:
            from .token_usage import log_token_usage
            usage_meta = getattr(result, "usage_metadata", None)
            if usage_meta:
                model = getattr(self, "model_name", None) or getattr(self, "model", "unknown")
                log_token_usage(
                    model=str(model),
                    prompt_tokens=int(usage_meta.get("input_tokens", 0)),
                    completion_tokens=int(usage_meta.get("output_tokens", 0)),
                )
            else:
                meta = getattr(result, "response_metadata", {}) or {}
                usage = meta.get("token_usage") or meta.get("usage")
                if usage:
                    model = meta.get("model_name") or meta.get("model") or getattr(self, "model_name", "unknown")
                    log_token_usage(
                        model=str(model),
                        prompt_tokens=int(usage.get("prompt_tokens", usage.get("input_tokens", 0))),
                        completion_tokens=int(usage.get("completion_tokens", usage.get("output_tokens", 0))),
                    )
        except Exception as e:
            logger.debug(f"Arden: LangChain token usage capture failed (non-fatal): {e}")

    _orig_invoke = BaseChatModel.invoke
    _orig_ainvoke = BaseChatModel.ainvoke

    @functools.wraps(_orig_invoke)
    def _patched_invoke(self, input, config=None, **kwargs):
        result = _orig_invoke(self, input, config=config, **kwargs)
        _extract_and_log(self, result)
        return result

    @functools.wraps(_orig_ainvoke)
    async def _patched_ainvoke(self, input, config=None, **kwargs):
        result = await _orig_ainvoke(self, input, config=config, **kwargs)
        _extract_and_log(self, result)
        return result

    BaseChatModel.invoke = _patched_invoke
    BaseChatModel.ainvoke = _patched_ainvoke
    setattr(BaseChatModel, "_arden_llm_patched", True)
    _patched.add("langchain-llm")
    logger.debug("Arden: auto-patched LangChain BaseChatModel.invoke and ainvoke for token usage")
    return True


# ── Token usage: OpenAI Agents SDK ───────────────────────────────────────────

def _try_patch_openai_agents_runner() -> bool:
    """Patch Runner.run to capture token usage from the RunResult."""
    if "openai-agents-runner" in _patched:
        return False

    try:
        from agents import Runner
    except ImportError:
        return False

    if getattr(Runner, "_arden_runner_patched", False):
        _patched.add("openai-agents-runner")
        return False

    def _log_runner_usage(starting_agent, result):
        try:
            usage = getattr(result, "usage", None)
            if usage:
                model = (
                    getattr(starting_agent, "model", None)
                    or getattr(starting_agent, "model_name", None)
                    or "unknown"
                )
                from .token_usage import log_token_usage
                log_token_usage(
                    model=str(model),
                    prompt_tokens=int(getattr(usage, "input_tokens", 0)),
                    completion_tokens=int(getattr(usage, "output_tokens", 0)),
                )
        except Exception as e:
            logger.debug(f"Arden: OpenAI Agents Runner token usage capture failed (non-fatal): {e}")

    _orig_run = Runner.run

    @classmethod  # type: ignore[misc]
    @functools.wraps(_orig_run.__func__ if hasattr(_orig_run, "__func__") else _orig_run)
    async def _patched_run(cls, starting_agent, input, **kwargs):
        result = await _orig_run.__func__(cls, starting_agent, input, **kwargs)
        _log_runner_usage(starting_agent, result)
        return result

    Runner.run = _patched_run

    _orig_run_sync = getattr(Runner, "run_sync", None)
    if _orig_run_sync is not None:
        @classmethod  # type: ignore[misc]
        @functools.wraps(_orig_run_sync.__func__ if hasattr(_orig_run_sync, "__func__") else _orig_run_sync)
        def _patched_run_sync(cls, starting_agent, input, **kwargs):
            result = _orig_run_sync.__func__(cls, starting_agent, input, **kwargs)
            _log_runner_usage(starting_agent, result)
            return result

        Runner.run_sync = _patched_run_sync

    setattr(Runner, "_arden_runner_patched", True)
    _patched.add("openai-agents-runner")
    logger.debug("Arden: auto-patched OpenAI Agents SDK Runner.run and Runner.run_sync for token usage")
    return True
