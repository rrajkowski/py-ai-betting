# pages/live_scores_page.py

from app.auth import add_auth_to_page
from app.live_scores import display_live_scores

# Protect this page with authentication and subscription check
add_auth_to_page()

display_live_scores()
