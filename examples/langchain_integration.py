"""
LangChain Integration with Arden

Shows how to protect LangChain tools using protect_tools() from
ardenpy.integrations.langchain. This is the recommended approach for
LangChain agents — no per-tool boilerplate required.

Requirements:
    pip install "ardenpy[langchain]" langchain-community langchain-openai

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


# ── Define your raw tool functions ───────────────────────────────────────────

def web_search(query: str) -> str:
    """Search the web (simulated)."""
    return f"Search results for '{query}': [simulated results]"


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}: '{subject}'"


def issue_refund(amount: float, customer_id: str) -> str:
    """Issue a refund to a customer."""
    return f"Refund of ${amount} issued to {customer_id}"


# ── Wrap into LangChain Tools ─────────────────────────────────────────────────

raw_tools = [
    Tool(name="web_search",   func=web_search,   description="Search the web for information."),
    Tool(name="send_email",   func=send_email,   description="Send an email. Args: to, subject, body separated by '|'."),
    Tool(name="issue_refund", func=issue_refund, description="Issue a refund. Args: amount, customer_id separated by '|'."),
]

# protect_tools() wraps each tool's run() with Arden policy enforcement.
# Arden policy names: "langchain.web_search", "langchain.send_email", "langchain.issue_refund"
safe_tools = protect_tools(raw_tools, approval_mode="wait")


# ── Build and run the agent ───────────────────────────────────────────────────

llm = ChatOpenAI(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])

prompt = PromptTemplate.from_template("""
You are a helpful assistant. Use available tools to answer the user.

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

agent = create_react_agent(llm, safe_tools, prompt)
executor = AgentExecutor(agent=agent, tools=safe_tools, verbose=True,
                         handle_parsing_errors=True, max_iterations=5)

if __name__ == "__main__":
    result = executor.invoke({"input": "Issue a refund of $150 to customer cus_abc"})
    print(result["output"])
