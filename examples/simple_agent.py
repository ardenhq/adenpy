"""Simple example of using Arden to protect AI agent tool calls."""

import time
from ardenpy import guard_tool, configure

# Configure the SDK with your test API key from https://arden.sh
configure(api_key="test_12345_your_test_api_key_here")

# Example tools that an AI agent might use
def read_file(filename: str) -> str:
    """Read a file and return its contents."""
    print(f"Reading file: {filename}")
    return f"Contents of {filename}"

def write_file(filename: str, content: str) -> bool:
    """Write content to a file."""
    print(f"Writing to file: {filename}")
    print(f"Content: {content}")
    return True

def delete_file(filename: str) -> bool:
    """Delete a file."""
    print(f"Deleting file: {filename}")
    return True

def execute_command(command: str) -> str:
    """Execute a system command."""
    print(f"Executing command: {command}")
    return f"Command output: {command}"

def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers."""
    print(f"Calculating: {a} + {b}")
    return a + b

# Wrap tools with Arden protection
safe_read = guard_tool("read_file", read_file)
safe_write = guard_tool("write_file", write_file)
safe_delete = guard_tool("delete_file", delete_file)
safe_execute = guard_tool("execute_command", execute_command)
safe_calculate = guard_tool("calculate_sum", calculate_sum)

def demo_agent_workflow():
    """Demonstrate how an AI agent would use protected tools."""
    print("=== Arden Demo ===\n")
    
    # Safe operations should be allowed immediately
    print("1. Safe operations (should be allowed):")
    try:
        result = safe_calculate(5, 7)
        print(f"   Result: {result}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    try:
        result = safe_read("data.txt")
        print(f"   Result: {result}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Sensitive operations might require approval
    print("2. Sensitive operations (might require approval):")
    try:
        result = safe_write("output.txt", "Hello World")
        print(f"   Result: {result}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    try:
        result = safe_delete("temp.txt")
        print(f"   Result: {result}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # Dangerous operations should be blocked
    print("3. Dangerous operations (should be blocked):")
    try:
        result = safe_execute("rm -rf /")
        print(f"   Result: {result}\n")
    except Exception as e:
        print(f"   Error: {e}\n")

def demo_approval_workflow():
    """Demonstrate the approval workflow for operations that require human approval."""
    print("=== Approval Workflow Demo ===\n")
    
    # This operation will likely require approval based on default policies
    print("Attempting operation that requires approval...")
    
    try:
        # Start the operation in a separate thread/process in a real scenario
        result = safe_delete("important_file.txt")
        print(f"Operation completed: {result}")
    except Exception as e:
        print(f"Operation failed: {e}")
        print("\nIn a real scenario:")
        print("1. The agent would be paused")
        print("2. A human would receive a notification")
        print("3. The human could approve/deny via API or UI")
        print("4. The agent would resume or fail based on the decision")

if __name__ == "__main__":
    print("Arden Demo - Using hosted service")
    print("Get your test API key at https://arden.sh\n")
    print("Replace 'test_12345_your_test_api_key_here' with your actual test API key\n")
    
    time.sleep(2)  # Give user time to read the message
    
    demo_agent_workflow()
    print("\n" + "="*50 + "\n")
    demo_approval_workflow()
