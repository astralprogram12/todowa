# intent_classifier_agent.py (IMPROVED VERSION)
# This agent can now express uncertainty, leading to a better user experience.
# Located in: src/multi_agent_system/agents/

from .base_agent import BaseAgent
import json

class IntentClassifierAgent(BaseAgent):
    """AI-powered agent that classifies user intent and can express uncertainty."""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "IntentClassifierAgent")
    
    async def classify_intent(self, user_input, context):
        """Classifies user intent using an AI model."""
        classification_prompt = self._build_classification_prompt(user_input, context)
        
        try:
            # Ask AI to classify the intent
            response = self.ai_model.generate_content(classification_prompt)
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
        # --- [THE FIX] Updated prompt with better rules and a new intent ---
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

**Rules for Responding:**
1.  Analyze the user input based on keywords, context, and history.
2.  Your primary goal is accuracy. If confidence is low (below 0.5), you MUST choose 'clarification_needed'.
3.  You can select a primary intent and optional secondary intents if the request is complex (e.g., "remind me to finish the report" is both 'reminder' and 'task').
4.  Your response MUST be ONLY the JSON object, with no other text before or after it.

**JSON Response Format:**
{{
    "primary_intent": "intent_name",
    "secondary_intents": ["optional_intent_name"],
    "confidence": 0.0,
    "reasoning": "A brief explanation of why you chose this intent.",
    "assumptions": {{}}
}}
"""
        # --- [END OF FIX] ---

    def _parse_ai_response(self, response_text):
        """Extracts the JSON decision from the AI's response text."""
        try:
            # Clean the response text to better isolate the JSON
            json_str = response_text.strip().replace("```json", "").replace("```", "")
            return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            print("Failed to parse JSON from AI response. Falling back.")
            return self._clarification_fallback("")
    
    # --- [THE FIX] Replaced "confident_fallback" with "clarification_fallback" ---
    def _clarification_fallback(self, user_input):
        """
        When the AI is unsure or fails, return a response that will trigger
        the orchestrator to ask the user for more information.
        """
        return {
            "primary_intent": "clarification_needed",
            "confidence": 0.1,
            "reasoning": "Could not confidently determine user's intent from the input.",
            "assumptions": {}
        }