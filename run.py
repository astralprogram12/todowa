#!/usr/bin/env python
# run.py
# Entry point for the enhanced multi-agent system

import os
import sys

# Get current directory (where run.py is located)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add current directory to path
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Add src directory to path
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Define prompt files directory
prompts_dir = os.path.join(current_dir, 'prompts')
if not os.path.exists(prompts_dir):
    print(f"WARNING: Prompts directory not found at {prompts_dir}")

# Import Supabase integration
import supabase_integration

# Import dependencies
from supabase import create_client
import google.generativeai as genai
import config

# Configure services
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')
supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

# Import multi-agent system
from src.multi_agent_system.orchestrator import create_multi_agent_system

# Create the multi-agent system
# Pass the prompts directory to the orchestrator
multi_agent_system = create_multi_agent_system(supabase, model, prompts_dir=prompts_dir)

# Print status
print("Enhanced multi-agent system initialized with Supabase integration")
print(f"Supabase URL: {config.SUPABASE_URL}")
print(f"AI Model: gemini-2.5-flash-lite")
print(f"Prompts directory: {prompts_dir}")

# Start the Flask app
import app
print("Starting Flask app...")
app.multi_agent_system = multi_agent_system
app.supabase = supabase
app.model = model

# Run the app
if __name__ == "__main__":
    from waitress import serve
    port = 5000
    print(f"--- Starting production server with Waitress on port {port} ---")
    serve(app.app, host='0.0.0.0', port=port)
