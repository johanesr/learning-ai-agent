"""
JADWAL — Week 5, Step 5.7: one-time Google OAuth setup.

Run this once. It opens your browser, you log into Google and approve
calendar access, and it saves a refresh token to token.pickle so future
scripts (jadwal_mcp.py, etc.) can talk to your real Google Calendar without
logging in again — until Testing mode's 7-day refresh token expiry kicks in,
at which point you just run this again.

RUN:
  uv run google_auth_setup.py
"""

import pickle

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)

with open("token.pickle", "wb") as f:
    pickle.dump(creds, f)

print("Saved token.pickle — you won't need to log in again until it expires.")
