# Arden Configuration Guide

This guide explains how to configure Arden for different environments and use cases.

## Quick Start

```python
from ardenpy import configure

# Simple configuration - auto-detects test environment
configure(api_key="test_12345_your_test_api_key_here")
```

## API Endpoints

Arden automatically uses the correct API endpoint based on your environment:

- **Test Environment**: `https://test-api.arden.sh`
- **Live Environment**: `https://api.arden.sh`

## Environment Detection

Arden automatically detects your environment in several ways:

### 1. API Key Prefix (Recommended)
```python
# Test environment - API key starts with 'test_'
configure(api_key="test_12345_your_test_api_key_here")

# Live environment - any other API key
configure(api_key="live_67890_your_live_api_key_here")
```

### 2. Explicit Environment
```python
# Explicitly set test environment
configure(api_key="your_api_key", environment="test")

# Explicitly set live environment  
configure(api_key="your_api_key", environment="live")
```

### 3. Convenience Functions
```python
from ardenpy import configure_test, configure_live

# Test environment
configure_test("test_12345_your_test_api_key_here")

# Live environment
configure_live("live_67890_your_live_api_key_here")
```

## Environment Variables

You can also configure Arden using environment variables:

```bash
# Set your API key
export ARDEN_API_KEY="test_12345_your_test_api_key_here"

# Optionally set environment (defaults to 'live')
export ARDEN_ENVIRONMENT="test"

# Optionally override API URL
export ARDEN_API_URL="https://custom-api.arden.sh"
```

Then in your code:
```python
from ardenpy import configure

# Uses environment variables
configure()
```

## Configuration Options

```python
configure(
    api_key="your_api_key",           # Required: Your Arden API key
    environment="test",               # Optional: 'test' or 'live' (auto-detected)
    api_url="https://api.arden.sh",   # Optional: Custom API URL
    timeout=30.0,                     # Optional: Request timeout in seconds
    poll_interval=2.0,                # Optional: Polling interval for approvals
    max_poll_time=300.0,              # Optional: Max time to wait for approval
    retry_attempts=3                  # Optional: Number of retry attempts
)
```

## Development vs Production

### Development Setup
```python
from ardenpy import configure_test

# Use test API keys for development
configure_test("test_12345_your_test_api_key_here")

# Your development code here
```

### Production Setup
```python
from ardenpy import configure_live
import os

# Use live API keys for production
configure_live(os.getenv("ARDEN_API_KEY"))

# Your production code here
```

## Getting API Keys

1. Visit [https://arden.dev](https://arden.dev)
2. Sign up for an account
3. Generate test keys for development
4. Generate live keys for production

Test keys start with `test_` and are free for development and testing.
Live keys are for production use and require a paid plan.

## Troubleshooting

### Wrong Environment
If you're using the wrong environment, check:
- API key prefix (`test_` for test environment)
- Environment variable `ARDEN_ENVIRONMENT`
- Explicit `environment` parameter

### Connection Issues
If you can't connect to the API:
- Verify your API key is correct
- Check your internet connection
- Ensure you're using the correct API URL
- Check if there are any firewall restrictions

### Configuration Errors
```python
from ardenpy import get_config

# Check current configuration
config = get_config()
print(f"Environment: {config.environment}")
print(f"API URL: {config.api_url}")
```
