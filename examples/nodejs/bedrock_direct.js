/**
 * Direct @aws-sdk/client-bedrock-runtime example (no Anthropic SDK required).
 *
 * Use this approach when you need fine-grained AWS control or can't install
 * @anthropic-ai/bedrock-sdk.
 *
 * Prerequisites:
 *   cd examples/nodejs && npm install
 *   export AWS_REGION=us-east-1
 *   export AWS_PROFILE=my-bedrock-profile
 */

import {
  BedrockRuntimeClient,
  ConverseCommand,
  InvokeModelCommand,
  InvokeModelWithResponseStreamCommand,
} from "@aws-sdk/client-bedrock-runtime";

const region = process.env.AWS_REGION ?? "us-east-1";
const client = new BedrockRuntimeClient({ region });
const MODEL_ID = "anthropic.claude-opus-4-7";

async function invoke(prompt, maxTokens = 1024) {
  const response = await client.send(
    new InvokeModelCommand({
      modelId: MODEL_ID,
      contentType: "application/json",
      accept: "application/json",
      body: JSON.stringify({
        anthropic_version: "bedrock-2023-05-31",
        max_tokens: maxTokens,
        messages: [{ role: "user", content: prompt }],
      }),
    })
  );

  const body = JSON.parse(new TextDecoder().decode(response.body));
  return body.content[0].text;
}

async function invokeStreaming(prompt, maxTokens = 1024) {
  const response = await client.send(
    new InvokeModelWithResponseStreamCommand({
      modelId: MODEL_ID,
      contentType: "application/json",
      body: JSON.stringify({
        anthropic_version: "bedrock-2023-05-31",
        max_tokens: maxTokens,
        messages: [{ role: "user", content: prompt }],
      }),
    })
  );

  const parts = [];
  for await (const event of response.body) {
    if (!event.chunk?.bytes) continue;

    const chunk = JSON.parse(new TextDecoder().decode(event.chunk.bytes));
    if (chunk.type === "content_block_delta") {
      const delta = chunk.delta ?? {};
      if (delta.type === "text_delta" && delta.text) {
        process.stdout.write(delta.text);
        parts.push(delta.text);
      }
    } else if (chunk.type === "message_stop") {
      break;
    }
  }

  process.stdout.write("\n");
  return parts.join("");
}

async function invokeWithTools(prompt) {
  const tools = [
    {
      toolSpec: {
        name: "get_weather",
        description: "Get current weather for a location.",
        inputSchema: {
          json: {
            type: "object",
            properties: {
              location: { type: "string", description: "City name" },
            },
            required: ["location"],
          },
        },
      },
    },
  ];

  const messages = [{ role: "user", content: [{ text: prompt }] }];

  while (true) {
    const response = await client.send(
      new ConverseCommand({
        modelId: MODEL_ID,
        messages,
        toolConfig: { tools },
      })
    );

    const stopReason = response.stopReason;
    const outputMessage = response.output.message;
    messages.push(outputMessage);

    if (stopReason === "end_turn") {
      const textBlock = outputMessage.content.find((block) => "text" in block);
      return textBlock?.text ?? "";
    }

    if (stopReason === "tool_use") {
      const toolResults = [];
      for (const block of outputMessage.content) {
        if ("toolUse" in block) {
          const tool = block.toolUse;
          const resultText = JSON.stringify({
            temperature: 68,
            condition: "cloudy",
          });
          toolResults.push({
            toolResult: {
              toolUseId: tool.toolUseId,
              content: [{ text: resultText }],
            },
          });
        }
      }
      messages.push({ role: "user", content: toolResults });
      continue;
    }

    return `Unexpected stop reason: ${stopReason}`;
  }
}

console.log("=== Non-streaming ===");
console.log(await invoke("What is the capital of France? One sentence."));

console.log("\n=== Streaming ===");
await invokeStreaming("Write a two-sentence poem about AWS Bedrock.");

console.log("\n=== Tool use (Converse API) ===");
console.log(await invokeWithTools("What is the weather like in Paris?"));
