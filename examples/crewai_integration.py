"""
Real-World CrewAI Integration with Arden Protection

This example shows a complete CrewAI crew with Arden-protected tools.
Users can run this and see Arden intercepting CrewAI tool calls in real-time.

Requirements:
    pip install crewai crewai-tools ardenpy requests

Setup:
    1. Get OpenAI API key from https://platform.openai.com/api-keys
    2. Get Arden API key from https://arden.sh
    3. Set environment variables:
       export OPENAI_API_KEY="your_openai_key"
       export ARDEN_API_KEY="test_12345_your_arden_key"
    4. Run: python crewai_integration.py

Usage:
    The crew will automatically:
    - Research a topic (web search - protected)
    - Analyze findings (calculation - protected)
    - Create a report (file creation - protected)
    - Send summary (email - protected)
"""

import os
import requests
import math
from datetime import datetime
from typing import Dict, Any

# CrewAI imports
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Arden imports
from ardenpy import guard_tool, configure

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
ARDEN_API_KEY = os.getenv("ARDEN_API_KEY", "test_12345_your_arden_api_key_here")

# Configure Arden
configure(api_key=ARDEN_API_KEY)

# Set OpenAI API key for CrewAI
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

class WebSearchInput(BaseModel):
    """Input schema for web search tool."""
    query: str = Field(..., description="Search query to look up information")

class WebSearchTool(BaseTool):
    """Arden-protected web search tool for CrewAI."""
    name: str = "web_search"
    description: str = "Search the web for current information and news"
    args_schema: type[BaseModel] = WebSearchInput
    
    def __init__(self):
        super().__init__()
        # Protect the actual search function with Arden
        self._protected_search = guard_tool("web.search", self._search_web)
    
    def _search_web(self, query: str) -> str:
        """Actual web search implementation."""
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
                return f"Search completed for '{query}' - try a more specific query for detailed results."
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def _run(self, query: str) -> str:
        """CrewAI calls this method - we route to Arden-protected function."""
        return self._protected_search(query)

class FileCreateInput(BaseModel):
    """Input schema for file creation tool."""
    filename: str = Field(..., description="Name of the file to create")
    content: str = Field(..., description="Content to write to the file")

