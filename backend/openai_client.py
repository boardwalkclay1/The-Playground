# backend/openai_client.py

import os
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------
# CORE CALLS
# ---------------------------------------------------------

def _call(model: str, messages: list, tools=None, tool_choice="auto", temperature=0.3):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        temperature=temperature,
    )


def _image(prompt: str, size="1024x1024"):
    return client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size=size,
    )

# ---------------------------------------------------------
# MULTI-MODEL FUSION LOGIC
# ---------------------------------------------------------

def chat(model: str, messages: list, tools=None, tool_choice="auto", temperature=0.3):
    """
    Primary chat call (single model).
    """
    return _call(model, messages, tools, tool_choice, temperature)


def fused_chat(messages: list):
    """
    Multi-model fusion:
    - gpt-4o (reasoning)
    - gpt-4o-mini (speed)
    - gpt-4o-mini (coding)
    - gpt-4o (final synthesis)

    Returns a single superior answer.
    """

    # Pass 1 — Deep reasoning
    r1 = _call("gpt-4o", messages, temperature=0.2).choices[0].message.content

    # Pass 2 — Fast refinement
    r2 = _call("gpt-4o-mini", [
        {"role": "system", "content": "Refine the reasoning. Keep it tight."},
        {"role": "user", "content": r1}
    ], temperature=0.1).choices[0].message.content

    # Pass 3 — Coding intelligence
    r3 = _call("gpt-4o-mini", [
        {"role": "system", "content": "Extract any technical or coding improvements."},
        {"role": "user", "content": r2}
    ], temperature=0.1).choices[0].message.content

    # Pass 4 — Final synthesis (superior output)
    final = _call("gpt-4o", [
        {"role": "system", "content": "Combine all inputs into the best possible answer."},
        {"role": "user", "content": f"Reasoning:\n{r1}\n\nRefinement:\n{r2}\n\nTechnical:\n{r3}"}
    ], temperature=0.2).choices[0].message.content

    return final


def generate_image(prompt: str, size="1024x1024"):
    return _image(prompt, size)
