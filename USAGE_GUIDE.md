# Arden Usage Guide: Approval Workflows for AI Agents

This guide explains how to integrate Arden's approval workflows into your AI agents using the three different modes: Wait, Async, and Webhook.

## Quick Overview

| Mode | Best For | Blocks Agent | Complexity | Scalability |
|------|----------|--------------|------------|-------------|
| **Wait** | Demos, simple agents | ✅ Yes | Low | Low |
| **Async** | Multi-task agents | ❌ No | Medium | Medium |
| **Webhook** | Production systems | ❌ No | High | High |

## Mode 1: Wait Mode (Default)

**When to use**: Simple agents, demos, single-threaded applications

**How it works**: Agent pauses and waits until human approves/denies the action.

### Basic Usage

```python
from ardenpy import guard_tool, configure

configure(api_key="test_12345_your_key")

# Protect any function
def send_email(to: str, message: str):
    return f"Email sent to {to}: {message}"

# Default wait mode - blocks until approval
safe_email = guard_tool("communication.email", send_email)

# Agent blocks here until approved/denied
result = safe_email("user@example.com", "Hello!")
print(result)  # Only runs if approved
```

### Agent Integration Examples

#### LangChain Agent (Wait Mode)
```python
from langchain.agents import create_openai_functions_agent
from langchain.tools import Tool
from ardenpy import guard_tool, configure

configure(api_key="test_12345_your_key")

def search_web(query: str) -> str:
    # Your search logic
    return f"Search results for: {query}"

def send_email(to: str, message: str) -> str:
    # Your email logic  
    return f"Email sent to {to}"

# Create protected tools (wait mode)
safe_search = guard_tool("web.search", search_web)
safe_email = guard_tool("communication.email", send_email)

# LangChain tools
tools = [
    Tool(name="search", func=safe_search, description="Search the web"),
    Tool(name="email", func=safe_email, description="Send email")
]

# Agent will pause at each protected tool call
agent = create_openai_functions_agent(llm, tools, prompt)
```

#### CrewAI Agent (Wait Mode)
```python
from crewai import Agent, Task, Crew
from ardenpy import guard_tool, configure

configure(api_key="test_12345_your_key")

def file_operations(action: str, filename: str) -> str:
    if action == "delete":
        return f"Deleted {filename}"
    return f"Performed {action} on {filename}"

# Protected tool
safe_file_ops = guard_tool("file.operations", file_operations)

# CrewAI agent
agent = Agent(
    role="File Manager",
    goal="Manage files safely",
    tools=[safe_file_ops],  # Agent pauses for approvals
    backstory="I manage files with human oversight"
)
```

## Mode 2: Async Mode

**When to use**: Multi-task agents, concurrent operations, when you need the agent to continue working

**How it works**: Agent continues working while approvals happen in background via callbacks.

### Basic Usage

```python
from ardenpy import guard_tool, configure

configure(api_key="test_12345_your_key")

def send_email(to: str, message: str):
    return f"Email sent to {to}: {message}"

# Callback functions
def on_email_approved(result):
    print(f"✅ Email sent successfully: {result}")
    # Continue with next steps...

def on_email_denied(error):
    print(f"❌ Email was blocked: {error}")
    # Handle denial...

# Async mode - non-blocking
safe_email = guard_tool(
    "communication.email", 
    send_email,
    approval_mode="async",
    on_approval=on_email_approved,
    on_denial=on_email_denied
)

# Returns immediately, callbacks called later
safe_email("user@example.com", "Hello!")
print("Agent continues working...")  # This runs immediately
```

### Agent Integration Examples

