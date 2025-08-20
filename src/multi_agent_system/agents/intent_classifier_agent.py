from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import
import json

class IntentClassifierAgent(BaseAgent):
    """AI-powered agent that classifies user intent and can express uncertainty."""
    
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, "IntentClassifierAgent")
    
    async def classify_intent(self, user_input, context):
        """Classifies user intent using an AI model."""
        classification_prompt = self._build_classification_prompt(user_input, context)
        
        try:
            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([classification_prompt])
            parsed_response = self._parse_ai_response(response.text)
            
            # --- [THE FIX] Sanity Check on Confidence ---
            # If the AI's confidence is too low, override its decision and ask for clarification.
            if parsed_response.get("confidence", 0) < 0.5:
                print("AI confidence is too low. Overriding to ask for clarification.")
                return self._clarification_fallback(user_input)
            # --- [END OF FIX] ---

            return parsed_response

        except Exception as e:
            print(f"Classification error: {e}. Falling back to ask for clarification.")
            return self._clarification_fallback(user_input)
    
    def _build_classification_prompt(self, user_input, context):
        """Builds a robust prompt for the AI to classify user intent."""
        return f"""
You are an expert at understanding user requests. Your job is to analyze the user's input and determine the most appropriate action or agent to handle it.

**User Input:** "{user_input}"
**Conversation History:** {context.get('history', [])}

**Available Intents:**
- **task**: The user wants to create, list, update, or complete a task. (e.g., "add milk to my shopping list", "what do I have to do today?")
- **reminder**: The user wants to set a time-based alert or reminder. (e.g., "remind me to call the doctor at 4pm")
- **silent_mode**: The user wants to manage quiet periods, stopping notifications. (e.g., "go silent for 2 hours", "stop silent mode")
- **expert**: The user is asking for advice, tips, or strategy. (e.g., "what's the best way to organize my projects?")
- **guide**: The user is asking for help about how to use the application. (e.g., "how do I set a reminder?")
- **general**: The user is making small talk or a general conversational statement. (e.g., "hello", "thank you")
- **information**: The user is asking for a specific piece of factual information. (e.g., "what's the capital of France?")
- **clarification_needed**: Use this if you are genuinely unsure what the user wants. It is better to ask for clarification than to guess wrong.

**Instructions:**
1. Choose the SINGLE most likely intent from the list above.
2. Provide a confidence score from 0.0 to 1.0.
3. If your confidence is below 0.5, choose "clarification_needed" instead.
4. Include specific assumptions about what the user might want.

**Required JSON Response Format:**
{{
    "intent": "chosen_intent",
    "confidence": 0.0-1.0,
    "assumptions": {{
        "key": "value",
        "another_key": "another_value"
    }}
}}

Analyze the input and respond with valid JSON only.
"""
    
    def _parse_ai_response(self, response_text):
        """Parse the AI's classification response."""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback parsing
                return {
                    "intent": "general",
                    "confidence": 0.3,
                    "assumptions": {}
                }
        except json.JSONDecodeError:
            return {
                "intent": "clarification_needed",
                "confidence": 0.2,
                "assumptions": {}
            }
    
    def _clarification_fallback(self, user_input):
        """Return a clarification request when intent is unclear."""
        return {
            "intent": "clarification_needed",
            "confidence": 0.0,
            "assumptions": {
                "requires_clarification": True,
                "original_input": user_input
            },
            "message": "I'm not sure what you'd like me to help you with. Could you please be more specific?"
        }
