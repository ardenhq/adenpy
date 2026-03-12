"""
Production Webhook Server for Arden Approvals

This example shows how to implement a production-ready webhook server for Arden approval notifications.
Use this when you want real-time, scalable approval workflows without blocking your agent.

Requirements:
    pip install flask ardenpy

Setup:
    1. Get Arden API key from https://arden.sh
    2. Set environment variables:
       export ARDEN_API_KEY="test_12345_your_arden_key"
    3. Configure your Arden backend to send webhooks to your endpoint
    4. Run: python production_webhook_server.py

Production Notes:
    - Use a production WSGI server (gunicorn, uwsgi) instead of Flask dev server
    - Add authentication/validation for webhook security
    - Use a database to store pending actions instead of in-memory storage
    - Add proper error handling and logging
    - Consider using a message queue for high-volume scenarios
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Callable
from flask import Flask, request, jsonify
from ardenpy import guard_tool, configure

# Configure Arden
ARDEN_API_KEY = os.getenv("ARDEN_API_KEY", "test_12345_your_arden_api_key_here")
configure(api_key=ARDEN_API_KEY)

# Flask app for webhook handling
app = Flask(__name__)

# In-memory storage for pending actions (use database in production)
pending_actions: Dict[str, Dict[str, Any]] = {}

# =============================================================================
# WEBHOOK HANDLER
# =============================================================================

@app.route('/arden-webhook', methods=['POST'])
def handle_arden_webhook():
    """
    Handle webhook notifications from Arden backend.
    
    Expected payload:
    {
        "action_id": "act_12345",
        "status": "approved|denied", 
        "message": "Optional message",
        "tool_name": "communication.email",
        "timestamp": "2024-03-11T16:30:00Z"
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        
        # Extract webhook data
        action_id = data.get('action_id')
        status = data.get('status')
        message = data.get('message', '')
        tool_name = data.get('tool_name', 'unknown')
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        
        # Validate required fields
        if not action_id or not status:
            return jsonify({"error": "Missing required fields: action_id, status"}), 400
        
        if status not in ['approved', 'denied']:
            return jsonify({"error": "Invalid status. Must be 'approved' or 'denied'"}), 400
        
        print(f"\n🔔 Webhook received at {timestamp}")
        print(f"   Action ID: {action_id}")
        print(f"   Tool: {tool_name}")
        print(f"   Status: {status}")
        print(f"   Message: {message}")
        
        # Process the approval/denial
        result = process_approval_decision(action_id, status, message, tool_name)
        
        if result['success']:
            return jsonify({"status": "success", "message": "Webhook processed successfully"})
        else:
            return jsonify({"status": "error", "message": result['error']}), 400
    
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_approval_decision(action_id: str, status: str, message: str, tool_name: str) -> Dict[str, Any]:
    """Process an approval decision from the webhook."""
    
    # Check if we have this pending action
    if action_id not in pending_actions:
        error_msg = f"Action {action_id} not found in pending actions"
        print(f"⚠️ {error_msg}")
        return {"success": False, "error": error_msg}
    
    action_info = pending_actions[action_id]
    func = action_info['func']
    args = action_info['args']
    kwargs = action_info['kwargs']
    callbacks = action_info['callbacks']
    
    try:
        if status == 'approved':
            print(f"✅ Executing approved action: {tool_name}")
            
            # Execute the original function
            result = func(*args, **kwargs)
            
            # Call success callback if provided
            if callbacks.get('on_success'):
                callbacks['on_success'](result)
            
            print(f"✅ Action {action_id} completed successfully")
            
        else:  # denied
            print(f"❌ Action {action_id} was denied: {message}")
            
            # Call denial callback if provided
            if callbacks.get('on_denial'):
                error = Exception(f"Action denied: {message}")
                callbacks['on_denial'](error)
        
        # Clean up pending action
        del pending_actions[action_id]
        
        return {"success": True}
    
    except Exception as e:
        print(f"❌ Error processing action {action_id}: {e}")
        
        # Call error callback if provided
        if callbacks.get('on_error'):
            callbacks['on_error'](e)
        
        return {"success": False, "error": str(e)}

# =============================================================================
# WEBHOOK-ENABLED GUARD TOOL
# =============================================================================

def webhook_guard_tool(
    tool_name: str,
    func: Callable,
    webhook_url: str = "http://localhost:5000/arden-webhook",
    on_success: Callable[[Any], None] = None,
    on_denial: Callable[[Exception], None] = None,
    on_error: Callable[[Exception], None] = None
):
    """
    Create a webhook-enabled protected tool.
    
    Args:
        tool_name: Name for policy evaluation
        func: Function to protect
        webhook_url: URL for webhook notifications
        on_success: Callback when action is approved and executed
        on_denial: Callback when action is denied
        on_error: Callback when execution fails
    
    Returns:
        Protected function that uses webhooks for approvals
    """
    
    # Use the standard guard_tool with webhook mode
    protected_func = guard_tool(
        tool_name=tool_name,
        func=func,
        approval_mode="webhook",
        webhook_url=webhook_url
    )
    
    # Override to store callbacks for webhook processing
    original_wrapper = protected_func
    
    def webhook_wrapper(*args, **kwargs):
        # Call the original protected function
        result = original_wrapper(*args, **kwargs)
        
        # If it returned None (webhook mode), store callbacks
        if result is None:
            # Find the action_id from the pending calls
            # This is a simplified approach - in production, you'd get this from the API response
            action_id = f"act_{int(time.time())}"  # Simplified for demo
            
            pending_actions[action_id] = {
                'func': func,
                'args': args,
                'kwargs': kwargs,
                'callbacks': {
                    'on_success': on_success,
                    'on_denial': on_denial,
                    'on_error': on_error
                },
                'tool_name': tool_name,
                'created_at': datetime.utcnow().isoformat()
            }
            
            print(f"📝 Stored pending action {action_id} for webhook processing")
        
        return result
    
    return webhook_wrapper

# =============================================================================
# EXAMPLE USAGE
# =============================================================================

# Example tool functions
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    print(f"📧 Sending email to {to}")
    print(f"   Subject: {subject}")
    time.sleep(1)  # Simulate email sending
    return f"Email sent to {to}: {subject}"

def process_payment(amount: float, account: str) -> str:
    """Process a payment."""
    print(f"💳 Processing payment of ${amount} to {account}")
    time.sleep(2)  # Simulate payment processing
    return f"Payment of ${amount} processed for {account}"

def delete_user_data(user_id: str) -> str:
    """Delete user data (sensitive operation)."""
    print(f"🗑️ Deleting all data for user {user_id}")
    time.sleep(1)  # Simulate data deletion
    return f"All data deleted for user {user_id}"

# Callback functions
def handle_email_success(result):
    print(f"✅ Email callback: {result}")

def handle_email_denial(error):
    print(f"❌ Email denied callback: {error}")

def handle_payment_success(result):
    print(f"✅ Payment callback: {result}")

def handle_payment_denial(error):
    print(f"❌ Payment denied callback: {error}")

def handle_deletion_success(result):
    print(f"✅ Deletion callback: {result}")

def handle_deletion_denial(error):
    print(f"❌ Deletion denied callback: {error}")

# Create webhook-protected tools
safe_email = webhook_guard_tool(
    "communication.email",
    send_email,
    on_success=handle_email_success,
    on_denial=handle_email_denial
)

safe_payment = webhook_guard_tool(
    "finance.payment",
    process_payment,
    on_success=handle_payment_success,
    on_denial=handle_payment_denial
)

safe_deletion = webhook_guard_tool(
    "data.delete",
    delete_user_data,
    on_success=handle_deletion_success,
    on_denial=handle_deletion_denial
)

# =============================================================================
# DEMO FUNCTIONS
# =============================================================================

def demo_webhook_workflow():
    """Demonstrate the webhook workflow."""
    print("🌐 Production Webhook Server Demo")
    print("=" * 40)
    
    print("\n📋 How it works:")
    print("1. Agent calls protected function")
    print("2. Function returns immediately (non-blocking)")
    print("3. Arden backend evaluates policy")
    print("4. If approval needed, backend sends webhook to your endpoint")
    print("5. Human approves/denies via dashboard")
    print("6. Backend sends webhook with decision")
    print("7. Your webhook handler executes function or handles denial")
    
    print("\n🚀 Making protected function calls...")
    
    # These calls return immediately
    safe_email("user@example.com", "Test Email", "Hello from webhook mode!")
    safe_payment(150.00, "account-12345")
    safe_deletion("user-67890")
    
    print("\n📤 All calls submitted! Webhook server is listening for approvals...")
    print("💡 In production:")
    print("   - Approvals come from your Arden dashboard")
    print("   - Webhooks are sent automatically")
    print("   - Functions execute when approved")

def start_webhook_server():
    """Start the webhook server."""
    print("🌐 Starting production webhook server on http://localhost:5000")
    print("📡 Webhook endpoint: http://localhost:5000/arden-webhook")
    print("⏳ Server ready to receive approval notifications...")
    
    app.run(host='localhost', port=5000, debug=False)

# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main function to run the webhook example."""
    print("🛡️ Arden Production Webhook Server")
    print("=" * 50)
    
    # Check API key
    if ARDEN_API_KEY == "test_12345_your_arden_api_key_here":
        print("⚠️  Please set your ARDEN_API_KEY environment variable")
        print("   Get one from: https://arden.sh")
        return
    
    print("🔑 API Key configured")
    
    # Start webhook server in background
    server_thread = threading.Thread(target=start_webhook_server, daemon=True)
    server_thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    # Run demo
    demo_webhook_workflow()
    
    print("\n" + "="*50)
    print("🎉 Production webhook server running!")
    print("📡 Webhook server is active and ready")
    print("💡 Test by sending POST requests to http://localhost:5000/arden-webhook")
    print("\n📝 Example webhook payload:")
    print(json.dumps({
        "action_id": "act_12345",
        "status": "approved",
        "message": "Approved by admin",
        "tool_name": "communication.email",
        "timestamp": "2024-03-11T16:30:00Z"
    }, indent=2))
    
    # Keep server running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down webhook server...")

if __name__ == "__main__":
    main()
