import os

# --- Secrets and Configurations ---
# It is STRONGLY recommended to load these from environment variables in production.
# Example for production: FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN")

# Fonnte API Token for sending WhatsApp messages
FONNTE_TOKEN = "fdPkqhCpSHzVBES3HHmZ"

# Google Generative AI API Key for accessing Gemini
GEMINI_API_KEY = "AIzaSyDq3N2Os_0KdR6f1vxVNWEHZJwXgQRdHKU"


# --- Supabase Project Credentials ---
# WARNING: The SERVICE_ROLE_KEY is a secret and should never be exposed in client-side code
# or committed to a public repository. Load it from an environment variable.
SUPABASE_URL = "https://heagzwnxlcvpwglyuoyg.supabase.co"
SUPABASE_SERVICE_KEY ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhlYWd6d254bGN2cHdnbHl1b3lnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ2NTE0MzQsImV4cCI6MjA3MDIyNzQzNH0.VpiIpl8XYSKFelu0EhIb2V8dZD23vQ1jQaurIoe91Ak"



# --- Application Settings ---

# Usage limits for the WhatsApp bot
UNVERIFIED_LIMIT = 10  # Lifetime message limit for numbers not registered
VERIFIED_LIMIT = 100   # Daily message limit for verified users
MAX_AGENT_LOOPS = 5 # Safety limit for the agent loop
# --- AI Instructions (System Prompt) ---
# This has been moved to agent.py to keep all AI logic together.