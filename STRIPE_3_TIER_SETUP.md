# 🎯 Stripe 3-Tier Pricing Setup Guide

## Overview
The app now supports 3 pricing tiers:
- **Monthly**: $10/month
- **Quarterly**: $25/3 months (BEST VALUE - Save 17%)
- **Yearly**: $100/year (Save 17%)

## 🔧 Streamlit Cloud Configuration

### Step 1: Go to Streamlit Cloud Secrets
1. Visit https://share.streamlit.io/
2. Select your app: `py-ai-betting`
3. Click **Settings** → **Secrets**

### Step 2: Add/Update Stripe Configuration

Replace the old `STRIPE_LINK` variables with the new 3-tier links:

```toml
# ============================================
# STRIPE PAYMENT CONFIGURATION - 3 TIERS
# ============================================

# Set to false for production
TESTING_MODE = false

# LIVE MODE credentials (for production)
STRIPE_API_KEY = "pk_live_YOUR_LIVE_KEY"

# 3 Pricing Tiers
STRIPE_1_MONTH_LINK = "https://buy.stripe.com/7sY6oI28HaAl6aLaKy93y00"
STRIPE_3_MONTH_LINK = "https://buy.stripe.com/00w7sM4gP7o9bv5aKy93y01"
STRIPE_1_YEAR_LINK = "https://buy.stripe.com/00w3cweVt4bXbv58Cq93y02"

# TEST MODE credentials (for localhost testing)
STRIPE_API_KEY_TEST = "pk_test_YOUR_TEST_KEY"
STRIPE_1_MONTH_LINK_TEST = "https://buy.stripe.com/test_YOUR_1_MONTH_LINK"
STRIPE_3_MONTH_LINK_TEST = "https://buy.stripe.com/test_YOUR_3_MONTH_LINK"
STRIPE_1_YEAR_LINK_TEST = "https://buy.stripe.com/test_YOUR_1_YEAR_LINK"
```

### Step 3: Remove Old Variables (if present)
Delete these old variables if they exist:
- ❌ `STRIPE_LINK`
- ❌ `STRIPE_LINK_TEST`
- ❌ `stripe_link`
- ❌ `stripe_link_test`

### Step 4: Save and Deploy
1. Click **Save**
2. Streamlit Cloud will automatically redeploy (~1 minute)
3. Test the subscription flow

## 🎨 What Users Will See

### New Signup Flow:
```
👋 Welcome! Please choose a subscription plan to access the app.

💎 Choose Your Plan

┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ 📅 Monthly  │  │ 📆 Quarterly│  │ 📅 Yearly   │
│             │  │ BEST VALUE  │  │             │
│    $10      │  │    $25      │  │   $100      │
│  per month  │  │ every 3 mo  │  │  per year   │
│             │  │ Save 17%    │  │  Save 17%   │
│ [Subscribe] │  │ [Subscribe] │  │ [Subscribe] │
└─────────────┘  └─────────────┘  └─────────────┘
```

### Expired Subscription Flow:
Same 3-tier pricing display with "Renew" buttons instead of "Subscribe"

## 🧪 Testing Locally

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
2. Set `TESTING_MODE = true`
3. Add your test Stripe links
4. Run `streamlit run streamlit_app.py`
5. Test with Stripe test card: `4242 4242 4242 4242`

## 📊 Stripe Dashboard

Your 3 products should be configured in Stripe:
- **RAGE Sports Picks [Month]** - $10.00 USD / month
- **RAGE Sports Picks [3 Month]** - $25.00 USD every 3 months
- **RAGE Sports Picks [1 year]** - $100.00 USD every 12 months

## ✅ Verification Checklist

- [ ] All 3 Stripe links are added to Streamlit Cloud secrets
- [ ] `TESTING_MODE = false` for production
- [ ] Old `STRIPE_LINK` variables removed
- [ ] App redeployed successfully
- [ ] Test signup flow shows 3 pricing tiers
- [ ] All 3 buttons link to correct Stripe checkout pages
- [ ] Email is pre-filled in Stripe checkout

## 🐛 Troubleshooting

### Error: "Stripe API key not configured"
**Fix:** Make sure `STRIPE_API_KEY` is set in Streamlit Cloud secrets

### Only 1 button shows instead of 3
**Fix:** Check that all 3 `STRIPE_X_LINK` variables are set correctly

### Buttons don't work
**Fix:** Verify the Stripe links are active in your Stripe dashboard

### Email not pre-filled
**Fix:** The app automatically appends `?prefilled_email={user_email}` to all links

