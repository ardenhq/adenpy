"""
Getting Started with Arden

The simplest possible Arden integration. Wraps three plain functions and
shows allow / approval / block in action.

Setup:
    export ARDEN_API_KEY="arden_live_..."   # or arden_test_...
    python getting_started.py
"""

import os
from ardenpy import guard_tool, configure

configure(api_key=os.environ["ARDEN_API_KEY"])

# Step 2: Define functions with different risk levels
def read_config(filename: str):
    """Read configuration - LOW RISK (typically allowed)"""
    print(f"📖 Reading config: {filename}")
    return f"Config loaded from {filename}: {{'debug': True, 'port': 8080}}"

def send_email(to: str, subject: str, message: str):
    """Send email - MEDIUM RISK (typically requires approval)"""
    print(f"📧 Sending email to {to}")
    print(f"Subject: {subject}")
    print(f"Message: {message}")
    return f"Email sent to {to}"

def delete_database(table: str):
    """Delete database table - HIGH RISK (typically blocked)"""
    print(f"� DANGER: Attempting to delete table: {table}")
    return f"Table {table} deleted - ALL DATA LOST!"

def execute_system_command(command: str):
    """Execute system command - CRITICAL RISK (should be blocked)"""
    print(f"⚠️ CRITICAL: Executing system command: {command}")
    return f"Command executed: {command}"

# Step 3: Protect functions with descriptive tool names
# These names should match your policy configuration
safe_read_config = guard_tool("config.read", read_config)           # Allow
safe_send_email = guard_tool("communication.email", send_email)     # Requires approval  
safe_delete_db = guard_tool("database.delete", delete_database)     # Block
safe_system_cmd = guard_tool("system.execute", execute_system_command)  # Block

# Step 4: Use your protected functions normally
def main():
    print("🚀 Welcome to Arden!")
    print("=" * 50)
    print()
    
    print("Let's try some operations...")
    print()
    
    # LOW RISK - Should be allowed immediately
    print("1. Reading config (LOW RISK - typically allowed):")
    try:
        result = safe_read_config("app.json")
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    print()
    
    # MEDIUM RISK - Should require approval
    print("2. Sending email (MEDIUM RISK - typically requires approval):")
    try:
        result = safe_send_email("team@company.com", "Alert", "System detected anomaly")
        print(f"✅ {result}")
    except Exception as e:
        print(f"⏳ Requires approval or blocked: {e}")
    
    print()
    
    # HIGH RISK - Should be blocked
    print("3. Deleting database (HIGH RISK - typically blocked):")
    try:
        result = safe_delete_db("user_accounts")
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    print()
    
    # CRITICAL RISK - Should definitely be blocked
    print("4. System command (CRITICAL RISK - should be blocked):")
    try:
        result = safe_system_cmd("rm -rf /")
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ Blocked: {e}")
    
    print()
    print("🎉 That's how Arden protects your systems!")
    print()
    print("What you just saw:")
    print("• LOW RISK (config.read): ✅ Allowed immediately")
    print("• MEDIUM RISK (communication.email): ⏳ Requires approval")
    print("• HIGH RISK (database.delete): ❌ Blocked by policy")
    print("• CRITICAL RISK (system.execute): ❌ Blocked by policy")
    print()
    print("Configure your policies at https://arden.sh/dashboard:")
    print("• Set 'config.*' to ALLOW for safe operations")
    print("• Set 'communication.*' to REQUIRE_APPROVAL for sensitive actions")
    print("• Set 'database.delete' and 'system.*' to BLOCK for dangerous operations")

if __name__ == "__main__":
    main()
