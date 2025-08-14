# app.py

import json
from flask import Flask, request, jsonify
from supabase import create_client, Client
import google.generativeai as genai
import traceback

# --- Local Imports ---
# Ensure these files exist in the same directory and are correctly named.
import config
import database
import services
import agent
from ai_tools import AVAILABLE_TOOLS

# --- Initialization ---
app = Flask(__name__)

# Configure AI and Supabase from your config.py file
# This will fail gracefully if the environment variables are not set.
try:
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
except Exception as e:
    print(f"!!! FATAL ERROR: Could not initialize services. Check your environment variables. Error: {e}")
    # In a real production scenario, you might exit or have more robust health checks.

# In-memory cache for conversation history.
# For production, consider using a persistent cache like Redis for better scalability.
CONVERSATION_HISTORIES = {}


@app.route('/test-actions', methods=['GET'])
def test_list_ai_actions():
    """
    A simple test endpoint to fetch AI Actions directly, bypassing the AI.
    """
    print("\n--- RUNNING DIRECT DATABASE TEST FOR AI ACTIONS ---")
    
    # !!! IMPORTANT !!!
    # REPLACE this placeholder with YOUR actual user_id from the Supabase screenshot.
    test_user_id = 'cf750539-b5f8-41fa-be5b-41298e19547d'
    
    print(f"Attempting to fetch actions for user_id: {test_user_id}")

    try:
        # This directly calls the function we want to test.
        actions = database.get_all_active_ai_actions(supabase, test_user_id)
        
        # We print the raw result directly to your console.
        print("--- RAW RESPONSE FROM database.get_all_active_ai_actions ---")
        print(actions)
        print("----------------------------------------------------------")

        # We also return a JSON response to the browser.
        return jsonify({
            "status": "success",
            "user_id_tested": test_user_id,
            "actions_found": len(actions),
            "data": actions
        }), 200

    except Exception as e:
        print(f"!!! ERROR DURING DIRECT DATABASE TEST: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Main webhook to handle all incoming messages."""
    if request.method == 'GET':
        # A simple health check endpoint for your hosting provider.
        return jsonify({"status": "Webhook is active and listening"}), 200

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
            reply = "Welcome! To get started, please sign up on our website."
            services.send_fonnte_message(sender_phone, reply)
            return jsonify({"status": "unauthorized_user_prompted"}), 200

        # --- 2. Manage Conversation History ---
        history = CONVERSATION_HISTORIES.get(sender_phone, [])
        history.append({"role": "user", "content": message_text})
        
        # --- 3. Get All Context and Run Agent ---
        print("\n--- AGENT RUN ---")
        
        # Fetch all context types required by the agent's system prompt
        task_data = database.get_task_context_for_ai(supabase, user_id)
  
        memory_data = database.get_memory_context_for_ai(supabase, user_id)
        user_data = database.get_user_context_for_ai(supabase, user_id)
        # --- NEW: ADD THE MISSING DATABASE CALL HERE ---
        ai_actions_data = database.get_all_active_ai_actions(supabase, user_id)
        reminders_data = database.get_all_reminders(supabase, user_id)
        # Combine all contexts into a single object for the agent
        full_context = {
            "tasks": task_data,
            "memory_context": memory_data,
            "user_context": user_data,
            # --- NEW: ADD THE AI ACTIONS TO THE CONTEXT OBJECT ---
            "ai_actions_context": {"actions": ai_actions_data},
            "reminders_context": {"reminders": reminders_data}
        }
        
        # Call the agent's main entrypoint function
        conversational_reply, actions = agent.run_agent_one_shot(
            model=model,
            history=history,
            context=full_context
        )
        print(f"AGENT REPLY: {conversational_reply}")
        print(f"AGENT ACTIONS: {json.dumps(actions, indent=2)}")

        # Add the AI's response to the history and trim to prevent excessive length
        history.append({"role": "assistant", "content": conversational_reply})
        CONVERSATION_HISTORIES[sender_phone] = history[-10:] # Keep last 5 user/assistant turns

        # --- 4. Execute the AI's Action Plan ---
        final_reply = conversational_reply # Start with the AI's default reply

        if actions:
            for action in actions:
                action_type = action.get("type")
                if action_type in AVAILABLE_TOOLS:
                    action_args = {k: v for k, v in action.items() if k != 'type'}
                    try:
                        print(f"EXECUTING ACTION: {action_type} with args {action_args}")
                        tool_result = AVAILABLE_TOOLS[action_type](supabase, user_id, **action_args)
                        
                        # This logic for handling the result is still correct
                        if isinstance(tool_result, str):
                            final_reply = tool_result
                        elif isinstance(tool_result, dict) and tool_result.get("message"):
                            final_reply = tool_result["message"]

                        # --- THE FIX IS HERE ---
                        # This is a much simpler and more robust way to handle tool output.
                        
                        # If the tool returns a string, that string is our new final reply.
                        # This will correctly handle list_ai_actions and search_memories.
                        if isinstance(tool_result, str):
                            final_reply = tool_result
                            
                        # If the tool returns a dictionary with a 'message' key, use that.
                        # This handles all our other tools (add, update, delete, etc.).
                        elif isinstance(tool_result, dict) and tool_result.get("message"):
                            final_reply = tool_result["message"]

                    except Exception as e:
                        print(f"!!! TOOL EXECUTION FAILED for '{action_type}': {e}")
                        traceback.print_exc()
                        final_reply += f"\n\n(Note: I had an issue performing the '{action_type}' action.)"
                else:
                    print(f"!!! WARNING: Agent planned an unknown action type: '{action_type}'")
        
        # --- 5. Send the Final Reply to the User ---
        services.send_fonnte_message(sender_phone, final_reply)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"!!! AN UNEXPECTED ERROR OCCURRED IN WEBHOOK: {e}")
        traceback.print_exc()
        error_reply = "I seem to have run into an unexpected problem. My developers have been notified."
        
        # Avoid sending messages in a loop if the messaging service itself is what's failing
        if 'services' in locals() and hasattr(services, 'send_fonnte_message') and 'sender_phone' in locals():
            services.send_fonnte_message(sender_phone, error_reply)
            
        return jsonify({"status": "internal_server_error"}), 500

# --- Server Entrypoint ---
if __name__ == '__main__':
    # Use Waitress, a production-ready WSGI server that works well on Windows and other platforms.
    from waitress import serve
    port = 5000
    print(f"--- Starting production server with Waitress on port {port} ---")
    serve(app, host='0.0.0.0', port=port)



