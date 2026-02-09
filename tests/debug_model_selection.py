"""Debug why Claude models are being skipped."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 80)
print("DEBUG: Model Selection Issue")
print("=" * 80)

# Check API keys
print("\n1. API KEY STATUS:")
print("-" * 80)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(f"GEMINI_API_KEY:    {'✅ SET' if GEMINI_API_KEY else '❌ NOT SET'}")
print(f"OPENAI_API_KEY:    {'✅ SET' if OPENAI_API_KEY else '❌ NOT SET'}")
print(f"ANTHROPIC_API_KEY: {'✅ SET' if ANTHROPIC_API_KEY else '❌ NOT SET'}")

if ANTHROPIC_API_KEY:
    print(f"  Value: {ANTHROPIC_API_KEY[:20]}...{ANTHROPIC_API_KEY[-10:]}")

# Test Claude model directly
print("\n2. TESTING CLAUDE MODEL:")
print("-" * 80)

if not ANTHROPIC_API_KEY:
    print("❌ Cannot test Claude - ANTHROPIC_API_KEY not set")
    sys.exit(1)

try:
    from anthropic import Anthropic
    print("✅ anthropic package imported successfully")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    print("✅ Anthropic client created successfully")

    # Test with a simple prompt
    print("\n🧪 Testing Claude Sonnet 4.5 with simple prompt...")

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Say 'Hello from Claude!' if you can read this."
            }
        ],
    )

    response_text = response.content[0].text
    print(f"✅ Claude Response: {response_text}")

    # Test with JSON prompt (like in rage_picks.py)
    print("\n🧪 Testing Claude with JSON prompt...")

    json_prompt = """Return a JSON object with this format: {"picks": [{"game": "Test Game", "confidence": 5}]}

IMPORTANT: Return ONLY valid JSON in this exact format: {"picks": [...]}"""

    response2 = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": json_prompt
            }
        ],
    )

    response_text2 = response2.content[0].text
    print(f"✅ Claude JSON Response: {response_text2[:200]}")

    # Try to parse JSON
    import json
    try:
        parsed = json.loads(response_text2)
        print(f"✅ JSON parsed successfully: {parsed}")
    except Exception as e:
        print(f"⚠️ JSON parsing failed: {e}")
        print(f"   Raw response: {response_text2}")

    print("\n" + "=" * 80)
    print("✅ Claude model is working correctly!")
    print("=" * 80)

except ImportError as e:
    print(f"❌ Failed to import anthropic: {e}")
    print("   Run: pip install anthropic")
    sys.exit(1)

except Exception as e:
    print(f"❌ Claude test failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Full error: {str(e)}")
    sys.exit(1)

# Check if the issue is in the app code
print("\n3. CHECKING APP CODE:")
print("-" * 80)

try:
    # Import the function from app/llm.py
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from app.llm import _call_claude_model

    print("✅ _call_claude_model imported successfully")

    # Test the function
    test_prompt = """Return a JSON object: {"picks": [{"game": "Test", "confidence": 5}]}

IMPORTANT: Return ONLY valid JSON."""

    print("\n🧪 Testing _call_claude_model function...")
    result = _call_claude_model("claude-sonnet-4-5", test_prompt)
    print(f"✅ Function returned: {result}")

except Exception as e:
    print(f"❌ Function test failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Full error: {str(e)}")

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
