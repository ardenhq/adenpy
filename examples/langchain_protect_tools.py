"""
LangChain Integration with Arden — explicit protect_tools()

Use this pattern when you need different approval modes per tool.
For the common case (all tools in wait mode), use langchain_integration.py
instead — configure() alone is enough and protect_tools() is not needed.

All tool calls are still logged regardless of which tools you pass to
protect_tools(). configure() auto-patches LangChain's BaseTool at the
class level, so any tool NOT in your protect_tools() list is still
intercepted by the auto-patcher and recorded in the action log.

Requirements:
    pip install ardenpy langchain-community langchain-openai

Setup:
    export OPENAI_API_KEY="sk-..."
    export ARDEN_API_KEY="arden_live_..."
"""

import os
from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

import ardenpy as arden
from ardenpy.integrations.langchain import protect_tools

arden.configure(api_key=os.environ["ARDEN_API_KEY"])


# ── Tool functions ────────────────────────────────────────────────────────────

def web_search(query: str) -> str:
    return f"Search results for '{query}': [simulated results]"


def send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to}: '{subject}'"


def issue_refund(amount: float, customer_id: str) -> str:
    return f"Refund of ${amount} issued to {customer_id}"


# ── Approval callbacks (required for async/webhook modes) ─────────────────────

def on_refund_approved(event: arden.WebhookEvent) -> None:
    print(f"Refund approved! Executing with args: {event.context}")
    result = issue_refund(**event.context)
    print(f"Result: {result}")


def on_refund_denied(event: arden.WebhookEvent) -> None:
    print(f"Refund denied. Notes: {event.notes}")


# ── Wrap tools — different approval modes per tool ────────────────────────────
#
# web_search and send_email: not passed to protect_tools(). They are still
# intercepted by the auto-patcher and logged. Policy is enforced if configured
# in the dashboard; otherwise allowed and recorded with reason=no_policy_configured.
#
# issue_refund: explicitly wrapped with webhook mode so the agent is not
# blocked waiting for human approval — it receives a pending message and
# continues, while the approval is handled out-of-band.

raw_tools = [
    Tool(name="web_search",   func=web_search,   description="Search the web."),
    Tool(name="send_email",   func=send_email,   description="Send an email."),
    Tool(name="issue_refund", func=issue_refund, description="Issue a refund."),
]

refund_tool = Tool(name="issue_refund", func=issue_refund, description="Issue a refund.")

protected = protect_tools(
    [refund_tool],
    approval_mode="webhook",
    on_approval=on_refund_approved,
    on_denial=on_refund_denied,
)

# Replace the auto-patched refund tool with the explicitly wrapped one.
# web_search and send_email remain in the list, auto-patched as usual.
tools = [
    Tool(name="web_search", func=web_search, description="Search the web."),
    Tool(name="send_email", func=send_email, description="Send an email."),
    protected[0],  # issue_refund with webhook approval
]


# ── Build and run the agent ───────────────────────────────────────────────────

llm = ChatOpenAI(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])

prompt = PromptTemplate.from_template("""
You are a helpful assistant. Use available tools to answer the user.
If a tool returns a message about pending approval, inform the user and stop.

Tools: {tools}
Tool names: {tool_names}

Format:
Question: {input}
Thought: ...
Action: <tool name>
Action Input: <input>
Observation: <result>
...
Final Answer: <answer>

Question: {input}
Thought: {agent_scratchpad}
""")

agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True,
                         handle_parsing_errors=True, max_iterations=5)

if __name__ == "__main__":
    user_message = "A customer says their order arrived damaged. Their ID is cus_abc."
    result = executor.invoke({"input": user_message})
    print(result["output"])
