# 🏈 RAGE Sports Picks & Tracker

An open-source sports betting analysis tool built with Python and Streamlit, featuring a sophisticated multi-provider AI engine that generates daily picks with automated fallback redundancy.

Deployed on **Railway** with persistent SQLite storage, this project uses a 3-tier AI model cascade (Anthropic Claude → Google Gemini → OpenAI GPT) to ensure 99.9% uptime. It fetches live odds, analyzes games against historical data and expert consensus, and presents AI-generated picks in a clean, interactive dashboard.

## ✨ Features

- **🤖 Multi-Provider AI Engine (3-Tier Cascade)**:
  - **Tier 1 (Primary)**: Claude Sonnet 4.5, Gemini 2.5 Pro, GPT-5
  - **Tier 2 (Fallback)**: Claude Haiku 4.5, Gemini 2.5 Flash, GPT-5 Mini
  - **Tier 3 (Emergency)**: GPT-5 Nano, Gemini 2.5 Flash Lite
  - Automatically cascades through models if primary fails, ensuring picks are always generated

- **📊 Automated Pick Generation**: Daily betting picks for NFL, NCAAF, NCAAB, NBA, and NHL across major markets (Moneyline, Spreads, Totals, Parlays)

- **💾 Persistent Data Storage**: SQLite database with Railway volume mounting for data persistence across deployments

- **📈 Historical Analysis**: Caches recent game scores and expert consensus data to minimize API calls and improve pick quality

- **🎯 Interactive Dashboard**: Streamlit interface to generate picks, view AI reasoning, track performance metrics, and browse pick history

- **🔐 Authentication & Monetization**: Google OAuth authentication with Stripe subscription integration ($10/month with discount code support)

- **☁️ Railway Deployment**: Production-ready deployment on Railway with auto-deploy from GitHub, persistent volumes, and environment-based configuration

