"""
CrewAI Integration with Arden — explicit protect_tools()

Use this pattern when you need different approval modes per tool.
For the common case (all tools in wait mode), use crewai_integration.py
instead — configure() alone is enough and protect_tools() is not needed.

All tool calls are still logged regardless of which tools you pass to
protect_tools(). configure() auto-patches CrewAI's BaseTool at the class
level, so any tool NOT in your protect_tools() list is still intercepted
by the auto-patcher and recorded in the action log.

Requirements:
    pip install ardenpy crewai

Setup:
    export OPENAI_API_KEY="sk-..."
    export ARDEN_API_KEY="arden_live_..."
"""

import os
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

import ardenpy as arden
from ardenpy.integrations.crewai import protect_tools

arden.configure(api_key=os.environ["ARDEN_API_KEY"])


# ── Tool definitions ──────────────────────────────────────────────────────────

class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for current information"
    args_schema: type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        return f"Search results for '{query}': [simulated]"


class RefundInput(BaseModel):
    amount: float = Field(..., description="Refund amount in USD")
    customer_id: str = Field(..., description="Customer ID")

class RefundTool(BaseTool):
    name: str = "issue_refund"
    description: str = "Issue a refund to a customer"
    args_schema: type[BaseModel] = RefundInput

    def _run(self, amount: float, customer_id: str) -> str:
        return f"Refund of ${amount} issued to {customer_id}"


class EmailInput(BaseModel):
    to: str = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")

class EmailTool(BaseTool):
    name: str = "send_email"
    description: str = "Send an email to a user"
    args_schema: type[BaseModel] = EmailInput

    def _run(self, to: str, subject: str, body: str) -> str:
        return f"Email sent to {to}: '{subject}'"


# ── Approval callbacks ────────────────────────────────────────────────────────

def on_refund_approved(event: arden.WebhookEvent) -> None:
    print(f"Refund approved! Executing with args: {event.context}")
    result = RefundTool()._run(**event.context)
    print(f"Result: {result}")


def on_refund_denied(event: arden.WebhookEvent) -> None:
    print(f"Refund denied. Notes: {event.notes}")


# ── Wrap tools — different approval modes per tool ────────────────────────────
#
# WebSearchTool and EmailTool: not passed to protect_tools(). Still intercepted
# by the auto-patcher and logged. Policy enforced if configured in the dashboard;
# otherwise allowed and recorded with reason=no_policy_configured.
#
# RefundTool: explicitly wrapped with webhook mode so the agent is not blocked
# waiting for human approval — it receives a pending message and continues,
# while the refund is handled out-of-band once approved.

protected = protect_tools(
    [RefundTool()],
    approval_mode="webhook",
    on_approval=on_refund_approved,
    on_denial=on_refund_denied,
)

tools = [WebSearchTool(), EmailTool(), protected[0]]


# ── Build the CrewAI agent and crew ──────────────────────────────────────────

support_agent = Agent(
    role="Customer Support Specialist",
    goal="Resolve customer issues efficiently and accurately",
    backstory="""You are a senior support specialist. If a tool returns a message
about pending approval, inform the user and stop — do not retry the tool.""",
    tools=tools,
    verbose=True,
)

task = Task(
    description="A customer says their order arrived damaged. Their ID is cus_abc. Resolve the issue.",
    expected_output="Confirmation of how the issue was resolved, or that approval is pending.",
    agent=support_agent,
)

crew = Crew(agents=[support_agent], tasks=[task], verbose=True)

if __name__ == "__main__":
    result = crew.kickoff()
    print(result)
