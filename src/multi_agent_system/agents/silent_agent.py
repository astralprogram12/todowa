from .base_agent import BaseAgent
import database_personal  # Fix #4: Proper database import

class SilentAgent(BaseAgent):
    def __init__(self, supabase, ai_model):  # Fix #1: Correct constructor
        super().__init__(supabase, ai_model, agent_name="SilentAgent")
        self.agent_type = "silent"

    async def process(self, user_input, context, routing_info=None):
        """
        Process requests that require no response or silent actions.
        routing_info contains assumptions and confidence from IntentClassifierAgent.
        """
        try:
            # Use routing_info assumptions if available
            assumptions = routing_info.get('assumptions', {}) if routing_info else {}
            
            # Fix #3: Load prompts synchronously (no await)
            prompts_dict = self.load_prompts("prompts")
            system_prompt = prompts_dict.get("00_core_identity", "You are a silent agent that provides minimal responses.")
            
            # Add routing info to context if available
            enhanced_context = context.copy()
            if routing_info:
                enhanced_context['routing_info'] = routing_info
                enhanced_context['intent_assumptions'] = assumptions
            
            # Determine if this truly requires silence or acknowledgment
            user_prompt = f"""
User Input: {user_input}
Context: {enhanced_context}

Analyze if this requires:
1. Complete silence (no response)
2. Silent action with acknowledgment
3. Minimal response

If routing assumptions suggest specific silent behavior, follow them confidently.
"""

            # Fix #2: Correct AI model call with array parameter
            response = await self.ai_model.generate_content([
                system_prompt, user_prompt
            ])
            response_text = response.text
            
            # Log the silent action
            user_id = context.get('user_id')
            if user_id:
                database_personal.log_action(
                    supabase=self.supabase,
                    user_id=user_id,
                    action_type="silent_processing",
                    entity_type="silent",
                    action_details={
                        "response_type": "analyzed"
                    },
                    success_status=True
                )
            
            # Determine response type based on analysis
            if "complete silence" in response_text.lower():
                # Return empty response for true silence
                return {
                    "message": "",
                    "actions": ["silent_mode"],
                    "silent": True
                }
            elif "acknowledgment" in response_text.lower():
                return {
                    "message": "👍",
                    "actions": ["silent_acknowledgment"]
                }
            else:
                return {
                    "message": "Understood.",
                    "actions": ["minimal_response"]
                }
                
        except Exception as e:
            # Even errors should be silent for this agent
            return {
                "message": "",
                "actions": ["silent_error"],
                "silent": True
            }
