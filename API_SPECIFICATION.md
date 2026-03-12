# Arden REST API Specification

This document defines the REST API that backends must implement to work with the Arden Python SDK, including support for the hybrid approval workflow modes.

## Base URL
- **Test Environment**: `https://api-test.arden.sh`
- **Production Environment**: `https://api.arden.sh`

## Authentication
All requests must include:
```
Authorization: Bearer {api_key}
Content-Type: application/json
User-Agent: Arden-SDK/0.1.0
```

## Core Endpoints

### 1. Policy Check
**Endpoint**: `POST /check`  
**Purpose**: Check if a tool call is allowed by policy

**Request Body**:
```json
{
  "tool_name": "string",           // Required: Name of the tool being called
  "args": ["any"],                 // Optional: Positional arguments (default: [])
  "kwargs": {"key": "value"},      // Optional: Keyword arguments (default: {})
  "metadata": {"optional": "data"}, // Optional: Additional metadata
  "webhook_url": "string"          // Optional: Webhook URL for webhook mode
}
```

**Response**:
```json
{
  "decision": "allow|requires_approval|block", // Required: Policy decision
  "action_id": "string|null",                  // Required for requires_approval
  "message": "string|null"                     // Optional: Human-readable message
}
```

**Status Codes**:
- `200`: Policy check successful
- `400`: Invalid request format
- `401`: Invalid API key
- `403`: API key lacks permissions
- `500`: Internal server error

### 2. Action Status
**Endpoint**: `GET /status/{action_id}`  
**Purpose**: Get current status of an action

**Path Parameters**:
- `action_id`: String identifier for the action

**Response**:
```json
{
  "action_id": "string",                    // Action identifier
  "status": "pending|approved|denied",     // Current status
  "message": "string|null",                // Optional status message
  "created_at": "2024-03-11T16:30:00Z"    // ISO8601 timestamp
}
```

**Status Codes**:
- `200`: Status retrieved successfully
- `401`: Invalid API key
- `404`: Action not found
- `500`: Internal server error

### 3. Approve Action
**Endpoint**: `POST /approve/{action_id}`  
**Purpose**: Approve a pending action

**Path Parameters**:
- `action_id`: String identifier for the action

**Request Body**:
```json
{
  "message": "string|null" // Optional approval message
}
```

**Response**: Empty body with status code

**Status Codes**:
- `200`: Action approved successfully
- `400`: Action cannot be approved (wrong status)
- `401`: Invalid API key
- `403`: Insufficient permissions
- `404`: Action not found
- `500`: Internal server error

### 4. Deny Action
**Endpoint**: `POST /deny/{action_id}`  
**Purpose**: Deny a pending action

**Path Parameters**:
- `action_id`: String identifier for the action

**Request Body**:
```json
{
  "message": "string|null" // Optional denial message
}
```

**Response**: Empty body with status code

**Status Codes**:
- `200`: Action denied successfully
- `400`: Action cannot be denied (wrong status)
- `401`: Invalid API key
- `403`: Insufficient permissions
- `404`: Action not found
- `500`: Internal server error

## Webhook Support

### Webhook Registration
When a tool call is made with `approval_mode="webhook"`, the SDK includes a `webhook_url` in the `/check` request. The backend should:

1. Store the webhook URL with the action
2. When the action is approved/denied, send a POST request to the webhook URL

### Webhook Payload
When an action is approved or denied, the backend sends:

**Endpoint**: `POST {webhook_url}`  
**Headers**:
```
Content-Type: application/json
User-Agent: Arden-Backend/1.0
X-Arden-Signature: {hmac_signature}  // Optional: for webhook verification
```

**Payload**:
```json
{
  "action_id": "string",                    // Action identifier
  "status": "approved|denied",             // Final status
  "message": "string|null",                // Optional message
  "tool_name": "string",                   // Original tool name
  "timestamp": "2024-03-11T16:30:00Z",    // Decision timestamp
  "args": ["any"],                         // Original arguments
  "kwargs": {"key": "value"},              // Original keyword arguments
  "metadata": {"optional": "data"}         // Original metadata
}
```

### Webhook Response
The webhook endpoint should respond with:
- `200 OK`: Webhook processed successfully
- `4xx/5xx`: Error processing webhook (backend may retry)

## Error Response Format

All error responses should follow this format:
```json
{
  "error": {
    "code": "string",        // Error code (e.g., "invalid_request")
    "message": "string",     // Human-readable error message
    "details": "object|null" // Optional additional error details
  }
}
```

## SDK Approval Mode Behaviors

### Wait Mode (Default)
1. SDK calls `POST /check`
2. If `requires_approval`, SDK polls `GET /status/{action_id}` every 2 seconds
3. When status changes to `approved`/`denied`, SDK proceeds accordingly

### Async Mode
1. SDK calls `POST /check`
2. If `requires_approval`, SDK starts background thread to poll `GET /status/{action_id}`
3. When status changes, SDK calls appropriate callback function
4. Original function call returns `None` immediately

