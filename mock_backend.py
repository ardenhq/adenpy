"""
Mock Arden Backend for Local Development

This provides a local mock server that simulates the Arden API
for testing and development without requiring the hosted service.

Usage:
    python mock_backend.py

Then configure your SDK to use: http://localhost:8000
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import time
import json
import random
from datetime import datetime

app = FastAPI(
    title="Arden Mock API",
    description="Local mock backend for Arden development and testing",
    version="0.1.0"
)

# In-memory storage for mock data
actions_db: Dict[str, Dict] = {}
policies_db: List[Dict] = []

# Default policies for testing
DEFAULT_POLICIES = [
    {
        "id": "policy_1",
        "name": "Safe Operations",
        "tool": "web.search",
        "action": "allow",
        "description": "Allow web searches immediately"
    },
    {
        "id": "policy_2", 
        "name": "File Read",
        "tool": "file.read",
        "action": "allow",
        "description": "Allow file reading"
    },
    {
        "id": "policy_3",
        "name": "Math Operations",
        "tool": "math.calculate",
        "action": "allow", 
        "description": "Allow mathematical calculations"
    },
    {
        "id": "policy_4",
        "name": "File Write",
        "tool": "file.write",
        "action": "require_approval",
        "description": "File writing requires approval",
        "timeout": 300
    },
    {
        "id": "policy_5",
        "name": "Email Sending",
        "tool": "communication.email",
        "action": "require_approval",
        "description": "Email sending requires approval",
        "timeout": 600
    },
    {
        "id": "policy_6",
        "name": "File Deletion",
        "tool": "file.delete",
        "action": "require_approval",
        "description": "File deletion requires approval",
        "timeout": 600
    },
    {
        "id": "policy_7",
        "name": "System Commands",
        "tool": "system.execute",
        "action": "block",
        "description": "System command execution is blocked"
    },
    {
        "id": "policy_8",
        "name": "Code Execution",
        "tool": "code.execute",
        "action": "block",
        "description": "Code execution is blocked for security"
    }
]

# Initialize with default policies
policies_db.extend(DEFAULT_POLICIES)

# Request/Response Models
class PolicyCheckRequest(BaseModel):
    tool_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class PolicyCheckResponse(BaseModel):
    decision: str  # "allow", "require_approval", "block"
    action_id: Optional[str] = None
    message: Optional[str] = None
    timeout: Optional[int] = None

class ApprovalRequest(BaseModel):
    action_id: str
    approved: bool
    reason: Optional[str] = None

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Arden Mock API",
        "version": "0.1.0",
        "status": "running",
        "mode": "development"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "arden-mock",
        "timestamp": datetime.now().isoformat(),
        "uptime": "mock"
    }

@app.post("/check", response_model=PolicyCheckResponse)
async def check_policy(request: PolicyCheckRequest):
    """Check if a tool call is allowed by policy."""
    
    print(f"🔍 Policy check for tool: {request.tool_name}")
    
    # Find matching policy
    matching_policy = None
    for policy in policies_db:
        if policy["tool"] == request.tool_name:
            matching_policy = policy
            break
    
    # Default policy if no match found
    if not matching_policy:
        print(f"⚠️ No policy found for {request.tool_name}, using default: require_approval")
        decision = "require_approval"
        action_id = f"action_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Store action for approval workflow
        actions_db[action_id] = {
            "id": action_id,
            "tool_name": request.tool_name,
            "args": request.args,
            "kwargs": request.kwargs,
            "metadata": request.metadata,
            "status": "pending",
            "created_at": time.time(),
            "decision": decision
        }
        
        return PolicyCheckResponse(
            decision=decision,
            action_id=action_id,
            message=f"No specific policy found for {request.tool_name}. Approval required.",
            timeout=300
        )
    
    decision = matching_policy["action"]
    print(f"✅ Policy decision: {decision}")
    
    if decision == "allow":
        return PolicyCheckResponse(
            decision="allow",
            message=f"Tool {request.tool_name} is allowed by policy"
        )
    
    elif decision == "block":
        return PolicyCheckResponse(
            decision="block",
            message=f"Tool {request.tool_name} is blocked by policy: {matching_policy.get('description', 'No reason provided')}"
        )
    
    elif decision == "require_approval":
        action_id = f"action_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Store action for approval workflow
        actions_db[action_id] = {
            "id": action_id,
            "tool_name": request.tool_name,
            "args": request.args,
            "kwargs": request.kwargs,
            "metadata": request.metadata,
            "status": "pending",
            "created_at": time.time(),
            "policy_id": matching_policy["id"],
            "decision": decision
        }
        
        return PolicyCheckResponse(
            decision="require_approval",
            action_id=action_id,
            message=f"Tool {request.tool_name} requires approval: {matching_policy.get('description', 'Approval needed')}",
            timeout=matching_policy.get("timeout", 300)
        )
    
    else:
        raise HTTPException(status_code=500, detail=f"Unknown policy decision: {decision}")

@app.get("/status/{action_id}")
async def get_action_status(action_id: str):
    """Get the status of an action awaiting approval."""
    
    if action_id not in actions_db:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action = actions_db[action_id]
    
    # Simulate auto-approval for demo purposes (10% chance every call)
    if action["status"] == "pending" and random.random() < 0.1:
        action["status"] = "approved"
        action["approved_at"] = time.time()
        action["approved_by"] = "auto-demo"
        print(f"🎲 Auto-approved action {action_id} for demo")
    
    return {
        "action_id": action_id,
        "status": action["status"],
        "tool_name": action["tool_name"],
        "created_at": action["created_at"],
        "approved_at": action.get("approved_at"),
        "approved_by": action.get("approved_by"),
        "reason": action.get("reason")
    }

@app.post("/approve/{action_id}")
async def approve_action(action_id: str, request: ApprovalRequest):
    """Approve or deny an action."""
    
    if action_id not in actions_db:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action = actions_db[action_id]
    
    if action["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action['status']}")
    
    if request.approved:
        action["status"] = "approved"
        action["approved_at"] = time.time()
        action["approved_by"] = "manual"
        action["reason"] = request.reason
        print(f"✅ Approved action {action_id}")
    else:
        action["status"] = "denied"
        action["denied_at"] = time.time()
        action["denied_by"] = "manual"
        action["reason"] = request.reason
        print(f"❌ Denied action {action_id}")
    
    return {
        "action_id": action_id,
        "status": action["status"],
        "message": f"Action {action['status']} successfully"
    }

@app.post("/deny/{action_id}")
async def deny_action(action_id: str, request: ApprovalRequest):
    """Deny an action (convenience endpoint)."""
    request.approved = False
    return await approve_action(action_id, request)

@app.get("/actions")
async def list_actions(status: Optional[str] = None, limit: int = 50):
    """List all actions, optionally filtered by status."""
    
    actions = list(actions_db.values())
    
    if status:
        actions = [a for a in actions if a["status"] == status]
    
    # Sort by creation time (newest first)
    actions.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "actions": actions[:limit],
        "total": len(actions),
        "filtered": len([a for a in actions_db.values() if not status or a["status"] == status])
    }

@app.get("/policies")
async def list_policies():
    """List all policies."""
    return {
        "policies": policies_db,
        "total": len(policies_db)
    }

@app.post("/policies")
async def create_policy(policy: Dict[str, Any]):
    """Create a new policy."""
    
    policy["id"] = f"policy_{len(policies_db) + 1}"
    policies_db.append(policy)
    
    print(f"📋 Created policy: {policy['name']} for tool {policy['tool']}")
    
    return {
        "message": "Policy created successfully",
        "policy": policy
    }

@app.put("/policies/{policy_id}")
async def update_policy(policy_id: str, policy: Dict[str, Any]):
    """Update an existing policy."""
    
    for i, p in enumerate(policies_db):
        if p["id"] == policy_id:
            policy["id"] = policy_id
            policies_db[i] = policy
            print(f"📝 Updated policy: {policy_id}")
            return {
                "message": "Policy updated successfully",
                "policy": policy
            }
    
    raise HTTPException(status_code=404, detail="Policy not found")

@app.delete("/policies/{policy_id}")
async def delete_policy(policy_id: str):
    """Delete a policy."""
    
    for i, p in enumerate(policies_db):
        if p["id"] == policy_id:
            deleted_policy = policies_db.pop(i)
            print(f"🗑️ Deleted policy: {policy_id}")
            return {
                "message": "Policy deleted successfully",
                "policy": deleted_policy
            }
    
    raise HTTPException(status_code=404, detail="Policy not found")

@app.get("/debug/reset")
async def reset_mock_data():
    """Reset all mock data to defaults (for testing)."""
    
    global actions_db, policies_db
    actions_db.clear()
    policies_db.clear()
    policies_db.extend(DEFAULT_POLICIES)
    
    print("🔄 Reset mock data to defaults")
    
    return {
        "message": "Mock data reset to defaults",
        "policies": len(policies_db),
        "actions": len(actions_db)
    }

@app.get("/debug/auto-approve/{action_id}")
async def auto_approve_action(action_id: str):
    """Auto-approve an action (for testing)."""
    
    if action_id not in actions_db:
        raise HTTPException(status_code=404, detail="Action not found")
    
    action = actions_db[action_id]
    action["status"] = "approved"
    action["approved_at"] = time.time()
    action["approved_by"] = "auto-debug"
    
    print(f"🔧 Debug: Auto-approved action {action_id}")
    
    return {
        "message": f"Action {action_id} auto-approved for testing",
        "action": action
    }

if __name__ == "__main__":
    print("🚀 Starting Arden Mock Backend")
    print("=" * 40)
    print("API will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("Health check: http://localhost:8000/health")
    print()
    print("Default policies loaded:")
    for policy in DEFAULT_POLICIES:
        print(f"  - {policy['tool']}: {policy['action']}")
    print()
    print("Configure your Arden SDK with:")
    print("  configure(api_key='test_local_key', api_url='http://localhost:8000')")
    print()
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )
