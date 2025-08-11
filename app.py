# app.py

import json
from flask import Flask, request, jsonify
from supabase import create_client, Client
import google.generativeai as genai
import traceback

# --- Local Imports ---
import config
import database
import services
import agent
from ai_tools import AVAILABLE_TOOLS

# --- Initialization ---
app = Flask(__name__)

# Configure AI and Supabase
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash') # Using 1.5 Flash as a good default
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

# Simple in-memory cache for conversation history
CONVERSATION_HISTORIES = {}

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return jsonify({"status": "Webhook is active"}), 200

    # --- 1. Request Parsing and User Verification ---
    try:
        data = request.get_json()
        sender_phone = data.get('sender')
        message_text = data.get('message')

        if not sender_phone or not message_text:
            return jsonify({"status": "error", "message": "Missing sender or message"}), 400

        user_id = database.get_user_id_by_phone(supabase, sender_phone)
        is_allowed, limit_message = database.check_and_update_usage(supabase, sender_phone, user_id)

        if not is_allowed:
            services.send_fonnte_message(sender_phone, limit_message)
            return jsonify({"status": "limit_exceeded"}), 429
            
        if not user_id:
            reply = "Welcome! Please sign up on our website to get started."
            services.send_fonnte_message(sender_phone, reply)
            return jsonify({"status": "unauthorized_user_prompted"}), 200

        # --- 2. Manage Conversation History ---
        history = CONVERSATION_HISTORIES.get(sender_phone, [])
        history.append({"role": "user", "content": message_text})
        
        # --- 3. Get Context and Run Agent (FIXED BLOCK) ---
        print("\n--- AGENT RUN ---")
        
        # STEP 1: Fetch both task and list context
        task_data = database.get_task_context_for_ai(supabase, user_id)
        list_data = database.get_list_context_for_ai(supabase, user_id)
        
        # STEP 2: Combine them into the structure the agent expects
        full_context = {
            "tasks": task_data.get("tasks", []),
            "list_context": list_data
        }
        
        # STEP 3: Call the agent with the correct 'context' keyword
        conversational_reply, actions = agent.run_agent_one_shot(
            model=model,
            history=history,
            context=full_context  # <-- THE FIX IS HERE
        )
        print(f"AGENT REPLY: {conversational_reply}")
        print(f"AGENT ACTIONS: {json.dumps(actions, indent=2)}")

        # Add the AI's response to the history for the next turn
        history.append({"role": "assistant", "content": conversational_reply})
        # Keep history to the last 10 messages (5 turns) to manage token size
        CONVERSATION_HISTORIES[sender_phone] = history[-10:]

        # --- 4. Execute the AI's Action Plan ---
        if actions:
            for action in actions:
                action_type = action.get("type")
                if action_type in AVAILABLE_TOOLS:
                    # Pass all keys except 'type' as arguments to the tool
                    action_args = {k: v for k, v in action.items() if k != 'type'}
                    try:
                        print(f"EXECUTING ACTION: {action_type} with args {action_args}")
                        AVAILABLE_TOOLS[action_type](supabase, user_id, **action_args)
                    except Exception as e:
                        print(f"!!! TOOL EXECUTION FAILED for '{action_type}': {e}")
                        # Optionally append a note to the reply about the failure
                        conversational_reply += f"\n\n(Note: I had an issue performing the '{action_type}' action.)"
                else:
                    print(f"!!! WARNING: Agent planned an unknown action type: '{action_type}'")
        
        # --- 5. Send the Final Reply to the User ---
        services.send_fonnte_message(sender_phone, conversational_reply)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"!!! AN UNEXPECTED ERROR OCCURRED IN WEBHOOK: {e}")
        traceback.print_exc()
        error_reply = "I seem to have run into an unexpected problem. My developers have been notified."
        # Avoid sending messages in a loop if the messaging service itself fails
        if 'services' in locals() and hasattr(services, 'send_fonnte_message'):
            services.send_fonnte_message(sender_phone, error_reply)
        return jsonify({"status": "internal_server_error"}), 500