### Webhook Mode
1. SDK calls `POST /check` with `webhook_url`
2. If `requires_approval`, SDK returns `None` immediately
3. Backend stores webhook URL and sends notification when action is decided
4. User's webhook handler processes the notification and executes/handles the function

## Implementation Notes

### API Key Format
- Test keys: Start with `test_` (e.g., `test_12345_abc...`)
- Live keys: Any other format (e.g., `live_67890_xyz...`)

### Action ID Format
- Should be unique, URL-safe strings
- Recommended: UUIDs or similar (e.g., `act_1234567890abcdef`)

### Timestamps
- Use ISO8601 format with UTC timezone
- Example: `2024-03-11T16:30:00Z`

### Rate Limiting
- Recommended: 100 requests per minute per API key
- Return `429 Too Many Requests` when exceeded

### Webhook Security
- Include `X-Arden-Signature` header with HMAC signature for verification
- Use HTTPS for webhook URLs
- Implement webhook retry logic with exponential backoff

### CORS Headers
If supporting web clients, include:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Authorization, Content-Type
```

## AWS API Gateway Implementation

### Lambda Function Structure
```
/check          -> PolicyCheckFunction
/status/{id}    -> ActionStatusFunction  
/approve/{id}   -> ApproveActionFunction
/deny/{id}      -> DenyActionFunction
```

### Required AWS Services
- **API Gateway**: REST API endpoints
- **Lambda**: Business logic functions
- **DynamoDB**: Store actions, policies, and webhook URLs
- **SQS**: Queue webhook notifications (optional)
- **IAM**: API key authentication
- **CloudWatch**: Logging and monitoring

### Database Schema (DynamoDB)

**Actions Table**:
```
action_id (PK): String
status: String (pending|approved|denied)
tool_name: String
args: List
kwargs: Map
metadata: Map
webhook_url: String (optional)
created_at: String
updated_at: String
message: String (optional)
api_key: String (for authorization)
```

**Policies Table**:
```
tool_name (PK): String
decision: String (allow|requires_approval|block)
conditions: Map (optional)
created_at: String
api_key (GSI): String (for user-specific policies)
```

**API Keys Table**:
```
api_key (PK): String
user_id: String
environment: String (test|live)
permissions: List
created_at: String
last_used: String
```

### Webhook Implementation
```python
# Lambda function for sending webhooks
import json
import boto3
import requests
from datetime import datetime

def send_webhook(action_id, status, message=None):
    # Get action details from DynamoDB
    action = get_action_from_db(action_id)
    
    if not action.get('webhook_url'):
        return  # No webhook configured
    
    payload = {
        "action_id": action_id,
        "status": status,
        "message": message,
        "tool_name": action['tool_name'],
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "args": action['args'],
        "kwargs": action['kwargs'],
        "metadata": action.get('metadata', {})
    }
    
    try:
        response = requests.post(
            action['webhook_url'],
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Arden-Backend/1.0'
            },
            timeout=30
        )
        response.raise_for_status()
        
    except Exception as e:
        # Log error and potentially retry
        print(f"Webhook failed for {action_id}: {e}")
        # Could add to SQS for retry
```

### Example Policy Check Lambda
```python
import json
import boto3
from datetime import datetime
import uuid

def lambda_handler(event, context):
    try:
        # Parse request
        body = json.loads(event['body'])
        tool_name = body['tool_name']
        args = body.get('args', [])
        kwargs = body.get('kwargs', {})
        metadata = body.get('metadata', {})
        webhook_url = body.get('webhook_url')
        
        # Get API key from headers
        api_key = event['headers'].get('Authorization', '').replace('Bearer ', '')
        
        # Validate API key
        if not validate_api_key(api_key):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': {'code': 'invalid_api_key', 'message': 'Invalid API key'}})
            }
        
        # Check policy
        policy_decision = check_policy(tool_name, api_key)
        
        if policy_decision == 'allow':
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'decision': 'allow',
                    'action_id': None,
                    'message': 'Tool call allowed by policy'
                })
            }
        
        elif policy_decision == 'requires_approval':
            # Create action record
            action_id = f"act_{uuid.uuid4().hex}"
            
            create_action({
                'action_id': action_id,
                'status': 'pending',
                'tool_name': tool_name,
                'args': args,
                'kwargs': kwargs,
                'metadata': metadata,
                'webhook_url': webhook_url,
                'api_key': api_key,
                'created_at': datetime.utcnow().isoformat()
            })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'decision': 'requires_approval',
                    'action_id': action_id,
                    'message': 'Tool call requires approval'
                })
            }
        
        else:  # block
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'decision': 'block',
                    'action_id': None,
                    'message': 'Tool call blocked by policy'
                })
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': {'code': 'internal_error', 'message': str(e)}})
        }
```

This specification provides everything needed to implement a complete Arden backend with support for all three approval modes: wait, async, and webhook.
