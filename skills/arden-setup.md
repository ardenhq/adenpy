Integrate Arden into this Python AI agent project by following these steps exactly.

## 1. Detect the project

Search the codebase to determine:
- Where the main agent entrypoint is (the file where the agent is created and run)
- Which dependency file exists: `requirements.txt`, `pyproject.toml`, or `setup.py`
- Whether a `.env` file exists for secrets

## 2. Add ardenpy to dependencies

Add `ardenpy>=0.5.0` to whichever dependency file exists:
- `requirements.txt` → append `ardenpy>=0.5.0`
- `pyproject.toml` → add to the `dependencies` array under `[project]`
- `setup.py` → add to `install_requires`

## 3. Add configure() to the entrypoint

Find the agent entrypoint file and add the following right after the existing imports:

```python
import ardenpy as arden

arden.configure(api_key=os.getenv("ARDEN_API_KEY"))
```

Make sure `import os` is present in the file. Do not hardcode the API key.

**That is the entire integration.** Arden auto-patches LangChain, CrewAI, and OpenAI Agents SDK at configure-time — every tool call is intercepted automatically with no other code changes required.

## 4. Add the API key to .env

If a `.env` file exists, add this line (leave the value empty for the user to fill in):
```
ARDEN_API_KEY=
```

If no `.env` file exists, create one with that line.

## 5. Add session tracking (optional but recommended)

If the project has a concept of users, conversations, or request IDs, add session tracking so all tool calls within a session are linked together in the Arden dashboard.

Find where a new conversation or request begins and add:

```python
from ardenpy import set_session
import uuid

set_session(str(uuid.uuid4()))  # or use an existing conversation/request ID
```

Call `set_session()` once per conversation, before the agent runs.

## 6. Show a summary

After making all changes, tell the user:
- Which files were modified and what was added to each
- Whether session tracking was added

Then print these next steps:

---

**Next steps:**

1. Get your API key at **https://arden.sh** and add it to `.env` as `ARDEN_API_KEY`
2. Run your agent — every tool call is now enforced and logged automatically
3. Open the Arden dashboard to set up policies (allow, block, or require human approval per tool) — no code changes needed when you update a policy

**Docs:** https://arden.sh/docs
