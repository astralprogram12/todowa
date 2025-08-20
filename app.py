# app.py
# This file now contains the Flask app AND its full initialization logic.

import os
import sys
import json
import traceback
import asyncio # <--- [THE FIX] IMPORT THE ASYNCIO LIBRARY

# --- 1. Add Project Directories to Python Path ---
# This ensures that imports from 'src' and root-level files work correctly.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# --- 2. Import All Necessary Modules ---
import google.generativeai as genai
from supabase import create_client, Client
from flask import Flask, request, jsonify

import config
from src.multi_agent_system.orchestrator import Orchestrator

# --- 3. Create and Initialize the Flask App ---
app = Flask(__name__)

# --- Initialize all services and the agent system directly in this file ---
try:
    print("--- [APP.PY] INITIALIZATION STARTED ---")

    print("[APP.PY] Initializing Google Generative AI...")
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    print("[APP.PY] Initializing Supabase client...")
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    print("[APP.PY] Creating Orchestrator instance...")
    multi_agent_system = Orchestrator(supabase, model)

    print("[APP.PY] Warming up agent by loading prompts...")
    prompts_dir = os.path.join(current_dir, 'prompts')
    multi_agent_system.load_all_agent_prompts(prompts_dir)

    print("--- [APP.PY] INITIALIZATION COMPLETE. Agent is ready. ---")

except Exception as e:
    print(f"FATAL: Application failed to initialize in app.py.")
    traceback.print_exc()
    multi_agent_system = None

# --- 4. Define Webhook and Other Routes ---
@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook endpoint for processing incoming messages."""
    if multi_agent_system is None:
        print("Webhook Error: multi_agent_system is None. Initialization likely failed during startup.")
        return jsonify({"error": "Internal server error: The agent system is not available."}), 500

    try:
        raw_data = request.get_data(as_text=True)
        data = json.loads(raw_data)
        print(f"Webhook successfully parsed data: {data}")

        user_id = data.get('pengirim') or data.get('sender')
        message_text = data.get('pesan') or data.get('message')

        if not user_id or not message_text:
            return jsonify({"error": "Missing user identifier or message text"}), 400
        
        # --- [THE FIX] ---
        # Use asyncio.run() to execute the async function and get its result.
        # This resolves the "coroutine was never awaited" error.
        print("[WEBHOOK] Calling async agent from sync context...")
        response = asyncio.run(multi_agent_system.process_user_input(user_id, message_text))
        print(f"[WEBHOOK] Agent returned response: {response}")
        # --- [END OF FIX] ---
        
        return jsonify({"success": True, "response": response})

    except Exception as e:
        print(f"An unexpected error occurred in webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    if multi_agent_system:
        return jsonify({"status": "healthy", "message": "Multi-agent system is initialized."})
    else:
        return jsonify({"status": "unhealthy", "message": "Multi-agent system failed to initialize."}), 500