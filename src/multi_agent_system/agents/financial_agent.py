import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class FinancialPromptBuilder:
    """Constructs prompts for the FinancialAgent."""

    def build_intent_parser_prompt(self, user_command: str) -> str:
        """Builds a prompt to parse the user's financial intent."""
        return f"""
You are an expert financial assistant. Your task is to analyze a user's command and deconstruct it into a list of specific, standalone financial actions.

User Command: "{user_command}"

**CRITICAL GOAL:** Your response MUST be a single JSON object with one key: "actions". The value of "actions" must be a list of action objects. Each action object must have an "intent" and other relevant fields.

**JSON Field Definitions for Each Action:**
- "intent": One of ['add_expense', 'add_income', 'set_budget'].
- "amount": The numeric amount of the transaction or budget.
- "currency": The currency code (e.g., 'USD', 'IDR'). Default to 'USD' if not specified.
- "category": The category of the expense, income, or budget.
- "description": A brief description of the transaction.
- "period": For budgets, the period ('weekly', 'monthly', 'yearly').

---
**EXAMPLES**
---

# Command: "I spent $25.50 on lunch at a cafe"
Response: {{"actions": [
    {{"intent": "add_expense", "amount": 25.50, "currency": "USD", "category": "Food", "description": "lunch at a cafe"}}
]}}

# Command: "I received my salary of 5,000,000 IDR"
Response: {{"actions": [
    {{"intent": "add_income", "amount": 5000000, "currency": "IDR", "category": "Salary", "description": "Received salary"}}
]}}

# Command: "set a monthly budget of $500 for groceries"
Response: {{"actions": [
    {{"intent": "set_budget", "amount": 500, "currency": "USD", "category": "Groceries", "period": "monthly"}}
]}}

# Command: "log 2 expenses: 15 for coffee and 100 for gas"
Response: {{"actions": [
    {{"intent": "add_expense", "amount": 15, "currency": "USD", "category": "Coffee", "description": "coffee"}},
    {{"intent": "add_expense", "amount": 100, "currency": "USD", "category": "Transportation", "description": "gas"}}
]}}

---
Now, analyze the user's command carefully. Respond with ONLY a valid JSON object.
"""

class FinancialAgent:
    """An agent for managing a user's finances."""

    def __init__(self, ai_model=None, supabase=None):
        self.ai_model = ai_model
        self.supabase = supabase
        self.prompt_builder = FinancialPromptBuilder()

    def process_command(self, user_command: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Main entry point for processing financial commands."""
        if not self.ai_model or not self.supabase:
            return self._error_response("Financial Agent is not properly initialized.")

        try:
            user_id = user_context.get('user_info', {}).get('user_id')
            if not user_id:
                return self._error_response("User ID is required.")

            prompt = self.prompt_builder.build_intent_parser_prompt(user_command)
            ai_response_text = self._make_ai_request_sync(prompt)
            if not ai_response_text:
                return self._error_response("I couldn't understand that. Could you rephrase?")

            parsed_response = json.loads(ai_response_text)
            parsed_actions = parsed_response.get('actions', [])
            if not parsed_actions:
                return self._error_response("I didn't find any financial actions in your request.")

            all_actions = []
            all_responses = []

            for action_details in parsed_actions:
                intent = action_details.get('intent')
                result = {}
                if intent in ['add_expense', 'add_income']:
                    result = self._handle_add_transaction(action_details)
                elif intent == 'set_budget':
                    result = self._handle_set_budget(action_details)

                if result.get('actions'):
                    all_actions.extend(result['actions'])
                if result.get('response'):
                    all_responses.append(result['response'])

            if not all_actions:
                return self._error_response("I understood the request, but failed to create a valid action.")

            final_response = "\\n".join(all_responses)
            return {'success': True, 'actions': all_actions, 'response': final_response}

        except json.JSONDecodeError:
            logger.warning(f"FinancialAgent failed to parse AI response: {ai_response_text}")
            return self._error_response("I had trouble understanding the response from my AI module.")
        except Exception as e:
            logger.exception(f"FinancialAgent processing failed unexpectedly: {e}")
            return self._error_response("An error occurred while processing your financial request.")

    def _handle_add_transaction(self, details: Dict) -> Dict:
        """Handles adding an income or expense transaction."""
        intent = details.get('intent')
        amount = details.get('amount')
        description = details.get('description', 'No description')
        category = details.get('category', 'Uncategorized')

        if not amount:
            return {'actions': [], 'response': f"Skipping action because no amount was specified."}

        action = {
            'type': 'create_financial_transaction',
            'transaction_type': 'expense' if intent == 'add_expense' else 'income',
            'amount': amount,
            'currency': details.get('currency', 'USD'),
            'category': category,
            'description': description
        }

        response_type = "expense" if intent == 'add_expense' else "income"
        response = f"Logged {response_type} of {amount} for '{category}'."

        return {'actions': [action], 'response': response}

    def _handle_set_budget(self, details: Dict) -> Dict:
        """Handles setting a budget."""
        amount = details.get('amount')
        category = details.get('category')
        period = details.get('period')

        if not all([amount, category, period]):
            return {'actions': [], 'response': "Skipping budget because category, amount, or period was missing."}

        action = {
            'type': 'create_or_update_budget',
            'amount': amount,
            'category': category,
            'period': period
        }

        response = f"Set a {period} budget of {amount} for '{category}'."
        return {'actions': [action], 'response': response}

    def _make_ai_request_sync(self, prompt: str) -> Optional[str]:
        """Makes a synchronous request to the AI model."""
        if not self.ai_model:
            return None
        try:
            response = self.ai_model.generate_content(prompt)
            return response.text.strip().replace('```json', '').replace('```', '')
        except Exception as e:
            logger.exception(f"AI request failed in FinancialAgent: {e}")
            return None

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Creates a standardized error response."""
        return {'success': False, 'actions': [], 'response': f"❌ {message}", 'error': message}
