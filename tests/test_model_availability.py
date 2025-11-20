"""Test which AI models are available and working."""

import sys
sys.path.insert(0, '/Users/rubenrajkowski/Sites/py-ai-betting')

import os
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

print("=" * 80)
print("TESTING AI MODEL AVAILABILITY")
print("=" * 80)

# Test Gemini models
print("\n📊 GOOGLE GEMINI MODELS:")
print("-" * 80)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # List all available models
    print("\n✅ Available Gemini models:")
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"   - {model.name}")
    
    # Test specific models
    test_models = [
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]
    
    print("\n🧪 Testing specific models:")
    for model_name in test_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Say 'OK' if you can read this.")
            print(f"   ✅ {model_name}: {response.text[:50]}")
        except Exception as e:
            print(f"   ❌ {model_name}: {str(e)[:100]}")
else:
    print("❌ GEMINI_API_KEY not set")

# Test OpenAI models
print("\n📊 OPENAI MODELS:")
print("-" * 80)

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Test specific models
    test_models = [
        "gpt-5",
        "gpt-5-mini",
        "gpt-5-nano",
        "gpt-4o",
        "gpt-4o-mini",
    ]
    
    print("\n🧪 Testing specific models:")
    for model_name in test_models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "Say 'OK' if you can read this."}],
                max_tokens=10
            )
            print(f"   ✅ {model_name}: {response.choices[0].message.content}")
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg:
                print(f"   ❌ {model_name}: Model does not exist")
            else:
                print(f"   ❌ {model_name}: {error_msg[:100]}")
else:
    print("❌ OPENAI_API_KEY not set")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)
print("""
Based on current model availability (November 2025):

🥇 TIER 1 - Best Performance (Primary):
   - claude-sonnet-4.5 (Anthropic) - Best coding model, strongest reasoning
   - gemini-2.5-pro (Google) - Most advanced multimodal model
   - gpt-5 (OpenAI) - Smartest, fastest GPT model

🥈 TIER 2 - Fast & Cost-Effective (Fallback):
   - claude-haiku-4.5 (Anthropic) - Fast, cost-effective
   - gemini-2.5-flash (Google) - Fast with long context
   - gpt-5-mini (OpenAI) - Balanced speed/cost

🥉 TIER 3 - Ultra-Fast (Emergency Fallback):
   - gpt-5-nano (OpenAI) - Fastest, cheapest
   - gemini-2.5-flash-lite (Google) - Ultra-fast, low cost

💡 RECOMMENDED ORDER FOR SPORTS BETTING:
   1. claude-sonnet-4.5 (best reasoning for complex analysis)
   2. gemini-2.5-pro (excellent at structured output)
   3. gpt-5 (strong general performance)
   4. gpt-5-mini (fast fallback)
""")

