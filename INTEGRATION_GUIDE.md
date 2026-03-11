# Arden Integration Guide

## User Journey Overview

### 1. **Get Started (2 minutes)**
1. Visit [https://arden.dev](https://arden.dev)
2. Sign up and get your API keys:
   - **Test API Key**: `test_abc123...` (for development)
   - **Live API Key**: `live_xyz789...` (for production)
3. Install the SDK: `pip install ardenpy`

### 2. **Integrate (5 minutes)**
```python
from ardenpy import guard_tool, configure

# One-time setup
configure(api_key="test_abc123_your_key_here")

# Wrap any dangerous function
protected_function = guard_tool("tool.name", your_function)

# Use normally - policies enforced automatically
result = protected_function(args)
```

### 3. **Configure Policies (10 minutes)**
- Visit [https://agentgate.dev/dashboard](https://agentgate.dev/dashboard)
- Create policies using natural language:
  - "Allow file reads immediately"
  - "Require approval for transfers over $1000"
  - "Block all system commands"

### 4. **Deploy & Monitor**
- Switch to live API key for production
- Monitor tool calls and approvals in dashboard
- Receive notifications via email/Slack/webhooks

---

## Framework Integration Examples

### LangChain Integration

```python
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI
from ardenpy import guard_tool, configure

# Configure Arden
configure(api_key="your-api-key-here")

# Define your tools
def search_web(query: str) -> str:
    """Search the web for information."""
    # Your web search implementation
    return f"Search results for: {query}"

def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email."""
    # Your email implementation
    return f"Email sent to {recipient}"

def execute_code(code: str) -> str:
    """Execute Python code."""
    # Your code execution implementation
    return f"Executed: {code}"

# Protect tools with Arden
protected_search = guard_tool("web.search", search_web)
protected_email = guard_tool("communication.email", send_email)
protected_code = guard_tool("code.execute", execute_code)

# Create LangChain tools
tools = [
    Tool(
        name="WebSearch",
        description="Search the web for current information",
        func=protected_search
    ),
    Tool(
        name="SendEmail", 
        description="Send an email to someone",
        func=protected_email
    ),
    Tool(
        name="ExecuteCode",
        description="Execute Python code",
        func=protected_code
    )
]

# Initialize agent with protected tools
llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",
    verbose=True
)

# Use the agent - Arden policies apply automatically
response = agent.run("Search for Python tutorials and email the results to john@example.com")
```

### AutoGPT Integration

```python
from ardenpy import guard_tool, configure
import json

# Configure Arden
configure(api_key="your-api-key-here")

class ProtectedAutoGPT:
    """AutoGPT with Arden protection."""
    
    def __init__(self):
        # Protect all agent capabilities
        self.file_operations = {
            "read": guard_tool("file.read", self._read_file),
            "write": guard_tool("file.write", self._write_file),
            "delete": guard_tool("file.delete", self._delete_file),
        }
        
        self.web_operations = {
            "browse": guard_tool("web.browse", self._browse_web),
            "search": guard_tool("web.search", self._search_web),
        }
        
        self.system_operations = {
            "execute": guard_tool("system.execute", self._execute_command),
            "install": guard_tool("system.install", self._install_package),
        }
        
        self.communication = {
            "email": guard_tool("communication.email", self._send_email),
            "slack": guard_tool("communication.slack", self._send_slack),
        }
    
    def _read_file(self, filepath: str) -> str:
        """Read file contents."""
        with open(filepath, 'r') as f:
            return f.read()
    
    def _write_file(self, filepath: str, content: str) -> bool:
        """Write content to file."""
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    
    def _delete_file(self, filepath: str) -> bool:
        """Delete a file."""
        import os
        os.remove(filepath)
        return True
    
    def _browse_web(self, url: str) -> str:
        """Browse a webpage."""
        # Web browsing implementation
        return f"Content from {url}"
    
    def _search_web(self, query: str) -> str:
        """Search the web."""
        # Web search implementation
        return f"Search results for: {query}"
    
    def _execute_command(self, command: str) -> str:
        """Execute system command."""
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    
    def _install_package(self, package: str) -> str:
        """Install a Python package."""
        import subprocess
        result = subprocess.run(f"pip install {package}", shell=True, capture_output=True, text=True)
        return result.stdout
    
    def _send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email."""
        # Email implementation
        return True
    
    def _send_slack(self, channel: str, message: str) -> bool:
        """Send Slack message."""
        # Slack implementation
        return True
    
    def execute_action(self, action: dict) -> str:
        """Execute an action with Arden protection."""
        action_type = action.get("type")
        
        if action_type == "file_operation":
            operation = action["operation"]
            return self.file_operations[operation](**action["args"])
        
        elif action_type == "web_operation":
            operation = action["operation"]
            return self.web_operations[operation](**action["args"])
        
        elif action_type == "system_operation":
            operation = action["operation"]
            return self.system_operations[operation](**action["args"])
        
        elif action_type == "communication":
            operation = action["operation"]
            return self.communication[operation](**action["args"])
        
        else:
            raise ValueError(f"Unknown action type: {action_type}")

# Usage example
agent = ProtectedAutoGPT()

# Example actions - all protected by Arden
actions = [
    {
        "type": "web_operation",
        "operation": "search",
        "args": {"query": "Python best practices"}
    },
    {
        "type": "file_operation", 
        "operation": "write",
        "args": {"filepath": "research.txt", "content": "Python research results..."}
    },
    {
        "type": "communication",
        "operation": "email",
        "args": {"to": "team@company.com", "subject": "Research Complete", "body": "Found great resources!"}
    }
]

for action in actions:
    try:
        result = agent.execute_action(action)
        print(f"Action completed: {result}")
    except Exception as e:
        print(f"Action blocked or failed: {e}")
```

### CrewAI Integration

```python
from crewai import Agent, Task, Crew
from ardenpy import guard_tool, configure

# Configure Arden
configure(api_key="your-api-key-here")

# Define protected tools
def research_topic(topic: str) -> str:
    """Research a topic online."""
    # Research implementation
    return f"Research results for {topic}"

def write_article(content: str, filename: str) -> str:
    """Write article to file."""
    with open(filename, 'w') as f:
        f.write(content)
    return f"Article written to {filename}"

def send_for_review(filepath: str, reviewer_email: str) -> str:
    """Send article for review."""
    # Email implementation
    return f"Sent {filepath} to {reviewer_email} for review"

def publish_article(filepath: str, platform: str) -> str:
    """Publish article to platform."""
    # Publishing implementation
    return f"Published {filepath} to {platform}"

# Protect tools with Arden
protected_research = guard_tool("research.topic", research_topic)
protected_write = guard_tool("content.write", write_article)
protected_review = guard_tool("workflow.send_review", send_for_review)
protected_publish = guard_tool("content.publish", publish_article)

# Create agents with protected tools
researcher = Agent(
    role='Research Specialist',
    goal='Research topics thoroughly and accurately',
    backstory='Expert at finding reliable information online',
    tools=[protected_research],
    verbose=True
)

writer = Agent(
    role='Content Writer',
    goal='Write engaging articles based on research',
    backstory='Skilled writer who creates compelling content',
    tools=[protected_write],
    verbose=True
)

editor = Agent(
    role='Editor',
    goal='Review and improve content quality',
    backstory='Detail-oriented editor with high standards',
    tools=[protected_review],
    verbose=True
)

publisher = Agent(
    role='Publisher',
    goal='Publish content to appropriate platforms',
    backstory='Experienced in content distribution',
    tools=[protected_publish],
    verbose=True
)

# Define tasks
research_task = Task(
    description='Research the latest trends in AI safety',
    agent=researcher
)

writing_task = Task(
    description='Write a comprehensive article about AI safety trends',
    agent=writer
)

editing_task = Task(
    description='Review the article and send for approval',
    agent=editor
)

publishing_task = Task(
    description='Publish the approved article',
    agent=publisher
)

# Create crew with protected workflow
crew = Crew(
    agents=[researcher, writer, editor, publisher],
    tasks=[research_task, writing_task, editing_task, publishing_task],
    verbose=2
)

# Execute crew workflow - all tools protected by Arden
result = crew.kickoff()
print(result)
```

### Custom Agent Framework Integration

```python
from ardenpy import guard_tool, configure
from typing import Dict, Any, Callable
import json

# Configure Arden
configure(api_key="your-api-key-here")

class SecureAgent:
    """Custom agent framework with Arden integration."""
    
    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, Callable] = {}
        self.conversation_history = []
    
    def register_tool(self, tool_name: str, tool_function: Callable, arden_name: str):
        """Register a tool with Arden protection."""
        protected_tool = guard_tool(arden_name, tool_function)
        self.tools[tool_name] = protected_tool
        print(f"Registered protected tool: {tool_name} -> {arden_name}")
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool with Arden protection."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        try:
            result = self.tools[tool_name](**kwargs)
            self.conversation_history.append({
                "action": "tool_execution",
                "tool": tool_name,
                "args": kwargs,
                "result": result,
                "status": "success"
            })
            return result
        except Exception as e:
            self.conversation_history.append({
                "action": "tool_execution", 
                "tool": tool_name,
                "args": kwargs,
                "error": str(e),
                "status": "failed"
            })
            raise
    
    def process_request(self, user_input: str) -> str:
        """Process user request and execute appropriate tools."""
        # Simple rule-based processing (in real implementation, use LLM)
        
        if "search" in user_input.lower():
            query = user_input.replace("search", "").strip()
            result = self.execute_tool("web_search", query=query)
            return f"Search completed: {result}"
        
        elif "email" in user_input.lower():
            # Extract email details (simplified)
            result = self.execute_tool("send_email", 
                                     to="user@example.com", 
                                     subject="Agent Response",
                                     body=user_input)
            return f"Email sent: {result}"
        
        elif "file" in user_input.lower() and "read" in user_input.lower():
            result = self.execute_tool("read_file", filepath="data.txt")
            return f"File content: {result}"
        
        elif "calculate" in user_input.lower():
            # Extract numbers (simplified)
            result = self.execute_tool("calculator", expression="2+2")
            return f"Calculation result: {result}"
        
        else:
            return "I don't understand that request."

# Define tool functions
def web_search(query: str) -> str:
    """Search the web."""
    return f"Found results for: {query}"

def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to} with subject '{subject}'"

def read_file(filepath: str) -> str:
    """Read a file."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"File {filepath} not found"

def calculator(expression: str) -> str:
    """Calculate mathematical expressions."""
    try:
        result = eval(expression)  # Note: Use safe eval in production
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"

def delete_file(filepath: str) -> str:
    """Delete a file."""
    import os
    try:
        os.remove(filepath)
        return f"Deleted {filepath}"
    except FileNotFoundError:
        return f"File {filepath} not found"

# Create agent and register protected tools
agent = SecureAgent("MySecureAgent")

agent.register_tool("web_search", web_search, "web.search")
agent.register_tool("send_email", send_email, "communication.email") 
agent.register_tool("read_file", read_file, "file.read")
agent.register_tool("calculator", calculator, "math.calculate")
agent.register_tool("delete_file", delete_file, "file.delete")

# Example usage
requests = [
    "Search for Python tutorials",
    "Send email about the meeting",
    "Read file contents", 
    "Calculate 15 * 23",
    "Delete temporary file"
]

for request in requests:
    try:
        response = agent.process_request(request)
        print(f"Request: {request}")
        print(f"Response: {response}\n")
    except Exception as e:
        print(f"Request: {request}")
        print(f"Error: {e}\n")

# View conversation history
print("Conversation History:")
print(json.dumps(agent.conversation_history, indent=2))
```

---

## Policy Configuration Examples

### Dashboard Configuration
Visit [https://agentgate.dev/dashboard](https://agentgate.dev/dashboard) and create policies like:

```yaml
# Safe operations - allow immediately
- name: "Web Search"
  tool: "web.search"
  action: "allow"
  
- name: "File Read"
  tool: "file.read" 
  action: "allow"

# Sensitive operations - require approval  
- name: "Email Sending"
  tool: "communication.email"
  action: "require_approval"
  policy: "Allow internal emails immediately, but require approval for external emails"
  
- name: "File Deletion"
  tool: "file.delete"
  action: "require_approval"
  policy: "Allow deleting .tmp files immediately, but require approval for any other files"

# Dangerous operations - block completely
- name: "System Commands"
  tool: "system.execute"
  action: "block"
  
- name: "Code Execution"
  tool: "code.execute"
  action: "block"
```

### CLI Configuration (Coming Soon)
```bash
# Upload policies from file
agentgate policies upload --file my-policies.yaml

# Test a policy
agentgate policies test --tool "file.delete" --args '{"filepath": "/important/data.txt"}'

# List current policies
agentgate policies list
```

---

## Best Practices

### 1. **Start with Test API Key**
- Use test API key during development
- Test all tool integrations thoroughly
- Verify policy behavior before going live

### 2. **Gradual Rollout**
- Start with `allow` policies for all tools
- Gradually add `require_approval` for sensitive operations
- Only use `block` for truly dangerous operations

### 3. **Tool Naming Convention**
Use descriptive, hierarchical names:
- `file.read`, `file.write`, `file.delete`
- `communication.email`, `communication.slack`
- `database.select`, `database.update`, `database.delete`
- `system.execute`, `system.install`

### 4. **Error Handling**
```python
from agentgate.types import PolicyDeniedError, ApprovalTimeoutError

try:
    result = protected_tool(args)
except PolicyDeniedError as e:
    print(f"Tool blocked by policy: {e}")
except ApprovalTimeoutError as e:
    print(f"Approval timed out: {e}")
except Exception as e:
    print(f"Tool execution failed: {e}")
```

### 5. **Monitoring & Alerts**
- Set up email/Slack notifications for approval requests
- Monitor tool usage patterns in dashboard
- Review and adjust policies based on usage data

---

## Deployment Checklist

- [ ] Install Arden SDK: `pip install ardenpy`
- [ ] Get API keys from [arden.dev](https://arden.dev)
- [ ] Wrap sensitive tools with `guard_tool()`
- [ ] Configure policies in dashboard
- [ ] Test with test API key
- [ ] Set up approval notifications
- [ ] Switch to live API key for production
- [ ] Monitor tool usage and approvals

Arden provides a universal safety layer that works with any Python agent framework, giving you precise control over what your agents can do while maintaining the flexibility to adjust policies in real-time.
