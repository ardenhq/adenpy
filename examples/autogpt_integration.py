"""
Autonomous (AutoGPT-style) Agent with Arden Protection

Shows an autonomous agent that runs in a loop, picking and executing tools
until it decides the goal is complete. Uses ArdenToolExecutor so every tool
call is checked against Arden policies before execution.

Requirements:
    pip install ardenpy openai

Setup:
    export OPENAI_API_KEY="sk-..."
    export ARDEN_API_KEY="arden_live_..."
"""

import os
import json
from openai import OpenAI
import ardenpy as arden
from ardenpy.integrations.openai import ArdenToolExecutor

arden.configure(api_key=os.environ["ARDEN_API_KEY"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ── Tool implementations ──────────────────────────────────────────────────────

def web_search(query: str) -> str:
    return f"Search results for '{query}': [simulated]"

def create_file(filename: str, content: str) -> str:
    os.makedirs("agent_workspace", exist_ok=True)
    path = os.path.join("agent_workspace", filename)
    with open(path, "w") as f:
        f.write(content)
    return f"File created: {path}"

def send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to}: '{subject}'"

def issue_refund(amount: float, customer_id: str) -> str:
    return f"Refund of ${amount} issued to {customer_id}"


# ── Register with Arden ───────────────────────────────────────────────────────

executor = ArdenToolExecutor(approval_mode="wait")
executor.register("web_search",  web_search)
executor.register("create_file", create_file)
executor.register("send_email",  send_email)
executor.register("issue_refund", issue_refund)

OPENAI_TOOLS = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web for information",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "create_file",
        "description": "Create a file with content",
        "parameters": {"type": "object",
                       "properties": {
                           "filename": {"type": "string"},
                           "content":  {"type": "string"}},
                       "required": ["filename", "content"]}}},
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Send an email",
        "parameters": {"type": "object",
                       "properties": {
                           "to":      {"type": "string"},
                           "subject": {"type": "string"},
                           "body":    {"type": "string"}},
                       "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {
        "name": "issue_refund",
        "description": "Issue a customer refund",
        "parameters": {"type": "object",
                       "properties": {
                           "amount":      {"type": "number"},
                           "customer_id": {"type": "string"}},
                       "required": ["amount", "customer_id"]}}},
]

SYSTEM_PROMPT = """You are an autonomous agent. Work step by step toward the user's goal.
Use tools as needed. When the goal is fully completed, respond with a plain text summary
(no tool calls). All tool calls are governed by Arden security policies — some may require
human approval before they execute."""


# ── Autonomous loop ───────────────────────────────────────────────────────────

def run_autonomous_agent(goal: str, max_iterations: int = 10):
    print(f"Goal: {goal}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": goal},
    ]

    for i in range(max_iterations):
        print(f"\n[Iteration {i + 1}]")
        response = client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=OPENAI_TOOLS
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            # Agent decided it's done
            print(f"\nCompleted: {msg.content}")
            return

        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  → {name}({args})")
            try:
                result = executor.run(name, args)
                print(f"     ✓ {result}")
            except arden.PolicyDeniedError as e:
                result = f"Blocked by policy: {e}"
                print(f"     ✗ {result}")
            except arden.ApprovalTimeoutError as e:
                result = f"Approval timed out: {e}"
                print(f"     ✗ {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })

    print("Max iterations reached.")


if __name__ == "__main__":
    run_autonomous_agent(
        "Search for information about AI safety, write a summary to summary.txt, "
        "then email it to team@example.com"
    )
