# Local Development Guide

## Testing Without pip install

You can test Arden locally without pip install or the hosted service using the mock backend.

### Quick Start

1. **Start the mock backend**:
```bash
# Install FastAPI for mock backend
pip install fastapi uvicorn

# Start mock server
python mock_backend.py
```

2. **Run local setup**:
```bash
python local_dev_setup.py
```

3. **Test with simple example**:
```bash
python local_test.py
```

4. **Run agent examples**:
```bash
python examples/local_simple_agent.py
```

### What's Included

#### Mock Backend (`mock_backend.py`)
- **Full API compatibility** with Arden service
- **Default policies** for common tools (allow/require_approval/block)
- **Approval workflow** with auto-approval for testing
- **Policy management** endpoints
- **Debug endpoints** for testing

#### Local Development Setup (`local_dev_setup.py`)
- **Path configuration** to import ardenpy without pip install
- **Verification** that everything works
- **Test file creation** for quick validation

#### Local Examples
- **`local_test.py`** - Basic functionality test
- **`examples/local_simple_agent.py`** - Full agent example with mock backend

### Mock Backend Features

The mock backend provides:

- **Policy Evaluation**: Matches tools against policies
- **Approval Workflow**: Simulates human approval process
- **Auto-approval**: 10% chance of auto-approval for testing
- **Policy Management**: Create, update, delete policies
- **Debug Endpoints**: Manual approval, data reset

### Default Policies

The mock backend comes with realistic policies:

```yaml
# Allowed immediately
- web.search: allow
- file.read: allow  
- math.calculate: allow

# Require approval
- file.write: require_approval (5 min timeout)
- communication.email: require_approval (10 min timeout)
- file.delete: require_approval (10 min timeout)

# Blocked completely
- system.execute: block
- code.execute: block
```

### API Endpoints

Mock backend provides all Arden endpoints:

- `POST /check` - Policy evaluation
- `GET /status/{action_id}` - Check approval status
- `POST /approve/{action_id}` - Approve action
- `GET /actions` - List all actions
- `GET /policies` - List policies
- `POST /policies` - Create policy
- `GET /debug/auto-approve/{action_id}` - Force approval (testing)

### Testing Different Scenarios

#### 1. Allowed Operations
```python
# These should execute immediately
safe_calculate = guard_tool("math.calculate", calculate_function)
result = safe_calculate(5, 7)  # ✅ Executes
```

#### 2. Approval Required
```python
# These will require approval (or timeout)
safe_write = guard_tool("file.write", write_function)
result = safe_write("file.txt", "content")  # ⏳ Waits for approval
```

#### 3. Blocked Operations
```python
# These will be blocked immediately
safe_execute = guard_tool("system.execute", execute_function)
result = safe_execute("rm -rf /")  # ❌ Blocked
```

### Manual Approval Testing

To test the approval workflow:

1. **Trigger approval-required action**:
```python
safe_write = guard_tool("file.write", write_function)
safe_write("test.txt", "content")  # Will wait for approval
```

2. **Check pending actions**:
```bash
curl http://localhost:8000/actions?status=pending
```

3. **Manually approve**:
```bash
curl -X POST http://localhost:8000/approve/action_123 \
  -H "Content-Type: application/json" \
  -d '{"action_id": "action_123", "approved": true}'
```

4. **Or use debug endpoint**:
```bash
curl http://localhost:8000/debug/auto-approve/action_123
```

### Customizing Policies

Add custom policies via API:

```bash
curl -X POST http://localhost:8000/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Tool",
    "tool": "custom.tool",
    "action": "require_approval",
    "description": "Custom tool needs approval",
    "timeout": 300
  }'
```

### Directory Structure

```
ardenpy-sdk/
├── ardenpy/              # SDK source code
├── examples/               # Agent examples
│   ├── local_simple_agent.py  # Local development example
│   ├── langchain_agent.py     # LangChain integration
│   └── ...
├── mock_backend.py         # Local mock server
├── local_dev_setup.py      # Development setup
├── local_test.py          # Basic test (created by setup)
└── LOCAL_DEVELOPMENT.md   # This guide
```

### Troubleshooting

#### Import Errors
```bash
# Make sure you're in the right directory
cd ardenpy-sdk

# Run setup again
python local_dev_setup.py
```

#### Mock Backend Not Running
```bash
# Check if running
curl http://localhost:8000/health

# Start if needed
python mock_backend.py
```

#### Connection Errors
```python
# Make sure SDK points to local backend
configure(
    api_key="test_local_key",
    api_url="http://localhost:8000"  # Not https://api.arden.dev
)
```

This setup lets you develop and test Arden integration completely offline without any external dependencies!
