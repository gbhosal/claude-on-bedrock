"""
Basic chat example using AnthropicBedrockMantle.

Prerequisites:
    pip install "anthropic[bedrock]"
    export AWS_REGION=us-east-1
    export AWS_PROFILE=my-bedrock-profile  # or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
"""

from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

message = client.messages.create(
    model="anthropic.claude-opus-4-7",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Explain the difference between STS temporary credentials and long-term IAM keys in two sentences."}
    ]
)

print(message.content[0].text)
print(f"\n--- Usage ---")
print(f"Input tokens:  {message.usage.input_tokens}")
print(f"Output tokens: {message.usage.output_tokens}")
