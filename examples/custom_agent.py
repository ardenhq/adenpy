"""
Custom Agent with Arden Protection (no framework)

Shows how to use guard_tool() directly when you're building a custom agent
without LangChain, CrewAI, or the OpenAI Agents SDK.

This is the right pattern when:
- You're dispatching tool calls yourself
- You have a custom agent loop
- You want fine-grained control over each tool's approval mode or name

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

arden.configure(api_key=os.environ["ARDEN_API_KEY"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ── Define raw tool functions ─────────────────────────────────────────────────

def search_web(query: str) -> str:
    return f"Search results for '{query}': [simulated]"

def send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to}: '{subject}'"

def issue_refund(amount: float, customer_id: str) -> str:
    return f"Refund of ${amount} issued to {customer_id}"

def delete_account(user_id: str) -> str:
    return f"Account {user_id} permanently deleted"


# ── Protect each function individually with guard_tool ────────────────────────
# Use this pattern when you need per-tool control over the Arden name or
# approval_mode. For framework users (LangChain, CrewAI), use protect_tools().

safe_search   = arden.guard_tool("web.search",         search_web)
safe_email    = arden.guard_tool("communication.email", send_email)
safe_refund   = arden.guard_tool("stripe.issue_refund", issue_refund)
safe_delete   = arden.guard_tool("admin.delete_account", delete_account)

TOOLS = {
    "search_web":    safe_search,
    "send_email":    safe_email,
    "issue_refund":  safe_refund,
    "delete_account": safe_delete,
}

OPENAI_TOOLS = [
    {"type": "function", "function": {
        "name": "search_web",
        "description": "Search the web for information",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "send_email",
        "description": "Send an email to a user",
        "parameters": {"type": "object", "properties": {
            "to":      {"type": "string"},
            "subject": {"type": "string"},
            "body":    {"type": "string"}}, "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {
        "name": "issue_refund",
        "description": "Issue a refund to a customer",
        "parameters": {"type": "object", "properties": {
            "amount":      {"type": "number"},
            "customer_id": {"type": "string"}}, "required": ["amount", "customer_id"]}}},
    {"type": "function", "function": {
        "name": "delete_account",
        "description": "Permanently delete a customer account",
        "parameters": {"type": "object", "properties": {
            "user_id": {"type": "string"}}, "required": ["user_id"]}}},
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
                result = TOOLS[name](**args)
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
    run_agent("Issue a refund of $200 to customer cus_abc123 and send them a confirmation email.")
