# app.py

import json
from flask import Flask, request, jsonify
from supabase import create_client, Client
import google.generativeai as genai
import traceback
<<<<<<< HEAD
=======
import sys
import os

# Get current directory (where app.py is located)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add current directory to path
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Add src directory to path
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)
>>>>>>> parent of 0aea5ac (Update app.py)

# --- Local Imports ---
# Ensure these files exist in the same directory and are correctly named.
import config
import database_personal
import database_silent
import services
import agent
from ai_tools import AVAILABLE_TOOLS

# Import the multi-agent system
# (This will be done in run.py, but we define it here for imports)

# --- Initialization ---
app = Flask(__name__)

<<<<<<< HEAD
# Configure AI and Supabase from your config.py file
# This will fail gracefully if the environment variables are not set.
try:
    if not all([config.GEMINI_API_KEY, config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY]):
        raise ValueError("One or more critical environment variables (GEMINI, SUPABASE) are missing.")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

except Exception as e:
    print(f"!!! FATAL ERROR: Could not initialize services. Check your environment variables. Error: {e}")
    traceback.print_exc()
    # Exit the application if critical services cannot be loaded.
    sys.exit(1)
=======
# These variables will be set by run.py
supabase = None
model = None
multi_agent_system = None
>>>>>>> parent of 0aea5ac (Update app.py)

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
<<<<<<< HEAD
        # This directly calls the function we want to test.
        actions = database_personal.get_all_active_ai_actions(supabase, test_user_id)
        
        # We print the raw result directly to your console.
        print("--- RAW RESPONSE FROM database_personal.get_all_active_ai_actions ---")
        print(actions)
        print("----------------------------------------------------------")

        # We also return a JSON response to the browser.
        return jsonify({
            "status": "success",
            "user_id_tested": test_user_id,
            "actions_found": len(actions),
            "data": actions
        }), 200

=======
        # Make sure supabase is initialized
        if not supabase:
            return jsonify({"error": "Supabase client not initialized"}), 500
        
        # Import database functions through supabase_integration
        from src.multi_agent_system.tool_collections.database_tools import get_all_active_ai_actions
        
        # Query actions
        actions = get_all_active_ai_actions(supabase, test_user_id)
        return jsonify({"success": True, "actions": actions})
