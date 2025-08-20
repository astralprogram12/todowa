# config.py
# Configuration for the multi-agent system

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# AI model configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Messaging service configuration
FONNTE_TOKEN = os.environ.get('FONNTE_TOKEN')
