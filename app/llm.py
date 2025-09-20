import os
import re
from openai import OpenAI, APIError, AuthenticationError, RateLimitError


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def parse_probability(text: str) -> float:
    text = text.strip()
    try:
        val = float(text)
        if 0 <= val <= 1:
            return val
        if 1 < val <= 100:
            return val / 100
    except ValueError:
        pass
    match = re.search(r"(\d+(\.\d+)?)", text)
    if match:
        val = float(match.group(1))
        if 0 <= val <= 1:
            return val
        if 1 < val <= 100:
            return val / 100
    return 0.5


async def get_probability(match, odds, bet_type, stats):
    if LLM_PROVIDER == "openai":
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        try:
            response = client.responses.create(
                model="gpt-5",
                input=(
                    f"Match: {match}\n"
                    f"Odds: {odds}\n"
                    f"Bet type: {bet_type}\n"
                    f"Stats: {stats}\n\n"
                    "Estimate the win probability as a decimal (0.0 - 1.0). "
                    "Return only the number."
                )
            )
            raw_output = response.output_text
            parsed = parse_probability(raw_output)
            return {"parsed": parsed, "raw_output": raw_output}

        except RateLimitError:
            return {
                "parsed": None,
                "raw_output": "Error: OpenAI quota exceeded (429 RateLimitError)"
            }
        except AuthenticationError:
            return {
                "parsed": None,
                "raw_output": "Error: Invalid or missing OpenAI API key"
            }
        except APIError as e:
            return {
                "parsed": None,
                "raw_output": f"OpenAI API error: {str(e)}"
            }
        except Exception as e:
            return {
                "parsed": None,
                "raw_output": f"Unexpected error: {str(e)}"
            }

    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")
