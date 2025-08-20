import sys
import os

# --- Path Correction ---
# This code helps Python find the 'services.py' file in the root directory
# when this tool is called from deep inside the 'src' folder.
# It goes up two levels from the current file's directory (tool_collections -> multi_agent_system -> src)
# to get to the project's root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
# --- End Path Correction ---

import services # Now this import should work

def send_reply_message(supabase_client, user_id: str, phone_number: str, message: str):
    """
    Sends a text message to the user's phone number. This should be the final action
    to deliver the AI's response to the user.
    
    Args:
        phone_number (str): The recipient's phone number from the original request.
        message (str): The text content to send to the user.
    """
    print(f"TOOL EXECUTED: send_reply_message")
    print(f"  - To: {phone_number}")
    print(f"  - Message: {message}")
    
    try:
        result = services.send_fonnte_message(phone_number, message)
        if result and result.get("status"):
            return {"status": "ok", "message": "Message sent successfully."}
        else:
            reason = result.get("reason", "Unknown Fonnte API error")
            return {"status": "error", "message": f"Failed to send message: {reason}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred while sending message: {str(e)}"}