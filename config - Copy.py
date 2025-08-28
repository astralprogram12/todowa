import os
from typing import Dict, Any, List

# --- Secrets and Configurations ---
# It is STRONGLY recommended to load these from environment variables in production.
# Example for production: FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN")

# Fonnte API Token for sending WhatsApp messages
FONNTE_TOKEN = "fdPkqhCpSHzVBES3HHmZ"

# Legacy Google Generative AI API Key for accessing Gemini (DEPRECATED)
# This is kept for backward compatibility. Use API_KEYS_CONFIG for new setups.
GEMINI_API_KEY = "AIzaSyC-tmPGOZMvHV7RxlqQJ_O_coCV8_56AUk"


UNVERIFIED_LIMIT = 10  # Lifetime message limit for numbers not registered
VERIFIED_LIMIT = 100   # Daily message limit for verified users
MAX_AGENT_LOOPS = 5 # Safety limit for the agent loop
# --- API Key Management Configuration ---
# JSON-based named API key configuration with database integration

# Named API Keys Configuration (JSON format)
# Focused on Gemini API keys with simple numbered naming
NAMED_API_KEYS = {
    "gemini": {
        "gemini 1": "AIzaSyC-tmPGOZMvHV7RxlqQJ_O_coCV8_56AUk",  # Current primary key
        "gemini 2": "AIzaSyDq3N2Os_0KdR6f1vxVNWEHZJwXgQRdHKU",  # Additional Gemini key
        "gemini 3": "AIzaSyBGpmqafTsj_memh37vGwreF-s8HdWnvA8",  # Additional Gemini key
        "gemini 4": "AIzaSyBg4WiPHvOM4s8m_14olZ34z9x6YCAChcM",  # Additional Gemini key
        "gemini 5": "AIzaSyCteSXCkElX6gyyQfXs-KWAiuDUSGBYgD4",  # Additional Gemini key
        "gemini 6": "AIzaSyBDfcZXfEihJbxFR7HFGxJ8cqvF3PRFWn4",  # Add your additional Gemini keys here
        "gemini 7": "AIzaSyCxykg818KhSvxXg8xljjYZzyLEnvFVReg",  # Add your additional Gemini keys sadssd
        "gemini 8": "AIzaSyDgIGOMSHmmWX8Pw8qwjFk-2dTVAjV_uX0",  # Add your additional Gemini keys here
        "gemini 9": "AIzaSyA2Y_0fK68rDjysc-ZtNc1T5MOH1WgbJ9A",  # Add your additional Gemini keys here
        "gemini 10": "AIzaSyBGpmqafTsj_memh37vGwreF-s8HdWnvA8", # Add your additional Gemini keys here
    }
}

def get_named_api_keys() -> Dict[str, Dict[str, str]]:
    """
    Get the named API keys configuration.
    
    This function returns the JSON-structured API keys organized by provider.
    Each provider has named keys (e.g., "primary", "backup", "development").
    
    Returns:
        Dict with provider -> {key_name: key_value} mapping
    """
    # Filter out empty keys
    filtered_keys = {}
    for provider, keys in NAMED_API_KEYS.items():
        filtered_keys[provider] = {name: key for name, key in keys.items() if key and key.strip()}
    
    return filtered_keys

def get_api_keys_config() -> Dict[str, Any]:
    """
    Get API keys configuration for Gemini provider with rotation support.
    
    DEPRECATED: This function is maintained for backward compatibility.
    New code should use get_named_api_keys() and ApiKeyManager.
    
    This function supports both environment variables and direct configuration.
    Environment variables take precedence over hardcoded values.
    
    Environment variable format:
    - GEMINI_API_KEYS: Comma-separated list of Gemini API keys
    
    Returns:
        Dict with provider configurations including API keys, rate limits, etc.
    """
    
    # Load from environment variables first
    gemini_keys_env = os.environ.get("GEMINI_API_KEYS", "")
    
    # Parse environment keys
    gemini_keys = [key.strip() for key in gemini_keys_env.split(",") if key.strip()]
    
    # If no environment keys, use named keys from JSON config
    if not gemini_keys:
        named_keys = get_named_api_keys()
        gemini_keys = list(named_keys.get("gemini", {}).values())
    
    # Final fallback to legacy GEMINI_API_KEY
    if not gemini_keys and GEMINI_API_KEY:
        gemini_keys = [GEMINI_API_KEY]
    
    config = {}
    
    # Configure Gemini keys only
    if gemini_keys:
        config["gemini"] = {
            "keys": []
        }
        
        for i, api_key in enumerate(gemini_keys):
            config["gemini"]["keys"].append({
                "key_id": f"gemini_{i+1}",
                "api_key": api_key,
                "name": f"Gemini {i+1}",
                "rate_limit_per_minute": 60,  # Gemini free tier limit
                "rate_limit_per_day": 1500    # Gemini free tier daily limit
            })
    
    return config

# API Key rotation settings
API_KEY_ROTATION_STRATEGY = os.environ.get("API_KEY_ROTATION_STRATEGY", "smart")  # round_robin, random, least_used, smart
API_KEY_MAX_RETRIES = int(os.environ.get("API_KEY_MAX_RETRIES", "3"))
API_KEY_HEALTH_CHECK_INTERVAL = int(os.environ.get("API_KEY_HEALTH_CHECK_INTERVAL", "300"))  # seconds


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

# --- Chat Configuration ---
CHAT_TEST_USER_ID = "e4824ec3-c9c4-4563-91f8-56077aa64d63"  # Test user created in Supabase
CHAT_TEST_PHONE = "CHAT_TEST_USER"  # Identifier for chat testing

# --- AI Instructions (System Prompt) ---
# This has been moved to agent.py to keep all AI logic together.