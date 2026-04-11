# backend/openai_client.py

import os
from openai import OpenAI

# Load API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

# Create the client
client = OpenAI(api_key=OPENAI_API_KEY)

# Convenience wrappers
def chat(model: str, messages: list, tools=None, tool_choice="auto", temperature=0.3):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        temperature=temperature,
    )

def generate_image(prompt: str, size="1024x1024"):
    return client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
    )
