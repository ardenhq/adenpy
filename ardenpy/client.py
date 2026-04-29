"""HTTP client for Arden API communication."""

import time
import json
import logging
from typing import Any, Dict, List, Optional, Union
import httpx

from .config import get_config
from .types import (
    ToolCallRequest,
    ToolCallResponse,
    ActionStatusResponse,
    ApprovalRequest,
    PolicyDecision,
    ActionStatus,
    ConfigurationError,
    ArdenError,
    ApprovalTimeoutError,
)


logger = logging.getLogger(__name__)


class ArdenClient:
    """HTTP client for communicating with Arden API."""
    
    def __init__(self):
        """Initialize the client with current configuration."""
        self.config = get_config()
        self._client = httpx.Client(timeout=self.config.timeout)
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to AgentGuard API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            ArdenError: If request fails
        """
        url = f"{self.config.api_url}{endpoint}"
        
        # Add API key to headers
        headers = {
            "X-API-Key": self.config.api_key,
            "Content-Type": "application/json",
            "User-Agent": "Arden-SDK/0.1.0"
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise ArdenError(f"API request failed: {e}")
                time.sleep(1)  # Simple backoff
            
            except httpx.RequestError as e:
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise ArdenError(f"API request failed: {e}")
                time.sleep(1)
        
        raise ArdenError("Max retry attempts exceeded")
    
    def check_tool_call(
        self,
        tool_name: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolCallResponse:
        """Check if a tool call is allowed by policy.
        
        Args:
            tool_name: Name of the tool being called
            args: Positional arguments
            kwargs: Keyword arguments
            metadata: Additional metadata
            
        Returns:
            Tool call policy decision
            
        Raises:
            AgentGuardError: If API request fails
        """
        request_data = ToolCallRequest(
            tool_name=tool_name,
            args=args,
            kwargs=kwargs,
            metadata=metadata,
        )
        
        try:
            response_data = self._make_request(
                method="POST",
                endpoint="/policy/check",
                data=request_data.dict(),
            )
            return ToolCallResponse(**response_data)
        
        except Exception as e:
            logger.error(f"Failed to check tool call policy: {e}")
            raise ArdenError(f"Policy check failed: {e}")
    
    def get_action_status(self, action_id: str) -> ActionStatusResponse:
        """Get status of an action.
        
        Args:
            action_id: Action identifier
            
        Returns:
            Current action status
            
        Raises:
            AgentGuardError: If API request fails
        """
        try:
            response_data = self._make_request(
                method="GET",
                endpoint=f"/status/{action_id}",
            )
            return ActionStatusResponse(**response_data)
        
        except Exception as e:
            logger.error(f"Failed to get action status: {e}")
            raise ArdenError(f"Status check failed: {e}")
    
    def wait_for_approval(
        self,
        action_id: str,
        timeout: Optional[float] = None,
    ) -> ActionStatusResponse:
        """Wait for an action to be approved or denied.
        
        Args:
            action_id: Action identifier
            timeout: Maximum time to wait (uses config default if None)
            
        Returns:
            Final action status
            
        Raises:
            ApprovalTimeoutError: If timeout is reached
            AgentGuardError: If API request fails
        """
        if timeout is None:
            timeout = self.config.max_poll_time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_action_status(action_id)
                
                if status.status in (ActionStatus.APPROVED, ActionStatus.DENIED):
                    return status
                
                logger.debug(f"Action {action_id} still {status.status}, waiting...")
                time.sleep(self.config.poll_interval)
            
            except Exception as e:
                logger.error(f"Error checking approval status: {e}")
                time.sleep(self.config.poll_interval)
        
        raise ApprovalTimeoutError(action_id, timeout)
    
    def approve_action(self, action_id: str, message: Optional[str] = None) -> bool:
        """Approve an action.
        
        Args:
            action_id: Action identifier
            message: Optional approval message
            
        Returns:
            True if approval was successful
            
        Raises:
            AgentGuardError: If API request fails
        """
        request_data = ApprovalRequest(message=message)
        
        try:
            self._make_request(
                method="POST",
                endpoint=f"/approve/{action_id}",
                data=request_data.dict(),
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to approve action: {e}")
            raise ArdenError(f"Approval failed: {e}")
    
    def deny_action(self, action_id: str, message: Optional[str] = None) -> bool:
        """Deny an action.
        
        Args:
            action_id: Action identifier
            message: Optional denial message
            
        Returns:
            True if denial was successful
            
        Raises:
            AgentGuardError: If API request fails
        """
        request_data = ApprovalRequest(message=message)
        
        try:
            self._make_request(
                method="POST",
                endpoint=f"/deny/{action_id}",
                data=request_data.dict(),
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to deny action: {e}")
            raise ArdenError(f"Denial failed: {e}")
    
    def log_token_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Log token usage for an LLM call.

        Args:
            model:             Model name, e.g. "gpt-4o".
            prompt_tokens:     Input token count.
            completion_tokens: Output token count.
            session_id:        Optional session ID.

        Returns:
            Response dict with usage_id, total_tokens, total_cost_usd.
        """
        payload: Dict[str, Any] = {
            "model":             model,
            "prompt_tokens":     prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        if session_id:
            payload["session_id"] = session_id

        try:
            return self._make_request(method="POST", endpoint="/token-usage", data=payload)
        except Exception as e:
            logger.debug(f"Token usage logging failed (non-fatal): {e}")
            return {}

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
