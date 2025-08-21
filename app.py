# app.py
# This file now contains the Flask app AND its full initialization logic.

import os
import sys
import json
import traceback
import asyncio # <--- [THE FIX] IMPORT THE ASYNCIO LIBRARY
import database_personal


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
    model = genai.GenerativeModel('gemini-2.5-flash')

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

        sender_phone = data.get('pengirim') or data.get('sender')
        message_text = data.get('pesan') or data.get('message')

        if not sender_phone or not message_text:
            return jsonify({"error": "Missing sender phone number or message text"}), 400
        
        # --- [THE FIX] LOOK UP THE REAL USER ID ---
        # 1. Call the function that ALREADY EXISTS in your database_personal.py file.
        real_user_id = database_personal.get_user_id_by_phone(supabase, sender_phone)
        
        # 2. Handle the case where the user is not registered in your system.
        if not real_user_id:
            print(f"Unauthorized access attempt from phone number: {sender_phone}")
            # For now, we return an error. You could also send a message back here.
            return jsonify({"error": "User not found for this phone number."}), 404

        # 3. Call the agent system with the CORRECT UUID and the phone number.
        print(f"[WEBHOOK] Calling async agent for user_id {real_user_id}...")
        response = asyncio.run(multi_agent_system.process_user_input(
            user_id=real_user_id,          # Pass the UUID here
            user_input=message_text,
            phone_number=sender_phone      # Pass the phone number separately for replies
        ))
        print(f"[WEBHOOK] Agent returned internal response: {response}")
        # --- [END OF FIX] ---
        
        return jsonify({"success": True, "response_from_agent": response})

    except Exception as e:
        print(f"An unexpected error occurred in webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    if multi_agent_system:
        return jsonify({"status": "healthy", "message": "Multi-agent system is initialized."})
    else:
        return jsonify({"status": "unhealthy", "message": "Multi-agent system failed to initialize."}), 500