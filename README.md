# Arden Python SDK

**AI Agent Warden - Keep Your AI Agents in Check**

Arden is the warden for your AI agents. Enforce policies, require human approval for sensitive actions, and maintain control over what your agents can actually do - no matter which framework you use.

## Installation

```bash
pip install ardenpy
```

## Quick Start

### 1. Get API Key
Visit [https://arden.sh](https://arden.sh) to get your free test API key.

Your test API key will start with `test_` and automatically connect to the test environment at `https://api-test.arden.sh`.

### 2. Protect Your Functions

```python
from ardenpy import guard_tool, configure

# Configure once
configure(api_key="test_12345_your_api_key_here")

# Protect different types of functions
def read_file(filename: str):
    # Low-risk operation - typically ALLOWED
    return f"Reading {filename}"

def send_email(to: str, subject: str, message: str):
    # Medium-risk operation - typically REQUIRES APPROVAL
    return f"Email sent to {to}: {subject}"

def delete_database(table: str):
    # High-risk operation - typically BLOCKED
    return f"Deleted table {table}"

# Apply protection with descriptive tool names
safe_read = guard_tool("file.read", read_file)
safe_email = guard_tool("communication.email", send_email)  
safe_delete = guard_tool("database.delete", delete_database)

# Use normally - Arden enforces your policies
result1 = safe_read("report.txt")        # ✅ Executes immediately (allowed)
result2 = safe_email("user@co.com", "Hi", "Hello")  # ⏳ Waits for approval
result3 = safe_delete("users")           # ❌ Throws error (blocked)
```

## How Arden Works

**Step 1: Protect your functions with descriptive names**
```python
def read_config(filename: str):
    return f"Config from {filename}"

def send_email(to: str, message: str):
    return f"Email sent to {to}: {message}"

def delete_files(pattern: str):
    return f"Deleted files matching {pattern}"

# Use descriptive tool names that match your policies
safe_read = guard_tool("config.read", read_config)      # Low risk
safe_email = guard_tool("communication.email", send_email)  # Medium risk  
safe_delete = guard_tool("file.delete", delete_files)   # High risk
```

**Step 2: Use in any framework**
```python
# Policy enforcement happens automatically:
config = safe_read("app.json")           # ✅ Allowed - executes immediately
safe_email("user@co.com", "Hello")      # ⏳ Requires approval - waits for human
safe_delete("*.tmp")                    # ❌ Blocked - throws PolicyError
```

**Step 3: Configure policies by risk level**
Set policies at [https://arden.sh/dashboard](https://arden.sh/dashboard) based on risk:

**Low Risk (Allow)**: `config.read`, `data.read`, `file.read`
**Medium Risk (Requires Approval)**: `communication.*`, `api.post`, `file.write`  
**High Risk (Block)**: `file.delete`, `database.drop`, `system.exec`

**Step 4: Choose approval workflow**
You can choose how approvals work (all examples work with any framework):

### Default: Wait for Approval
```python
safe_email = guard_tool("communication.email", send_email)
result = safe_email("user@example.com", "Hello")  # Pauses until approved
```

### Advanced: Async Callbacks  
```python
# For sensitive operations that need approval but shouldn't block
safe_deploy = guard_tool(
    "deployment.production", deploy_to_prod,
    approval_mode="async",
    on_approval=lambda result: notify_team(f"Deployment successful: {result}"),
    on_denial=lambda error: alert_team(f"Deployment blocked: {error}")
)
safe_deploy("v2.1.0")  # Returns immediately, callbacks handle result
```

### Production: Webhooks
```python
# For high-volume operations with external approval systems
safe_payment = guard_tool(
    "payment.process", process_payment,
    approval_mode="webhook", 
    webhook_url="https://approval-system.company.com/webhook"
)
safe_payment(amount=1000, customer="cust_123")  # Webhook notifies approval system
```

## Framework Integration

The same protected functions work with any agent framework:

### LangChain
```python
from langchain.tools import Tool
from ardenpy import guard_tool

# Protect different risk levels
def web_search(query: str):
    return f"Search results for: {query}"

def send_slack_message(channel: str, message: str):
    return f"Posted to #{channel}: {message}"

def execute_sql(query: str):
    return f"Executed: {query}"

# Apply appropriate protection levels
safe_search = guard_tool("web.search", web_search)           # Low risk - allow
safe_slack = guard_tool("communication.slack", send_slack_message)  # Medium risk - approval
safe_sql = guard_tool("database.execute", execute_sql)      # High risk - block

tools = [
    Tool(name="search", func=safe_search, description="Search the web"),
    Tool(name="slack", func=safe_slack, description="Send Slack messages"),
    Tool(name="sql", func=safe_sql, description="Execute SQL queries")
]
```

### CrewAI
```python
from crewai import Tool
from ardenpy import guard_tool

# Realistic agent tools with different risk profiles
@tool("research_tool")
def research_web(topic: str):
    protected_search = guard_tool("research.web", lambda q: f"Research on {q}")
    return protected_search(topic)  # Allowed - research is low risk

@tool("communication_tool") 
def send_email(recipient: str, content: str):
    protected_email = guard_tool("communication.email", lambda r, c: f"Email to {r}")
    return protected_email(recipient, content)  # Requires approval - external communication

@tool("system_tool")
def deploy_code(environment: str):
    protected_deploy = guard_tool("deployment.production", lambda e: f"Deploy to {e}")
    return protected_deploy(environment)  # Blocked or requires approval - high risk
```

### Custom Agents
```python
class SecurityAwareAgent:
    def __init__(self):
        # Different protection levels for different capabilities
        self.read_data = guard_tool("data.read", self._read_data)           # Allow
        self.send_email = guard_tool("communication.email", self._send_email)  # Approval
        self.delete_files = guard_tool("file.delete", self._delete_files)   # Block
        
    def _read_data(self, source: str):
        return f"Reading data from {source}"
        
    def _send_email(self, to: str, message: str):
        return f"Email sent to {to}: {message}"
        
    def _delete_files(self, pattern: str):
        return f"Deleted files matching {pattern}"
```

## Examples

See the `examples/` directory for complete working examples:

- **getting_started.py** - Simple 3-step introduction
- **langchain_integration.py** - LangChain + Arden
- **crewai_integration.py** - CrewAI + Arden  
- **autogpt_integration.py** - AutoGPT + Arden
- **direct_openai_integration.py** - Direct OpenAI (no frameworks)

## Publishing

Use the included publishing script:

```bash
python publish.py
```

## Links

- **Website**: [https://arden.sh](https://arden.sh)
- **Dashboard**: [https://app.arden.sh/dashboard](https://arden.sh/dashboard)  
- **Documentation**: [https://app.arden.sh/docs](https://arden.sh/docs)
- **Support**: [team@arden.sh](mailto:team@arden.sh)
- **PyPI Package**: [https://pypi.org/project/ardenpy/](https://pypi.org/project/ardenpy/)

## License

MIT License - see LICENSE file for details.
