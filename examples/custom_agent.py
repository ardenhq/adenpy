"""
Simple AI Assistant with Arden Protection

This example shows how to build a practical AI assistant that can:
- Search the web safely
- Read and write files with protection
- Send messages with approval
- Analyze data securely

Requirements:
    pip install ardenpy

Usage:
    python custom_agent.py
"""

from ardenpy import guard_tool, configure
import time

# Configure Arden with your API key
# Option 1: Auto-detect environment from API key prefix
configure(api_key="test_12345_your_test_api_key_here")

# Option 2: Explicitly set environment
# configure(api_key="your_api_key", environment="test")  # For testing
# configure(api_key="your_api_key", environment="live")  # For production

# Option 3: Use convenience functions
# from ardenpy import configure_test, configure_live
# configure_test("test_12345_your_test_api_key_here")
# configure_live("live_67890_your_live_api_key_here")

class SimpleAIAssistant:
    """A simple AI assistant with Arden protection."""
    
    def __init__(self, name: str = "Assistant"):
        self.name = name
        self.conversation_history = []
        
        # Set up protected tools
        self.search_web = guard_tool("web.search", self._search_web)
        self.read_file = guard_tool("file.read", self._read_file)
        self.write_file = guard_tool("file.write", self._write_file)
        self.send_email = guard_tool("communication.email", self._send_email)
        self.analyze_data = guard_tool("data.analyze", self._analyze_data)
        
        print(f"🤖 {self.name} is ready to help!")
        print("🛡️ All actions are protected by Arden")
    
    def _search_web(self, query: str) -> str:
        """Search the web for information."""
        print(f"🔍 Searching for: {query}")
        # Simulate web search
        results = [
            f"Article: Everything you need to know about {query}",
            f"Guide: Best practices for {query}",
            f"Tutorial: How to get started with {query}"
        ]
        return f"Found {len(results)} results for '{query}': " + "; ".join(results)
    
    def _analyze_data(self, data_description: str) -> str:
        """Analyze data and provide insights."""
        print(f"📊 Analyzing: {data_description}")
        # Simulate data analysis
        insights = [
            "Data shows positive trend over time",
            "Key patterns identified in the dataset", 
            "Recommendations for improvement available"
        ]
        return f"Analysis of {data_description}: " + "; ".join(insights)
    
    def _read_file(self, filename: str) -> str:
        """Read a file safely."""
        print(f"� Reading file: {filename}")
        # Simulate file reading
        return f"Contents of {filename}: This is sample file content."
    
    def _write_file(self, filename: str, content: str) -> str:
        """Write content to a file."""
        print(f"📝 Writing to file: {filename}")
        print(f"Content preview: {content[:50]}...")
        # Simulate file writing
        return f"Successfully wrote {len(content)} characters to {filename}"
    
    def _send_email(self, to: str, subject: str, message: str) -> str:
        """Send an email."""
        print(f"📧 Sending email to: {to}")
        print(f"Subject: {subject}")
        # Simulate email sending
        return f"Email sent to {to} with subject '{subject}'"
    
    # Helper methods for the assistant
    def help_user(self, request: str) -> str:
        """Process a user request and decide what action to take."""
        print(f"🤔 Processing request: {request}")
        
        request_lower = request.lower()
        
        if "search" in request_lower:
            query = request.replace("search for", "").replace("search", "").strip()
            return self.search_web(query)
        
        elif "email" in request_lower:
            return self.send_email("user@example.com", "Assistant Response", f"Regarding: {request}")
        
        elif "analyze" in request_lower:
            return self.analyze_data(request)
        
        elif "read" in request_lower and "file" in request_lower:
            return self.read_file("example.txt")
        
        elif "write" in request_lower and "file" in request_lower:
            return self.write_file("output.txt", f"Response to: {request}")
        
        else:
            return f"I can help you with: searching, reading/writing files, sending emails, or analyzing data. You asked: {request}"

# Demo functions to show how the assistant works
def demo_assistant():
    """Demonstrate the AI assistant capabilities."""
    print("🚀 AI Assistant Demo")
    print("=" * 40)
    
    # Create an assistant
    assistant = SimpleAIAssistant("Helper")
    print()
    
    # Try different requests
    requests = [
        "search for Python tutorials",
        "analyze sales data from last quarter", 
        "read the config file",
        "write a summary report",
        "send email to the team"
    ]
    
    for i, request in enumerate(requests, 1):
        print(f"{i}. User request: '{request}'")
        try:
            result = assistant.help_user(request)
            print(f"   ✅ Result: {result}")
        except Exception as e:
            print(f"   ⏳ Blocked or needs approval: {e}")
        print()
    
    print("🎉 Demo complete!")

