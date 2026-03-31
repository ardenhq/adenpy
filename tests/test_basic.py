#!/usr/bin/env python3
"""
Basic test suite for ArdenPy library.
Designed for GitHub Actions CI/CD pipeline - focuses on core functionality without external dependencies.
"""

import unittest
import os
import sys

# Add the ardenpy package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestImports(unittest.TestCase):
    """Test that all modules can be imported successfully."""
    
    def test_import_ardenpy(self):
        """Test importing main ardenpy module."""
        import ardenpy
        self.assertTrue(hasattr(ardenpy, 'configure'))
        self.assertTrue(hasattr(ardenpy, 'guard_tool'))
    
    def test_import_config(self):
        """Test importing config module."""
        from ardenpy import configure, get_config, is_configured
        self.assertTrue(callable(configure))
        self.assertTrue(callable(get_config))
        self.assertTrue(callable(is_configured))
    
    def test_import_types(self):
        """Test importing types module."""
        from ardenpy.types import (
            ActionStatus,
            PolicyDecision,
            ToolCallRequest,
            ToolCallResponse,
            ArdenError,
            PolicyDeniedError
        )
        self.assertTrue(issubclass(ArdenError, Exception))
        self.assertTrue(issubclass(PolicyDeniedError, ArdenError))
    
    def test_import_client(self):
        """Test importing client module."""
        from ardenpy.client import ArdenClient
        self.assertTrue(callable(ArdenClient))
    
    def test_import_guard(self):
        """Test importing guard module."""
        from ardenpy.guard import guard_tool
        self.assertTrue(callable(guard_tool))


class TestConfiguration(unittest.TestCase):
    """Test configuration functionality."""
    
    def setUp(self):
        """Reset configuration before each test."""
        import ardenpy.config
        ardenpy.config._config = None
    
    def tearDown(self):
        """Clean up after each test."""
        import ardenpy.config
        ardenpy.config._config = None
    
    def test_configure_basic(self):
        """Test basic configuration."""
        from ardenpy import configure, is_configured, get_config
        
        config = configure(api_key="test_key", api_url="https://test.api.com")
        
        self.assertTrue(is_configured())
        retrieved_config = get_config()
        self.assertEqual(retrieved_config.api_key, "test_key")
        self.assertEqual(retrieved_config.api_url, "https://test.api.com")
    
    def test_configure_with_environment(self):
        """Test configuration with environment settings."""
        from ardenpy import configure, get_config
        
        # Test live environment
        config = configure(api_key="arden_live_123", environment="live")
        self.assertEqual(config.environment, "live")
        self.assertEqual(config.api_url, "https://api.arden.sh")
        
        # Test test environment
        config = configure(api_key="arden_test_456", environment="test")
        self.assertEqual(config.environment, "test")
        self.assertEqual(config.api_url, "https://api-test.arden.sh")
    
    def test_configure_missing_api_key(self):
        """Test that missing API key raises error."""
        from ardenpy import configure
        
        with self.assertRaises(ValueError) as context:
            configure()
        
        self.assertIn("API key is required", str(context.exception))
    
    def test_get_config_not_configured(self):
        """Test get_config when not configured."""
        from ardenpy import get_config, is_configured
        from ardenpy.types import ConfigurationError
        
        self.assertFalse(is_configured())
        
        with self.assertRaises(ConfigurationError):
            get_config()


class TestTypes(unittest.TestCase):
    """Test type definitions."""
    
    def test_action_status_enum(self):
        """Test ActionStatus enum."""
        from ardenpy.types import ActionStatus
        
        self.assertEqual(ActionStatus.PENDING.value, "pending")
        self.assertEqual(ActionStatus.APPROVED.value, "approved")
        self.assertEqual(ActionStatus.DENIED.value, "denied")
    
    def test_policy_decision_enum(self):
        """Test PolicyDecision enum."""
        from ardenpy.types import PolicyDecision
        
        self.assertEqual(PolicyDecision.ALLOW.value, "allow")
        self.assertEqual(PolicyDecision.BLOCK.value, "block")
        self.assertEqual(PolicyDecision.REQUIRE_APPROVAL.value, "requires_approval")
    
    def test_tool_call_request_creation(self):
        """Test ToolCallRequest model."""
        from ardenpy.types import ToolCallRequest
        
        request = ToolCallRequest(
            tool_name="test.tool",
            args=[1, 2, 3],
            kwargs={"key": "value"}
        )
        
        self.assertEqual(request.tool_name, "test.tool")
        self.assertEqual(request.args, [1, 2, 3])
        self.assertEqual(request.kwargs, {"key": "value"})
    
    def test_tool_call_response_creation(self):
        """Test ToolCallResponse model."""
        from ardenpy.types import ToolCallResponse, PolicyDecision
        
        response = ToolCallResponse(
            decision=PolicyDecision.ALLOW,
            message="Tool is allowed"
        )
        
        self.assertEqual(response.decision, PolicyDecision.ALLOW)
        self.assertEqual(response.message, "Tool is allowed")
    
    def test_exceptions(self):
        """Test exception classes."""
        from ardenpy.types import ArdenError, PolicyDeniedError, ApprovalTimeoutError
        
        # Test basic exception
        error = ArdenError("Test error")
        self.assertEqual(str(error), "Test error")
        
        # Test PolicyDeniedError
        denied_error = PolicyDeniedError("Access denied", tool_name="test.tool")
        self.assertEqual(str(denied_error), "Access denied")
        self.assertEqual(denied_error.tool_name, "test.tool")
        
        # Test inheritance
        self.assertIsInstance(denied_error, ArdenError)
        self.assertIsInstance(denied_error, Exception)


