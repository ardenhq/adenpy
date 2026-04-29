"""Tests for token_usage module."""

import pytest
from unittest.mock import MagicMock, patch
import ardenpy.config as _cfg


@pytest.fixture(autouse=True)
def reset_config():
    _cfg._config = None
    yield
    _cfg._config = None


# ---------------------------------------------------------------------------
# log_token_usage (public function)
# ---------------------------------------------------------------------------

class TestLogTokenUsage:

    def test_does_nothing_when_not_configured(self):
        from ardenpy.token_usage import log_token_usage
        # Should not raise even though Arden is not configured
        with patch("threading.Thread") as mock_thread:
            log_token_usage("gpt-4o", 100, 50)
        mock_thread.assert_not_called()

    def test_spawns_background_thread_when_configured(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")
        from ardenpy.token_usage import log_token_usage

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            log_token_usage("gpt-4o", 100, 50)

        mock_thread_cls.assert_called_once()
        mock_thread.start.assert_called_once()

    def test_uses_session_from_context_when_no_session_id_arg(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")
        ardenpy.set_session("sess_from_context")

        from ardenpy.token_usage import log_token_usage
        captured_args = {}

        def fake_thread_init(target, args, daemon):
            captured_args["args"] = args
            return MagicMock()

        with patch("threading.Thread", side_effect=fake_thread_init):
            log_token_usage("gpt-4o", 10, 5)

        # args = (model, prompt_tokens, completion_tokens, session_id)
        assert captured_args["args"][3] == "sess_from_context"
        ardenpy.clear_session()

    def test_explicit_session_id_overrides_context(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")
        ardenpy.set_session("context_session")

        from ardenpy.token_usage import log_token_usage
        captured_args = {}

        def fake_thread_init(target, args, daemon):
            captured_args["args"] = args
            return MagicMock()

        with patch("threading.Thread", side_effect=fake_thread_init):
            log_token_usage("gpt-4o", 10, 5, session_id="explicit_session")

        assert captured_args["args"][3] == "explicit_session"
        ardenpy.clear_session()

    def test_no_session_when_none_set(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")

        from ardenpy.token_usage import log_token_usage
        captured_args = {}

        def fake_thread_init(target, args, daemon):
            captured_args["args"] = args
            return MagicMock()

        with patch("threading.Thread", side_effect=fake_thread_init):
            log_token_usage("gpt-4o", 10, 5)

        assert captured_args["args"][3] is None


# ---------------------------------------------------------------------------
# _send_usage
# ---------------------------------------------------------------------------

class TestSendUsage:

    def test_calls_client_log_token_usage(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")

        from ardenpy.token_usage import _send_usage

        mock_client = MagicMock()
        mock_client.log_token_usage.return_value = {"usage_id": "u_1"}

        with patch("ardenpy.client.ArdenClient", return_value=mock_client):
            _send_usage("gpt-4o", 100, 50, "sess_1")

        mock_client.log_token_usage.assert_called_once_with(
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            session_id="sess_1",
        )
        mock_client.close.assert_called_once()

    def test_closes_client_even_on_exception(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")

        from ardenpy.token_usage import _send_usage

        mock_client = MagicMock()
        mock_client.log_token_usage.side_effect = Exception("network error")

        with patch("ardenpy.client.ArdenClient", return_value=mock_client):
            # Should not raise
            _send_usage("gpt-4o", 10, 5, None)

        mock_client.close.assert_called_once()

    def test_swallows_client_creation_error(self):
        import ardenpy
        ardenpy.configure(api_key="arden_test_key", api_url="https://api-test.arden.sh")

        from ardenpy.token_usage import _send_usage

        with patch("ardenpy.client.ArdenClient", side_effect=Exception("config error")):
            # Should not raise
            _send_usage("gpt-4o", 10, 5, None)


# ---------------------------------------------------------------------------
# _extract_langchain_usage
# ---------------------------------------------------------------------------

class TestExtractLangchainUsage:

    def _make_result(self, llm_output=None, generations=None):
        result = MagicMock()
        result.llm_output = llm_output or {}
        result.generations = generations or []
        return result

    def test_extracts_openai_token_usage(self):
        from ardenpy.token_usage import _extract_langchain_usage
        response = self._make_result(llm_output={
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "model_name": "gpt-4o",
        })
        usage = _extract_langchain_usage(response)
        assert usage == {"model": "gpt-4o", "prompt_tokens": 100, "completion_tokens": 50}

    def test_extracts_usage_key_as_fallback(self):
        from ardenpy.token_usage import _extract_langchain_usage
        response = self._make_result(llm_output={
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            "model": "claude-sonnet-4-6",
        })
        usage = _extract_langchain_usage(response)
        assert usage["prompt_tokens"] == 20
        assert usage["completion_tokens"] == 10
        assert usage["model"] == "claude-sonnet-4-6"

    def test_uses_input_output_tokens_when_prompt_completion_missing(self):
        from ardenpy.token_usage import _extract_langchain_usage
        response = self._make_result(llm_output={
            "token_usage": {"input_tokens": 30, "output_tokens": 15},
            "model_name": "gpt-4",
        })
        usage = _extract_langchain_usage(response)
        assert usage["prompt_tokens"] == 30
        assert usage["completion_tokens"] == 15

    def test_returns_unknown_model_when_missing(self):
        from ardenpy.token_usage import _extract_langchain_usage
        response = self._make_result(llm_output={
            "token_usage": {"prompt_tokens": 5, "completion_tokens": 3},
        })
        usage = _extract_langchain_usage(response)
        assert usage["model"] == "unknown"

    def test_returns_none_when_no_usage_data(self):
        from ardenpy.token_usage import _extract_langchain_usage
        response = self._make_result(llm_output={})
        response.generations = []
        usage = _extract_langchain_usage(response)
        assert usage is None

    def test_extracts_usage_metadata_from_generation(self):
        from ardenpy.token_usage import _extract_langchain_usage

        gen = MagicMock()
        gen.generation_info = {"model": "gpt-4o-mini"}
        gen.usage_metadata = {"input_tokens": 40, "output_tokens": 20}

        response = self._make_result()
        response.llm_output = {}
        response.generations = [[gen]]

        usage = _extract_langchain_usage(response)
        assert usage["model"] == "gpt-4o-mini"
        assert usage["prompt_tokens"] == 40
        assert usage["completion_tokens"] == 20

    def test_returns_none_when_generation_has_no_usage_metadata(self):
        from ardenpy.token_usage import _extract_langchain_usage

        gen = MagicMock()
        gen.generation_info = {}
        gen.usage_metadata = None

        response = self._make_result()
        response.llm_output = {}
        response.generations = [[gen]]

        usage = _extract_langchain_usage(response)
        assert usage is None


# ---------------------------------------------------------------------------
# ArdenTokenUsageCallback (lazy export)
# ---------------------------------------------------------------------------

class TestArdenTokenUsageCallback:

    def test_attribute_error_when_langchain_not_installed(self):
        from ardenpy import token_usage
        import sys

        # Temporarily remove langchain_core and langchain from sys.modules
        saved = {}
        for key in list(sys.modules.keys()):
            if "langchain" in key:
                saved[key] = sys.modules.pop(key)
        try:
            with pytest.raises((ImportError, AttributeError)):
                _ = token_usage.ArdenTokenUsageCallback
        finally:
            sys.modules.update(saved)
