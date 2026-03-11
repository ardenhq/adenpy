"""
Direct OpenAI Integration with Arden Protection

This example shows how to integrate Arden with OpenAI directly (no framework).
Use this when you want to build a custom agent without framework dependencies.

For framework-specific examples, see:
- langchain_integration.py (LangChain + Arden)
- crewai_integration.py (CrewAI + Arden)
- autogpt_integration.py (AutoGPT + Arden)

This example demonstrates:
- Direct OpenAI API usage with function calling
- Custom agent architecture with Arden protection
- Interactive chat interface
- Real tool functions (file ops, web requests, calculations)

Requirements:
    pip install openai requests ardenpy

Setup:
    1. Get OpenAI API key from https://platform.openai.com/api-keys
    2. Get Arden API key from https://arden.sh
    3. Set environment variables:
       export OPENAI_API_KEY="your_openai_key"
       export ARDEN_API_KEY="test_12345_your_arden_key"
    4. Run: python direct_openai_integration.py

When to use this example:
- You want direct OpenAI integration without frameworks
- You're building a custom agent architecture
- You want minimal dependencies
- You need full control over the agent logic
"""

import os
import json
import requests
import math
from datetime import datetime
from typing import Dict, Any, List
from openai import OpenAI
from ardenpy import guard_tool, configure

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
ARDEN_API_KEY = os.getenv("ARDEN_API_KEY", "test_12345_your_arden_api_key_here")

# Configure Arden
configure(api_key=ARDEN_API_KEY)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

