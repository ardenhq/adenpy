"""
Hybrid Approval Modes Example

This example demonstrates all three approval modes in Arden:
1. Wait mode (default) - blocks until approval/denial
2. Async mode - non-blocking with callbacks  
3. Webhook mode - uses webhook for notifications

Requirements:
    pip install ardenpy flask

Setup:
    1. Get Arden API key from https://arden.sh
    2. Set environment variables:
       export ARDEN_API_KEY="test_12345_your_arden_key"
    3. Run: python hybrid_approval_modes.py

Usage:
    This example shows how to use each approval mode and when to choose each one.
"""

import os
import time
import threading
from flask import Flask, request, jsonify
from ardenpy import guard_tool, configure

# Configure Arden
ARDEN_API_KEY = os.getenv("ARDEN_API_KEY", "test_12345_your_arden_api_key_here")
configure(api_key=ARDEN_API_KEY)

# Example tool functions
def send_email(to: str, subject: str, message: str) -> str:
    """Send an email (simulated)."""
    print(f"📧 Sending email to {to}")
    print(f"   Subject: {subject}")
    print(f"   Message: {message}")
    time.sleep(1)  # Simulate email sending
    return f"Email sent successfully to {to}"

def delete_files(pattern: str) -> str:
    """Delete files matching pattern (simulated)."""
    print(f"🗑️ Deleting files matching: {pattern}")
    time.sleep(0.5)  # Simulate file deletion
    return f"Deleted 3 files matching pattern: {pattern}"

def transfer_money(amount: float, to_account: str) -> str:
    """Transfer money (simulated)."""
    print(f"💰 Transferring ${amount} to {to_account}")
    time.sleep(2)  # Simulate bank transfer
    return f"Transferred ${amount} to {to_account}"

# =============================================================================
# MODE 1: WAIT MODE (DEFAULT) - Blocking until approval
# =============================================================================

print("🔄 WAIT MODE EXAMPLE")
print("=" * 50)

# Create protected tools with wait mode (default)
safe_email_wait = guard_tool("communication.email", send_email)
safe_delete_wait = guard_tool("file.delete", delete_files)

def demo_wait_mode():
    """Demonstrate wait mode - blocks until approval."""
    print("\n📋 Wait Mode Demo:")
    print("- Function calls will BLOCK until approved/denied")
    print("- Agent appears 'frozen' during approval process")
    print("- Simple to use, good for demos and simple workflows")
    
    try:
        print("\n🔄 Calling safe_email_wait...")
        result = safe_email_wait("user@example.com", "Test", "Hello from wait mode!")
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    try:
        print("\n🔄 Calling safe_delete_wait...")
        result = safe_delete_wait("*.tmp")
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Blocked: {e}")

# =============================================================================
# MODE 2: ASYNC MODE - Non-blocking with callbacks
# =============================================================================

print("\n\n🚀 ASYNC MODE EXAMPLE")
print("=" * 50)

# Callback functions for async mode
def handle_email_approval(result):
    """Called when email is approved."""
    print(f"✅ Email approved and sent: {result}")

def handle_email_denial(error):
    """Called when email is denied."""
    print(f"❌ Email denied: {error}")

def handle_transfer_approval(result):
    """Called when transfer is approved."""
    print(f"✅ Transfer approved and completed: {result}")

def handle_transfer_denial(error):
    """Called when transfer is denied."""
    print(f"❌ Transfer denied: {error}")

# Create protected tools with async mode
safe_email_async = guard_tool(
    "communication.email", 
    send_email,
    approval_mode="async",
    on_approval=handle_email_approval,
    on_denial=handle_email_denial
)

safe_transfer_async = guard_tool(
    "finance.transfer",
    transfer_money,
    approval_mode="async", 
    on_approval=handle_transfer_approval,
    on_denial=handle_transfer_denial
)

def demo_async_mode():
    """Demonstrate async mode - non-blocking with callbacks."""
    print("\n📋 Async Mode Demo:")
    print("- Function calls return IMMEDIATELY")
    print("- Callbacks are called when approved/denied")
    print("- Agent can continue other work while waiting")
    print("- Good for production systems with multiple concurrent operations")
    
    print("\n🚀 Calling safe_email_async (returns immediately)...")
    safe_email_async("user@example.com", "Async Test", "Hello from async mode!")
    print("📤 Email call submitted, continuing...")
    
    print("\n🚀 Calling safe_transfer_async (returns immediately)...")
    safe_transfer_async(1000.0, "account-12345")
    print("📤 Transfer call submitted, continuing...")
    
    print("\n⏳ Agent can do other work while waiting for approvals...")
    for i in range(5):
        print(f"   🔄 Doing other work... {i+1}/5")
        time.sleep(1)
    
    print("✅ Other work completed! Callbacks will be called when approvals come in.")

