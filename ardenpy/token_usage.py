"""Token usage logging for Arden.

Provides:
  - log_token_usage()              — call manually after any LLM invocation
  - ArdenTokenUsageCallback        — LangChain callback for automatic capture
                                     (also works in CrewAI, which uses LangChain)

For LangChain and CrewAI, configure() auto-patches BaseChatModel so you
don't need to add the callback yourself.  For OpenAI Agents SDK, configure()
patches Runner.run to capture usage from the RunResult automatically.

All logging is fire-and-forget (background thread) — no latency added to
your agent's critical path.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional, Sequence

logger = logging.getLogger(__name__)


# ── Public function ───────────────────────────────────────────────────────────

def log_token_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    session_id: Optional[str] = None,
) -> None:
    """Log token usage for an LLM call to Arden (fire-and-forget).

    Call this after any LLM invocation when you have the token counts.
    For supported frameworks (LangChain, CrewAI, OpenAI Agents SDK) this is
    called automatically by the auto-patcher — you only need this for custom
    agent loops.

    Args:
        model:             Model name, e.g. "gpt-4o" or "claude-sonnet-4-6".
        prompt_tokens:     Number of input / prompt tokens consumed.
        completion_tokens: Number of output / completion tokens generated.
        session_id:        Optional session ID to group calls in the dashboard.
                           Falls back to the current arden.set_session() value.
    """
    from .config import is_configured
    if not is_configured():
        return

    from .session import get_session
    sid = session_id or get_session()

    thread = threading.Thread(
        target=_send_usage,
        args=(model, prompt_tokens, completion_tokens, sid),
        daemon=True,
    )
    thread.start()


def _send_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    session_id: Optional[str],
) -> None:
    try:
        from .client import ArdenClient
        client = ArdenClient()
        try:
            client.log_token_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                session_id=session_id,
            )
        finally:
            client.close()
    except Exception as e:
        logger.debug(f"Arden: token usage logging failed (non-fatal): {e}")


# ── LangChain callback ────────────────────────────────────────────────────────

def _make_langchain_callback():
    """Return ArdenTokenUsageCallback class, importing LangChain lazily."""
    try:
        from langchain_core.callbacks.base import BaseCallbackHandler
        from langchain_core.outputs import LLMResult
    except ImportError:
        try:
            from langchain.callbacks.base import BaseCallbackHandler  # type: ignore
            from langchain.schema import LLMResult  # type: ignore
        except ImportError:
            return None

    class ArdenTokenUsageCallback(BaseCallbackHandler):
        """LangChain callback that logs token usage to Arden after each LLM call.

        Add to your chain or AgentExecutor::

            from ardenpy.token_usage import ArdenTokenUsageCallback
            executor = AgentExecutor(agent=agent, tools=tools,
                                     callbacks=[ArdenTokenUsageCallback()])

        When configure() is called, this is injected automatically — you only
        need to add it manually if you have disabled auto-patching.
        """

        def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
            try:
                usage = _extract_langchain_usage(response)
                if usage:
                    log_token_usage(
                        model=usage["model"],
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"],
                    )
            except Exception as e:
                logger.debug(f"Arden: ArdenTokenUsageCallback.on_llm_end failed: {e}")

    return ArdenTokenUsageCallback


def _extract_langchain_usage(response: Any) -> Optional[Dict[str, Any]]:
    """Pull token counts and model name out of a LangChain LLMResult."""
    llm_output = getattr(response, "llm_output", None) or {}

    # OpenAI / Azure OpenAI
    usage = llm_output.get("token_usage") or llm_output.get("usage")
    if usage:
        model = llm_output.get("model_name") or llm_output.get("model") or "unknown"
        return {
            "model":             str(model),
            "prompt_tokens":     int(usage.get("prompt_tokens",     usage.get("input_tokens",  0))),
            "completion_tokens": int(usage.get("completion_tokens", usage.get("output_tokens", 0))),
        }

    # Newer LangChain usage_metadata on the generation
    try:
        gen = response.generations[0][0] if response.generations else None
        if gen:
            meta = getattr(gen, "generation_info", None) or {}
            usage_meta = getattr(gen, "usage_metadata", None)
            if usage_meta:
                model = meta.get("model", "unknown")
                return {
                    "model":             str(model),
                    "prompt_tokens":     int(usage_meta.get("input_tokens",  0)),
                    "completion_tokens": int(usage_meta.get("output_tokens", 0)),
                }
    except Exception:
        pass

    return None


# ── Lazy export ───────────────────────────────────────────────────────────────

def __getattr__(name: str):
    if name == "ArdenTokenUsageCallback":
        cls = _make_langchain_callback()
        if cls is None:
            raise ImportError(
                "ArdenTokenUsageCallback requires langchain-core. "
                "Install it with: pip install langchain-core"
            )
        return cls
    raise AttributeError(f"module 'ardenpy.token_usage' has no attribute {name!r}")
