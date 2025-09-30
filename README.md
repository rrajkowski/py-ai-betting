# 🏈 AI Sports Betting Tracker

An open-source FastAPI + Streamlit project that:
- Fetches live odds from [The Odds API](https://the-odds-api.com/sports-odds-data/)
- Calls an LLM (default **OpenAI GPT-5**) to estimate win probabilities
- Calculates expected value (EV) for bets
- Logs bets, raw LLM outputs, outcomes, and profits in SQLite
- Visualizes ROI & performance with a **Streamlit dashboard**

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
