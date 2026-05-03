Integrate Arden into this Python AI agent project by following these steps exactly.

## 1. Detect the project

Search the codebase to determine:
- Where the main agent entrypoint is (the file where the agent is created and run)
- Which framework is used: LangChain, CrewAI, OpenAI Agents SDK, or a custom agent loop
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

### What configure() does automatically

For **LangChain, CrewAI, and OpenAI Agents SDK**, `configure()` auto-patches the framework at startup — every tool call is intercepted and enforced with no other code changes needed:

- **LangChain**: patches `BaseTool.run` and `BaseTool.arun` (sync + async)
- **CrewAI**: patches `BaseTool.run` and `BaseTool.arun` (sync + async)
- **OpenAI Agents SDK**: patches `FunctionTool.__init__` so every `on_invoke_tool` goes through Arden

For **custom agents with no supported framework**, wrap individual functions explicitly:

```python
safe_refund = arden.guard_tool("stripe.issue_refund", issue_refund)
result = safe_refund(150.0, customer_id="cus_abc")
```

## 4. Add the API key to .env

If a `.env` file exists, add this line (leave the value empty for the user to fill in):
```
ARDEN_API_KEY=
```

If no `.env` file exists, create one with that line.

The user needs to get their API key from **https://app.arden.sh** after signing up (free during beta, no credit card required). They will receive two keys:
- `arden_test_...` — for development (hits `api-test.arden.sh`)
- `arden_live_...` — for production (hits `api.arden.sh`)

## 5. Add session tracking (optional but recommended)

If the project has a concept of users, conversations, or request IDs, add session tracking so all tool calls within a session are linked together in the Arden dashboard.

Find where a new conversation or request begins and add:

```python
import ardenpy as arden
import uuid

arden.set_session(str(uuid.uuid4()))  # or use an existing conversation/request ID
```

Call `set_session()` once per conversation, before the agent runs. It uses a `ContextVar` so it is safe for concurrent async requests.

## 6. Token usage tracking (automatic for supported frameworks)

Token usage and estimated cost are tracked automatically for LangChain, CrewAI, and the OpenAI Agents SDK — no setup needed. The dashboard shows cost broken down by model, day, and session.

For custom agent loops or direct OpenAI/Anthropic API calls, log usage manually after each LLM call:

```python
response = openai_client.chat.completions.create(model="gpt-4o", messages=messages)

arden.log_token_usage(
    model="gpt-4o",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
)
```

Only add this if the project does NOT use LangChain, CrewAI, or the OpenAI Agents SDK — those are already captured automatically.

## 7. Handle policy outcomes (if relevant)

By default, tool calls with no policy configured are **allowed and logged**. When the user later adds policies in the dashboard (no code changes needed), tool calls can be blocked or held for approval. If the project has error handling you should make it aware of Arden exceptions:

```python
try:
    result = safe_tool(...)
except arden.PolicyDeniedError:
    # blocked by policy, or denied by a human reviewer
    ...
except arden.ApprovalTimeoutError as e:
    # nobody approved within the timeout (default 5 min)
    # e.action_id contains the pending action ID
    ...
```

Only add this error handling if the entrypoint has a meaningful place for it (e.g. a request handler, agent loop, or CLI command). Don't add it around every individual call.

## 8. Show a summary

After making all changes, tell the user:
- Which files were modified and what was added to each
- Which framework was detected and whether auto-patching applies
- Whether session tracking was added
- Whether `log_token_usage()` was added (custom loop only)

Then print these next steps:

---

**Next steps:**

1. Sign up free at **https://app.arden.sh** and copy your API key into `.env` as `ARDEN_API_KEY`
2. Run your agent — every tool call is now enforced and logged automatically
3. Open the Arden dashboard → your agent → **Actions** tab to see the live audit trail
4. Add policies in the dashboard to allow, block, or require human approval per tool — no code changes needed when you update a policy
5. For human-in-the-loop approval notifications in Slack, configure a webhook under agent settings in the dashboard

**Docs:** https://arden.sh/docs  
**Dashboard:** https://app.arden.sh
