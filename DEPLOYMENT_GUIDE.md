# 🚀 Streamlit Cloud Deployment Guide

## ⚠️ Current Error

If you see: `AttributeError: st.user has no attribute "is_logged_in"`

**This means:** Streamlit native authentication is not configured in your Streamlit Cloud secrets.

## ✅ Solution: Configure Secrets

### Step 1: Go to Streamlit Cloud Settings

1. Visit https://share.streamlit.io/
2. Select your app: `py-ai-sports-betting`
3. Click **Settings** → **Secrets**

### Step 2: Add Authentication Configuration

Add this to your secrets (replace with your actual values):

```toml
# ============================================
# STREAMLIT NATIVE AUTHENTICATION
# ============================================
# Using Google OpenID Connect (OIDC)

[auth.google]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

# ============================================
# STRIPE PAYMENT CONFIGURATION
# ============================================
payment_provider = "stripe"
testing_mode = false

stripe_api_key = "YOUR_STRIPE_LIVE_API_KEY"
stripe_link = "YOUR_STRIPE_PAYMENT_LINK"

stripe_api_key_test = "YOUR_STRIPE_TEST_API_KEY"
stripe_link_test = "YOUR_STRIPE_TEST_PAYMENT_LINK"
```

### Step 3: Important Notes

**Section Name:**
- MUST be `[auth.google]` (not `[auth]` or `[google_auth]`)
- This is case-sensitive and format-sensitive

**DO NOT include:**
- `IS_LOCAL = true` (only for localhost)
- `cookie_secret` (not needed with Google OIDC)
- `redirect_uri` (not needed with Google OIDC)

**server_metadata_url:**
- Use EXACTLY: `https://accounts.google.com/.well-known/openid-configuration`
- This is the same for everyone using Google OIDC

### Step 4: Set Python Version

1. In Streamlit Cloud settings, go to **General**
2. Set Python version to **3.10** (not 3.13)
3. Python 3.13 is too new and may have compatibility issues

### Step 5: Get Your Google OAuth Credentials

If you don't have them yet:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Find your OAuth 2.0 Client ID
4. Copy the `client_id` and `client_secret`
5. Under "Authorized redirect URIs", make sure you have:
   - `https://py-ai-sports-betting.streamlit.app`

### Step 6: Deploy

1. Save your secrets
2. Streamlit Cloud will automatically redeploy
3. Visit your app
4. You should see a "Log in with Google" button

## 🎯 How It Works

### Two-Layer Authentication:

1. **Layer 1: Streamlit Native Auth**
   - User clicks "Log in with Google"
   - Streamlit handles OAuth flow
   - User is authenticated

2. **Layer 2: st-paywall**
   - Checks if authenticated user has Stripe subscription
   - If yes → full access
   - If no → shows "Subscribe now!" button

## 🐛 Troubleshooting

### Error: "st.user has no attribute 'is_logged_in'"
**Fix:** Add `[auth.google]` section to Streamlit Cloud secrets

### Error: Login button doesn't appear
**Fix:** 
1. Check section name is `[auth.google]` (exact spelling)
2. Make sure `IS_LOCAL` is NOT in cloud secrets
3. Verify Python version is 3.10

### Error: Login works but subscription check fails
**Fix:**
1. Verify Stripe API keys are correct
2. Check `payment_provider = "stripe"` is set
3. Make sure `testing_mode = false` for production

## 📚 References

- **Streamlit Auth Docs**: https://docs.streamlit.io/develop/concepts/connections/authentication
- **st-paywall Docs**: https://st-paywall.readthedocs.io/
- **Google Cloud Console**: https://console.cloud.google.com/

## ✅ Checklist

- [ ] Added `[auth.google]` section to Streamlit Cloud secrets
- [ ] Added Stripe configuration to secrets
- [ ] Set Python version to 3.10
- [ ] Updated Google OAuth redirect URIs
- [ ] Removed `IS_LOCAL` from cloud secrets
- [ ] Saved secrets and redeployed
- [ ] Tested login flow

Your app should now work! 🎉