## ⚙️ Requirements
- macOS or Linux
- [Homebrew](https://brew.sh/) (for Mac)
- Python 3.10+
- Node.js (for Railway CLI)

## 🛠 Local Development Setup

```bash
git clone https://github.com/rrajkowski/py-ai-betting.git
cd py-ai-betting
brew update
brew install python sqlite3
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Copy `.env.example` → `.env` and fill in your API keys:
```env
GEMINI_API_KEY=your-gemini-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
RAPIDAPI_KEY=your-rapidapi-key
STRIPE_SECRET_KEY=your-stripe-key
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-secret
```

## 🔐 Authentication & Paywall Setup

To enable Google OAuth authentication and Stripe payment integration:

1. Copy the secrets template:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. Follow the detailed setup guide in [PAYWALL_SETUP.md](PAYWALL_SETUP.md) to:
   - Configure Google OAuth credentials
   - Set up Stripe subscription products
   - Create discount codes (optional)
   - Test the integration

**Note**: The app requires authentication by default. To disable it for development, comment out the `add_auth(required=True)` lines in the app files.

## ▶️ Run Locally

### Option 1: Streamlit Dashboard (Recommended)
```bash
streamlit run streamlit_app.py
```
Dashboard 👉 http://localhost:8501

### Option 2: FastAPI Backend (Optional)
```bash
uvicorn app.main:app --reload
```
API Docs 👉 http://127.0.0.1:8000/docs

## 🚀 Production Deployment (Railway)

This app is configured for deployment on **Railway** with persistent SQLite storage.

### Quick Deploy

1. **Push to GitHub** (Railway auto-deploys from `main` branch)
2. **Configure Railway** (see [RAILWAY_SETUP.md](RAILWAY_SETUP.md) for detailed instructions):
   - Create persistent volume: `sqlite_data` mounted at `/app/data`
   - Set environment variables (all API keys + `RAILWAY_ENVIRONMENT=production`)
   - Upload existing database (optional)
3. **Deploy** 🎉

### Detailed Setup Guide

See **[RAILWAY_SETUP.md](RAILWAY_SETUP.md)** for complete step-by-step instructions including:
- Volume configuration
- Environment variable setup
- Database migration
- OAuth redirect URI configuration
- Troubleshooting

### Database Persistence

The app automatically detects Railway environment and uses:
- **Local**: `./bets.db`
- **Railway**: `/app/data/bets.db` (persistent volume)

No code changes needed - it just works! ✨

## 🤖 AI Model Architecture

### Multi-Provider Cascade System

The app uses a sophisticated 3-tier cascade system across three AI providers to ensure 99.9% uptime:

```
┌─────────────────────────────────────────────────────────┐
│ TIER 1: Best Reasoning (Primary)                       │
├─────────────────────────────────────────────────────────┤
│ 1. Claude Sonnet 4.5    → Best reasoning & analysis    │
│ 2. Gemini 2.5 Pro       → Excellent structured output  │
│ 3. GPT-5                → Strong general performance    │
└─────────────────────────────────────────────────────────┘
                          ↓ (if fails)
┌─────────────────────────────────────────────────────────┐
│ TIER 2: Fast & Cost-Effective (Fallback)               │
├─────────────────────────────────────────────────────────┤
│ 4. Claude Haiku 4.5     → Fast, cost-effective         │
│ 5. Gemini 2.5 Flash     → Fast with long context       │
│ 6. GPT-5 Mini           → Balanced speed/cost           │
└─────────────────────────────────────────────────────────┘
                          ↓ (if fails)
┌─────────────────────────────────────────────────────────┐
│ TIER 3: Ultra-Fast (Emergency Fallback)                │
├─────────────────────────────────────────────────────────┤
│ 7. GPT-5 Nano           → Fastest, cheapest             │
│ 8. Gemini 2.5 Flash Lite → Ultra-fast, low cost        │
└─────────────────────────────────────────────────────────┘
```

### Why This Approach?

- **Reliability**: If one provider has an outage, automatically falls back to the next
- **Cost Optimization**: Uses best model when available, cheaper models as fallback
- **Performance**: Prioritizes reasoning quality while maintaining speed
- **Redundancy**: 8 models across 3 providers = virtually zero downtime

### Model Selection Logic

1. Attempts **Claude Sonnet 4.5** first (best reasoning for complex sports analysis)
2. Falls back to **Gemini 2.5 Pro** if Claude fails (excellent at structured JSON output)
3. Falls back to **GPT-5** if Gemini fails (strong general performance)
4. Continues through Tier 2 and Tier 3 if all Tier 1 models fail
5. Returns picks from first successful model

## 🛠 Tech Stack

- **Frontend**: Streamlit (Python web framework)
- **AI Models**:
  - Anthropic Claude (Sonnet 4.5, Haiku 4.5)
  - Google Gemini (2.5 Pro, 2.5 Flash, 2.5 Flash Lite)
  - OpenAI GPT (GPT-5, GPT-5 Mini, GPT-5 Nano)
- **Database**: SQLite with persistent volume storage
- **Deployment**: Railway (with auto-deploy from GitHub)
- **Authentication**: Google OAuth 2.0
- **Payments**: Stripe Subscriptions
- **APIs**:
  - RapidAPI (odds & scores)
  - Kalshi (prediction markets)
  - Web scraping (expert consensus)

## 📊 Supported Sports & Markets

### Sports
- 🏈 **NFL** (National Football League)
- 🏈 **NCAAF** (College Football)
- 🏀 **NCAAB** (College Basketball)
- 🏀 **NBA** (National Basketball Association)
- 🏒 **NHL** (National Hockey League)

### Markets
- **Moneyline** (ML) - Pick the winner
- **Spread** - Point spread betting
- **Totals** (Over/Under) - Combined score
- **Parlays** - Multi-leg combinations

## 📈 Performance Tracking

The app automatically tracks:
- Win/Loss/Push records
- ROI (Return on Investment)
- Confidence ratings (1-5 stars)
- Historical performance by sport
- Model attribution (which AI generated each pick)

## 🔒 Security & Privacy

- Google OAuth for secure authentication
- Stripe for PCI-compliant payment processing
- Environment variables for API key management
- No user data stored beyond email/subscription status

## 📝 License

MIT License - See [LICENSE](LICENSE) for details

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

## 📞 Support

- **Documentation**: See [RAILWAY_SETUP.md](RAILWAY_SETUP.md) for deployment
- **Issues**: Open a GitHub issue
- **Live App**: https://rage-sports-picks.up.railway.app

---

**Built with ❤️ for sports betting enthusiasts**
