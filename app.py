import json
from flask import Flask, request, jsonify
from supabase import create_client, Client
import google.generativeai as genai
import traceback
import sys
import os

# --- Boilerplate Setup ---
# Get current directory (where app.py is located)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add current directory to path
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Add src directory to path
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.append(src_dir)

# --- Local Imports ---
# Import original modules - these will be imported from Supabase integration
import config

# --- Initialization ---
app = Flask(__name__)

# These variables will be set by a runner script (e.g., run.py)
supabase = None
model = None
multi_agent_system = None

# In-memory cache for conversation history.
# For production, consider using a persistent cache like Redis.
CONVERSATION_HISTORIES = {}


@app.route('/test-actions', methods=['GET'])
def test_list_ai_actions():
    """A simple test endpoint to fetch AI Actions directly, bypassing the AI."""
    print("\n--- RUNNING DIRECT DATABASE TEST FOR AI ACTIONS ---")
    
    # Replace this placeholder with an actual user_id from your database.
    test_user_id = 'cf750539-b5f8-41fa-be5b-41298e19547d' # !!! IMPORTANT !!!
    
    try:
        if not supabase:
            return jsonify({"error": "Supabase client not initialized"}), 500
        
        from src.multi_agent_system.tool_collections.database_tools import get_all_active_ai_actions
        
        actions = get_all_active_ai_actions(supabase, test_user_id)
        return jsonify({"success": True, "actions": actions})
    except Exception as e:
        print(f"Error in test endpoint: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    """Main webhook endpoint for processing incoming messages."""
    try:
        # Step 1: Get the raw request body as text. This is the most reliable way.
        raw_data = request.get_data(as_text=True)

        if not raw_data:
            print("Webhook Error: Received an empty request body.")
            return jsonify({"error": "Empty request body received"}), 400

        # Step 2: Manually parse the raw text data into a Python dictionary.
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            print(f"Webhook Error: Failed to decode JSON. Raw data received: {raw_data}")
            return jsonify({"error": "Invalid JSON format in request body"}), 400

        # Step 3: Verify that the parsed data is a dictionary.
        if not isinstance(data, dict):
            print(f"Webhook Error: JSON did not parse into a dictionary. Type: {type(data)}")
            return jsonify({"error": "Request body must be a JSON object (dictionary)"}), 400

        # --- From this point on, 'data' is guaranteed to be a dictionary ---
        print(f"Webhook successfully parsed data: {data}")

        # Step 4: Safely extract user ID and message text using .get()
        user_id = data.get('user_id')
        message_text = data.get('message', {}).get('text', '')
        
        if not user_id or not message_text:
            print(f"Webhook Error: Missing 'user_id' or 'text'. UserID: {user_id}, Message: {message_text}")
            return jsonify({"error": "Missing user_id or message text in JSON body"}), 400
        
        # Ensure the agent system is ready before processing
        if multi_agent_system is None:
            print("Webhook Error: multi_agent_system is not initialized.")
            return jsonify({"error": "Internal server error: agent system not ready"}), 500

        # Process the message through the multi-agent system
        response = multi_agent_system.process_message(user_id, message_text)
        
        return jsonify({"success": True, "response": response})

    except Exception as e:
        print(f"An unexpected error occurred in webhook: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy", "message": "Multi-agent system with Supabase is running"})