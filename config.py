import os
from typing import Dict, Optional

# ==============================================================================
# --- CORE SECRETS & CREDENTIALS ---
# Load all secrets from environment variables in your Vercel project settings.
# This is the most secure and standard way for serverless deployments.
# ==============================================================================

# Fonnte API Token for sending WhatsApp messages
FONNTE_TOKEN: Optional[str] = os.environ.get("FONNTE_TOKEN")

# Supabase Project Credentials
SUPABASE_URL: Optional[str] = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY: Optional[str] = os.environ.get("SUPABASE_SERVICE_KEY")


# ==============================================================================
# --- GEMINI API KEY CONFIGURATION FOR APIKEYMANAGER ---
# This section is designed to gather all Gemini API keys from environment
# variables and provide them in the dictionary format that your ApiKeyManager expects.
#
# INSTRUCTIONS:
# In your Vercel project's Environment Variables, add your keys like this:
# GEMINI_API_KEY1="your_first_ai_key_here"
# GEMINI_API_KEY2="your_second_ai_key_here"
# GEMINI_API_KEY3="your_third_ai_key_here"
# ...and so on.
# ==============================================================================

def get_gemini_api_keys() -> Dict[str, str]:
    """
    Loads all Gemini API keys from environment variables into a named dictionary.

    This function scans for environment variables named `GEMINI_API_KEY1`, 
    `GEMINI_API_KEY2`, etc., and formats them into a dictionary like
    `{'gemini_1': 'key_value', 'gemini_2': 'key_value'}` which is the
    format expected by your ApiKeyManager.

    Returns:
        A dictionary mapping a generated key name to its value.
    """
    keys: Dict[str, str] = {}
    i = 1
    while True:
        # Continuously look for the next numbered key
        key_value = os.environ.get(f"GEMINI_API_KEY{i}")
        if key_value:
            # Add the key to the dictionary with a generated name
            keys[f"gemini_{i}"] = key_value
            i += 1
        else:
            # Stop when the next sequential key is not found
            break

    # As a fallback for a single, non-numbered key
    if not keys:
        legacy_key = os.environ.get("GEMINI_API_KEY")
        if legacy_key:
            keys["gemini_1"] = legacy_key

    if not keys:
        print("WARNING: No Gemini API keys were found in environment variables.")

    return keys


# ==============================================================================
# --- APPLICATION SETTINGS ---
# ==============================================================================

# Usage limits for the WhatsApp bot
UNVERIFIED_LIMIT: int = 10      # Lifetime message limit for non-registered numbers
VERIFIED_LIMIT: int = 100       # Daily message limit for verified users
MAX_AGENT_LOOPS: int = 5        # Safety limit for AI agent loops to prevent runaways


# ==============================================================================
# --- CHAT & TESTING CONFIGURATION ---
# ==============================================================================

CHAT_TEST_USER_ID: str = "e4824ec3-c9c4-4563-91f8-56077aa64d63"  # A test user UUID from your Supabase db
CHAT_TEST_PHONE: str = "CHAT_TEST_USER"                          # A special identifier for chat testing