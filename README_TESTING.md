# ArdenPy Testing Guide

## GitHub Actions Ready Test Suite

This repository includes a comprehensive test suite designed specifically for GitHub Actions CI/CD pipelines. The tests validate the core functionality of the ArdenPy library without requiring external API calls or manual approvals.

## Test Structure

### Core Test Files

- **`tests/test_basic.py`** - Main test suite with comprehensive coverage
- **`run_basic_tests.py`** - Test runner optimized for CI/CD
- **`.github/workflows/test.yml`** - GitHub Actions workflow configuration

### Test Coverage

The test suite covers:

✅ **Module Imports** - All core modules can be imported successfully
✅ **Configuration** - API key validation, environment settings, error handling
✅ **Type Definitions** - Enums, Pydantic models, exception classes
✅ **API Key Formats** - New `arden_live_` and `arden_test_` format validation
✅ **Guard Tool** - Function wrapping, serialization helpers
✅ **Client Basics** - Client creation and cleanup
✅ **Error Handling** - Proper exception propagation

## Running Tests

### Local Development

```bash
# Run the basic test suite
python run_basic_tests.py

# Run individual test modules
python -m unittest tests.test_basic

# Run with verbose output
python -m unittest tests.test_basic -v
```

### GitHub Actions

The tests automatically run on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Multiple Python versions: 3.8, 3.9, 3.10, 3.11, 3.12

## Test Results

**Latest Test Run: ✅ ALL TESTS PASSED**

```
ARDENPY BASIC TEST SUITE
======================================================================
Tests run: 21
Failures: 0
Errors: 0

✅ ALL BASIC TESTS PASSED!
ArdenPy library is ready for GitHub Actions!
```

## API Key Format Validation

The test suite validates the new API key formats:

- **Live Keys**: `arden_live_3e6159f645814adfa86b01f8c368d503`
- **Test Keys**: `arden_test_79ca7d77540646be88ce65f276adc32d`

## Key Features Tested

### 1. Configuration Management
- Basic configuration with API keys and URLs
- Environment-based configuration (live/test)
- Error handling for missing API keys
- Global configuration state management

### 2. Type System
- Enum definitions (`ActionStatus`, `PolicyDecision`)
- Pydantic model validation (`ToolCallRequest`, `ToolCallResponse`)
- Exception hierarchy (`ArdenError`, `PolicyDeniedError`, `ConfigurationError`)

### 3. Guard Tool Functionality
- Function wrapping without external dependencies
- Argument serialization helpers
- Configuration validation
- Error propagation

### 4. Client Basics
- Client instantiation with global configuration
- Proper cleanup and resource management

## CI/CD Integration

The test suite is designed to:
- ✅ Run without external dependencies
- ✅ Complete quickly (< 1 second)
- ✅ Provide clear pass/fail indicators
- ✅ Work across multiple Python versions
- ✅ Validate core library functionality

## Future Enhancements

For integration testing with live APIs, consider:
- Separate integration test suite with API mocking
- Environment-specific test configurations
- Performance benchmarking tests
- Security validation tests

## Troubleshooting

If tests fail:

1. **Import Errors**: Ensure all dependencies are installed via `requirements.txt`
2. **Configuration Errors**: Check that the global config is properly reset between tests
3. **Type Errors**: Verify Pydantic models match the actual implementation
4. **Path Issues**: Ensure the test runner can find the `ardenpy` package

## Contributing

When adding new features to ArdenPy:

1. Add corresponding tests to `tests/test_basic.py`
2. Ensure tests run without external dependencies
3. Update this documentation
4. Verify GitHub Actions workflow still passes
