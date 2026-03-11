"""
AutoGPT-Style Agent with Arden Protection

This example shows an autonomous agent similar to AutoGPT with Arden-protected commands.
Users can run this and see Arden intercepting autonomous agent actions in real-time.

Requirements:
    pip install openai ardenpy requests

Setup:
    1. Get OpenAI API key from https://platform.openai.com/api-keys
    2. Get Arden API key from https://arden.sh
    3. Set environment variables:
       export OPENAI_API_KEY="your_openai_key"
       export ARDEN_API_KEY="test_12345_your_arden_key"
    4. Run: python autogpt_integration.py

Usage:
    Give the agent a goal like:
    - "Research and create a summary about renewable energy"
    - "Analyze the latest tech news and write a report"
    - "Calculate project costs and send a budget email"
"""

import os
import json
import requests
import math
from datetime import datetime
from typing import Dict, Any, List
from openai import OpenAI

# Arden imports
from ardenpy import guard_tool, configure

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
ARDEN_API_KEY = os.getenv("ARDEN_API_KEY", "test_12345_your_arden_api_key_here")

# Configure Arden
configure(api_key=ARDEN_API_KEY)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

class AutonomousAgent:
    """AutoGPT-style autonomous agent with Arden protection."""
    
    def __init__(self, name: str = "ArdenGPT"):
        self.name = name
        self.memory = []
        self.goals = []
        self.max_iterations = 10
        
        print(f"🤖 Initializing {self.name} with Arden Protection")
        
        # Set up Arden-protected commands
        self.commands = {
            "web_search": guard_tool("web.search", self._web_search),
            "create_file": guard_tool("file.create", self._create_file),
            "read_file": guard_tool("file.read", self._read_file),
            "calculate": guard_tool("math.calculate", self._calculate),
            "send_email": guard_tool("communication.email", self._send_email),
            "execute_code": guard_tool("code.execute", self._execute_code),
            "make_request": guard_tool("api.request", self._make_request),
        }
        
        print("🛡️ All commands protected by Arden policies")
        print("✅ Agent ready for autonomous operation")
    
    def _web_search(self, query: str) -> str:
        """Search the web for information."""
        try:
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('Abstract'):
                return f"Search results: {data['Abstract']}"
            elif data.get('Definition'):
                return f"Definition: {data['Definition']}"
            else:
                return f"Search completed for '{query}' - no detailed results found."
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def _create_file(self, filename: str, content: str) -> str:
        """Create a file with content."""
        try:
            os.makedirs("agent_workspace", exist_ok=True)
            filepath = os.path.join("agent_workspace", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"File created: {filepath} ({len(content)} chars)"
        except Exception as e:
            return f"File creation failed: {str(e)}"
    
    def _read_file(self, filename: str) -> str:
        """Read a file's contents."""
        try:
            filepath = os.path.join("agent_workspace", filename)
            
            if not os.path.exists(filepath):
                return f"File not found: {filename}"
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"File contents: {content}"
        except Exception as e:
            return f"File read failed: {str(e)}"
    
    def _calculate(self, expression: str) -> str:
        """Perform calculations."""
        try:
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": math.sqrt,
                "pi": math.pi, "e": math.e
            }
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"Calculation result: {expression} = {result}"
        except Exception as e:
            return f"Calculation failed: {str(e)}"
    
    def _send_email(self, recipient: str, subject: str, message: str) -> str:
        """Send an email (simulated)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"Email sent to {recipient} at {timestamp}: {subject}"
    
    def _execute_code(self, code: str, language: str = "python") -> str:
        """Execute code safely (simulated)."""
        return f"Code execution simulated: {code[:50]}... (Language: {language})"
    
    def _make_request(self, url: str, method: str = "GET") -> str:
        """Make HTTP request."""
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=10)
                return f"Request to {url}: Status {response.status_code}"
            else:
                return f"HTTP {method} request to {url} (simulated)"
        except Exception as e:
            return f"Request failed: {str(e)}"
    
    def get_available_commands(self) -> List[Dict[str, str]]:
        """Get list of available commands for the LLM."""
        return [
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
                    "name": "create_file",
                    "description": "Create a file with content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Name of file to create"},
                            "content": {"type": "string", "description": "File content"}
                        },
                        "required": ["filename", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "Name of file to read"}
                        },
                        "required": ["filename"]
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
                            "expression": {"type": "string", "description": "Mathematical expression"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send an email",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "recipient": {"type": "string", "description": "Email recipient"},
                            "subject": {"type": "string", "description": "Email subject"},
                            "message": {"type": "string", "description": "Email message"}
                        },
                        "required": ["recipient", "subject", "message"]
                    }
                }
            }
        ]
    
    def execute_command(self, command_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a command using Arden-protected functions."""
        try:
            if command_name in self.commands:
                command_func = self.commands[command_name]
                
                # Call the protected function with arguments
                if command_name == "web_search":
                    return command_func(arguments["query"])
                elif command_name == "create_file":
                    return command_func(arguments["filename"], arguments["content"])
                elif command_name == "read_file":
                    return command_func(arguments["filename"])
                elif command_name == "calculate":
                    return command_func(arguments["expression"])
                elif command_name == "send_email":
                    return command_func(arguments["recipient"], arguments["subject"], arguments["message"])
                else:
                    return f"Command {command_name} not implemented"
            else:
                return f"Unknown command: {command_name}"
        
        except Exception as e:
            return f"Command execution blocked or failed: {str(e)}"
    
    def think_and_act(self, goal: str, context: str = "") -> str:
        """Use GPT to think about the goal and decide on actions."""
        
        system_prompt = f"""You are {self.name}, an autonomous AI agent with access to various commands.
Your goal is: {goal}

Available commands: {', '.join(self.commands.keys())}

You should think step by step about how to achieve the goal, then use the available commands.
All your commands are protected by Arden security policies - some may require approval or be blocked.

Current context: {context}

Think about what you need to do next and use the appropriate command."""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Work towards this goal: {goal}"}
                ],
                tools=self.get_available_commands(),
                tool_choice="auto"
            )
            
            message = response.choices[0].message
            
            if message.tool_calls:
                # Execute the tool calls
                results = []
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"🔧 Executing: {function_name} with {function_args}")
                    
                    # Execute command (Arden protection happens here!)
                    result = self.execute_command(function_name, function_args)
                    results.append(f"{function_name}: {result}")
                    
                    # Add to memory
                    self.memory.append({
                        "action": function_name,
                        "args": function_args,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
                
                return "; ".join(results)
            else:
                return message.content or "No action taken"
                
        except Exception as e:
            return f"Thinking failed: {str(e)}"
    
    def run_autonomous_session(self, goal: str):
        """Run autonomous session towards a goal."""
        
        print(f"\n🎯 Goal: {goal}")
        print(f"🤖 {self.name} starting autonomous session...")
        print("🛡️ All actions protected by Arden policies\n")
        
        self.goals.append(goal)
        context = ""
        
        for iteration in range(self.max_iterations):
            print(f"--- Iteration {iteration + 1} ---")
            
            # Think and act
            result = self.think_and_act(goal, context)
            print(f"📋 Result: {result}")
            
            # Update context with result
            context += f"Previous action result: {result}\n"
            
            # Check if goal seems completed
            if any(word in result.lower() for word in ["completed", "finished", "done", "created", "sent"]):
                print(f"\n✅ Goal appears to be completed after {iteration + 1} iterations")
                break
            
            print()
        
        print(f"\n📊 Session Summary:")
        print(f"   - Goal: {goal}")
        print(f"   - Iterations: {iteration + 1}")
        print(f"   - Actions taken: {len(self.memory)}")
        
        if self.memory:
            print("   - Recent actions:")
            for action in self.memory[-3:]:
                print(f"     • {action['action']}: {action['result'][:50]}...")

def main():
    """Main function to run the autonomous agent."""
    
    # Check API keys
    if OPENAI_API_KEY == "your_openai_api_key_here":
        print("⚠️  Please set your OPENAI_API_KEY environment variable")
        print("   Get one from: https://platform.openai.com/api-keys")
        return
    
    if ARDEN_API_KEY == "test_12345_your_arden_api_key_here":
        print("⚠️  Please set your ARDEN_API_KEY environment variable")
        print("   Get one from: https://arden.sh")
        return
    
    print("🤖 AutoGPT-Style Agent with Arden Protection")
    print("=" * 50)
    
    # Initialize agent
    try:
        agent = AutonomousAgent()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    print("\n💡 Example goals:")
    print("   - 'Research renewable energy and create a summary report'")
    print("   - 'Calculate project costs and send budget email'")
    print("   - 'Find latest AI news and write analysis'")
    
    try:
        goal = input("\n🎯 Enter your goal for the agent: ").strip()
        
        if not goal:
            goal = "Research renewable energy trends and create a summary report"
            print(f"Using default goal: {goal}")
        
        print("\n🛡️ Arden Protection Active:")
        print("   - Web searches may require approval")
        print("   - File operations may require approval") 
        print("   - Email sending may require approval")
        print("   - The agent will work autonomously within policy limits")
        
        confirm = input("\n▶️  Start autonomous session? (y/n): ").strip().lower()
        if confirm in ['y', 'yes']:
            agent.run_autonomous_session(goal)
        else:
            print("👋 Cancelled")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
