"""
Direct OpenAI Chat Completions Integration with Arden

Shows how to use ArdenToolExecutor in an OpenAI Chat Completions tool-call
loop. This is the recommended pattern when you're managing the message loop
yourself (no Agents SDK, no LangChain).

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


# ── Define raw tool functions ─────────────────────────────────────────────────

def search_web(query: str) -> str:
    return f"Search results for '{query}': [simulated results]"

def send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to}: '{subject}'"

def issue_refund(amount: float, customer_id: str) -> str:
    return f"Refund of ${amount} issued to {customer_id}"


# ── Register tools with Arden ─────────────────────────────────────────────────
# Arden policy names: "support.search_web", "support.send_email", "support.issue_refund"

executor = ArdenToolExecutor(tool_name_prefix="support", approval_mode="wait")
executor.register("search_web",  search_web)
executor.register("send_email",  send_email)
executor.register("issue_refund", issue_refund)

OPENAI_TOOLS = [
    {"type": "function", "function": {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Send an email to a user",
        "parameters": {"type": "object",
                       "properties": {
                           "to":      {"type": "string"},
                           "subject": {"type": "string"},
                           "body":    {"type": "string"}},
                       "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {
        "name": "issue_refund",
        "description": "Issue a refund to a customer",
        "parameters": {"type": "object",
                       "properties": {
                           "amount":      {"type": "number"},
                           "customer_id": {"type": "string"}},
                       "required": ["amount", "customer_id"]}}},
]


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(user_message: str):
    messages = [
        {"role": "system", "content": "You are a helpful customer support agent."},
        {"role": "user",   "content": user_message},
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o", messages=messages, tools=OPENAI_TOOLS
        )
        msg = response.choices[0].message
        if not msg.tool_calls:
            print(f"Agent: {msg.content}")
            break

        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f"  → calling {name}({args})")
            try:
                result = executor.run(name, args)
            except arden.PolicyDeniedError as e:
                result = f"Blocked by policy: {e}"
            except arden.ApprovalTimeoutError as e:
                result = f"Approval timed out: {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": str(result),
            })


if __name__ == "__main__":
    run_agent("Issue a $150 refund to customer cus_abc and send them a confirmation email.")
