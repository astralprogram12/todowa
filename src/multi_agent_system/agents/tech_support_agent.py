import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TechSupportPromptBuilder:
    """Constructs prompts for the TechSupportAgent."""

    def build_intent_parser_prompt(self, user_command: str) -> str:
        """Builds a prompt to parse the user's tech support request."""
        return f"""
You are an expert at parsing structured commands. Your task is to extract the user's original message from a command to create a tech support ticket.

Command: "{user_command}"

**CRITICAL GOAL:** Your response MUST be a single JSON object with one key: "message".

---
**EXAMPLES**
---

# Command: "create a new tech support ticket with the message 'this isn't working, I'm so frustrated! it's not saving my tasks'"
Response: {{"message": "this isn't working, I'm so frustrated! it's not saving my tasks"}}

# Command: "create a new tech support ticket with the message 'the app crashed when I tried to add a reminder'"
Response: {{"message": "the app crashed when I tried to add a reminder"}}

---
Now, analyze the command carefully. Respond with ONLY a valid JSON object.
"""

class TechSupportAgent:
    """An agent that handles user frustration and technical issues by creating a support ticket."""

    def __init__(self, ai_model=None, supabase=None):
        self.ai_model = ai_model
        self.supabase = supabase
        self.prompt_builder = TechSupportPromptBuilder()

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Processes the structured command and creates a tech support ticket action.
        """
        if not self.ai_model:
            return self._error_response("Tech Support Agent is not properly initialized.")

        try:
            prompt = self.prompt_builder.build_intent_parser_prompt(user_command)
            ai_response_text = self._make_ai_request_sync(prompt)
            if not ai_response_text:
                return self._error_response("I couldn't understand the message for the support ticket.")

            parsed_response = json.loads(ai_response_text)
            message = parsed_response.get('message')

            if not message:
                return self._error_response("I understood you need help, but I couldn't get the details. Could you please rephrase?")

            action = {
                'type': 'create_tech_support_ticket',
                'message': message
            }

            response_message = (
                "I'm sorry you're having trouble. I've created a tech support ticket for you. "
                "Our support team will look into it as soon as possible."
            )

            return {
                'success': True,
                'response': response_message,
                'actions': [action]
            }
        except json.JSONDecodeError:
            logger.warning(f"TechSupportAgent failed to parse AI response: {ai_response_text}")
            return self._error_response("I had trouble understanding the response from my AI module.")
        except Exception as e:
            logger.exception(f"TechSupportAgent processing failed unexpectedly: {e}")
            return self._error_response("An error occurred while creating your support ticket.")

    def _make_ai_request_sync(self, prompt: str) -> Optional[str]:
        """Makes a synchronous request to the AI model."""
        if not self.ai_model:
            return None
        try:
            response = self.ai_model.generate_content(prompt)
            return response.text.strip().replace('```json', '').replace('```', '')
        except Exception as e:
            logger.exception(f"AI request failed in TechSupportAgent: {e}")
            return None

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Creates a standardized error response."""
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}