# =============================================================================
# MODE 3: WEBHOOK MODE - Uses webhook for notifications
# =============================================================================

print("\n\n🌐 WEBHOOK MODE EXAMPLE")
print("=" * 50)

# Flask app for webhook handling
webhook_app = Flask(__name__)

@webhook_app.route('/arden-webhook', methods=['POST'])
def handle_arden_webhook():
    """Handle webhook notifications from Arden."""
    try:
        data = request.get_json()
        action_id = data.get('action_id')
        status = data.get('status')  # 'approved' or 'denied'
        message = data.get('message', '')
        
        print(f"\n🔔 Webhook received: action_id={action_id}, status={status}")
        
        # Get the pending call details (in production, this would be from a database)
        if hasattr(guard_tool, 'pending_calls') and action_id in guard_tool.pending_calls:
            call_info = guard_tool.pending_calls[action_id]
            func = call_info['func']
            args = call_info['args'] 
            kwargs = call_info['kwargs']
            tool_name = call_info['tool_name']
            
            if status == 'approved':
                try:
                    result = func(*args, **kwargs)
                    print(f"✅ Webhook: {tool_name} approved and executed: {result}")
                except Exception as e:
                    print(f"❌ Webhook: Error executing {tool_name}: {e}")
            else:
                print(f"❌ Webhook: {tool_name} denied: {message}")
            
            # Clean up
            del guard_tool.pending_calls[action_id]
        
        return jsonify({"status": "success"})
    
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Create protected tools with webhook mode
safe_email_webhook = guard_tool(
    "communication.email",
    send_email,
    approval_mode="webhook", 
    webhook_url="http://localhost:5000/arden-webhook"
)

safe_delete_webhook = guard_tool(
    "file.delete",
    delete_files,
    approval_mode="webhook",
    webhook_url="http://localhost:5000/arden-webhook"
)

def demo_webhook_mode():
    """Demonstrate webhook mode - uses webhook for notifications."""
    print("\n📋 Webhook Mode Demo:")
    print("- Function calls return IMMEDIATELY")
    print("- Arden backend calls your webhook when approved/denied")
    print("- Most scalable for production systems")
    print("- Requires webhook endpoint setup")
    
    print("\n🌐 Starting webhook server on http://localhost:5000...")
    
    # Start webhook server in background thread
    def run_webhook_server():
        webhook_app.run(host='localhost', port=5000, debug=False)
    
    webhook_thread = threading.Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()
    time.sleep(2)  # Give server time to start
    
    print("\n🚀 Calling safe_email_webhook (returns immediately)...")
    safe_email_webhook("user@example.com", "Webhook Test", "Hello from webhook mode!")
    print("📤 Email call submitted via webhook")
    
    print("\n🚀 Calling safe_delete_webhook (returns immediately)...")
    safe_delete_webhook("*.log")
    print("📤 Delete call submitted via webhook")
    
    print("\n⏳ Webhook server is running, waiting for approval notifications...")
    print("   💡 In production, approvals would come from your Arden dashboard")
    print("   💡 The webhook will be called automatically when actions are approved/denied")

# =============================================================================
# MAIN DEMO
# =============================================================================

def main():
    """Run all approval mode demonstrations."""
    print("🛡️ Arden Hybrid Approval Modes Demo")
    print("=" * 60)
    print("This demo shows three ways to handle approval workflows:")
    print("1. Wait mode - blocks until approval (simple)")
    print("2. Async mode - non-blocking with callbacks (flexible)")  
    print("3. Webhook mode - uses webhooks (scalable)")
    print()
    
    # Check API key
    if ARDEN_API_KEY == "test_12345_your_arden_api_key_here":
        print("⚠️  Please set your ARDEN_API_KEY environment variable")
        print("   Get one from: https://arden.sh")
        return
    
    print("🔑 API Key configured, starting demos...")
    
    # Demo each mode
    demo_wait_mode()
    
    print("\n" + "="*60)
    demo_async_mode()
    
    print("\n" + "="*60) 
    demo_webhook_mode()
    
    print("\n" + "="*60)
    print("🎉 Demo complete!")
    print("\n💡 Choose the right mode for your use case:")
    print("   - Wait mode: Simple demos, single-threaded apps")
    print("   - Async mode: Multi-threaded apps, concurrent operations")
    print("   - Webhook mode: Production systems, microservices, scalability")

if __name__ == "__main__":
    main()