#### Multi-Task Agent (Async Mode)
```python
import asyncio
from ardenpy import guard_tool, configure

configure(api_key="test_12345_your_key")

class MultiTaskAgent:
    def __init__(self):
        self.tasks_completed = []
        self.setup_protected_tools()
    
    def setup_protected_tools(self):
        # Async callbacks
        def on_email_done(result):
            self.tasks_completed.append(f"Email: {result}")
            
        def on_file_done(result):
            self.tasks_completed.append(f"File: {result}")
            
        def on_denied(error):
            self.tasks_completed.append(f"Denied: {error}")
        
        # Protected tools with async mode
        self.safe_email = guard_tool(
            "communication.email", self.send_email,
            approval_mode="async",
            on_approval=on_email_done,
            on_denial=on_denied
        )
        
        self.safe_file_ops = guard_tool(
            "file.operations", self.file_operations,
            approval_mode="async", 
            on_approval=on_file_done,
            on_denial=on_denied
        )
    
    def send_email(self, to: str, message: str):
        return f"Email sent to {to}: {message}"
    
    def file_operations(self, action: str, filename: str):
        return f"Performed {action} on {filename}"
    
    async def run_agent(self):
        """Agent can handle multiple concurrent approvals"""
        print("🤖 Starting multi-task agent...")
        
        # Submit multiple tasks (all return immediately)
        self.safe_email("user1@example.com", "Task 1")
        self.safe_file_ops("delete", "temp.txt")
        self.safe_email("user2@example.com", "Task 2")
        
        print("📤 All tasks submitted, agent continues working...")
        
        # Agent can do other work while waiting for approvals
        for i in range(10):
            print(f"🔄 Doing other work... {i+1}/10")
            await asyncio.sleep(1)
        
        print(f"✅ Tasks completed: {len(self.tasks_completed)}")
        for task in self.tasks_completed:
            print(f"   - {task}")

# Usage
agent = MultiTaskAgent()
asyncio.run(agent.run_agent())
```

#### LangChain with Async Callbacks
```python
from langchain.agents import create_openai_functions_agent
from ardenpy import guard_tool, configure

class AsyncLangChainAgent:
    def __init__(self):
        configure(api_key="test_12345_your_key")
        self.pending_actions = {}
        self.setup_tools()
    
    def setup_tools(self):
        def on_search_approved(result):
            print(f"🔍 Search completed: {result}")
            # Could trigger follow-up actions
            
        def on_email_approved(result):
            print(f"📧 Email sent: {result}")
            # Could update conversation state
        
        # Async protected tools
        self.safe_search = guard_tool(
            "web.search", self.search_web,
            approval_mode="async",
            on_approval=on_search_approved,
            on_denial=lambda e: print(f"Search denied: {e}")
        )
        
        self.safe_email = guard_tool(
            "communication.email", self.send_email,
            approval_mode="async", 
            on_approval=on_email_approved,
            on_denial=lambda e: print(f"Email denied: {e}")
        )
    
    def search_web(self, query: str) -> str:
        return f"Search results for: {query}"
    
    def send_email(self, to: str, message: str) -> str:
        return f"Email sent to {to}: {message}"
```

## Mode 3: Webhook Mode

**When to use**: Production systems, microservices, high-scale applications

**How it works**: Agent submits actions and continues. Arden backend sends webhooks when approved/denied.

### Basic Usage

```python
from ardenpy import guard_tool, configure

configure(api_key="test_12345_your_key")

def send_email(to: str, message: str):
    return f"Email sent to {to}: {message}"

# Webhook mode - requires webhook server
safe_email = guard_tool(
    "communication.email",
    send_email,
    approval_mode="webhook",
    webhook_url="https://myapp.com/arden-webhook"
)

# Returns immediately, webhook handles execution
safe_email("user@example.com", "Hello!")
print("Agent continues immediately...")
```

### Webhook Server Implementation

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Store pending actions (use database in production)
pending_actions = {}

