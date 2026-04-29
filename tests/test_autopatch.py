"""Tests for auto-patch: framework tool interception and failure modes.

Covers:
- LangChain BaseTool.run intercepted (sync)
- LangChain BaseTool.arun intercepted (async) — regression for the arun gap
- CrewAI BaseTool.run and arun intercepted
- _arden_guarded sentinel skips policy check
- Allow/block/requires_approval/fail-closed via _run_with_policy_check
- OpenAI Agents SDK: tool created before configure() is NOT patched (known limitation)
- OpenAI Agents SDK: tool created after configure() IS patched

Known limitation NOT tested (by design):
- LangChain tool that overrides run() directly (shadows the monkey-patch at the subclass level)
  This is a rare pattern and would require per-class patching to fix.
"""

import asyncio
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ── Response factories ────────────────────────────────────────────────────────

def _allow():
    from ardenpy.types import ToolCallResponse, PolicyDecision
    return ToolCallResponse(decision=PolicyDecision.ALLOW, message="allowed")

def _block():
    from ardenpy.types import ToolCallResponse, PolicyDecision
    return ToolCallResponse(decision=PolicyDecision.BLOCK, message="blocked by policy")

def _requires_approval(action_id="act_123"):
    from ardenpy.types import ToolCallResponse, PolicyDecision
    return ToolCallResponse(decision=PolicyDecision.REQUIRE_APPROVAL, action_id=action_id)

def _approved():
    s = MagicMock()
    s.status.value = "approved"
    s.message = None
    return s

def _denied():
    s = MagicMock()
    s.status.value = "denied"
    s.message = "denied by admin"
    return s


# ── Fake framework modules ────────────────────────────────────────────────────

class _FakeLangChainModules:
    """Context manager: injects a fresh LangChain BaseTool into sys.modules.

    Creates a brand-new class each time (no _arden_class_patched sentinel),
    captures which method the tool body was actually called through, and
    restores sys.modules on exit.
    """

    def __enter__(self):
        self._executed = []
        executed = self._executed

        class BaseTool:
            name = "test_tool"

            def run(self, tool_input, *args, **kwargs):
                executed.append(("run", tool_input))
                return f"run:{tool_input}"

            async def arun(self, tool_input, *args, **kwargs):
                executed.append(("arun", tool_input))
                return f"arun:{tool_input}"

        self.BaseTool = BaseTool

        pkg = types.ModuleType("langchain_core")
        tools_pkg = types.ModuleType("langchain_core.tools")
        base_mod = types.ModuleType("langchain_core.tools.base")
        base_mod.BaseTool = BaseTool

        self._saved = {k: sys.modules.get(k) for k in [
            "langchain_core", "langchain_core.tools", "langchain_core.tools.base"
        ]}
        sys.modules["langchain_core"] = pkg
        sys.modules["langchain_core.tools"] = tools_pkg
        sys.modules["langchain_core.tools.base"] = base_mod
        return self

    def __exit__(self, *_):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


class _FakeCrewAIModules:
    """Same as above but for CrewAI's import path."""

    def __enter__(self):
        self._executed = []
        executed = self._executed

        class BaseTool:
            name = "test_tool"

            def run(self, tool_input=None, **kwargs):
                executed.append(("run", tool_input))
                return f"run:{tool_input}"

            async def arun(self, tool_input=None, **kwargs):
                executed.append(("arun", tool_input))
                return f"arun:{tool_input}"

        self.BaseTool = BaseTool

        pkg = types.ModuleType("crewai")
        tools_pkg = types.ModuleType("crewai.tools")
        base_mod = types.ModuleType("crewai.tools.base_tool")
        base_mod.BaseTool = BaseTool

        self._saved = {k: sys.modules.get(k) for k in [
            "crewai", "crewai.tools", "crewai.tools.base_tool"
        ]}
        sys.modules["crewai"] = pkg
        sys.modules["crewai.tools"] = tools_pkg
        sys.modules["crewai.tools.base_tool"] = base_mod
        return self

    def __exit__(self, *_):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def _fake_agents_modules():
    """Inject a minimal FunctionTool into sys.modules; return the class."""
    class FunctionTool:
        name = "fake_fn_tool"

        def __init__(self, on_invoke_tool=None, **kwargs):
            self.on_invoke_tool = on_invoke_tool

    agents_pkg = types.ModuleType("agents")
    tool_mod = types.ModuleType("agents.tool")
    tool_mod.FunctionTool = FunctionTool
    agents_pkg.FunctionTool = FunctionTool
    sys.modules["agents"] = agents_pkg
    sys.modules["agents.tool"] = tool_mod
    return FunctionTool


# ── Shared setUp/tearDown helpers ─────────────────────────────────────────────

def _reset_autopatch(*framework_keys):
    import ardenpy._autopatch as ap
    for k in framework_keys:
        ap._patched.discard(k)


def _configure():
    import ardenpy.config
    ardenpy.config._config = None
    from ardenpy import configure
    configure(api_key="test_key", api_url="https://test.api.com")


def _unconfigure():
    import ardenpy.config
    ardenpy.config._config = None


