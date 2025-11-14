#!/usr/bin/env python3
"""
Test script to verify st-paywall installation and configuration.
Run this before starting the Streamlit app to check if everything is set up correctly.
"""

import sys
import os
from pathlib import Path


def check_package_installed():
    """Check if st-paywall is installed."""
    try:
        import importlib.util
        spec = importlib.util.find_spec("st_paywall")
        if spec is not None:
            print("✅ st-paywall package is installed")
            return True
        else:
            print("❌ st-paywall package is NOT installed")
            print("   Run: pip install st-paywall")
            return False
    except Exception as e:
        print(f"❌ Error checking st-paywall: {e}")
        print("   Run: pip install st-paywall")
        return False


def check_secrets_file():
    """Check if secrets.toml exists and has required fields."""
    secrets_path = Path(".streamlit/secrets.toml")

    if not secrets_path.exists():
        print("❌ .streamlit/secrets.toml does NOT exist")
        print("   Run: cp .streamlit/secrets.toml.example .streamlit/secrets.toml")
        print("   Then edit it with your credentials")
        return False

    print("✅ .streamlit/secrets.toml exists")

    # Check if it has the required sections
    try:
        import toml
        secrets = toml.load(secrets_path)

        # Check for testing_mode
        testing_mode = secrets.get("testing_mode", True)
        if testing_mode:
            print("   ℹ️  Testing mode: ENABLED (using test Stripe credentials)")
        else:
            print("   ℹ️  Testing mode: DISABLED (using live Stripe credentials)")

        # Check Google OAuth
        all_good = True
        if 'google_auth' not in secrets:
            print("   ⚠️  Missing section: [google_auth]")
            all_good = False
        else:
            for key in ['client_id', 'client_secret']:
                if key not in secrets['google_auth']:
                    print(f"   ⚠️  Missing key: google_auth.{key}")
                    all_good = False
                elif "YOUR_" in str(secrets['google_auth'][key]):
                    print(f"   ⚠️  Placeholder value in google_auth.{key}")
                    all_good = False

        # Check Stripe credentials based on testing_mode
        if testing_mode:
            # Check test credentials
            required_keys = ['stripe_api_key_test', 'stripe_link_test']
            for key in required_keys:
                if key not in secrets:
                    print(
                        f"   ⚠️  Missing key: {key} (required for testing mode)")
                    all_good = False
                elif "YOUR_" in str(secrets.get(key, "")):
                    print(f"   ⚠️  Placeholder value in {key}")
                    all_good = False
                else:
                    print(f"   ✅ {key} is configured")
        else:
            # Check live credentials
            required_keys = ['stripe_api_key', 'stripe_link']
            for key in required_keys:
                if key not in secrets:
                    print(
                        f"   ⚠️  Missing key: {key} (required for live mode)")
                    all_good = False
                elif "YOUR_" in str(secrets.get(key, "")):
                    print(f"   ⚠️  Placeholder value in {key}")
                    all_good = False
                else:
                    print(f"   ✅ {key} is configured")

        if all_good:
            print("✅ All required secrets are configured")
        else:
            print("⚠️  Some secrets need to be configured")
            print("   See PAYWALL_SETUP.md for instructions")

        return all_good

    except Exception as e:
        print(f"⚠️  Error reading secrets.toml: {e}")
        return False


def check_gitignore():
    """Check if secrets.toml is in .gitignore."""
    gitignore_path = Path(".gitignore")

    if not gitignore_path.exists():
        print("⚠️  .gitignore does not exist")
        return False

    with open(gitignore_path, 'r') as f:
        content = f.read()
        if 'secrets.toml' in content:
            print("✅ secrets.toml is in .gitignore")
            return True
        else:
            print("⚠️  secrets.toml is NOT in .gitignore")
            print("   Add this line to .gitignore: .streamlit/secrets.toml")
            return False


def check_streamlit_files():
    """Check if main Streamlit files have authentication integrated."""
    files_to_check = [
        'streamlit_app.py',
        'pages/ai_picks_page.py',
        'pages/live_scores_page.py'
    ]

    all_good = True
    for file_path in files_to_check:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  {file_path} does not exist")
            all_good = False
            continue

        with open(path, 'r') as f:
            content = f.read()
            if 'from st_paywall import add_auth' in content and 'add_auth(required=True)' in content:
                print(f"✅ {file_path} has authentication integrated")
            else:
                print(
                    f"⚠️  {file_path} does NOT have authentication integrated")
                all_good = False

    return all_good


def main():
    """Run all checks."""
    print("=" * 60)
    print("🔐 Paywall Setup Verification")
    print("=" * 60)
    print()

    checks = [
        ("Package Installation", check_package_installed),
        ("Secrets Configuration", check_secrets_file),
        ("Git Ignore", check_gitignore),
        ("Streamlit Files", check_streamlit_files),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking: {name}")
        print("-" * 60)
        results.append(check_func())
        print()

    print("=" * 60)
    if all(results):
        print("✅ All checks passed! You're ready to run the app.")
        print("\nNext steps:")
        print("1. Make sure you've configured Google OAuth and Stripe")
        print("2. Run: streamlit run streamlit_app.py")
        print("3. Test the authentication and subscription flow")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        print("\nSee PAYWALL_SETUP.md for detailed setup instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