>>>>>>> parent of 0aea5ac (Update app.py)
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
<<<<<<< HEAD
        data = request.get_json()
        sender_phone = data.get('sender')
        message_text = data.get('message')

        if not sender_phone or not message_text:
            return jsonify({"status": "error", "message": "Missing sender or message"}), 400

        user_id = database_personal.get_user_id_by_phone(supabase, sender_phone)
        is_allowed, limit_message = database_personal.check_and_update_usage(supabase, sender_phone, user_id)

        if not is_allowed:
            services.send_fonnte_message(sender_phone, limit_message)
            return jsonify({"status": "limit_exceeded"}), 429
            
        if not user_id:
            reply = "Welcome! To get started, please sign up on our website."
            services.send_fonnte_message(sender_phone, reply)
            return jsonify({"status": "unauthorized_user_prompted"}), 200

        # --- 2. Check Silent Mode Status ---
        active_silent_session = database_silent.get_active_silent_session(supabase, user_id)
        is_silent_mode = active_silent_session is not None
        
        # Check for silent mode commands first
        message_lower = message_text.lower().strip()
        
        # Handle silent mode deactivation commands
        if is_silent_mode and any(cmd in message_lower for cmd in ['exit silent', 'end silent', 'stop silent', 'deactivate silent']):
            try:
                tool_result = AVAILABLE_TOOLS['deactivate_silent_mode'](supabase, user_id)
                if tool_result and tool_result.get('status') == 'ok':
                    services.send_fonnte_message(sender_phone, tool_result.get('message', 'Silent mode ended.'))
                    return jsonify({"status": "success", "action": "silent_mode_deactivated"}), 200
            except Exception as e:
                print(f"!!! ERROR deactivating silent mode: {e}")
                services.send_fonnte_message(sender_phone, "I had trouble ending silent mode, but let me try to process your message normally.")
        
        # Handle silent mode activation commands
        elif not is_silent_mode and any(cmd in message_lower for cmd in ['silent for', 'don\'t reply for', 'go silent', 'activate silent']):
            # Extract duration from message
            duration_minutes = None
            try:
                import re
                # Look for patterns like "for 2 hours", "for 60 minutes"
                hour_match = re.search(r'for\s+(\d+)\s*h(?:our)?s?', message_lower)
                minute_match = re.search(r'for\s+(\d+)\s*m(?:inute)?s?', message_lower)
                
                if hour_match:
                    duration_minutes = int(hour_match.group(1)) * 60
                elif minute_match:
                    duration_minutes = int(minute_match.group(1))
                else:
                    # Default to 1 hour if no specific time mentioned
                    duration_minutes = 60
                
                tool_result = AVAILABLE_TOOLS['activate_silent_mode'](supabase, user_id, duration_minutes=duration_minutes)
                if tool_result:
                    services.send_fonnte_message(sender_phone, tool_result.get('message', 'Silent mode activated.'))
                    return jsonify({"status": "success", "action": "silent_mode_activated"}), 200
            except Exception as e:
                print(f"!!! ERROR activating silent mode: {e}")
                services.send_fonnte_message(sender_phone, "I had trouble activating silent mode. Please try again.")
                return jsonify({"status": "error", "action": "silent_mode_activation_failed"}), 500
        
        # If in silent mode and not a deactivation command, accumulate the message
        if is_silent_mode:
            print(f"\n--- SILENT MODE: Accumulating message from {sender_phone} ---")
            try:
                # Add the user input to silent session
                action_data = {
                    'action_type': 'user_message',
                    'details': {
                        'message': message_text,
                        'phone': sender_phone,
                        'user_input': message_text
                    }
                }
                database_silent.add_action_to_silent_session(supabase, active_silent_session['id'], action_data)
                print(f"Message accumulated in silent session {active_silent_session['id']}")
                
                # Don't send any reply - just return success
                return jsonify({"status": "success", "action": "message_accumulated_silent_mode"}), 200
                
            except Exception as e:
                print(f"!!! ERROR accumulating message in silent mode: {e}")
                # If there's an error with silent mode, process normally as fallback
                pass
        
        # --- 3. Manage Conversation History ---
        history = CONVERSATION_HISTORIES.get(sender_phone, [])
        history.append({"role": "user", "content": message_text})
        
        # --- 4. Get All Context and Run Agent ---
        print("\n--- AGENT RUN ---")
        
        # Fetch all context types required by the agent's system prompt
        task_data = database_personal.get_task_context_for_ai(supabase, user_id)
  
        memory_data = database_personal.get_memory_context_for_ai(supabase, user_id)
        user_data = database_personal.get_user_context_for_ai(supabase, user_id)
        # --- NEW: ADD THE MISSING DATABASE CALL HERE ---
        ai_actions_data = database_personal.get_all_active_ai_actions(supabase, user_id)
        reminders_data = database_personal.get_all_reminders(supabase, user_id)
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
        
        # Store conversation history in memory
        try:
            database_personal.store_conversation_history(supabase, user_id, history)
        except Exception as e:
            print(f"!!! ERROR STORING CONVERSATION HISTORY: {e}")

        # --- 5. Execute the AI's Action Plan ---
        final_reply = conversational_reply  # <-- keep this as the default

        if actions:
            for action in actions:
                action_type = action.get("type")
                if action_type in AVAILABLE_TOOLS:
                    action_args = {k: v for k, v in action.items() if k not in ["type", "user_id"]}

                    try:
                        print(f"EXECUTING ACTION: {action_type} with args {action_args}")
                        
                        # Check if we should accumulate this action in silent mode
                        # (This is a backup check - main silent mode logic is handled above)
                        current_silent_session = database_silent.get_active_silent_session(supabase, user_id)
                        if current_silent_session and action_type not in ['deactivate_silent_mode', 'get_silent_status']:
                            # Accumulate action instead of executing
                            action_data = {
                                'action_type': action_type,
                                'details': action_args,
                                'user_input': message_text
                            }
                            database_silent.add_action_to_silent_session(supabase, current_silent_session['id'], action_data)
                            print(f"Action {action_type} accumulated in silent mode")
                            continue
                        
                        # Execute action normally
                        tool_result = AVAILABLE_TOOLS[action_type](supabase, user_id, **action_args)

                        # ✅ Only overwrite reply if the tool explicitly reports an error or important message
                        if isinstance(tool_result, dict) and tool_result.get("error"):
                            final_reply += f"\n\n(Note: {tool_result['error']})"

                    except Exception as e:
                        print(f"!!! TOOL EXECUTION FAILED for '{action_type}': {e}")
                        traceback.print_exc()
                        final_reply += f"\n\n(Note: I had an issue performing the '{action_type}' action.)"
                else:
                    print(f"!!! WARNING: Agent planned an unknown action type: '{action_type}'")
        
        # --- 6. Send the Final Reply to the User ---
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



=======
        # Get data from the request. This might be a dict or a string.
        data = request.get_json(silent=True)

        # If get_json() fails (e.g., wrong content type), it returns None.
        # In that case, get the raw data as text.
        if data is None:
            raw_data = request.get_data(as_text=True)
            # If we got raw data, try to parse it as JSON
            if raw_data:
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    return jsonify({"error": "Invalid JSON format received"}), 400
            else:
                # Handle cases where there is no data at all
                return jsonify({"error": "No data received"}), 400
        
        # At this point, 'data' should be a dictionary.
        # Now you can safely use .get()
        user_id = data.get('user_id')
        message_text = data.get('message', {}).get('text', '')
        
        if not user_id or not message_text:
            return jsonify({"error": "Missing user_id or message text"}), 400
        
        # Process the message through the multi-agent system
        # Ensure multi_agent_system is initialized
        if not multi_agent_system:
            return jsonify({"error": "Multi-agent system not initialized"}), 500
        
        response = multi_agent_system.process_message(user_id, message_text)
        
        return jsonify({"success": True, "response": response})

    except Exception as e:
        # It's helpful to log the type of data that caused the error
        print(f"Error processing webhook. Data type received: {type(request.get_data(as_text=True))}")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy", "message": "Multi-agent system with Supabase is running"})
>>>>>>> parent of 0aea5ac (Update app.py)