# ── Core policy-check logic ───────────────────────────────────────────────────

class TestPolicyCheckCore(unittest.TestCase):
    """_run_with_policy_check: allow / block / approval flows / fail-closed."""

    def setUp(self):
        _configure()

    def tearDown(self):
        _unconfigure()

    def _call(self, mock_response=None, mock_approval=None, side_effect=None):
        from ardenpy.guard import _run_with_policy_check
        executed = []

        check_kwargs = {}
        if side_effect:
            check_kwargs["side_effect"] = side_effect
        else:
            check_kwargs["return_value"] = mock_response

        with patch("ardenpy.client.ArdenClient.check_tool_call", **check_kwargs):
            with patch("ardenpy.client.ArdenClient.close"):
                wait_kwargs = {"return_value": mock_approval} if mock_approval else {}
                with patch("ardenpy.client.ArdenClient.wait_for_approval", **wait_kwargs):
                    result = _run_with_policy_check(
                        tool_name="test.tool",
                        context={"amount": 50},
                        executor=lambda: executed.append(True) or "ok",
                    )
        return result, executed

    def test_allow_executes_tool(self):
        result, executed = self._call(mock_response=_allow())
        self.assertEqual(result, "ok")
        self.assertTrue(executed)

    def test_block_raises_and_does_not_execute(self):
        from ardenpy.types import PolicyDeniedError
        from ardenpy.guard import _run_with_policy_check
        executed = []
        with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_block()):
            with patch("ardenpy.client.ArdenClient.close"):
                with self.assertRaises(PolicyDeniedError):
                    _run_with_policy_check("test.tool", {}, lambda: executed.append(True) or "ok")
        self.assertFalse(executed, "Tool must not execute when blocked")

    def test_approval_approved_executes_tool(self):
        result, executed = self._call(mock_response=_requires_approval(), mock_approval=_approved())
        self.assertEqual(result, "ok")
        self.assertTrue(executed)

    def test_approval_denied_raises_and_does_not_execute(self):
        from ardenpy.types import PolicyDeniedError
        from ardenpy.guard import _run_with_policy_check
        executed = []
        with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_requires_approval()):
            with patch("ardenpy.client.ArdenClient.wait_for_approval", return_value=_denied()):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(PolicyDeniedError):
                        _run_with_policy_check("test.tool", {}, lambda: executed.append(True) or "ok")
        self.assertFalse(executed, "Tool must not execute when denied")

    def test_arden_api_down_raises_does_not_execute(self):
        """Arden unreachable → ArdenError raised, tool never executes (fail-closed)."""
        from ardenpy.types import ArdenError
        from ardenpy.guard import _run_with_policy_check
        executed = []
        with patch("ardenpy.client.ArdenClient.check_tool_call", side_effect=ArdenError("connection refused")):
            with patch("ardenpy.client.ArdenClient.close"):
                with self.assertRaises(ArdenError):
                    _run_with_policy_check("test.tool", {}, lambda: executed.append(True) or "ok")
        self.assertFalse(executed, "Tool must not execute when Arden API is down (fail-closed)")


# ── LangChain sync (run) ──────────────────────────────────────────────────────

class TestLangChainRunPatch(unittest.TestCase):

    def setUp(self):
        _reset_autopatch("langchain")
        _configure()

    def tearDown(self):
        _reset_autopatch("langchain")
        _unconfigure()

    def test_run_allowed(self):
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_allow()):
                with patch("ardenpy.client.ArdenClient.close"):
                    result = tool.run("hello")
            self.assertEqual(result, "run:hello")
            self.assertIn(("run", "hello"), lc._executed)

    def test_run_blocked_tool_does_not_execute(self):
        from ardenpy.types import PolicyDeniedError
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_block()):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(PolicyDeniedError):
                        tool.run("hello")
            self.assertFalse(lc._executed, "Tool body must not run when blocked")

    def test_run_guarded_skips_policy_check(self):
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            setattr(tool, "_arden_guarded", True)
            check = MagicMock()
            with patch("ardenpy.client.ArdenClient.check_tool_call", check):
                result = tool.run("hello")
            self.assertEqual(result, "run:hello")
            check.assert_not_called()

    def test_run_fail_closed_when_arden_down(self):
        from ardenpy.types import ArdenError
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", side_effect=ArdenError("down")):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(ArdenError):
                        tool.run("hello")
            self.assertFalse(lc._executed, "Tool must not execute when Arden is down")


# ── LangChain async (arun) ────────────────────────────────────────────────────