@app.route('/arden-webhook', methods=['POST'])
def handle_arden_webhook():
    """Handle approval notifications from Arden"""
    data = request.get_json()
    
    action_id = data['action_id']
    status = data['status']  # 'approved' or 'denied'
    
    if status == 'approved':
        # Execute the original function
        action_info = pending_actions.get(action_id)
        if action_info:
            func = action_info['func']
            args = action_info['args']
            kwargs = action_info['kwargs']
            
            try:
                result = func(*args, **kwargs)
                print(f"✅ Executed: {result}")
            except Exception as e:
                print(f"❌ Execution failed: {e}")
    else:
        print(f"❌ Action {action_id} was denied")
    
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Production Agent with Webhooks

```python
class ProductionAgent:
    def __init__(self, webhook_url: str):
        configure(api_key="live_your_production_key")
        self.webhook_url = webhook_url
        self.setup_protected_tools()
    
    def setup_protected_tools(self):
        # All tools use webhook mode
        self.safe_email = guard_tool(
            "communication.email", self.send_email,
            approval_mode="webhook",
            webhook_url=self.webhook_url
        )
        
        self.safe_payment = guard_tool(
            "finance.payment", self.process_payment,
            approval_mode="webhook", 
            webhook_url=self.webhook_url
        )
        
        self.safe_data_delete = guard_tool(
            "data.delete", self.delete_user_data,
            approval_mode="webhook",
            webhook_url=self.webhook_url
        )
    
    def send_email(self, to: str, message: str):
        # Your email implementation
        return f"Email sent to {to}"
    
    def process_payment(self, amount: float, account: str):
        # Your payment implementation
        return f"Processed ${amount} to {account}"
    
    def delete_user_data(self, user_id: str):
        # Your data deletion implementation
        return f"Deleted data for {user_id}"
    
    async def handle_user_request(self, request: str):
        """Handle user requests with webhook approvals"""
        
        if "send email" in request.lower():
            # Submits immediately, webhook handles execution
            self.safe_email("user@example.com", "Hello!")
            return "Email request submitted for approval"
        
        elif "process payment" in request.lower():
            # Submits immediately, webhook handles execution
            self.safe_payment(100.0, "account-123")
            return "Payment request submitted for approval"
        
        elif "delete data" in request.lower():
            # Submits immediately, webhook handles execution
            self.safe_data_delete("user-456")
            return "Data deletion request submitted for approval"
        
        else:
            return "I can help with emails, payments, and data deletion"

# Usage
agent = ProductionAgent("https://myapp.com/arden-webhook")
response = await agent.handle_user_request("send email to user")
print(response)  # "Email request submitted for approval"
```

## Choosing the Right Mode

### Use Wait Mode When:
- Building demos or prototypes
- Simple, single-threaded agents
- You want the simplest possible integration
- Agent can afford to pause for approvals

### Use Async Mode When:
- Agent needs to handle multiple concurrent tasks
- You want to provide immediate feedback to users
- Agent should continue working while waiting for approvals
- You can implement callback functions

### Use Webhook Mode When:
- Building production systems
- High-scale applications with many agents
- Microservices architecture
- You need the most scalable solution
- You can implement webhook infrastructure

## Best Practices

### Security
- Always use HTTPS for webhook URLs
- Validate webhook signatures in production
- Store API keys securely (environment variables)
- Use different API keys for test vs production

### Error Handling
```python
# Always handle denials gracefully
def on_denial(error):
    logger.warning(f"Action denied: {error}")
    # Inform user, try alternative approach, etc.

def on_error(error):
    logger.error(f"Execution failed: {error}")
    # Retry logic, fallback actions, etc.
```

### Monitoring
- Log all approval requests and outcomes
- Monitor approval response times
- Set up alerts for high denial rates
- Track webhook delivery success rates

### Testing
```python
# Test with different approval outcomes
def test_approval_workflow():
    # Test approved case
    safe_tool = guard_tool("test.tool", my_function)
    # ... test logic
    
    # Test denied case
    # ... configure policy to deny
    # ... test denial handling
```

This guide provides comprehensive examples for integrating Arden into any type of AI agent architecture while choosing the right approval mode for your use case.
