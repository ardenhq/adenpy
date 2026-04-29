"""Tests for session module."""

import pytest


class TestSession:

    def setup_method(self):
        from ardenpy.session import clear_session
        clear_session()

    def teardown_method(self):
        from ardenpy.session import clear_session
        clear_session()

    def test_default_is_none(self):
        from ardenpy.session import get_session
        assert get_session() is None

    def test_set_and_get_round_trip(self):
        from ardenpy.session import set_session, get_session
        set_session("conv_abc123")
        assert get_session() == "conv_abc123"

    def test_clear_removes_session(self):
        from ardenpy.session import set_session, get_session, clear_session
        set_session("some_session")
        clear_session()
        assert get_session() is None

    def test_overwrite_replaces_previous_value(self):
        from ardenpy.session import set_session, get_session
        set_session("first")
        set_session("second")
        assert get_session() == "second"

    def test_set_session_exposed_on_ardenpy_module(self):
        import ardenpy
        assert callable(ardenpy.set_session)
        assert callable(ardenpy.clear_session)

    def test_ardenpy_module_set_clear_round_trip(self):
        import ardenpy
        from ardenpy.session import get_session
        ardenpy.set_session("module_level_session")
        assert get_session() == "module_level_session"
        ardenpy.clear_session()
        assert get_session() is None
