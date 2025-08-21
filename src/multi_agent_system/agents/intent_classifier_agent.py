# src/multi_agent_system/agents/intent_classifier_agent.py (DEFINITIVE VERSION)

from .base_agent import BaseAgent
import database_personal as database
import os
import json

class IntentClassifierAgent(BaseAgent):
    def __init__(self, supabase, ai_model):
        super().__init__(supabase, ai_model, agent_name="IntentClassifierAgent")
        self.comprehensive_prompts = {}

    async def classify_intent(self, user_input, context):
        """Classifies user intent using an AI model."""
        try:
            if not self.comprehensive_prompts:
                self.load_comprehensive_prompts()
            
            system_prompt = self.comprehensive_prompts.get('core_system', "You are an expert at classifying user intent.")
            user_prompt = self._build_classification_prompt(user_input, context)

            # --- DIAGNOSTIC TEST ---
            # This line is added to prove that this new version of the file is running.
            # If you do NOT see this message in your logs, your deployment is not updating.
            print(">>> RUNNING DEFINITIVE VERSION WITH DIAGNOSTIC LOG ...")
            # --- END OF TEST ---

            # --- [THE DEFINITIVE FIX] ---
            # 1. ALWAYS 'await' the call to the AI library.
            response = await self.ai_model.generate_content([system_prompt, user_prompt])
            # 2. The 'response' object itself is NOT awaitable. Get the text directly.
            response_text = response.text
            # --- [END OF FIX] ---
            
            # Log the classification action
            user_id = context.get('user_id')
            if user_id:
                database.log_action(
                    supabase=self.supabase, user_id=user_id, action_type="intent_classified",
                    entity_type="classification", action_details={"result": response_text[:200]},
                    success_status=True
                )
            
            parsed_response = self._parse_ai_response(response_text)
            
            # Sanity check on the AI's confidence
            if parsed_response.get("confidence", 0) < 0.5:
                print("AI confidence is too low. Overriding to ask for clarification.")
                return self._clarification_fallback(user_input)
                
            return parsed_response
            
        except Exception as e:
            print(f"!!! ERROR in IntentClassifierAgent: {e}")
            return self._clarification_fallback(user_input)

    def load_comprehensive_prompts(self):
        """Loads all prompts relative to the project's structure."""
        try:
            prompts_dict = {}
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            v1_dir = os.path.join(project_root, "prompts", "v1")
            
            if os.path.exists(v1_dir):
                for file_name in os.listdir(v1_dir):
                    if file_name.endswith('.md'):
                        prompt_name = file_name.replace('.md', '')
                        file_path = os.path.join(v1_dir, file_name)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prompts_dict[prompt_name] = f.read()
            else:
                print(f"WARNING: Prompts directory not found at {v1_dir}")

            self.comprehensive_prompts = {'core_system': self._build_intent_classifier_system_prompt(prompts_dict)}
            return self.comprehensive_prompts
        except Exception as e:
            print(f"Error loading comprehensive prompts: {e}")
            return {}
    
    def _build_intent_classifier_system_prompt(self, prompts_dict):
        """Builds the system prompt for the Intent Classifier agent."""
        core_identity = prompts_dict.get('00_core_identity', '')
        decision_tree = prompts_dict.get('09_intelligent_decision_tree', '')
        return f"{core_identity}\n\n{decision_tree}"

    def _build_classification_prompt(self, user_input, context):
        """Builds the user part of the prompt for the AI."""
        return f"""
Analyze the following user input and conversation history to determine the user's intent.

**User Input:** "{user_input}"
**Conversation History:** {context.get('history', [])}

**Available Intents:**
- task, reminder, silent_mode, expert, guide, general, information, clarification_needed

**Instructions:**
1. Choose the SINGLE most likely intent.
2. Provide a confidence score from 0.0 to 1.0. If confidence is below 0.5, you MUST choose 'clarification_needed'.
3. Respond ONLY with a valid JSON object in the specified format.

**Required JSON Response Format:**
{{
    "primary_intent": "chosen_intent",
    "secondary_intents": [],
    "confidence": 0.0,
    "reasoning": "Your brief reasoning here."
}}
"""

    def _parse_ai_response(self, response_text: str) -> dict:
        """Safely parses JSON from the AI's raw text response."""
        try:
            json_str = response_text.strip().replace("```json", "").replace("```", "")
            return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError):
            print(f"Failed to parse JSON from AI response: {response_text}")
            return self._clarification_fallback("")

    def _clarification_fallback(self, user_input: str) -> dict:
        """Returns a default response when classification is impossible."""
        return {
            "primary_intent": "clarification_needed",
            "confidence": 0.1,
            "reasoning": "Could not confidently determine intent.",
        }