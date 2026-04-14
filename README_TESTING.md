# Testing ardenpy

## Unit tests (no network required)

```bash
# Set up
python -m venv .venv
.venv/bin/pip install -e ".[all]" pytest -q

# Run
.venv/bin/pytest tests/ -v -m "not integration"
```

Tests run in under a second and require no API keys or AWS credentials.

## Integration tests (live backend)

```bash
AWS_DEFAULT_PROFILE=arden-dev .venv/bin/pytest tests/ -v -m integration -s
```

Requires valid `ARDEN_API_KEY` and a live backend. See `LOCAL_DEVELOPMENT.md` for
running a local mock backend instead.

## What the unit tests cover

| Area | What's tested |
|------|--------------|
| Imports | All public symbols importable from `ardenpy` and `ardenpy.integrations.*` |
| Configuration | `configure()`, env var detection, key prefix → URL mapping, error on missing key |
| Types | `PolicyDecision`, `ActionStatus`, `ToolCallRequest`, `ToolCallResponse` (including `reason` field), exceptions |
| `guard_tool` | Function wrapping, argument serialization, `_make_serializable` |
| `ToolCallResponse` | `reason: no_policy_configured` field present and optional |
| Client | Instantiation and cleanup |

## CI

Tests run automatically on every push and pull request via GitHub Actions
(`.github/workflows/test.yml`) across Python 3.8–3.12.

## Adding tests

Add to `tests/test_basic.py` for unit tests. Keep all unit tests free of
network calls — mock the `ArdenClient` or test pure functions directly.
Integration tests go in a separate file marked with `@pytest.mark.integration`.
