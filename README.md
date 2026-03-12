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

### 2. Protect Your Functions

```python
from ardenpy import guard_tool, configure

# Configure once
configure(api_key="test_12345_your_api_key_here")

# Protect any function
def send_email(to: str, subject: str, message: str):
    # Your email logic here
    return f"Email sent to {to}"

def delete_files(pattern: str):
    # Your file deletion logic here
    return f"Deleted files matching {pattern}"

# Apply protection
safe_email = guard_tool("communication.email", send_email)
safe_delete = guard_tool("file.delete", delete_files)

# Use normally - Arden handles security
result = safe_email("user@example.com", "Hello", "Test message")
# ↑ May require approval based on your policies
```

## How Arden Works

**Step 1: Protect your functions**
```python
def send_email(to: str, message: str):
    return f"Email sent to {to}: {message}"

# Wrap with Arden protection
safe_email = guard_tool("communication.email", send_email)
```

**Step 2: Use in any framework**
```python
# Works the same in any framework:
result = safe_email("user@example.com", "Hello")  # May require approval
```

**Step 3: Choose approval behavior**
You can choose how approvals work (all examples work with any framework):

### Default: Wait for Approval
```python
safe_email = guard_tool("communication.email", send_email)
result = safe_email("user@example.com", "Hello")  # Pauses until approved
```

### Advanced: Async Callbacks  
```python
safe_email = guard_tool(
    "communication.email", send_email,
    approval_mode="async",
    on_approval=lambda result: print(f"Sent: {result}"),
    on_denial=lambda error: print(f"Blocked: {error}")
)
safe_email("user@example.com", "Hello")  # Returns immediately, callbacks later
```

### Production: Webhooks
```python
safe_email = guard_tool(
    "communication.email", send_email,
    approval_mode="webhook", 
    webhook_url="https://myapp.com/webhook"
)
safe_email("user@example.com", "Hello")  # Returns immediately, webhook handles result
```

## Framework Integration

The same protected functions work with any agent framework:

### LangChain
```python
from langchain.tools import Tool
from ardenpy import guard_tool

safe_search = guard_tool("web.search", search_function)
tools = [Tool(name="search", func=safe_search, description="Search web")]
```

### CrewAI
```python
from crewai import Tool
from ardenpy import guard_tool

@tool("protected_file_ops")
def file_operations(action: str, filename: str):
    return guard_tool("file.delete", delete_file)(filename)
```

### Custom Agents
```python
class MyAgent:
    def __init__(self):
        self.search = guard_tool("web.search", self._search)
        self.email = guard_tool("communication.email", self._email)
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
- **Dashboard**: [https://arden.sh/dashboard](https://arden.sh/dashboard)  
- **Documentation**: [https://arden.sh/docs](https://arden.sh/docs)
- **Support**: [team@arden.dev](mailto:team@arden.dev)
- **PyPI Package**: [https://pypi.org/project/ardenpy/](https://pypi.org/project/ardenpy/)

## License

MIT License - see LICENSE file for details.
