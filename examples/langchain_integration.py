"""
LangChain Integration with Arden

Arden automatically patches LangChain at configure() time — no explicit wrapping
required. Every tool call in the process is intercepted without modifying how you
build the agent.

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

# That's it. Arden patches LangChain's BaseTool at configure() time.
# Tool names in the dashboard match the tool's .name attribute directly.
arden.configure(api_key=os.environ["ARDEN_API_KEY"])


# ── Define your tool functions ────────────────────────────────────────────────

def web_search(query: str) -> str:
    """Search the web (simulated)."""
    return f"Search results for '{query}': [simulated results]"


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {to}: '{subject}'"


def issue_refund(amount: float, customer_id: str) -> str:
    """Issue a refund to a customer."""
    return f"Refund of ${amount} issued to {customer_id}"


# ── Wrap into LangChain Tools — no protect_tools() needed ────────────────────

tools = [
    Tool(name="web_search",   func=web_search,   description="Search the web for information."),
    Tool(name="send_email",   func=send_email,   description="Send an email. Args: to, subject, body separated by '|'."),
    Tool(name="issue_refund", func=issue_refund, description="Issue a refund. Args: amount, customer_id separated by '|'."),
]


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

agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True,
                         handle_parsing_errors=True, max_iterations=5)

if __name__ == "__main__":
    # The agent decides which tools to call based on the user's message.
    # Arden intercepts each tool call before it executes.
    user_message = "A customer says their order arrived damaged. Their ID is cus_abc."
    result = executor.invoke({"input": user_message})
    print(result["output"])
