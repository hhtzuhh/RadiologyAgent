#!/usr/bin/env python3
"""
Simple chat interface for the Levia Orchestrator Agent.
Connects via JSON-RPC and provides a clean conversational interface.
"""
import requests
import json
import sys
from datetime import datetime

# Configuration
ORCHESTRATOR_URL = "http://localhost:8001/"
COLORS = {
    'user': '\033[96m',      # Cyan
    'agent': '\033[92m',     # Green
    'tool': '\033[93m',      # Yellow
    'error': '\033[91m',     # Red
    'reset': '\033[0m',      # Reset
    'bold': '\033[1m',       # Bold
}

def print_colored(text, color='reset'):
    """Print colored text."""
    print(f"{COLORS.get(color, '')}{text}{COLORS['reset']}")

def send_message(text, context_id=None):
    """Send a message to the orchestrator and get response."""
    message_id = f"msg-{datetime.now().timestamp()}"

    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": message_id,
                "role": "user",
                "parts": [{"text": text}]
            }
        },
        "id": 1
    }

    # Add context ID if continuing conversation
    if context_id:
        payload["params"]["contextId"] = context_id

    try:
        response = requests.post(ORCHESTRATOR_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def extract_response_text(result):
    """Extract the agent's text response from the JSON-RPC result."""
    if "error" in result:
        return None, result["error"], None

    if "result" not in result:
        return None, "No result in response", None

    data = result["result"]
    context_id = data.get("contextId")

    # Get the final agent response from artifacts
    if "artifacts" in data and data["artifacts"]:
        for artifact in data["artifacts"]:
            for part in artifact.get("parts", []):
                if part.get("kind") == "text":
                    return part["text"], None, context_id

    # Fallback: get from history
    history = data.get("history", [])
    for msg in reversed(history):
        if msg.get("role") == "agent":
            for part in msg.get("parts", []):
                if part.get("kind") == "text":
                    return part["text"], None, context_id

    return "No response text found", None, context_id

def extract_tool_calls(result):
    """Extract tool/agent calls for debugging."""
    if "result" not in result:
        return []

    history = result["result"].get("history", [])
    tool_calls = []

    for msg in history:
        if msg.get("role") == "agent":
            for part in msg.get("parts", []):
                if part.get("kind") == "data":
                    data = part.get("data", {})
                    if data.get("name") == "transfer_to_agent":
                        agent_name = data.get("args", {}).get("agent_name", "unknown")
                        tool_calls.append(f"→ Calling {agent_name}")

    return tool_calls

def main():
    """Run the interactive chat."""
    print_colored("=" * 70, 'bold')
    print_colored("Levia Orchestrator Chat Interface", 'bold')
    print_colored("=" * 70, 'bold')
    print_colored("\nConnected to: " + ORCHESTRATOR_URL, 'reset')
    print_colored("Type 'exit' or 'quit' to end the conversation\n", 'reset')

    context_id = None

    while True:
        try:
            # Get user input
            print(f"\n{COLORS['user']}You: {COLORS['reset']}", end='')
            user_input = input().strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print_colored("\nGoodbye!", 'bold')
                break

            # Send message
            print_colored("\n[Thinking...]", 'tool')
            result = send_message(user_input, context_id)

            # Extract tool calls for transparency
            tool_calls = extract_tool_calls(result)
            if tool_calls:
                for call in tool_calls:
                    print_colored(f"  {call}", 'tool')

            # Extract and display response
            response_text, error, context_id = extract_response_text(result)

            if error:
                print_colored(f"\n❌ Error: {error}", 'error')
            else:
                print_colored("\nOrchestrator: ", 'agent')
                print_colored(response_text, 'reset')

        except KeyboardInterrupt:
            print_colored("\n\nGoodbye!", 'bold')
            break
        except Exception as e:
            print_colored(f"\n❌ Unexpected error: {e}", 'error')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
