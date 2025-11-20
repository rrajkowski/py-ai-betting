"""Test Anthropic Claude API key."""

from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, '/Users/rubenrajkowski/Sites/py-ai-betting')


load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print("=" * 80)
print("TESTING ANTHROPIC CLAUDE API")
print("=" * 80)

if not ANTHROPIC_API_KEY:
    print("❌ ANTHROPIC_API_KEY not found in .env file")
    sys.exit(1)

print(f"✅ API Key found: {ANTHROPIC_API_KEY[:20]}...{ANTHROPIC_API_KEY[-10:]}")

try:
    from anthropic import Anthropic
    print("✅ anthropic package installed")
except ImportError:
    print("❌ anthropic package not installed")
    sys.exit(1)

print("\n🧪 Testing API connection...")

try:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Test with Claude Sonnet 4.5 (correct model name)
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Say 'Hello! I am Claude Sonnet 4.5 and I am ready to analyze sports betting data.' if you can read this."
            }
        ],
    )

    response_text = message.content[0].text
    print(f"\n✅ Claude Sonnet 4.5 Response:")
    print(f"   {response_text}")

    # Test with Claude Haiku 4.5 (correct model name)
    message2 = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Say 'Hello! I am Claude Haiku 4.5 and I am ready for fast analysis.' if you can read this."
            }
        ],
    )

    response_text2 = message2.content[0].text
    print(f"\n✅ Claude Haiku 4.5 Response:")
    print(f"   {response_text2}")

    print("\n" + "=" * 80)
    print("✅ SUCCESS! Both Claude models are working correctly!")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ API Test Failed: {e}")
    sys.exit(1)
