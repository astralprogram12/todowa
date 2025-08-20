# NEW FILE: intent_classifier_agent.py
# PUT THIS IN: src/multi_agent_system/agents/

from .base_agent import BaseAgent
import json

class IntentClassifierAgent(BaseAgent):
    """AI-powered intent classification agent - replaces keyword matching"""
    
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, "IntentClassifierAgent")
    
    async def classify_intent(self, user_input, context):
        """This is the main method that replaces old keyword matching"""
        classification_prompt = self._build_classification_prompt(user_input, context)
        
        try:
            # Ask AI to classify the intent
            response = self.ai_model.generate_content(classification_prompt)
            return self._parse_ai_response(response.text)
        except Exception as e:
            print(f"Classification error: {e}")
            # Always return a confident guess, never "I don't know"
            return self._confident_fallback(user_input)
    
    def _build_classification_prompt(self, user_input, context):
        """Build the prompt for AI to understand user intent"""
        return f"""
You are an expert at understanding what users want. Analyze this input and make a CONFIDENT decision.

User said: "{user_input}"
Previous conversation: {context.get('history', [])}

AVAILABLE AGENTS:
- task: list, Create, update, complete tasks  
- reminder: Set time alerts
- silent_mode: Manage quiet periods
- expert: Give productivity advice
- guide: Help with app features
- general: Social conversation
- information: Trivial , Fact, Information

RULES:
1. NEVER say "I don't know" - always pick something
2. Confidence must be 0.6 to 1.0 (be confident!)
3. Make smart assumptions about missing details
4. You can pick multiple agents if needed
5, Reminder is always with creation of task if the task didnt exist

Respond ONLY with this JSON format:
{{
    "primary_intent": "agent_name",
    "secondary_intents": ["other_agent"],
    "confidence": 0.85,
    "reasoning": "why you picked this",
    "assumptions": {{"category": "work", "priority": "medium"}}
}}
"""

    def _parse_ai_response(self, response_text):
        """Extract the JSON decision from AI response"""
        try:
            # Find the JSON part in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        except:
            # If parsing fails, make a confident fallback decision
            return self._confident_fallback("")
    
    def _confident_fallback(self, user_input):
        """When AI fails, still make a confident decision (never confusion)"""
        user_lower = user_input.lower()
        
        # Simple smart guesses
        if any(word in user_lower for word in ['remind', 'alert', 'notify', 'at', 'tomorrow']):
            return {
                "primary_intent": "reminder",
                "confidence": 0.7,
                "reasoning": "Detected time/reminder related words",
                "assumptions": {}
            }
        elif any(word in user_lower for word in ['help', 'how', 'what can']):
            return {
                "primary_intent": "guide", 
                "confidence": 0.7,
                "reasoning": "User asking for help",
                "assumptions": {}
            }
        else:
            # When completely unsure, guess task (most common)
            return {
                "primary_intent": "task",
                "confidence": 0.6,
                "reasoning": "Default confident guess - likely wants task help",
                "assumptions": {"category": "general"}
            }