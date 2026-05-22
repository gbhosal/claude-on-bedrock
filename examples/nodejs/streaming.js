/**
 * Streaming response example using @anthropic-ai/bedrock-sdk.
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

console.log("Streaming response:\n");

const stream = client.messages.stream({
  model: "anthropic.claude-opus-4-7",
  max_tokens: 512,
  messages: [
    {
      role: "user",
      content:
        "Write a three-sentence story about a developer who migrated to AWS Bedrock.",
    },
  ],
});

for await (const event of stream) {
  if (
    event.type === "content_block_delta" &&
    event.delta.type === "text_delta"
  ) {
    process.stdout.write(event.delta.text);
  }
}

const final = await stream.finalMessage();
console.log("\n\n--- Final message stats ---");
console.log(`Stop reason:   ${final.stop_reason}`);
console.log(`Input tokens:  ${final.usage.input_tokens}`);
console.log(`Output tokens: ${final.usage.output_tokens}`);
