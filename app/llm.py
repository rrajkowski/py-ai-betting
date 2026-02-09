"""
LLM model callers for AI pick generation.

Supports OpenAI, Google Gemini, and Anthropic Claude with
multi-model fallback strategy.
"""

import json
import logging

import google.generativeai as genai
from dotenv import load_dotenv
from openai import OpenAI

from .auth import get_config

logger = logging.getLogger(__name__)

load_dotenv()

# Load API keys using get_config() helper (env vars first, then secrets.toml)
GEMINI_API_KEY = get_config("GEMINI_API_KEY")
OPENAI_API_KEY = get_config("OPENAI_API_KEY")
ANTHROPIC_API_KEY = get_config("ANTHROPIC_API_KEY")

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _call_openai_model(model_name, prompt):
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    req = dict(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a betting assistant returning valid JSON."},
            {"role": "user", "content": f"Return picks JSON only:\n\n{prompt}"}
        ],
        response_format={"type": "json_object"},
        timeout=90.0,
    )
    if not model_name.startswith("gpt-5"):
        req["temperature"] = 0.6
    resp = client.chat.completions.create(**req)
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw).get("picks", [])
    except Exception:
        return []


def _call_gemini_model(model_name, prompt):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set.")
    gen_config = genai.types.GenerationConfig(
        response_mime_type="application/json")
    model = genai.GenerativeModel(model_name, generation_config=gen_config)
    resp = model.generate_content(prompt)
    resp_json = json.loads(resp.text)
    if isinstance(resp_json, list):
        parsed = resp_json
    else:
        parsed = resp_json.get("picks", [])
    return parsed


def _call_claude_model(model_name, prompt):
    """Call Anthropic Claude model with retry logic for rate limits."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set.")

    try:
        from anthropic import Anthropic, RateLimitError
    except ImportError as err:
        raise ValueError(
            "anthropic package not installed. Run: pip install anthropic") from err

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Claude requires explicit JSON formatting instruction
    json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON in this exact format: {{\"picks\": [...]}}"

    # Retry logic for rate limits (free tier has strict limits)
    max_retries = 2
    retry_delay = 2  # seconds

    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": json_prompt}]
            )

            raw = response.content[0].text

            # Claude sometimes wraps JSON in markdown code blocks - strip them
            if raw.strip().startswith("```"):
                # Remove ```json or ``` from start and ``` from end
                lines = raw.strip().split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]  # Remove first line (```json or ```)
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # Remove last line (```)
                raw = '\n'.join(lines)

            try:
                return json.loads(raw).get("picks", [])
            except Exception:
                return []

        except RateLimitError:
            if attempt < max_retries:
                import time
                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Rate limited. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                raise  # Re-raise on final attempt
