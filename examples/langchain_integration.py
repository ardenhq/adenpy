"""
Real-World LangChain Integration with Arden Protection

This example shows a complete LangChain agent with Arden-protected tools.
Users can run this and see Arden intercepting LangChain tool calls in real-time.

Requirements:
    pip install langchain langchain-openai ardenpy requests

Setup:
    1. Get OpenAI API key from https://platform.openai.com/api-keys
    2. Get Arden API key from https://arden.sh
    3. Set environment variables:
       export OPENAI_API_KEY="your_openai_key"
       export ARDEN_API_KEY="test_12345_your_arden_key"
    4. Run: python langchain_integration.py

Usage:
    Try these requests:
    - "Search for the latest news about AI"
    - "Create a file called summary.txt with today's findings"
    - "Calculate 15% of $50,000"
    - "Send an email summary to the team"
"""

import os
import requests
import math
from datetime import datetime
from typing import Dict, Any

# LangChain imports
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Arden imports
from ardenpy import guard_tool, configure

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
ARDEN_API_KEY = os.getenv("ARDEN_API_KEY", "test_12345_your_arden_api_key_here")

# Configure Arden
configure(api_key=ARDEN_API_KEY)

class ArdenProtectedTools:
    """Collection of tools protected by Arden for LangChain agents."""
    
    def __init__(self):
        print("🛡️ Setting up Arden-protected tools for LangChain...")
        
        # Create protected versions of all tools
        self.web_search = guard_tool("web.search", self._web_search)
        self.file_create = guard_tool("file.create", self._create_file)
        self.file_read = guard_tool("file.read", self._read_file)
        self.calculate = guard_tool("math.calculate", self._calculate)
        self.send_email = guard_tool("communication.email", self._send_email)
        self.get_weather = guard_tool("api.weather", self._get_weather)
        
        print("✅ All tools protected by Arden policies")
    
    def _web_search(self, query: str) -> str:
        """Search the web for information."""
        try:
            # Using DuckDuckGo Instant Answer API
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('Abstract'):
                return f"Search results for '{query}':\n{data['Abstract']}"
            elif data.get('Definition'):
                return f"Definition for '{query}':\n{data['Definition']}"
            else:
                return f"Search completed for '{query}' but no detailed results found."
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def _create_file(self, filename: str, content: str) -> str:
        """Create a file with content."""
        try:
            # Create in safe directory
            os.makedirs("agent_files", exist_ok=True)
            filepath = os.path.join("agent_files", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"✅ File created: {filepath} ({len(content)} characters)"
        except Exception as e:
            return f"❌ Failed to create file: {str(e)}"
    
    def _read_file(self, filename: str) -> str:
        """Read a file's contents."""
        try:
            filepath = os.path.join("agent_files", filename)
            
            if not os.path.exists(filepath):
                return f"❌ File not found: {filename}"
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"📄 Contents of {filename}:\n{content}"
        except Exception as e:
            return f"❌ Failed to read file: {str(e)}"
    
    def _calculate(self, expression: str) -> str:
        """Safely calculate mathematical expressions."""
        try:
            # Safe mathematical operations only
            allowed_names = {
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow, "sqrt": math.sqrt,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "log": math.log, "exp": math.exp, "pi": math.pi, "e": math.e
            }
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"🧮 {expression} = {result}"
        except Exception as e:
            return f"❌ Calculation failed: {str(e)}"
    
    def _send_email(self, recipient: str, subject: str, message: str) -> str:
        """Send an email (simulated)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"📧 Email sent to {recipient} at {timestamp}\nSubject: {subject}\nMessage: {message}"
    
    def _get_weather(self, location: str) -> str:
        """Get weather information (simulated)."""
        # In a real implementation, you'd call a weather API
        return f"🌤️ Weather in {location}: 72°F, partly cloudy with light winds"
    
    def get_langchain_tools(self) -> list:
        """Get LangChain Tool objects with Arden protection."""
        return [
            Tool(
                name="web_search",
                func=self.web_search,
                description="Search the web for current information. Input should be a search query."
            ),
            Tool(
                name="create_file",
                func=lambda args: self.file_create(*args.split('|', 1)) if '|' in args else "Error: Use format 'filename|content'",
                description="Create a file with content. Input format: 'filename|content'"
            ),
            Tool(
                name="read_file", 
                func=self.file_read,
                description="Read the contents of a file. Input should be the filename."
            ),
            Tool(
                name="calculate",
                func=self.calculate,
                description="Perform mathematical calculations. Input should be a mathematical expression."
            ),
            Tool(
                name="send_email",
                func=lambda args: self.send_email(*args.split('|', 2)) if args.count('|') >= 2 else "Error: Use format 'recipient|subject|message'",
                description="Send an email. Input format: 'recipient|subject|message'"
            ),
            Tool(
                name="get_weather",
                func=self.get_weather,
                description="Get weather information for a location. Input should be a city name."
            ),
        ]

class ArdenLangChainAgent:
    """LangChain agent with Arden-protected tools."""
    
    def __init__(self):
        print("🚀 Initializing LangChain Agent with Arden Protection")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0.7
        )
        
        # Set up protected tools
        self.tools_manager = ArdenProtectedTools()
        self.tools = self.tools_manager.get_langchain_tools()
        
        # Create agent prompt
        self.prompt = PromptTemplate.from_template("""
You are a helpful AI assistant with access to various tools. All your tool usage is protected by Arden security policies.

When using tools:
- For create_file: use format "filename|content"  
- For send_email: use format "recipient|subject|message"
- Be specific and clear in your tool inputs

Available tools: {tool_names}
Tool descriptions: {tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}
""")
        
        # Create agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        print("✅ LangChain agent ready with Arden protection!")
    
    def chat(self, user_input: str) -> str:
        """Process user input through the LangChain agent."""
        try:
            print(f"\n🤖 Processing: '{user_input}'")
            print("🛡️ All tool calls will be intercepted by Arden")
            
            result = self.agent_executor.invoke({"input": user_input})
            return result["output"]
        
        except Exception as e:
            return f"❌ Error processing request: {str(e)}"

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
    
    # Initialize agent
    try:
        agent = ArdenLangChainAgent()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    print("\n" + "="*60)
    print("🤖 LangChain Agent with Arden Protection")
    print("="*60)
    print("\n💬 Try these example requests:")
    print("   - 'Search for the latest AI news'")
    print("   - 'Create a file called notes.txt with my meeting summary'")
    print("   - 'Calculate 15% of $50,000'")
    print("   - 'Send an email update to the team'")
    print("   - 'Get the weather in San Francisco'")
    print("\n🛡️ All tool calls are protected by Arden policies")
    print("   - Safe operations may run immediately")
    print("   - Sensitive operations may require approval")
    print("   - Dangerous operations may be blocked")
    print("\n   Type 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            if user_input:
                response = agent.chat(user_input)
                print(f"\n🤖 Agent: {response}\n")
        
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
