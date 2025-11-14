#!/bin/bash
# Quick start script for the AI Sports Betting Dashboard

echo "🏈 AI Sports Betting Dashboard - Startup Script"
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if secrets.toml exists
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "⚠️  Warning: .streamlit/secrets.toml not found!"
    echo "   Authentication will not work without proper configuration."
    echo ""
    echo "   To set up:"
    echo "   1. cp .streamlit/secrets.toml.example .streamlit/secrets.toml"
    echo "   2. Edit .streamlit/secrets.toml with your credentials"
    echo "   3. See PAYWALL_SETUP.md for detailed instructions"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run verification script
echo "🔍 Running verification checks..."
python test_paywall_setup.py
VERIFY_EXIT_CODE=$?

if [ $VERIFY_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "⚠️  Some checks failed. The app may not work correctly."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Starting Streamlit app..."
echo "   Dashboard will open at: http://localhost:8501"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

# Start the app
streamlit run streamlit_app.py

