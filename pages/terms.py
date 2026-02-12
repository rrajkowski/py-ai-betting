# pages/terms.py
"""
Terms & Conditions page for RagePicks LLC.
Public-facing page with full terms and conditions.
No authentication required - fully public.
"""
import streamlit as st

from app.db import init_ai_picks
from app.utils.branding import render_global_css_overrides, render_logo_in_sidebar, render_mobile_web_app_meta_tags
from app.utils.sidebar import render_admin_section, render_sidebar_navigation

# --- Page Configuration ---
st.set_page_config(
    page_title="Terms & Conditions - RAGE Sports Picks",
    page_icon="img/favicon.ico",
    layout="wide"
)

# --- INITIALIZATION ---
# Ensure database tables exist
init_ai_picks()

# --- Global CSS Overrides ---
render_global_css_overrides()

# --- Mobile Web App Meta Tags ---
render_mobile_web_app_meta_tags()

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Logo & Navigation (always on top) ---
render_logo_in_sidebar()
render_sidebar_navigation()
render_admin_section()

# --- PAGE CONTENT ---
st.markdown("""
# Terms & Conditions – RagePicks LLC

**Last Updated:** February 11, 2026

Welcome to RagePicks LLC ("RagePicks," "we," "us," or "our"). These Terms & Conditions ("Terms") govern your access to and use of our website, services, free daily picks, premium paid subscriptions, content, and any related materials (collectively, the "Services").

By accessing, browsing, or using the Services (including signing up for free picks or purchasing a premium subscription), you agree to be bound by these Terms. If you do not agree, do not use the Services.

## 1. Entertainment and Informational Purposes Only – Important Disclaimer

All content, picks, predictions, analysis, statistics, and information provided by RagePicks LLC is strictly for entertainment and informational purposes only.

RagePicks LLC is not a sportsbook, bookmaker, gambling operator, or handicapping service that accepts or places wagers. We do not provide betting advice, gambling recommendations, financial advice, investment advice, or any form of professional wagering guidance.

Nothing on our site or in our communications should be construed as an endorsement, inducement, or suggestion to bet, wager, or gamble on any sporting event.

We do not guarantee, warrant, or promise any level of accuracy, profitability, success, or positive outcomes from using our picks—free or paid.

Past performance is not indicative of future results. Any referenced historical win rates, records, or results are for illustrative purposes only and do not guarantee or predict future performance.

Sports outcomes are inherently uncertain and involve risk. There are no certainties or "locks" in sports.

You are solely responsible for your own decisions. Always Do Your Own Research (DYOR), verify information independently, and only risk money you can afford to lose. If you have a gambling problem, seek help—call 1-800-GAMBLER (US) or visit the National Council on Problem Gambling.

## 2. User Eligibility and Responsibility

You must be at least 18 years old (or the age of majority in your jurisdiction) to use the Services. By using the Services, you represent that you meet this requirement and that your use complies with all applicable local, state, federal, and international laws regarding gambling, betting, and online activities.

It is your responsibility to determine whether accessing or using our Services (including any picks) is legal in your jurisdiction. RagePicks LLC makes no representations that the Services are appropriate or available for use in all locations.

## 3. Free Daily Picks and Paid Premium Subscriptions

**Free Daily Picks:** We offer select sports picks and content free of charge as a promotional/entertainment service. No payment is required, and no purchase is necessary to view them.

**Paid Monthly Subscriptions:** Premium picks and additional content are available via recurring monthly subscription fees. Subscriptions auto-renew until canceled. Pricing, features, and availability may change at any time.

- Payments are processed securely via our third-party provider(s).
- No refunds for partial months, unused picks, or dissatisfaction with outcomes—fees are earned upon receipt.
- You may cancel anytime via your account settings or by contacting support. Cancellation takes effect at the end of the current billing period; no pro-rated refunds.
- Sharing, distributing, reproducing, or reselling premium content (free or paid) is strictly prohibited and may result in immediate termination without refund.

## 4. No Guarantees or Warranties

The Services are provided "as is" and "as available" without any warranties of any kind, express or implied, including but not limited to warranties of accuracy, completeness, reliability, timeliness, merchantability, fitness for a particular purpose, or non-infringement.

We do not warrant:

- That picks or predictions will be profitable or error-free.
- Uninterrupted, secure, or error-free access to the Services.
- That any results will match advertised or historical performance.

## 5. Limitation of Liability

To the fullest extent permitted by law, RagePicks LLC, its owners, officers, employees, affiliates, and agents shall not be liable for any direct, indirect, incidental, special, consequential, punitive, or exemplary damages (including lost profits, data, opportunities, or betting/gambling losses) arising from:

- Use of or reliance on any picks, content, or Services.
- Any errors, omissions, delays, or inaccuracies in the information provided.
- Your betting, wagering, or financial decisions.

Our total liability to you shall not exceed the amount you paid us in the 12 months preceding any claim (or $100, whichever is less). This limitation applies even if we were advised of the possibility of such damages.

## 6. Intellectual Property

All content on RagePicks LLC—including text, picks, graphics, logos, analyses, and materials—is owned by RagePicks LLC or its licensors and protected by copyright, trademark, and other laws. You may view and use content for personal, non-commercial entertainment purposes only. No sharing, reproduction, distribution, modification, or commercial use without express written permission.

## 7. Prohibited Uses

You agree not to:

- Use the Services for any illegal purpose or in violation of any law.
- Share, sell, or redistribute picks/content.
- Harass, threaten, or abuse our team or other users.
- Attempt to reverse-engineer, scrape, or interfere with the Services.

Violation may result in immediate account termination without refund.

## 8. Termination

We may suspend or terminate your access at any time, with or without cause or notice, including for violations of these Terms. You remain liable for any amounts owed.

## 9. Governing Law and Dispute Resolution

These Terms are governed by the laws of the State of California, USA, without regard to conflict of law principles. Any disputes shall be resolved exclusively in the state or federal courts located in Los Angeles County, California.

## 10. Changes to Terms

We may update these Terms at any time. Continued use after changes constitutes acceptance of the revised Terms. Check this page periodically.

## 11. Contact Us

Questions? Email: [support@ragepicks.com](mailto:support@ragepicks.com)

---

By using RagePicks LLC, you acknowledge that you have read, understood, and agree to these Terms & Conditions, including all disclaimers and limitations.

Thank you for using RagePicks – enjoy the games responsibly!
""")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9em; padding: 0.8em 0; margin-top: 2em;">
    <p style="margin: 0.3em 0;"><strong>For entertainment and informational purposes only.</strong></p>
    <p style="margin: 0.3em 0;">No guarantees. No financial advice. If you're mad about a loss, blame variance — not the model.</p>
    <p style="margin: 0.3em 0;">RAGE Picks &copy; 2026</p>
</div>
""", unsafe_allow_html=True)