class TestLangChainArunPatch(unittest.TestCase):
    """Regression: arun was previously unpatched and bypassed policy checks."""

    def setUp(self):
        _reset_autopatch("langchain")
        _configure()

    def tearDown(self):
        _reset_autopatch("langchain")
        _unconfigure()

    def test_arun_allowed(self):
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_allow()):
                with patch("ardenpy.client.ArdenClient.close"):
                    result = asyncio.run(tool.arun("hello"))
            self.assertEqual(result, "arun:hello")
            self.assertIn(("arun", "hello"), lc._executed)

    def test_arun_blocked_tool_does_not_execute(self):
        from ardenpy.types import PolicyDeniedError
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_block()):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(PolicyDeniedError):
                        asyncio.run(tool.arun("hello"))
            self.assertFalse(lc._executed, "Tool body must not run when blocked")

    def test_arun_approval_approved_executes(self):
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_requires_approval()):
                with patch("ardenpy.client.ArdenClient.wait_for_approval", return_value=_approved()):
                    with patch("ardenpy.client.ArdenClient.close"):
                        result = asyncio.run(tool.arun("hello"))
            self.assertEqual(result, "arun:hello")

    def test_arun_approval_denied_raises(self):
        from ardenpy.types import PolicyDeniedError
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_requires_approval()):
                with patch("ardenpy.client.ArdenClient.wait_for_approval", return_value=_denied()):
                    with patch("ardenpy.client.ArdenClient.close"):
                        with self.assertRaises(PolicyDeniedError):
                            asyncio.run(tool.arun("hello"))
            self.assertFalse(lc._executed)

    def test_arun_guarded_skips_policy_check(self):
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            setattr(tool, "_arden_guarded", True)
            check = MagicMock()
            with patch("ardenpy.client.ArdenClient.check_tool_call", check):
                result = asyncio.run(tool.arun("hello"))
            self.assertEqual(result, "arun:hello")
            check.assert_not_called()

    def test_arun_fail_closed_when_arden_down(self):
        from ardenpy.types import ArdenError
        import ardenpy._autopatch as ap
        with _FakeLangChainModules() as lc:
            ap._try_patch_langchain()
            tool = lc.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", side_effect=ArdenError("down")):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(ArdenError):
                        asyncio.run(tool.arun("hello"))
            self.assertFalse(lc._executed, "Tool must not execute when Arden is down")


# ── CrewAI (run + arun) ───────────────────────────────────────────────────────

class TestCrewAIPatch(unittest.TestCase):

    def setUp(self):
        _reset_autopatch("crewai")
        _configure()

    def tearDown(self):
        _reset_autopatch("crewai")
        _unconfigure()

    def test_run_allowed(self):
        import ardenpy._autopatch as ap
        with _FakeCrewAIModules() as crew:
            ap._try_patch_crewai()
            tool = crew.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_allow()):
                with patch("ardenpy.client.ArdenClient.close"):
                    result = tool.run("hello")
            self.assertEqual(result, "run:hello")

    def test_run_blocked(self):
        from ardenpy.types import PolicyDeniedError
        import ardenpy._autopatch as ap
        with _FakeCrewAIModules() as crew:
            ap._try_patch_crewai()
            tool = crew.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_block()):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(PolicyDeniedError):
                        tool.run("hello")
            self.assertFalse(crew._executed)

    def test_arun_allowed(self):
        import ardenpy._autopatch as ap
        with _FakeCrewAIModules() as crew:
            ap._try_patch_crewai()
            tool = crew.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_allow()):
                with patch("ardenpy.client.ArdenClient.close"):
                    result = asyncio.run(tool.arun("hello"))
            self.assertEqual(result, "arun:hello")

    def test_arun_blocked(self):
        from ardenpy.types import PolicyDeniedError
        import ardenpy._autopatch as ap
        with _FakeCrewAIModules() as crew:
            ap._try_patch_crewai()
            tool = crew.BaseTool()
            with patch("ardenpy.client.ArdenClient.check_tool_call", return_value=_block()):
                with patch("ardenpy.client.ArdenClient.close"):
                    with self.assertRaises(PolicyDeniedError):
                        asyncio.run(tool.arun("hello"))
            self.assertFalse(crew._executed)


# ── OpenAI Agents SDK: configure() order ─────────────────────────────────────

class TestOpenAIAgentsConfigureOrder(unittest.TestCase):
    """Tools created before configure() are NOT patched — known limitation."""

    def setUp(self):
        _reset_autopatch("openai-agents")
        _unconfigure()

    def tearDown(self):
        _reset_autopatch("openai-agents")
        _unconfigure()
        for k in ["agents", "agents.tool"]:
            sys.modules.pop(k, None)

    def test_tool_created_after_configure_is_patched(self):
        FunctionTool = _fake_agents_modules()
        import ardenpy._autopatch as ap
        _configure()
        ap._try_patch_openai_agents()

        original_fn = MagicMock()
        tool = FunctionTool(on_invoke_tool=original_fn)

        self.assertIsNot(
            tool.on_invoke_tool, original_fn,
            "Tool created after configure() must have its on_invoke_tool wrapped by Arden",
        )

    def test_tool_created_before_configure_is_not_patched(self):
        """Documents the known gap: tools built before configure() bypass Arden."""
        FunctionTool = _fake_agents_modules()

        original_fn = MagicMock()
        tool = FunctionTool(on_invoke_tool=original_fn)  # created BEFORE configure

        import ardenpy._autopatch as ap
        _configure()
        ap._try_patch_openai_agents()

        self.assertIs(
            tool.on_invoke_tool, original_fn,
            "Tool created before configure() keeps its original on_invoke_tool (known limitation)",
        )


if __name__ == "__main__":
    unittest.main()
