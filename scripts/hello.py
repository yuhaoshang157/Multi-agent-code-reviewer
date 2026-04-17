import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)

message = client.chat.completions.create(
    model="anthropic/claude-sonnet-4-5",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "Say hello and confirm you are Claude Sonnet 4.5."}
    ],
)

print(message.choices[0].message.content)
