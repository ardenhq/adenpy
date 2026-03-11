"""
Getting Started with Arden - Super Simple Example

This is the easiest way to get started with Arden.
Just run this file and see how it protects your functions!

Steps to run:
1. Get your free test API key from https://arden.sh
2. Replace "test_12345_your_test_api_key_here" with your actual key
3. Run: python examples/getting_started.py

That's it! 🚀
"""

from ardenpy import guard_tool, configure

# Step 1: Configure Arden with your API key
# The SDK automatically detects test environment from 'test_' prefix
configure(api_key="test_12345_your_test_api_key_here")

# Step 2: Define some functions you want to protect
def send_email(to: str, subject: str, message: str):
    """Send an email - this should require approval."""
    print(f"📧 Sending email to {to}")
    print(f"Subject: {subject}")
    print(f"Message: {message}")
    return f"Email sent to {to}"

def read_file(filename: str):
    """Read a file - this is usually safe."""
    print(f"📖 Reading file: {filename}")
    return f"Contents of {filename}: Hello World!"

def delete_file(filename: str):
    """Delete a file - this is dangerous and should require approval."""
    print(f"🗑️ Deleting file: {filename}")
    return f"File {filename} deleted"

# Step 3: Protect your functions with Arden
safe_send_email = guard_tool("communication.email", send_email)
safe_read_file = guard_tool("file.read", read_file)
safe_delete_file = guard_tool("file.delete", delete_file)

# Step 4: Use your protected functions normally
def main():
    print("🚀 Welcome to Arden!")
    print("=" * 50)
    print()
    
    print("Let's try some operations...")
    print()
    
    # This should work immediately (safe operation)
    print("1. Reading a file (safe operation):")
    try:
        result = safe_read_file("example.txt")
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()
    
    # This might require approval (sensitive operation)
    print("2. Sending an email (might need approval):")
    try:
        result = safe_send_email("user@example.com", "Hello", "This is a test email")
        print(f"✅ {result}")
    except Exception as e:
        print(f"⏳ Waiting for approval or blocked: {e}")
    
    print()
    
    # This will likely require approval (dangerous operation)
    print("3. Deleting a file (dangerous - needs approval):")
    try:
        result = safe_delete_file("important.txt")
        print(f"✅ {result}")
    except Exception as e:
        print(f"⏳ Waiting for approval or blocked: {e}")
    
    print()
    print("🎉 That's how easy Arden is!")
    print()
    print("What happened:")
    print("• Safe operations run immediately")
    print("• Sensitive operations may require approval")
    print("• Dangerous operations are blocked or need approval")
    print()
    print("Next steps:")
    print("• Configure policies at https://arden.sh/dashboard")
    print("• Set up approval notifications")
    print("• Integrate with your actual agent code")

if __name__ == "__main__":
    main()
