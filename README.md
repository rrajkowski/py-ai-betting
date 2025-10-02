# 🏈 AI Sports Betting Tracker

An open-source tool built with Python and Streamlit that uses a multi-tier AI engine to generate daily sports betting picks.

This project leverages Google's Gemini 2.5 Pro as its primary model for analysis, with automated fallbacks to OpenAI's GPT-5 series to ensure reliability. It fetches live odds, analyzes upcoming games against historical data, and presents the AI-generated picks in a clean, interactive dashboard.

## ✨ Features

- Multi-Provider AI Engine: Prioritizes Google's Gemini 2.5 Pro for analysis and automatically falls back to OpenAI's GPT-5 models (gpt-5-mini, etc.) if the primary model fails.

- Automated Pick Generation: Generates daily betting picks for NFL, NCAAF, and MLB across major markets (Moneyline, Spreads, Totals).

- Historical Caching: Caches recent game scores in a local SQLite database to minimize API calls and reduce costs.

- Interactive Dashboard: A Streamlit interface to generate new picks, view the AI's reasoning, and browse a history of all generated picks.

## ⚙️ Requirements
- macOS or Linux
- [Homebrew](https://brew.sh/)
- Python 3.10+

## 🛠 Installation (Mac)
```bash
git clone https://github.com/yourname/ai-betting.git
cd ai-betting
brew update
brew install python sqlite3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
cp .env.example .env
```

Copy `.env.example` >  `.env` and fill in your keys:
```env
{replace values}
```

## ▶️ Run the Backend (FastAPI)
```bash
uvicorn app.main:app --reload
```
Docs 👉 http://127.0.0.1:8000/docs

## 📊 Run the Dashboard (Streamlit)
```bash
streamlit run streamlit_app.py
```
Dashboard 👉 http://localhost:8501
