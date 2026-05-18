"""
Tool use (function calling) example on Bedrock.

Demonstrates a complete agentic loop: define tools, handle tool_use stop_reason,
execute tools, send results back, and get the final response.

Prerequisites:
    pip install "anthropic[bedrock]"
    export AWS_REGION=us-east-1
    export AWS_PROFILE=my-bedrock-profile
"""

import json
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g. 'Seattle, WA'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit. Defaults to fahrenheit."
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_stock_price",
        "description": "Get the current stock price for a ticker symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol, e.g. 'AMZN'"
                }
            },
            "required": ["ticker"]
        }
    }
]


def get_weather(location: str, unit: str = "fahrenheit") -> dict:
    # Stub — replace with real weather API call
    return {"location": location, "temperature": 72, "condition": "partly cloudy", "unit": unit}


def get_stock_price(ticker: str) -> dict:
    # Stub — replace with real stock API call
    prices = {"AMZN": 185.42, "MSFT": 415.30, "GOOGL": 178.90}
    price = prices.get(ticker.upper(), 0)
    return {"ticker": ticker.upper(), "price": price, "currency": "USD"}


def execute_tool(name: str, tool_input: dict) -> str:
    if name == "get_weather":
        result = get_weather(**tool_input)
    elif name == "get_stock_price":
        result = get_stock_price(**tool_input)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result)


def run_agent(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="anthropic.claude-opus-4-7",
            max_tokens=1024,
            tools=TOOLS,
            messages=messages
        )

        print(f"[stop_reason: {response.stop_reason}]")
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text

        elif response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → Calling {block.name}({block.input})")
                    result = execute_tool(block.name, block.input)
                    print(f"  ← Result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            return f"Unexpected stop reason: {response.stop_reason}"


if __name__ == "__main__":
    answer = run_agent("What's the weather in Seattle and the current price of Amazon stock?")
    print(f"\nFinal answer:\n{answer}")
