"""Session context for Arden SDK.

Provides a lightweight, per-async-task (or per-thread) session ID that is
automatically attached to every policy-check request made in that context.

Usage::

    import ardenpy as arden

    # Set once at the start of a request / conversation turn
    arden.set_session("conv_abc123")

    # All guard_tool / auto-patch calls in this context now carry session_id
    result = safe_send_email(to="alice@example.com", subject="Hi", body="Hello")

    # Clear when the session ends (optional — GC'd automatically in async tasks)
    arden.clear_session()
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

# ContextVar is the right primitive here:
# - In async code (FastAPI, asyncio) each Task gets its own copy, so setting
#   the session ID in one request never bleeds into another.
# - In sync/threaded code it behaves like a thread-local.
_session_id: ContextVar[Optional[str]] = ContextVar("arden_session_id", default=None)


def set_session(session_id: str) -> None:
    """Attach a session ID to the current async task or thread.

    Every policy-check call made after this point (guard_tool, auto-patched
    LangChain/CrewAI tools) will include ``session_id`` in the request sent
    to the Arden backend, allowing you to group and replay all actions from a
    single conversation or workflow run on the dashboard.

    Args:
        session_id: Any string that identifies this session — a UUID, a
            conversation ID from your app, a user ID, etc.

    Example (FastAPI)::

        @app.post("/chat")
        async def chat(request: Request):
            body = await request.json()
            arden.set_session(body.get("session_id") or str(uuid.uuid4()))
            reply = await run_agent(messages)
            ...
    """
    _session_id.set(session_id)


def get_session() -> Optional[str]:
    """Return the current session ID, or ``None`` if none has been set."""
    return _session_id.get()


def clear_session() -> None:
    """Remove the session ID from the current context."""
    _session_id.set(None)