def interactive_mode():
    """Interactive mode to chat with the assistant."""
    print("\n" + "=" * 50)
    print("🤖 Interactive AI Assistant")
    print("Type your requests or 'quit' to exit")
    print("=" * 50)
    
    assistant = SimpleAIAssistant("Interactive Helper")
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break
            
            if user_input:
                print(f"🤖 {assistant.name}:", end=" ")
                try:
                    result = assistant.help_user(user_input)
                    print(result)
                except Exception as e:
                    print(f"⏳ Request needs approval or was blocked: {e}")
        
        except KeyboardInterrupt:
            break
    
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    print("🚀 Simple AI Assistant with Arden Protection")
    print("Get your API key from https://arden.sh")
    print()
    
    # Run the demo
    demo_assistant()
    
    # Ask if user wants interactive mode
    try:
        choice = input("\nWould you like to try interactive mode? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            interactive_mode()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        return task_id
    
    def _select_best_agent(self, task_description: str) -> Optional[SecureAgentFramework]:
        """Select best agent for a task based on role and capabilities."""
        if not self.agents:
            return None
        
        description_lower = task_description.lower()
        
        # Role-based assignment
        if "research" in description_lower or "search" in description_lower:
            researchers = [a for a in self.agents.values() if a.role == AgentRole.RESEARCHER]
            if researchers:
                return researchers[0]
        
        elif "analyze" in description_lower or "data" in description_lower:
            analysts = [a for a in self.agents.values() if a.role == AgentRole.ANALYST]
            if analysts:
                return analysts[0]
        
        elif "execute" in description_lower or "command" in description_lower:
            executors = [a for a in self.agents.values() if a.role == AgentRole.EXECUTOR]
            if executors:
                return executors[0]
        
        # Default to least busy generalist
        generalists = [a for a in self.agents.values() if a.role == AgentRole.GENERALIST]
        if generalists:
            return min(generalists, key=lambda a: len([t for t in a.tasks if t.status == TaskStatus.PENDING]))
        
        # Fallback to any available agent
        return min(self.agents.values(), key=lambda a: len([t for t in a.tasks if t.status == TaskStatus.PENDING]))
    
    def execute_all_pending_tasks(self):
        """Execute all pending tasks across all agents."""
        print("🚀 Executing all pending tasks...")
        
        for agent_name, agent in self.agents.items():
            pending_tasks = [t for t in agent.tasks if t.status == TaskStatus.PENDING]
            
            for task in pending_tasks:
                print(f"\n👤 Agent {agent_name} executing: {task.description}")
                result = agent.execute_task(task.id)
                print(f"✅ Result: {result[:200]}...")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        total_tasks = sum(len(agent.tasks) for agent in self.agents.values())
        completed_tasks = sum(len([t for t in agent.tasks if t.status == TaskStatus.COMPLETED]) for agent in self.agents.values())
        
        return {
            "total_agents": len(self.agents),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "agents": {name: {
                "role": agent.role.value,
                "tasks": len(agent.tasks),
                "capabilities": len(agent.capabilities)
            } for name, agent in self.agents.items()}
        }

def run_single_agent_example():
    """Demonstrate single agent capabilities."""
    
    print("🤖 Single Agent Example")
    print("=" * 30)
    
    # Create agent
    agent = SecureAgentFramework("DataAnalyst", AgentRole.ANALYST)
    
    # Add some tasks
    tasks = [
        "Search for machine learning trends",
        "Analyze the search results data",
        "Create report on ML trends",
        "Send notification about completed analysis",
        "Backup the analysis results"
    ]
    
    task_ids = []
    for task_desc in tasks:
        task_id = agent.add_task(task_desc, priority=random.randint(1, 10))
        task_ids.append(task_id)
    
    # Execute tasks
    for task_id in task_ids:
        print(f"\n📋 Executing task: {task_id}")
        result = agent.execute_task(task_id)
        print(f"Result: {result[:150]}...")
    
    # Show final status
    print(f"\n📊 Agent Status:")
    print(f"Completed tasks: {len([t for t in agent.tasks if t.status == TaskStatus.COMPLETED])}")
    print(f"Memory entries: {len(agent.memory)}")

def run_multi_agent_example():
    """Demonstrate multi-agent system."""
    
    print("\n👥 Multi-Agent System Example")
    print("=" * 35)
    
    # Create multi-agent system
    system = MultiAgentSystem()
    
    # Add specialized agents
    system.add_agent("Researcher", AgentRole.RESEARCHER)
    system.add_agent("Analyst", AgentRole.ANALYST)
    system.add_agent("Executor", AgentRole.EXECUTOR)
    system.add_agent("Coordinator", AgentRole.GENERALIST)
    
    # Assign various tasks
    collaborative_tasks = [
        "Research current AI safety practices",
        "Analyze the research data for trends",
        "Execute backup of research findings",
        "Create comprehensive report on AI safety",
        "Schedule team meeting to discuss findings",
        "Send summary to stakeholders"
    ]
    
    for task in collaborative_tasks:
        system.assign_task(task, priority=random.randint(5, 10))
    
    # Execute all tasks
    system.execute_all_pending_tasks()
    
    # Show system status
    print(f"\n📊 System Status:")
    status = system.get_system_status()
    print(json.dumps(status, indent=2))

def interactive_agent_mode():
    """Run agent in interactive mode."""
    
    print("\n🎮 Interactive Agent Mode")
    print("Commands:")
    print("  create <name> <role> - Create new agent")
    print("  task <agent_name> <description> - Add task to agent")
    print("  execute <agent_name> <task_id> - Execute specific task")
    print("  status <agent_name> - Show agent status")
    print("  list agents - List all agents")
    print("  quit - Exit")
    print()
    
    system = MultiAgentSystem()
    
    while True:
        try:
            user_input = input("👤 Command: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            elif user_input.startswith('create '):
                parts = user_input[7:].split()
                if len(parts) >= 2:
                    name = parts[0]
                    role_str = parts[1].upper()
                    try:
                        role = AgentRole[role_str]
                        system.add_agent(name, role)
                    except KeyError:
                        print(f"Invalid role. Use: {[r.name for r in AgentRole]}")
                else:
                    print("Usage: create <name> <role>")
            
            elif user_input.startswith('task '):
                parts = user_input[5:].split(' ', 1)
                if len(parts) == 2:
                    agent_name, description = parts
                    if agent_name in system.agents:
                        task_id = system.agents[agent_name].add_task(description)
                        print(f"Added task {task_id}")
                    else:
                        print(f"Agent {agent_name} not found")
                else:
                    print("Usage: task <agent_name> <description>")
            
            elif user_input.startswith('execute '):
                parts = user_input[8:].split()
                if len(parts) == 2:
                    agent_name, task_id = parts
                    if agent_name in system.agents:
                        result = system.agents[agent_name].execute_task(task_id)
                        print(f"Result: {result[:200]}...")
                    else:
                        print(f"Agent {agent_name} not found")
                else:
                    print("Usage: execute <agent_name> <task_id>")
            
            elif user_input.startswith('status '):
                agent_name = user_input[7:]
                if agent_name in system.agents:
                    agent = system.agents[agent_name]
                    print(f"Agent: {agent.name}")
                    print(f"Role: {agent.role.value}")
                    print(f"Tasks: {len(agent.tasks)}")
                    print(f"Capabilities: {len(agent.capabilities)}")
                    
                    # Show recent tasks
                    recent_tasks = agent.list_tasks()[-3:]
                    if recent_tasks:
                        print("Recent tasks:")
                        for task in recent_tasks:
                            print(f"  {task['id']}: {task['status']} - {task['description'][:50]}...")
                else:
                    print(f"Agent {agent_name} not found")
            
            elif user_input == 'list agents':
                if system.agents:
                    print("Agents:")
                    for name, agent in system.agents.items():
                        print(f"  {name} ({agent.role.value}) - {len(agent.tasks)} tasks")
                else:
                    print("No agents created")
            
            else:
                print("Unknown command. Type 'quit' to exit.")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("👋 Goodbye!")

if __name__ == "__main__":
    print("🚀 Custom Agent Framework with Arden Protection")
    print("Make sure you have:")
    print("1. Arden API key configured")
    print("2. Policies configured at https://arden.sh/dashboard")
    print()
    
    try:
        # Run single agent example
        run_single_agent_example()
        
        # Run multi-agent example
        run_multi_agent_example()
        
        # Enter interactive mode
        interactive_agent_mode()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Please check your Arden configuration.")
