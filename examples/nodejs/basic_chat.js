/**
 * Basic chat example using @anthropic-ai/bedrock-sdk.
 *
 * Prerequisites:
 *   cd examples/nodejs && npm install
 *   export AWS_REGION=us-east-1
 *   export AWS_PROFILE=my-bedrock-profile  # or AWS_BEARER_TOKEN_BEDROCK / access keys
 */

import { AnthropicBedrock } from "@anthropic-ai/bedrock-sdk";

const client = new AnthropicBedrock({
  awsRegion: process.env.AWS_REGION ?? "us-east-1",
});

const message = await client.messages.create({
  model: "anthropic.claude-opus-4-7",
  max_tokens: 1024,
  messages: [
    {
      role: "user",
      content:
        "Explain the difference between STS temporary credentials and long-term IAM keys in two sentences.",
    },
  ],
});

const textBlock = message.content.find((block) => block.type === "text");
console.log(textBlock?.text ?? message.content);
console.log("\n--- Usage ---");
console.log(`Input tokens:  ${message.usage.input_tokens}`);
console.log(`Output tokens: ${message.usage.output_tokens}`);
