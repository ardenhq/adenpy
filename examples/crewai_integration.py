"""
CrewAI Integration with Arden

Arden automatically patches CrewAI at configure() time — no explicit wrapping
required. Define plain BaseTool subclasses as usual and pass them directly to
your agent. Every _run() call is intercepted automatically.

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

# That's it. Arden patches CrewAI's BaseTool at import time.
# Tool names in the dashboard: "support.web_search", "support.issue_refund", etc.
arden.configure(api_key=os.environ["ARDEN_API_KEY"])


# ── Define plain BaseTool classes — no guard_tool boilerplate ─────────────────

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


# ── Build the CrewAI agent and crew — tools passed directly ──────────────────

tools = [WebSearchTool(), RefundTool(), EmailTool()]

support_agent = Agent(
    role="Customer Support Specialist",
    goal="Resolve customer issues efficiently and accurately",
    backstory="You are a senior support specialist who handles refunds and inquiries.",
    tools=tools,
    verbose=True,
)

task = Task(
    description="A customer says their order arrived damaged. Their ID is cus_abc. Resolve the issue.",
    expected_output="Confirmation of how the issue was resolved.",
    agent=support_agent,
)

crew = Crew(agents=[support_agent], tasks=[task], verbose=True)

if __name__ == "__main__":
    result = crew.kickoff()
    print(result)
