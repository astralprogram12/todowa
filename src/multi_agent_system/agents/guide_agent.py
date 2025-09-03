import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GuideAgent:
    """An agent that provides basic guidance on how to use the application."""

    def __init__(self):
        # This agent doesn't require any external services like AI or a database yet.
        pass

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes the user's command to see if it's a request for help.
        """
        # Simple keyword-based detection for now.
        triggers = ["how do i use", "how to use", "help", "guide"]

        if any(trigger in user_command.lower() for trigger in triggers):

            # Construct a helpful guide message.
            guide_message = (
                "Welcome! Here's a quick guide to get you started:\\n\\n"
                "1. *Tasks*: You can ask me to create, update, or check your tasks. For example, try saying: 'add a task to buy milk' or 'what are my tasks for today?'\\n"
                "2. *Finances*: I can track your income and expenses. Try: 'I spent $10 on coffee' or 'add my salary of $2000'.\\n"
                "3. *Journals*: Keep a diary by telling me to 'create a journal entry'.\\n"
                "4. *Schedules*: Set reminders by saying 'remind me to call mom every day at 5pm'.\\n\\n"
                "Just type your request in plain English, and I'll do my best to help!"
            )

            return {
                'success': True,
                'response': guide_message,
                'actions': [] # No database actions needed for this agent.
            }
        else:
            # If the command doesn't seem to be about guidance, this agent can't handle it.
            return {
                'success': False,
                'response': "I am the guide agent, I can't help with that.",
                'actions': [],
                'error': 'Command not related to guidance.' # This helps the orchestrator know why it failed.
            }

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Creates a standardized error response."""
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}
