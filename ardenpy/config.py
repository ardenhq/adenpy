"""Configuration management for Arden SDK."""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator


class ArdenConfig(BaseModel):
    """Configuration for Arden SDK."""
    api_key: str = Field(..., description="API key for Arden service")
    api_url: str = Field(default="https://api.arden.sh", description="Base URL for Arden API")
    environment: str = Field(default="live", description="Environment: 'test' or 'live'")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    poll_interval: float = Field(default=2.0, description="Polling interval for approvals")
    max_poll_time: float = Field(default=300.0, description="Maximum time to wait for approval")
    retry_attempts: int = Field(default=3, description="Number of retry attempts for API calls")
    signing_key: Optional[str] = Field(default=None, description="Webhook signing key for verifying incoming webhook payloads")
    
    @validator('api_url')
    def validate_api_url(cls, v):
        """Validate that API URL is properly formatted."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('API URL must start with http:// or https://')
        return v.rstrip('/')
    
    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment is test or live."""
        if v not in ('test', 'live'):
            raise ValueError('Environment must be "test" or "live"')
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout is positive."""
        if v <= 0:
            raise ValueError('Timeout must be positive')
        return v
    
    @validator('poll_interval')
    def validate_poll_interval(cls, v):
        """Validate poll interval is positive."""
        if v <= 0:
            raise ValueError('Poll interval must be positive')
        return v


# Global configuration instance
_config: Optional[ArdenConfig] = None


def configure(
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    environment: Optional[str] = None,
    timeout: Optional[float] = None,
    poll_interval: Optional[float] = None,
    max_poll_time: Optional[float] = None,
    retry_attempts: Optional[int] = None,
    signing_key: Optional[str] = None,
) -> ArdenConfig:
    """Configure Arden SDK.
    
    Args:
        api_key: API key for Arden service. Can also be set via ARDEN_API_KEY env var.
        api_url: Base URL for Arden API (defaults to hosted service).
        environment: Environment to use ('test' or 'live'). Automatically sets correct API URL.
        timeout: Request timeout in seconds.
        poll_interval: Polling interval for approvals in seconds.
        max_poll_time: Maximum time to wait for approval in seconds.
        retry_attempts: Number of retry attempts for API calls.
        
    Returns:
        Configured ArdenConfig instance.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    global _config
    
    # Get values from environment if not provided
    api_key = api_key or os.getenv('ARDEN_API_KEY')
    environment = environment or os.getenv('ARDEN_ENVIRONMENT', 'live')
    
    # Auto-detect test environment from API key prefix
    if api_key and api_key.startswith('test_'):
        environment = 'test'
    
    # Set API URL based on environment if not explicitly provided
    if api_url is None:
        api_url = os.getenv('ARDEN_API_URL')
        if api_url is None:
            if environment == 'test':
                api_url = 'https://api-test.arden.sh'
            else:
                api_url = 'https://api.arden.sh'
    
    if not api_key:
        raise ValueError(
            "API key is required. Set it via configure(api_key=...) or "
            "ARDEN_API_KEY environment variable. Get your API key at https://arden.dev"
        )
    
    # Create configuration with provided values
    config_dict = {
        'api_key': api_key,
        'api_url': api_url,
        'environment': environment
    }
    
    if timeout is not None:
        config_dict['timeout'] = timeout
    if poll_interval is not None:
        config_dict['poll_interval'] = poll_interval
    if max_poll_time is not None:
        config_dict['max_poll_time'] = max_poll_time
    if retry_attempts is not None:
        config_dict['retry_attempts'] = retry_attempts
    if signing_key is not None:
        config_dict['signing_key'] = signing_key

    _config = ArdenConfig(**config_dict)

    # Auto-patch installed frameworks so tool calls are intercepted without
    # any explicit wrapping.  Failures are swallowed — a broken framework
    # import should never prevent configure() from succeeding.
    try:
        from . import _autopatch
        patched = _autopatch.patch_all()
        if patched:
            import logging as _logging
            _logging.getLogger(__name__).debug(
                "Arden: auto-patched frameworks: %s", ", ".join(patched)
            )
    except Exception:
        pass

    return _config


def get_config() -> ArdenConfig:
    """Get current Arden configuration.
    
    Returns:
        Current ArdenConfig instance.
        
    Raises:
        ConfigurationError: If SDK is not configured.
    """
    global _config
    
    if _config is None:
        from .types import ConfigurationError
        raise ConfigurationError(
            "Arden is not configured. Call configure() first."
        )
    
    return _config


def is_configured() -> bool:
    """Check if Arden SDK is configured.
    
    Returns:
        True if configured, False otherwise.
    """
    global _config
    return _config is not None


def configure_test(api_key: str, **kwargs) -> ArdenConfig:
    """Configure Arden SDK for test environment.
    
    Args:
        api_key: Test API key (should start with 'test_').
        **kwargs: Additional configuration options.
        
    Returns:
        Configured ArdenConfig instance for testing.
    """
    return configure(api_key=api_key, environment='test', **kwargs)


def configure_live(api_key: str, **kwargs) -> ArdenConfig:
    """Configure Arden SDK for live/production environment.
    
    Args:
        api_key: Live API key.
        **kwargs: Additional configuration options.
        
    Returns:
        Configured ArdenConfig instance for production.
    """
    return configure(api_key=api_key, environment='live', **kwargs)
