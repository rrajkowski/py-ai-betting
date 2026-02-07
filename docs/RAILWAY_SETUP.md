# Railway Deployment Guide for py-ai-betting

This guide walks you through migrating your py-ai-betting app from Streamlit Cloud to Railway while preserving your SQLite data.

## ✅ Code Changes (Already Complete)

The following changes have been made to your codebase:

1. **Database Path Configuration** - Updated `app/db.py` and `app/utils/db.py` to use `/app/data` when running on Railway
2. **Procfile** - Created `Procfile` for Railway to know how to start your Streamlit app
3. **Environment Detection** - Code now checks for `RAILWAY_ENVIRONMENT` variable to determine if running on Railway

## 📋 Railway Dashboard Configuration

### Phase 1: Set Up Persistent Volume

Your SQLite database needs persistent storage to survive deployments.

1. **Go to your Railway project** at https://railway.app
2. **Open the Canvas view** (your project dashboard)
3. **Create a new Volume:**
   - Right-click the canvas → Select **+ New** → **Volume**
   - **Name:** `sqlite_data`
   - **Mount Path:** `/app/data` (⚠️ This MUST match exactly)
4. **Connect the Volume:**
   - Click and drag from the Volume to your Python service to attach it

### Phase 2: Configure Environment Variables

Move your secrets from Streamlit's `secrets.toml` to Railway's Variables.

1. **Navigate to your service** in Railway
2. **Click the "Variables" tab**
3. **Add the following variables:**

```
RAILWAY_ENVIRONMENT=production
GEMINI_API_KEY=<your-gemini-key>
OPENAI_API_KEY=<your-openai-key>
ANTHROPIC_API_KEY=<your-anthropic-key>
STRIPE_SECRET_KEY=<your-stripe-key>
GOOGLE_CLIENT_ID=<your-google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<your-google-oauth-secret>
X_API_KEY=<your-twitter-api-key>
X_API_SECRET=<your-twitter-api-secret>
```

**Optional (if you encounter permission errors):**
```
RAILWAY_RUN_UID=0
```

### Phase 3: Update OAuth Redirect URIs

1. **Go to Google Cloud Console** → APIs & Services → Credentials
2. **Find your OAuth 2.0 Client ID**
3. **Update Authorized Redirect URIs:**
   - Add: `https://your-app-name.up.railway.app/_stcore/login`
   - Replace `your-app-name` with your actual Railway app URL

## 📦 Migrating Your Existing Database

You have historical data in `bets.db` that needs to be uploaded to Railway's volume.

### Option A: Railway CLI (Recommended)

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Link to your project:**
   ```bash
   railway link
   ```

4. **Upload your database:**
   ```bash
   railway volume upload sqlite_data ./bets.db /app/data/bets.db
   ```

### Option B: Temporary File Browser

1. **Deploy a File Browser** from Railway's template marketplace
2. **Attach the same `sqlite_data` volume** to the File Browser service
3. **Upload `bets.db`** via the web interface
4. **Delete the File Browser service** after upload

### Option C: Start Fresh (Not Recommended)

If you don't need historical data, Railway will create a new empty database automatically.

## 🧪 Testing Your Deployment

### 1. Test Database Persistence

1. **Deploy your app** (push to GitHub or use Railway CLI)
2. **Create a test pick** in your app
3. **Go to Railway Dashboard** → Deployments → Click "Redeploy"
4. **Check if your test pick is still there** after redeployment
5. ✅ If yes, your volume is working correctly!

### 2. Test Stripe Integration

1. **Trigger a test payment** in your app
2. **Check the database** to verify the transaction was recorded
3. **Verify the data persists** after a redeploy

### 3. Test OAuth Login

1. **Try logging in with Google**
2. **Verify the redirect works** (you may need to update the redirect URI)

## 🚀 Deployment Checklist

Use this checklist to ensure everything is configured correctly:

- [ ] Volume created with name `sqlite_data`
- [ ] Volume mounted to `/app/data`
- [ ] Volume connected to your Python service
- [ ] All API keys added to Railway Variables
- [ ] `RAILWAY_ENVIRONMENT=production` variable set
- [ ] Google OAuth redirect URI updated
- [ ] Existing `bets.db` uploaded to volume (if migrating data)
- [ ] Code pushed to GitHub (Railway auto-deploys)
- [ ] App deployed successfully
- [ ] Database persistence tested (create data → redeploy → verify data exists)
- [ ] Stripe integration tested
- [ ] OAuth login tested

## 🔧 Troubleshooting

### Database Permission Errors

If you see "Permission Denied" errors when writing to the database:

1. Add environment variable: `RAILWAY_RUN_UID=0`
2. Redeploy your app

### Database Not Persisting

If data disappears after redeployment:

1. Verify volume is mounted to `/app/data` (not `/data` or `/app`)
2. Check that volume is connected to your service (drag connection in Canvas)
3. Verify `RAILWAY_ENVIRONMENT` variable is set

### OAuth Redirect Errors

If Google login fails:

1. Check Google Cloud Console → Credentials
2. Verify redirect URI matches: `https://your-app.up.railway.app/_stcore/login`
3. Make sure to use your actual Railway URL

### App Won't Start

1. Check Railway logs for errors
2. Verify `Procfile` exists in root directory
3. Verify all required environment variables are set
4. Check that `requirements.txt` includes all dependencies

## 📊 Monitoring Your App

### View Logs

```bash
railway logs
```

Or view in Railway Dashboard → Deployments → Click on deployment → Logs

### Check Database Size

Railway volumes have size limits based on your plan. Monitor usage in:
- Railway Dashboard → Your Volume → Usage

### Database Backups

**Important:** Railway volumes are persistent but not automatically backed up.

**Recommended backup strategy:**

1. **Periodic downloads via CLI:**
   ```bash
   railway volume download sqlite_data /app/data/bets.db ./backups/bets_$(date +%Y%m%d).db
   ```

2. **Automated backups:** Consider setting up a cron job or GitHub Action to download backups

## 🎯 Next Steps After Deployment

1. **Test all features** thoroughly in production
2. **Set up monitoring** for errors and performance
3. **Configure custom domain** (optional) in Railway settings
4. **Set up automated backups** for your database
5. **Monitor costs** - Railway Hobby plan is $5/month with usage limits

## 📞 Support

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **Streamlit Docs:** https://docs.streamlit.io

## 🔄 Reverting to Streamlit Cloud

If you need to revert:

1. Your code still works on Streamlit Cloud (it checks for `RAILWAY_ENVIRONMENT`)
2. Download your database from Railway volume
3. Upload to Streamlit Cloud using their file manager
4. Redeploy on Streamlit Cloud

---

**Good luck with your migration! 🚀**