class FileCreateTool(BaseTool):
    """Arden-protected file creation tool for CrewAI."""
    name: str = "create_file"
    description: str = "Create a file with specified content"
    args_schema: type[BaseModel] = FileCreateInput
    
    def __init__(self):
        super().__init__()
        # Protect file creation with Arden
        self._protected_create = guard_tool("file.create", self._create_file)
    
    def _create_file(self, filename: str, content: str) -> str:
        """Actual file creation implementation."""
        try:
            # Create in safe directory
            os.makedirs("crew_output", exist_ok=True)
            filepath = os.path.join("crew_output", filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"✅ File created: {filepath} ({len(content)} characters)"
        except Exception as e:
            return f"❌ Failed to create file: {str(e)}"
    
    def _run(self, filename: str, content: str) -> str:
        """CrewAI calls this method - we route to Arden-protected function."""
        return self._protected_create(filename, content)

class CalculatorInput(BaseModel):
    """Input schema for calculator tool."""
    expression: str = Field(..., description="Mathematical expression to evaluate")

class CalculatorTool(BaseTool):
    """Arden-protected calculator tool for CrewAI."""
    name: str = "calculate"
    description: str = "Perform mathematical calculations safely"
    args_schema: type[BaseModel] = CalculatorInput
    
    def __init__(self):
        super().__init__()
        # Protect calculations with Arden
        self._protected_calc = guard_tool("math.calculate", self._calculate)
    
    def _calculate(self, expression: str) -> str:
        """Actual calculation implementation."""
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
    
    def _run(self, expression: str) -> str:
        """CrewAI calls this method - we route to Arden-protected function."""
        return self._protected_calc(expression)

class EmailInput(BaseModel):
    """Input schema for email tool."""
    recipient: str = Field(..., description="Email recipient")
    subject: str = Field(..., description="Email subject")
    message: str = Field(..., description="Email message content")

class EmailTool(BaseTool):
    """Arden-protected email tool for CrewAI."""
    name: str = "send_email"
    description: str = "Send an email with specified content"
    args_schema: type[BaseModel] = EmailInput
    
    def __init__(self):
        super().__init__()
        # Protect email sending with Arden
        self._protected_email = guard_tool("communication.email", self._send_email)
    
    def _send_email(self, recipient: str, subject: str, message: str) -> str:
        """Actual email sending implementation (simulated)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"📧 Email sent to {recipient} at {timestamp}\nSubject: {subject}\nMessage: {message[:100]}..."
    
    def _run(self, recipient: str, subject: str, message: str) -> str:
        """CrewAI calls this method - we route to Arden-protected function."""
        return self._protected_email(recipient, subject, message)

class ArdenCrewAIExample:
    """CrewAI example with Arden-protected tools."""
    
    def __init__(self):
        print("🚀 Setting up CrewAI with Arden Protection")
        
        # Initialize Arden-protected tools
        self.web_search_tool = WebSearchTool()
        self.file_create_tool = FileCreateTool()
        self.calculator_tool = CalculatorTool()
        self.email_tool = EmailTool()
        
        print("🛡️ All tools protected by Arden policies")
        
        # Create agents with protected tools
        self.researcher = Agent(
            role='Research Analyst',
            goal='Research and gather information on given topics',
            backstory='You are an expert researcher who finds accurate, up-to-date information.',
            tools=[self.web_search_tool],
            verbose=True
        )
        
        self.analyst = Agent(
            role='Data Analyst', 
            goal='Analyze data and perform calculations',
            backstory='You are a skilled analyst who can process data and perform calculations.',
            tools=[self.calculator_tool],
            verbose=True
        )
        
        self.writer = Agent(
            role='Technical Writer',
            goal='Create comprehensive reports and documentation',
            backstory='You are a professional writer who creates clear, detailed reports.',
            tools=[self.file_create_tool],
            verbose=True
        )
        
        self.communicator = Agent(
            role='Communications Manager',
            goal='Send summaries and updates to stakeholders',
            backstory='You handle all external communications and updates.',
            tools=[self.email_tool],
            verbose=True
        )
        
        print("✅ CrewAI agents created with Arden-protected tools")
    
    def run_research_project(self, topic: str = "artificial intelligence trends 2024"):
        """Run a complete research project with the crew."""
        
        print(f"\n🎯 Starting research project on: {topic}")
        print("🛡️ All tool usage will be intercepted by Arden")
        
        # Define tasks
        research_task = Task(
            description=f"Research the latest information about {topic}. Find current trends, developments, and key insights.",
            agent=self.researcher,
            expected_output="Comprehensive research findings with key insights and trends"
        )
        
        analysis_task = Task(
            description="Analyze the research findings. If there are any numbers or statistics, calculate growth rates, percentages, or other relevant metrics.",
            agent=self.analyst,
            expected_output="Analysis with calculated metrics and insights",
            context=[research_task]
        )
        
        report_task = Task(
            description="Create a comprehensive report based on the research and analysis. Save it as 'research_report.md'.",
            agent=self.writer,
            expected_output="A well-structured markdown report file",
            context=[research_task, analysis_task]
        )
        
        communication_task = Task(
            description="Send an email summary of the research project to 'team@company.com' with subject 'Research Project Complete'.",
            agent=self.communicator,
            expected_output="Email confirmation",
            context=[research_task, analysis_task, report_task]
        )
        
        # Create and run crew
        crew = Crew(
            agents=[self.researcher, self.analyst, self.writer, self.communicator],
            tasks=[research_task, analysis_task, report_task, communication_task],
            process=Process.sequential,
            verbose=True
        )
        
        try:
            print("\n🚀 Starting CrewAI execution...")
            result = crew.kickoff()
            print(f"\n✅ Crew execution completed!")
            print(f"📋 Final result: {result}")
            return result
        
        except Exception as e:
            print(f"❌ Crew execution failed: {e}")
            return None

def main():
    """Main function to run the CrewAI example."""
    
    # Check API keys
    if OPENAI_API_KEY == "your_openai_api_key_here":
        print("⚠️  Please set your OPENAI_API_KEY environment variable")
        print("   Get one from: https://platform.openai.com/api-keys")
        return
    
    if ARDEN_API_KEY == "test_12345_your_arden_api_key_here":
        print("⚠️  Please set your ARDEN_API_KEY environment variable")
        print("   Get one from: https://arden.sh")
        return
    
    print("🤖 CrewAI Integration with Arden Protection")
    print("=" * 50)
    
    # Initialize the crew
    try:
        crew_example = ArdenCrewAIExample()
    except Exception as e:
        print(f"❌ Failed to initialize CrewAI: {e}")
        return
    
    # Ask user for topic or use default
    try:
        topic = input("\n📝 Enter research topic (or press Enter for default 'AI trends 2024'): ").strip()
        if not topic:
            topic = "artificial intelligence trends 2024"
        
        print(f"\n🎯 Research topic: {topic}")
        print("\n🛡️ Arden Protection Active:")
        print("   - Web searches may require approval")
        print("   - File creation may require approval")
        print("   - Email sending may require approval")
        print("   - Calculations are typically allowed")
        
        confirm = input("\n▶️  Start the crew? (y/n): ").strip().lower()
        if confirm in ['y', 'yes']:
            crew_example.run_research_project(topic)
        else:
            print("👋 Cancelled")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
