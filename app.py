# app.py

import json
from flask import Flask, request, jsonify
from supabase import create_client, Client
import google.generativeai as genai
import traceback
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

# --- Local Imports ---
# Import original modules - these will be imported from Supabase integration
import config

# Import the multi-agent system
# (This will be done in run.py, but we define it here for imports)

# --- Initialization ---
app = Flask(__name__)

# These variables will be set by run.py
supabase = None
model = None
multi_agent_system = None

# In-memory cache for conversation history.
# For production, consider using a persistent cache like Redis for better scalability.
CONVERSATION_HISTORIES = {}


@app.route('/test-actions', methods=['GET'])
def test_list_ai_actions():
    """A simple test endpoint to fetch AI Actions directly, bypassing the AI."""
    print("\n--- RUNNING DIRECT DATABASE TEST FOR AI ACTIONS ---")
    
    # !!! IMPORTANT !!!
    # REPLACE this placeholder with YOUR actual user_id from the Supabase screenshot.
    test_user_id = 'cf750539-b5f8-41fa-be5b-41298e19547d'
    
    try:
        # Make sure supabase is initialized
        if not supabase:
            return jsonify({"error": "Supabase client not initialized"}), 500
        
        # Import database functions through supabase_integration
        from src.multi_agent_system.tool_collections.database_tools import get_all_active_ai_actions
        
        # Query actions
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