class RealWorldAgent:
    """A real AI agent that uses OpenAI and Arden-protected tools."""
    
    def __init__(self):
        self.conversation_history = []
        self.setup_protected_tools()
        
        print("🤖 Real-World AI Agent with Arden Protection")
        print("=" * 50)
        print("✅ OpenAI integration ready")
        print("🛡️ Arden protection active")
        print("🚀 Agent ready for requests!")
    
    def setup_protected_tools(self):
        """Set up all the tools the agent can use, protected by Arden."""
        
        # File operations (potentially dangerous)
        self.create_file = guard_tool("file.create", self._create_file)
        self.read_file = guard_tool("file.read", self._read_file)
        self.delete_file = guard_tool("file.delete", self._delete_file)
        
        # Web operations (can access external resources)
        self.web_search = guard_tool("web.search", self._web_search)
        self.send_webhook = guard_tool("web.webhook", self._send_webhook)
        
        # Communication (sensitive)
        self.send_notification = guard_tool("communication.notify", self._send_notification)
        
        # Calculations (usually safe, but can be resource intensive)
        self.calculate = guard_tool("math.calculate", self._calculate)
        
        # System information (potentially sensitive)
        self.get_system_info = guard_tool("system.info", self._get_system_info)
    
    # Tool implementations - these are real, working functions
    
    def _create_file(self, filename: str, content: str) -> str:
        """Create a file with the given content."""
        try:
            # Create in a safe directory
            safe_dir = "agent_files"
            os.makedirs(safe_dir, exist_ok=True)
            filepath = os.path.join(safe_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"✅ File created: {filepath} ({len(content)} characters)"
        except Exception as e:
            return f"❌ Failed to create file: {str(e)}"
    
    def _read_file(self, filename: str) -> str:
        """Read the contents of a file."""
        try:
            # Only read from safe directory
            safe_dir = "agent_files"
            filepath = os.path.join(safe_dir, filename)
            
            if not os.path.exists(filepath):
                return f"❌ File not found: {filename}"
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"📄 File content ({len(content)} chars):\n{content}"
        except Exception as e:
            return f"❌ Failed to read file: {str(e)}"
    
    def _delete_file(self, filename: str) -> str:
        """Delete a file."""
        try:
            safe_dir = "agent_files"
            filepath = os.path.join(safe_dir, filename)
            
            if not os.path.exists(filepath):
                return f"❌ File not found: {filename}"
            
            os.remove(filepath)
            return f"🗑️ File deleted: {filename}"
        except Exception as e:
            return f"❌ Failed to delete file: {str(e)}"
    
    def _web_search(self, query: str) -> str:
        """Search the web using a simple API."""
        try:
            # Using DuckDuckGo Instant Answer API (no key required)
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('Abstract'):
                return f"🔍 Search result for '{query}':\n{data['Abstract']}"
            elif data.get('Definition'):
                return f"🔍 Definition for '{query}':\n{data['Definition']}"
            else:
                return f"🔍 Search completed for '{query}' but no detailed results found. Try a more specific query."
        except Exception as e:
            return f"❌ Search failed: {str(e)}"
    
    def _send_webhook(self, url: str, data: Dict[str, Any]) -> str:
        """Send data to a webhook URL."""
        try:
            response = requests.post(url, json=data, timeout=10)
            return f"📡 Webhook sent to {url}: {response.status_code} {response.reason}"
        except Exception as e:
            return f"❌ Webhook failed: {str(e)}"
    
    def _send_notification(self, message: str, recipient: str = "user") -> str:
        """Send a notification (simulated)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"📢 Notification sent to {recipient} at {timestamp}: {message}"
    
    def _calculate(self, expression: str) -> str:
        """Safely evaluate mathematical expressions."""
        try:
            # Only allow safe mathematical operations
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": math.sqrt,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "exp": math.exp, "pi": math.pi,
                "e": math.e
            }
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"🧮 Calculation result: {expression} = {result}"
        except Exception as e:
            return f"❌ Calculation failed: {str(e)}"
    
    def _get_system_info(self) -> str:
        """Get basic system information."""
        try:
            import platform
            info = {
                "system": platform.system(),
                "python_version": platform.python_version(),
                "current_time": datetime.now().isoformat()
            }
            return f"💻 System info: {json.dumps(info, indent=2)}"
        except Exception as e:
            return f"❌ Failed to get system info: {str(e)}"
    
    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools for the LLM."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_file",
                    "description": "Create a new file with specified content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Name of the file to create"},
                            "content": {"type": "string", "description": "Content to write to the file"}
                        },
                        "required": ["filename", "content"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Name of the file to read"}
                        },
                        "required": ["filename"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search", 
                    "description": "Search the web for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform mathematical calculations",
                    "parameters": {
                        "type": "object", 
                        "properties": {
                            "expression": {"type": "string", "description": "Mathematical expression to evaluate"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_notification",
                    "description": "Send a notification message",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Notification message"},
                            "recipient": {"type": "string", "description": "Recipient of notification", "default": "user"}
                        },
                        "required": ["message"]
                    }
                }
            }
        ]
    
    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call using Arden-protected functions."""
        try:
            if tool_name == "create_file":
                return self.create_file(arguments["filename"], arguments["content"])
            elif tool_name == "read_file":
                return self.read_file(arguments["filename"])
            elif tool_name == "web_search":
                return self.web_search(arguments["query"])
            elif tool_name == "calculate":
                return self.calculate(arguments["expression"])
            elif tool_name == "send_notification":
                recipient = arguments.get("recipient", "user")
                return self.send_notification(arguments["message"], recipient)
            else:
                return f"❌ Unknown tool: {tool_name}"
        except Exception as e:
            return f"⏳ Tool call blocked or failed: {str(e)}"
    
    def chat(self, user_message: str) -> str:
        """Process a user message using OpenAI and execute any tool calls."""
        
        # Add user message to conversation
        self.conversation_history.append({"role": "user", "content": user_message})
        
        try:
            # Call OpenAI with function calling
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                tools=self.get_available_tools(),
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            # Handle tool calls
            if message.tool_calls:
                # Add assistant message with tool calls
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": message.content,
                    "tool_calls": [{"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
                })
                
                tool_results = []
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🔧 Executing tool: {function_name} with args: {function_args}")
                    
                    # Execute the tool call (Arden protection happens here!)
                    result = self.execute_tool_call(function_name, function_args)
                    tool_results.append(result)
                    
                    # Add tool result to conversation
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
                
                # Get final response from OpenAI
                final_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=self.conversation_history
                )
                
                final_message = final_response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": final_message})
                
                return final_message
            
            else:
                # No tool calls, just return the response
                self.conversation_history.append({"role": "assistant", "content": message.content})
                return message.content
                
        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            if "api_key" in str(e).lower():
                error_msg += "\n💡 Make sure to set your OPENAI_API_KEY environment variable"
            return error_msg

def main():
    """Main interactive loop."""
    
    # Check API keys
    if OPENAI_API_KEY == "your_openai_api_key_here":
        print("⚠️  Please set your OPENAI_API_KEY environment variable")
        print("   Get one from: https://platform.openai.com/api-keys")
        return
    
    if ARDEN_API_KEY == "test_12345_your_arden_api_key_here":
        print("⚠️  Please set your ARDEN_API_KEY environment variable")
        print("   Get one from: https://arden.sh")
        return
    
    agent = RealWorldAgent()
    
    print("\n💬 Chat with the AI agent! Try these examples:")
    print("   - 'Search for information about machine learning'")
    print("   - 'Create a file called notes.txt with my meeting notes'") 
    print("   - 'Calculate the square root of 144'")
    print("   - 'Send me a notification when you're done'")
    print("   - Type 'quit' to exit")
    print()
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if user_input:
                print("🤖 Agent: ", end="", flush=True)
                response = agent.chat(user_input)
                print(response)
                print()
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
