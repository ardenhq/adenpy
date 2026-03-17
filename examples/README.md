# Arden Examples

Clean, working examples demonstrating Arden integration with AI agents.

## Quick Start

```bash
pip install ardenpy
python examples/getting_started.py
```

## Examples

### 🚀 **getting_started.py** - Start Here!
The simplest possible introduction to Arden protection.

### 🤖 **simple_agent.py** 
Basic agent with common protected operations.

### 🛠️ **custom_agent.py**
Custom AI assistant with interactive demo.

### 🔄 **approval_workflows_demo.py** - NEW! Approval Workflows
Demonstrates all three approval modes:
- **Wait mode** (default): Blocks until approval/denial
- **Async mode**: Non-blocking with callbacks  
- **Webhook mode**: Real-time webhook notifications

### 🌐 **production_webhook_server.py** - Production Webhooks
Complete production-ready webhook server for scalable approval workflows. Shows how to implement non-blocking approvals in production systems.

### 🌟 **direct_openai_integration.py** - Direct OpenAI
Shows direct OpenAI integration without frameworks. Use when building custom agents.

**Requirements**: 
```bash
export OPENAI_API_KEY="your_openai_key"
export ARDEN_API_KEY="test_12345_your_arden_key"
python direct_openai_integration.py
```

## Framework Integrations

### 🦜 **langchain_integration.py** - LangChain + Arden
Complete LangChain agent with Arden-protected tools.

**Requirements**: 
```bash
pip install langchain langchain-openai ardenpy requests
export OPENAI_API_KEY="your_openai_key"
export ARDEN_API_KEY="test_12345_your_arden_key"
python langchain_integration.py
```

### 👥 **crewai_integration.py** - CrewAI + Arden  
Multi-agent CrewAI crew with Arden protection.

**Requirements**:
```bash
pip install crewai crewai-tools ardenpy requests
export OPENAI_API_KEY="your_openai_key"
export ARDEN_API_KEY="test_12345_your_arden_key"
python crewai_integration.py
```

### 🤖 **autogpt_integration.py** - AutoGPT + Arden
Autonomous agent with Arden-protected commands.

**Requirements**:
```bash
pip install openai ardenpy requests
export OPENAI_API_KEY="your_openai_key"
export ARDEN_API_KEY="test_12345_your_arden_key"
python autogpt_integration.py
```


## Configuration

```python
from ardenpy import configure

# Test environment (auto-detected from key prefix)
configure(api_key="test_12345_your_api_key_here")

# Production environment
configure(api_key="live_67890_your_api_key", environment="live")
```

## Framework Integration Pattern

All frameworks use the same Arden pattern:

```python
from ardenpy import guard_tool

# 1. Protect your functions
safe_function = guard_tool("policy.name", original_function)

# 2. Use in any framework
# LangChain: Tool(func=safe_function)
# CrewAI: BaseTool with safe_function
# Custom: self.tool = safe_function
```

## Getting Help

- **Get API Key**:
   - Visit [https://arden.sh](https://arden.sh)
   - Sign up and get your free test API key
- **Website**: [https://arden.sh](https://arden.sh)
- **Dashboard**: [https://arden.sh/dashboard](https://arden.sh/dashboard)
- **Support**: [team@arden.sh](mailto:team@arden.sh)