class TestAPIKeyFormats(unittest.TestCase):
    """Test API key format validation."""
    
    def setUp(self):
        """Reset configuration before each test."""
        import ardenpy.config
        ardenpy.config._config = None
    
    def tearDown(self):
        """Clean up after each test."""
        import ardenpy.config
        ardenpy.config._config = None
    
    def test_live_api_key_format(self):
        """Test live API key format."""
        from ardenpy import configure, get_config
        
        live_key = "arden_live_3e6159f645814adfa86b01f8c368d503"
        config = configure(api_key=live_key, api_url="https://api.arden.sh")
        
        self.assertTrue(live_key.startswith("arden_live_"))
        self.assertEqual(config.api_key, live_key)
    
    def test_test_api_key_format(self):
        """Test test API key format."""
        from ardenpy import configure, get_config
        
        test_key = "arden_test_79ca7d77540646be88ce65f276adc32d"
        config = configure(api_key=test_key, api_url="https://api-test.arden.sh")
        
        self.assertTrue(test_key.startswith("arden_test_"))
        self.assertEqual(config.api_key, test_key)


class TestGuardToolBasic(unittest.TestCase):
    """Test basic guard_tool functionality without external dependencies."""
    
    def setUp(self):
        """Set up test configuration."""
        from ardenpy import configure
        configure(api_key="test_key", api_url="https://test.api.com")
    
    def tearDown(self):
        """Clean up after tests."""
        import ardenpy.config
        ardenpy.config._config = None
    
    def test_guard_tool_not_configured_raises_error(self):
        """Test guard_tool raises error when not configured."""
        # Reset configuration
        import ardenpy.config
        ardenpy.config._config = None
        
        from ardenpy import guard_tool
        from ardenpy.types import ArdenError
        
        def test_function():
            return "test"
        
        with self.assertRaises(ArdenError) as context:
            guard_tool("test.tool", test_function)
        
        self.assertIn("configured", str(context.exception))
    
    def test_guard_tool_function_wrapping(self):
        """Test that guard_tool properly wraps functions."""
        from ardenpy import guard_tool
        
        def original_function(x, y):
            return x + y
        
        # This will fail when trying to make HTTP request, but we can test the wrapping
        protected_function = guard_tool("test.add", original_function)
        
        # Verify it's a callable
        self.assertTrue(callable(protected_function))
        
        # Verify function name is preserved
        self.assertEqual(protected_function.__name__, original_function.__name__)
    
    def test_serialization_helper(self):
        """Test the _make_serializable helper function."""
        from ardenpy.guard import _make_serializable
        
        # Test primitives
        self.assertEqual(_make_serializable(None), None)
        self.assertEqual(_make_serializable("string"), "string")
        self.assertEqual(_make_serializable(42), 42)
        self.assertEqual(_make_serializable(3.14), 3.14)
        self.assertEqual(_make_serializable(True), True)
        
        # Test collections
        self.assertEqual(_make_serializable([1, 2, 3]), [1, 2, 3])
        self.assertEqual(_make_serializable((1, 2, 3)), [1, 2, 3])  # Tuple -> List
        
        # Test dict
        input_dict = {"key": "value", "number": 42}
        result = _make_serializable(input_dict)
        self.assertEqual(result, {"key": "value", "number": 42})


class TestClientBasic(unittest.TestCase):
    """Test basic client functionality without making HTTP requests."""
    
    def test_client_creation(self):
        """Test ArdenClient can be created."""
        from ardenpy.client import ArdenClient
        from ardenpy import configure
        
        # Configure first, then create client
        configure(api_key="test_key", api_url="https://test.api.com")
        client = ArdenClient()
        
        # Should have config from global configuration
        self.assertEqual(client.config.api_key, "test_key")
    
    def test_client_close(self):
        """Test client close method."""
        from ardenpy.client import ArdenClient
        from ardenpy import configure
        
        # Configure first, then create client
        configure(api_key="test_key", api_url="https://test.api.com")
        client = ArdenClient()
        
        # Should not raise an error
        client.close()


if __name__ == '__main__':
    unittest.main()
