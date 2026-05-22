/**
 * Tool use (function calling) example on Bedrock.
 *
 * Demonstrates a complete agentic loop: define tools, handle tool_use stop_reason,
 * execute tools, send results back, and get the final response.
 *
 * Prerequisites:
 *   cd examples/nodejs && npm install
 *   export AWS_REGION=us-east-1
 *   export AWS_PROFILE=my-bedrock-profile
 */

import { AnthropicBedrock } from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({
  awsRegion: process.env.AWS_REGION ?? "us-east-1",
});

const TOOLS = [
  {
    name: "get_weather",
    description: "Get the current weather for a city.",
    input_schema: {
      type: "object",
      properties: {
        location: {
          type: "string",
          description: "City name, e.g. 'Seattle, WA'",
        },
        unit: {
          type: "string",
          enum: ["celsius", "fahrenheit"],
          description: "Temperature unit. Defaults to fahrenheit.",
        },
      },
      required: ["location"],
    },
  },
  {
    name: "get_stock_price",
    description: "Get the current stock price for a ticker symbol.",
    input_schema: {
      type: "object",
      properties: {
        ticker: {
          type: "string",
          description: "Stock ticker symbol, e.g. 'AMZN'",
        },
      },
      required: ["ticker"],
    },
  },
];

function getWeather(location, unit = "fahrenheit") {
  return {
    location,
    temperature: 72,
    condition: "partly cloudy",
    unit,
  };
}

function getStockPrice(ticker) {
  const prices = { AMZN: 185.42, MSFT: 415.3, GOOGL: 178.9 };
  const symbol = ticker.toUpperCase();
  return {
    ticker: symbol,
    price: prices[symbol] ?? 0,
    currency: "USD",
  };
}

function executeTool(name, toolInput) {
  if (name === "get_weather") {
    return JSON.stringify(getWeather(toolInput.location, toolInput.unit));
  }
  if (name === "get_stock_price") {
    return JSON.stringify(getStockPrice(toolInput.ticker));
  }
  return JSON.stringify({ error: `Unknown tool: ${name}` });
}

async function runAgent(userMessage) {
  const messages = [{ role: "user", content: userMessage }];

  while (true) {
    const response = await client.messages.create({
      model: "anthropic.claude-opus-4-7",
      max_tokens: 1024,
      tools: TOOLS,
      messages,
    });

    console.log(`[stop_reason: ${response.stop_reason}]`);
    messages.push({ role: "assistant", content: response.content });

    if (response.stop_reason === "end_turn") {
      const textBlock = response.content.find((block) => block.type === "text");
      return textBlock?.text ?? "";
    }

    if (response.stop_reason === "tool_use") {
      const toolResults = [];
      for (const block of response.content) {
        if (block.type === "tool_use") {
          console.log(`  → Calling ${block.name}(${JSON.stringify(block.input)})`);
          const result = executeTool(block.name, block.input);
          console.log(`  ← Result: ${result}`);
          toolResults.push({
            type: "tool_result",
            tool_use_id: block.id,
            content: result,
          });
        }
      }
      messages.push({ role: "user", content: toolResults });
      continue;
    }

    return `Unexpected stop reason: ${response.stop_reason}`;
  }
}

const answer = await runAgent(
  "What's the weather in Seattle and the current price of Amazon stock?"
);
console.log(`\nFinal answer:\n${answer}`);
