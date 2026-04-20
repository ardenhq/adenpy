Integrate Arden into this Python AI agent project by following these steps exactly.

## 1. Detect the project

Search the codebase to determine:
- Which AI framework is in use: LangChain, CrewAI, OpenAI Agents SDK, Anthropic SDK, or plain Python with function-based tools
- Where the main agent entrypoint is (the file where the agent is created and run)
- Which dependency file exists: `requirements.txt`, `pyproject.toml`, or `setup.py`
- Whether a `.env` file exists for secrets

## 2. Add ardenpy to dependencies

Add `ardenpy>=0.5.0` to whichever dependency file exists:
- `requirements.txt`: append `ardenpy>=0.5.0`
- `pyproject.toml`: add to `dependencies` array under `[project]`
- `setup.py`: add to `install_requires`

## 3. Add the configure() call

Find the agent entrypoint file and add the Arden configuration at the top, right after the existing imports:

```python
import ardenpy as arden

arden.configure(api_key=os.getenv("ARDEN_API_KEY"))
```

Make sure `import os` is present. Do not hardcode the API key.

If a `.env` file exists, add this line to it (do not fill in the value):
```
ARDEN_API_KEY=
```

**That's all that's needed for LangChain and CrewAI** — `configure()` auto-patches `BaseTool.run` at the class level so every tool call is intercepted automatically. No other code changes are required.

## 4. Framework-specific additions

### OpenAI Agents SDK
The auto-patch does not cover OpenAI Agents SDK. Wrap the agent executor:

```python
from ardenpy import ArdenToolExecutor

executor = ArdenToolExecutor(approval_mode="wait")
# Replace agent.run(...) or Runner.run(...) with:
result = executor.invoke(agent, input=user_message)
```

### Plain Python (function-based tools)
Wrap each tool function individually using `guard_tool`:

```python
from ardenpy import guard_tool

safe_send_email = guard_tool("email.send", send_email)
safe_issue_refund = guard_tool("stripe.refund", issue_refund)
```

Replace calls to the original functions with the wrapped versions.

### Anthropic SDK (tool use)
Wrap each tool handler before it executes:

```python
from ardenpy import guard_tool

# Wrap the function that handles each tool_use block
safe_handler = guard_tool("tool_name", original_handler)
```

## 5. Add session tracking (optional but recommended)

If the project has a concept of users, conversations, or request IDs, add session tracking so all tool calls from a session are linked together in the Arden dashboard.

Find where a new conversation or request starts and add:

```python
from ardenpy import set_session
import uuid

session_id = str(uuid.uuid4())  # or use an existing request/conversation ID
set_session(session_id)
```

Call `set_session()` once per conversation/request, before the agent runs.

## 6. Verify the integration

After making all changes, show the user a summary:
- Which file(s) were modified
- Which framework path was taken (auto-patch vs manual wrapping)
- Whether session tracking was added
- The exact lines added

Then print these next steps for the user:

---

**Next steps:**

1. Get your API key at **https://arden.sh** and add it to your `.env` file as `ARDEN_API_KEY`
2. Run your agent — every tool call will now be logged automatically
3. Go to the Arden dashboard to set up policies (allow, block, or require human approval per tool)
4. To require human approval for sensitive tools (e.g. refunds > $100, external emails), create a policy rule in the dashboard — no code changes needed

**Need help?** See the full SDK reference at https://arden.sh/docs
