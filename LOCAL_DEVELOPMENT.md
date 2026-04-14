# Local Development

## Running without the hosted backend

A mock backend (`mock_backend.py`) is included for local development and testing.
It implements the same API as `api.arden.sh` so you can develop without an internet
connection or a real API key.

### Start the mock server

```bash
pip install fastapi uvicorn
python mock_backend.py
# Server runs at http://localhost:8000
```

### Point the SDK at it

```python
import ardenpy as arden

arden.configure(
    api_key="arden_test_localdev",
    api_url="http://localhost:8000",
)
```

### Default mock policies

The mock backend ships with these policies:

| Tool pattern | Decision |
|-------------|----------|
| `web.search`, `file.read`, `math.*` | allow |
| `file.write`, `communication.*` | requires_approval |
| `system.execute`, `code.execute` | block |

Everything else: **allow** (no policy configured).

### Manually approving actions

```bash
# List pending actions
curl http://localhost:8000/actions?status=pending

# Approve
curl -X POST http://localhost:8000/approve/<action_id> \
     -H "Content-Type: application/json" \
     -d '{"message": "approved for testing"}'

# Force auto-approve (debug endpoint)
curl http://localhost:8000/debug/auto-approve/<action_id>
```

---

## Running tests

```bash
# Install dev dependencies
python -m venv .venv
.venv/bin/pip install -e ".[all]" pytest boto3 -q

# Unit tests (no network, no AWS)
.venv/bin/pytest tests/ -v -m "not integration"

# Integration tests (requires live backend + AWS credentials)
AWS_DEFAULT_PROFILE=arden-dev .venv/bin/pytest tests/ -v -m integration -s
```

---

## Installing the SDK from source

```bash
git clone <repo>
cd ardenpy
pip install -e .           # editable install
pip install -e ".[all]"    # with all framework extras
```

---

## Project structure

```
ardenpy/
├── ardenpy/                # SDK source
│   ├── __init__.py
│   ├── guard.py            # guard_tool(), handle_webhook(), verify_webhook_signature()
│   ├── client.py           # ArdenClient HTTP layer
│   ├── config.py           # configure(), ArdenConfig
│   ├── types.py            # PolicyDecision, WebhookEvent, exceptions, etc.
│   └── integrations/
│       ├── langchain.py    # protect_tools(), ArdenCallbackHandler
│       ├── crewai.py       # protect_tools()
│       └── openai.py       # ArdenToolExecutor, protect_function_tools()
├── examples/               # Runnable examples (see examples/README.md)
├── tests/                  # Test suite
├── mock_backend.py         # Local development mock server
├── pyproject.toml
├── README.md               # Main documentation
└── LIBRARY_REFERENCE.md    # Full API reference
```
