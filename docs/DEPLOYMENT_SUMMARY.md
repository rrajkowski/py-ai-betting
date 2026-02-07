# 🚀 Railway Deployment - Ready to Deploy!

## ✅ Completed Steps

### 1. Code Changes (Pushed to GitHub)
- ✅ Updated `app/db.py` - Railway-aware database path
- ✅ Updated `app/utils/db.py` - Railway-aware database path  
- ✅ Created `Procfile` - Railway startup configuration
- ✅ Created `RAILWAY_SETUP.md` - Complete deployment guide
- ✅ Committed and pushed to `main` branch (commit: 4bcda06)

### 2. Railway Configuration (You've Already Done)
- ✅ Created persistent volume: `sqlite_data`
- ✅ Mount path: `/app/data`
- ✅ Set environment variable: `RAILWAY_ENVIRONMENT=production`
- ✅ Set all API keys (Gemini, OpenAI, Anthropic, Stripe, Google OAuth, Twitter)

## 🎯 Next Steps (Manual)

### Step 1: Deploy on Railway
Since you mentioned you'll manually deploy the first one:

1. **Go to Railway Dashboard**: https://railway.app
2. **Navigate to your project**: `rage-sports-picks`
3. **Trigger deployment** (Railway should auto-detect the GitHub push)
4. **Wait for deployment to complete**
5. **Check logs** for any errors

### Step 2: Upload Your Database
After the first deployment succeeds, upload your existing database:

```bash
# Link to your Railway project (select rage-sports-picks when prompted)
railway link

# Upload the database to the persistent volume
railway volume upload sqlite_data ./bets.db /app/data/bets.db
```

Your local `bets.db` is **1.6MB** and contains all your historical data.

### Step 3: Verify Database Persistence
1. **Visit your app**: https://rage-sports-picks.up.railway.app
2. **Check that your historical picks are visible**
3. **Create a test pick**
4. **Redeploy** (Railway Dashboard → Deployments → Redeploy)
5. **Verify the test pick still exists** ✅

### Step 4: Test OAuth Login
Your redirect URLs are configured for:
- `https://rage-sports-picks.up.railway.app`
- `https://rage-sports-picks.up.railway.app/oauth2callback`

Make sure these are set in **Google Cloud Console** → Credentials → OAuth 2.0 Client ID

### Step 5: Enable Auto-Deploy
Once the first deployment works:

1. **Railway Dashboard** → Your Service → **Settings**
2. **Source** → Connect to GitHub repository
3. **Branch**: `main`
4. **Enable auto-deploy** ✅

Now every push to `main` will automatically deploy!

## 📊 What Changed in Your Code

### Database Path Logic
```python
# Before (local only):
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "bets.db")

# After (Railway-aware):
PERSISTENT_DIR = "/app/data" if os.getenv("RAILWAY_ENVIRONMENT") else "."
DB_PATH = os.path.join(PERSISTENT_DIR, "bets.db")
```

### How It Works
- **Local development**: `RAILWAY_ENVIRONMENT` not set → uses `./bets.db`
- **Railway production**: `RAILWAY_ENVIRONMENT=production` → uses `/app/data/bets.db`

## 🔧 Troubleshooting

### If deployment fails:
1. Check Railway logs for errors
2. Verify `Procfile` exists in root directory
3. Verify all environment variables are set
4. Check that volume is connected to service

### If database doesn't persist:
1. Verify volume mount path is exactly `/app/data`
2. Check volume is connected to service (drag connection in Canvas)
3. Verify `RAILWAY_ENVIRONMENT=production` is set

### If OAuth fails:
1. Update Google Cloud Console redirect URIs
2. Make sure to use your actual Railway URL
3. Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set

## 📦 Database Upload Commands (Quick Reference)

```bash
# Install Railway CLI (if not already installed)
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link
# → Select: rage-sports-picks

# Upload database
railway volume upload sqlite_data ./bets.db /app/data/bets.db

# Verify upload (optional)
railway run ls -lh /app/data/
```

## 🎉 Success Checklist

- [ ] First deployment completed successfully
- [ ] Database uploaded to Railway volume
- [ ] Historical picks visible in app
- [ ] Test pick created and persists after redeploy
- [ ] OAuth login works
- [ ] Stripe integration tested
- [ ] Auto-deploy enabled from `main` branch

## 📞 Support Resources

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **Detailed Setup Guide**: See `RAILWAY_SETUP.md`

---

**Your app is ready to deploy! 🚀**

The code has been pushed to GitHub and Railway should detect it automatically.

